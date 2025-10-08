// Arduino Convección Natural y Forzada - Versión Refactorizada
// DIKOIN INGENIERIA IT03.2 V2.0.120

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <EEPROM.h>
#include <DallasTemperature.h>
#include <max6675.h>
#include <OneWire.h>
#include <LinxArduinoMega2560.h>
#include <LinxSerialListener.h>
#include <LiquidCrystal_I2C.h>

// --- Pin Definitions ---
#define LCD_ADDR 0x27
#define LCD_COLS 20
#define LCD_ROWS 4
/*#define BACKLIGHT_PIN 3
#define EN_PIN 2
#define RW_PIN 1
#define RS_PIN 0
#define D4_PIN 4
#define D5_PIN 5
#define D6_PIN 6
#define D7_PIN 7*/

const uint8_t PIN_MODE_SEL = 7;
const uint8_t PIN_START_SEL = 10;
const uint8_t PIN_FAN_PWM = 6;
const uint8_t PIN_HEAT_PWM = 9;
const uint8_t PIN_POT_CALENTADOR = A0;
const uint8_t PIN_VEL_AIRE = A3;
const uint8_t PIN_FLOW_ADC = A6;
const uint8_t PIN_POWER_ADC = A7;
const uint8_t PIN_DS18B20_ENTRY = 12;
const uint8_t PIN_DS18B20_EXIT = 2;

OneWire oneWireEntry(PIN_DS18B20_ENTRY);
OneWire oneWireExit(PIN_DS18B20_EXIT);
DallasTemperature sensorEntry(&oneWireEntry);
DallasTemperature sensorExit(&oneWireExit);

const uint8_t TC_SO = 50;
const uint8_t TC_CS = 53;
const uint8_t TC_CLK = 52;
MAX6675 thermocouple(TC_CLK, TC_CS, TC_SO);

LinxArduinoMega2560 *linxDevice;
LiquidCrystal_I2C lcd(LCD_ADDR, LCD_COLS, LCD_ROWS);

byte charCheck[8] = {B00000, B00000, B00001, B00011, B10110, B11100, B01000, B00000};
enum SystemMode
{
  MODE_STOPPED,
  MODE_MANUAL,
  MODE_PC
};
SystemMode currentMode = MODE_STOPPED;

const uint8_t MIN_POT_VALUE = 10;
const uint8_t NUM_READINGS = 10;
char buf[8];

int myCustomCommand_DS18B20(unsigned char numInputBytes, unsigned char *input, unsigned char *numResponseByte, unsigned char *response);

int myCustomCommand_Termopar(unsigned char numInputBytes, unsigned char *input, unsigned char *numResponseBytes, unsigned char *response);

void setupHardware();
void setupLCD();
void displaySplash();
void updateMode();
void handleStopped();
void handleManual();
void handlePC();
float readAverage(uint8_t pin, uint8_t samples);

void setup()
{
  linxDevice = new LinxArduinoMega2560();
  LinxSerialConnection.AttachCustomCommand(0, myCustomCommand_DS18B20);
  LinxSerialConnection.AttachCustomCommand(1, myCustomCommand_Termopar);
  LinxSerialConnection.Start(linxDevice, 0);
  setupHardware();
  setupLCD();

  updateMode();
  if (currentMode == MODE_PC)
  {
    return;
  }
  displaySplash();
}

void loop()
{
  updateMode();
  switch (currentMode)
  {
  case MODE_STOPPED:
    handleStopped();
    break;
  case MODE_MANUAL:
    handleManual();
    break;
  case MODE_PC:
    handlePC();
    break;
  }
}

void setupHardware()
{
  Serial.begin(9600);
  Wire.begin();
  sensorEntry.begin();
  sensorExit.begin();

  // Pines MODE y START con pull-up interna habilitada
  pinMode(PIN_MODE_SEL, INPUT_PULLUP);
  pinMode(PIN_START_SEL, INPUT_PULLUP);
  pinMode(PIN_FAN_PWM, OUTPUT);
  pinMode(PIN_HEAT_PWM, OUTPUT);
}

void setupLCD()
{
  lcd.init();      // init the display
  lcd.backlight(); // turn on the backlight
  lcd.createChar(0, charCheck);
}

void displaySplash()
{
  lcd.clear();

  lcd.setCursor(5, 0);
  lcd.print("CONVECTION");
  lcd.setCursor(1, 1);
  lcd.print("NATURAL AND FORCED");
  lcd.setCursor(7, 2);
  lcd.print("DKT032");

  unsigned long t0 = millis();
  while (millis() - t0 < 1500)
  {
    delay(5);
  }
}

void updateMode()
{
  bool selMode = !digitalRead(PIN_MODE_SEL);
  bool selStart = !digitalRead(PIN_START_SEL);
  if (!selMode && !selStart)
    currentMode = MODE_STOPPED;
  else if (!selMode && selStart)
    currentMode = MODE_MANUAL;
  else if (selMode)
    currentMode = MODE_PC;
}

void handleStopped()
{
  analogWrite(PIN_FAN_PWM, 0);
  analogWrite(PIN_HEAT_PWM, 0);
  lcd.clear();
  lcd.setCursor(1, 0);
  lcd.print("EQUIPMENT STOPPED");

  unsigned long prev = millis();
  while (currentMode == MODE_STOPPED)
  {
    while (analogRead(PIN_FLOW_ADC) > MIN_POT_VALUE || analogRead(PIN_POWER_ADC) > MIN_POT_VALUE)
    {

      updateMode();

      if (currentMode == MODE_PC)
      {
        return;
      }

      if (millis() - prev >= 150)
      {
        prev = millis();
        lcd.setCursor(0, 2);
        lcd.print("SET THE CONTROLS");
        lcd.setCursor(0, 3);
        lcd.print("TO THE MINIMUM");
        lcd.setCursor(19, 3);
        lcd.print('X');
      }
    }

    updateMode();

    if (millis() - prev >= 150)
    {
      prev = millis();

      lcd.setCursor(0, 2);
      lcd.print("SET THE SELECTOR");
      lcd.setCursor(0, 3);
      lcd.print("SWITCH TO ON  ");
      lcd.setCursor(19, 3);
      lcd.write(byte(0));
    }
    if (currentMode == MODE_PC)
    {
      return;
    }
    if (currentMode == MODE_MANUAL)
    {
      lcd.clear();
      lcd.setCursor(4, 1);
      lcd.print("INITIALISING");
      prev = millis();
      while (millis() - prev < 3000)
      {
        delay(5);
      }
    }
  }
}

void handleManual()
{
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("TE ");
  lcd.setCursor(7, 0);
  lcd.print(char(223));
  lcd.print('C');
  lcd.setCursor(11, 0);
  lcd.print("TS ");
  lcd.setCursor(18, 0);
  lcd.print(char(223));
  lcd.print('C');

  lcd.setCursor(0, 1);
  lcd.print("Thermocouple");
  lcd.setCursor(18, 1);
  lcd.print(char(223));
  lcd.print('C');

  lcd.setCursor(0, 2);
  lcd.print("Vel     %");
  lcd.setCursor(17, 2);
  lcd.print("m/s");

  lcd.setCursor(0, 3);
  lcd.print("Pow     %");
  lcd.setCursor(19, 3);
  lcd.print("W");

  while (currentMode == MODE_MANUAL)
  {
    sensorEntry.requestTemperatures();
    float entryTemp = sensorEntry.getTempCByIndex(0);
    sensorExit.requestTemperatures();
    float exitTemp = sensorExit.getTempCByIndex(0);

    dtostrf(entryTemp, 4, 1, buf);
    lcd.setCursor(3, 0);
    lcd.print(buf);
    dtostrf(exitTemp, 4, 1, buf);
    lcd.setCursor(14, 0);
    lcd.print(buf);

    uint8_t fanVal = map(analogRead(PIN_FLOW_ADC), 0, 1023, 0, 255);
    analogWrite(PIN_FAN_PWM, fanVal);
    dtostrf(map(analogRead(PIN_FLOW_ADC), 0, 1023, 0, 100), 3, 0, buf);
    lcd.setCursor(4, 2);
    lcd.print(buf);

    float flowAvg = readAverage(PIN_VEL_AIRE, NUM_READINGS) * 0.00489;
    dtostrf(flowAvg, 4, 1, buf);
    lcd.setCursor(13, 2);
    lcd.print(buf);

    int adcVal = analogRead(PIN_POWER_ADC);
    uint8_t heatVal;
    int heatPct;

    if (adcVal <= 10)
    {
      heatVal = 0; // PWM apagado por debajo del umbral
      heatPct = 0; // Mostrar 0% en la pantalla
    }
    else
    {
      heatVal = map(adcVal, 10, 1023, 140, 255); // Mapeo brusco a partir de >10
      heatPct = map(adcVal, 10, 1023, 0, 100);   // Porcentaje correspondiente
    }

    analogWrite(PIN_HEAT_PWM, heatVal);
    dtostrf(heatPct, 3, 0, buf);
    lcd.setCursor(4, 3);
    lcd.print(buf);

    float powAvg = (readAverage(PIN_POT_CALENTADOR, NUM_READINGS) - 156) / 3.2768;
    dtostrf(powAvg, 3, 0, buf);
    lcd.setCursor(14, 3);
    lcd.print(buf);

    float tcTemp = thermocouple.readCelsius() - 1.3;
    dtostrf(tcTemp, 4, 1, buf);
    lcd.setCursor(14, 1);
    lcd.print(buf);

    delay(150);
    updateMode();
    if (currentMode == MODE_PC)
      return;
  }
}

void sendReadings()
{
  // Obtener lecturas
  float powAvg = (readAverage(PIN_POT_CALENTADOR, NUM_READINGS) - 156) * 0.30517578125;
  sensorEntry.requestTemperatures();
  float entryTemp = sensorEntry.getTempCByIndex(0);
  sensorExit.requestTemperatures();
  float exitTemp = sensorExit.getTempCByIndex(0);
  float tcTemp = thermocouple.readCelsius() - 1.3;
  float flowAvg = readAverage(PIN_VEL_AIRE, NUM_READINGS) * 0.00489;
  

  // Enviar lecturas en el formato especificado
  Serial.print(entryTemp);
  Serial.print('\t');
  Serial.print(exitTemp);
  Serial.print('\t');
  Serial.print(tcTemp);
  Serial.print('\t');
  Serial.print(flowAvg);
  Serial.print('\t');
  Serial.print(powAvg);
  Serial.print('\n');
}

/*void processSerialCommand()
{
  if (Serial.available())
  {
    String command = Serial.readStringUntil('\n'); // Leer comando hasta nueva línea
    command.trim();                                // Eliminar espacios en blanco

    if (command.startsWith("FAN"))
    {
      int fanPWM = command.substring(4).toInt(); // Extraer valor
      analogWrite(PIN_FAN_PWM, fanPWM);
    }
    else if (command.startsWith("HEAT"))
    {
      int heatPWM = command.substring(5).toInt(); // Extraer valor
      analogWrite(PIN_HEAT_PWM, heatPWM);
    }
  }
}*/

void processSerialCommand() {
  if (!Serial.available()) return;

  // Asegura timeouts razonables (p.ej. 20 ms) para no bloquear si falta el EOL
  Serial.setTimeout(20);

  // Intenta leer hasta LF; si LabVIEW usa solo CR, puedes duplicar lectura con '\r'
  String cmd = Serial.readStringUntil('\n');
  if (cmd.length() == 0) {
    // Intento alternativo por si el EOL fuese solo '\r'
    cmd = Serial.readStringUntil('\r');
    if (cmd.length() == 0) return;  // no hay línea completa aún
  }

  cmd.trim();           // quita espacios y \r/\n de extremos
  cmd.toUpperCase();    // tolera minúsculas

  int fan  = -1;
  int heat = -1;

  // Función lambda para extraer exactamente 3 chars tras una etiqueta,
  // quitar espacios y convertir a int con límites 0..255.
  auto parseField3 = [](const String& s, int posAfterTag) -> int {
    if (posAfterTag < 0 || posAfterTag + 3 > s.length()) return -1;
    String field = s.substring(posAfterTag, posAfterTag + 3); // exactamente 3 chars
    // Elimina espacios dentro del campo (leading/trailing o en medio)
    for (int i = field.length() - 1; i >= 0; --i) {
      if (field[i] == ' ') field.remove(i, 1);
    }
    if (field.length() == 0) return -1;           // estaba todo en espacios
    long v = field.toInt();                        // "7", "42", "255"
    if (v < 0)   v = 0;
    if (v > 255) v = 255;
    return (int)v;
  };

  // --- FAN ---
  int i = cmd.indexOf("FAN");
  if (i >= 0) {
    fan = parseField3(cmd, i + 3);
  }

  // --- HEAT ---
  i = cmd.indexOf("HEAT");
  if (i >= 0) {
    heat = parseField3(cmd, i + 4);
  }

  if (fan  >= 0)  analogWrite(PIN_FAN_PWM,  fan);
  if (heat >= 0)  analogWrite(PIN_HEAT_PWM, heat);
}


void handlePC()
{
  lcd.clear();
  lcd.setCursor(5, 1);
  lcd.print("CONTROL PC");
  while (currentMode == MODE_PC)
  {
    sendReadings();         // Enviar lecturas al PC
    processSerialCommand(); // Procesar comandos del PC
    updateMode();           // Verificar si el modo cambia
    delay(150);             // Esperar un poco antes de la siguiente iteración
  }
}

float readAverage(uint8_t pin, uint8_t samples)
{
  long sum = 0;
  for (uint8_t i = 0; i < samples; i++)
  {
    sum += analogRead(pin);
    delay(5);
  }
  return sum / (float)samples;
}

// DS18B20: devuelve 2 floats (TE, TS)
int myCustomCommand_DS18B20(unsigned char numInputBytes, unsigned char *input, unsigned char *numResponseBytes, unsigned char *response)
{
  delay(150);
  sensorEntry.requestTemperatures();
  float entryTemp = sensorEntry.getTempCByIndex(0);
  sensorExit.requestTemperatures();
  float exitTemp = sensorExit.getTempCByIndex(0);

  // Empaquetar en little-endian
  memcpy(response + 0, &entryTemp, sizeof(float));
  memcpy(response + 4, &exitTemp, sizeof(float));

  *numResponseBytes = 8; // 2 floats
  return 0;              // L_OK
}

// MAX6675: devuelve 1 float (termopar)
int myCustomCommand_Termopar(unsigned char numInputBytes, unsigned char *input, unsigned char *numResponseBytes, unsigned char *response)
{
  delay(150);
  float tcTemp = thermocouple.readCelsius() - 1.3f;

  memcpy(response, &tcTemp, sizeof(float)); // 4 bytes
  *numResponseBytes = 4;
  return 0; // L_OK
}
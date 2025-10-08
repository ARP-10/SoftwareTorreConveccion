import serial
import serial.tools.list_ports
import time
import numpy as np
import sys

BAUD = 9600
COM_TIMEOUT = 1.0
READ_DELAY = 0.5
CALIBRATION_SAMPLES = 10

def detectar_puerto():
    """Detecta automáticamente el puerto COM donde está conectado el equipo."""
    print("🔍 Buscando puerto del equipo IT03.2...")
    puertos = serial.tools.list_ports.comports()
    if not puertos:
        print("❌ No se encontraron puertos disponibles.")
        return None

    for p in puertos:
        try:
            print(f"→ Probando {p.device} ...")
            with serial.Serial(p.device, BAUD, timeout=COM_TIMEOUT) as s:
                time.sleep(2)  # Espera a que el Arduino reinicie y empiece a enviar
                for _ in range(10):  # lee hasta 10 líneas
                    line = s.readline().decode(errors="ignore").strip()
                    if not line:
                        continue
                    parts = line.split("\t")
                    # Se espera 5 valores numéricos separados por tab
                    if len(parts) == 5:
                        try:
                            floats = list(map(float, parts))
                            print(f"✅ Equipo detectado en {p.device}: {floats}")
                            return p.device
                        except ValueError:
                            continue
        except Exception as e:
            print(f"⚠️ {p.device} no válido ({e})")

    print("⚠️ No se detectó automáticamente. Usa --port COMx si conoces el puerto.")
    return None

def leer_linea(ser):
    try:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            return None
        parts = line.split("\t")
        if len(parts) != 5:
            return None
        vals = list(map(float, parts))
        vals[0], vals[1] = vals[1], vals[0]
        return vals
    except Exception as e:
        print(f"⚠️ Error leyendo línea: {e}")
        return None


def calibrar_sensores(ser):
    """Lee varias muestras iniciales y calcula los promedios como offsets."""
    print("🧭 Calibrando sensores... espere unos segundos.")
    muestras = []
    for i in range(10):  # número de muestras
        valores = leer_linea(ser)
        if valores:
            muestras.append(valores)
            print(f"  Muestra {i+1}/10: {valores}")
        time.sleep(READ_DELAY)

    if not muestras:
        print("❌ No se recibieron datos durante la calibración.")
        return [0, 0, 0, 0, 0]

    arr = np.array(muestras)
    offsets = np.mean(arr, axis=0)
    print("\n✅ Calibración completada.")
    print(f"Offsets calculados: {offsets}\n")
    return offsets

def enviar_comando(ser, tipo, valor):
    """Envía un comando FAN o HEAT al microcontrolador."""
    try:
        # Asegurarse de que el valor está entre 0 y 255
        valor = int(max(0, min(255, valor)))
        # Construir el comando con formato: FAN000 o HEAT255
        cmd = f"{tipo.upper()}{valor:03d}\n"
        ser.write(cmd.encode())
        ser.flush()
        print(f"→ Enviado: {cmd.strip()}")
    except Exception as e:
        print(f"⚠️ Error enviando comando {tipo}: {e}")


def main():
    port = detectar_puerto()
    if not port:
        return None

    ser = None
    try:
        ser = serial.Serial(port, BAUD, timeout=COM_TIMEOUT)
        offsets = calibrar_sensores(ser)
        t_read = threading.Thread(target=hilo_lectura, args=(ser, offsets), daemon=True)
        t_read.start()
        hilo_comandos(ser)
    except KeyboardInterrupt:
        print("\n🟥 Programa interrumpido manualmente.")
    finally:
        if ser and ser.is_open:
            print("\n🟡 Cerrando puerto serial...")
            ser.close()
            time.sleep(1)
        print("✅ Programa finalizado correctamente.")


if __name__ == "__main__":
    main()

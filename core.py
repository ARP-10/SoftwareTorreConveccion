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
    print("🔍 Buscando puerto del equipo IT03.2...")
    puertos = serial.tools.list_ports.comports()
    if not puertos:
        print("❌ No se encontraron puertos disponibles.")
        return None

    for p in puertos:
        try:
            print(f"→ Probando {p.device} ...")
            with serial.Serial(p.device, BAUD, timeout=COM_TIMEOUT) as s:
                time.sleep(2)
                for _ in range(10):
                    line = s.readline().decode(errors="ignore").strip()
                    if not line:
                        continue

                    parts = line.split("\t")

                    # Tu formato tiene exactamente 12 campos
                    if len(parts) == 12:
                        try:
                            float(parts[3])
                            float(parts[5])
                            float(parts[7])
                            float(parts[9])
                            float(parts[11])
                            print(f"✅ Equipo detectado en {p.device}")
                            return p.device
                        except:
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

        # Deben llegar 12 campos exactos
        if len(parts) != 12:
            return None

        # Extraer los 5 valores numéricos en orden correcto:
        # T.entrada → parts[3]
        # T.salida  → parts[5]
        # Termopar  → parts[7]
        # V.aire    → parts[9]
        # Potencia  → parts[11]
        try:
            te = float(parts[3])
            ts = float(parts[5])
            tc = float(parts[7])
            vel = float(parts[9])
            pot = float(parts[11])
            return [te, ts, tc, vel, pot]
        except:
            return None

    except Exception as e:
        print(f"⚠️ Error leyendo línea: {e}")
        return None


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

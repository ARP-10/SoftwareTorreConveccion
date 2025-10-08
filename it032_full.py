# IT 03.2 – Python Version (reemplazo de LabVIEW)
# -----------------------------------------------
# Simula el comportamiento del software original en LabVIEW:
# - Detección de puerto COM automáticamente
# - Calibración de sensores (promedios iniciales)
# - Lectura continua de los 5 valores enviados por el microcontrolador
# - Aplicación de offsets de calibración
# - Envío de comandos FAN### y HEAT### al equipo


import serial
import serial.tools.list_ports
import time
import numpy as np
import threading
import sys

BAUD = 9600
CALIBRATION_SAMPLES = 10
READ_DELAY = 0.5  # segundos
COM_TIMEOUT = 1.0


# ---------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------
def detectar_puerto():
    """Intenta detectar automáticamente el puerto correcto."""
    print("🔍 Buscando puerto del equipo IT03.2...")
    puertos = serial.tools.list_ports.comports()
    if not puertos:
        print("❌ No se encontraron puertos disponibles.")
        return None

    for p in puertos:
        try:
            with serial.Serial(p.device, BAUD, timeout=COM_TIMEOUT) as s:
                line = s.readline().decode(errors="ignore").strip()
                if line.count("\t") == 4:  # Debe tener 5 valores separados por tab
                    print(f"✅ Equipo detectado en {p.device}")
                    return p.device
        except Exception:
            pass

    print("⚠️ No se detectó automáticamente. Usa --port COMx si conoces el puerto.")
    return None


def leer_linea(ser):
    """Lee una línea del puerto serie y devuelve 5 floats."""
    try:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            return None
        parts = line.split("\t")
        if len(parts) != 5:
            return None
        return list(map(float, parts))
    except Exception:
        return None


def calibrar_sensores(ser):
    """Lee varias muestras iniciales y calcula los promedios (offsets)."""
    print("🧭 Calibrando sensores... espere unos segundos.")
    muestras = []
    for i in range(CALIBRATION_SAMPLES):
        valores = leer_linea(ser)
        if valores:
            muestras.append(valores)
            print(f"  Muestra {i+1}/{CALIBRATION_SAMPLES}: {valores}")
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
    valor = int(max(0, min(255, valor)))
    cmd = f"{tipo.upper()}{valor:03d}\n"
    ser.write(cmd.encode())
    ser.flush()
    print(f"→ Enviado: {cmd.strip()}")


# ---------------------------------------------------------
# HILOS DE EJECUCIÓN
# ---------------------------------------------------------
def hilo_lectura(ser, offsets):
    """Lee continuamente los datos y los muestra aplicando los offsets."""
    print("📡 Iniciando lectura continua (Ctrl+C para detener)...\n")
    while True:
        valores = leer_linea(ser)
        if not valores:
            continue

        corregidos = [v - o for v, o in zip(valores, offsets)]
        te, ts, tc, vel, pot = corregidos
        hora = time.strftime("%H:%M:%S", time.localtime())
        print(
            f"[{hora}] TE={te:6.2f} °C | TS={ts:6.2f} °C | TC={tc:6.2f} °C | "
            f"Vel={vel:5.2f} m/s | P={pot:7.2f} W",
            end="\r"
        )
        time.sleep(READ_DELAY)


def hilo_comandos(ser):
    """Permite enviar comandos FAN/HEAT manualmente."""
    print("\n🕹️ Introduce comandos: 'fan <0-255>' o 'heat <0-255>' (exit para salir)")
    while True:
        try:
            cmd = input("> ").strip().lower()
        except EOFError:
            break
        if cmd in ("exit", "quit"):
            print("🚪 Saliendo...")
            ser.close()
            sys.exit(0)
        if cmd.startswith("fan "):
            try:
                v = int(cmd.split()[1])
                enviar_comando(ser, "FAN", v)
            except:
                print("Uso: fan <0-255>")
        elif cmd.startswith("heat "):
            try:
                v = int(cmd.split()[1])
                enviar_comando(ser, "HEAT", v)
            except:
                print("Uso: heat <0-255>")
        else:
            print("Comandos válidos: 'fan <n>', 'heat <n>', 'exit'.")


# ---------------------------------------------------------
# PROGRAMA PRINCIPAL
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# EJECUCIÓN DEL PROGRAMA
# ---------------------------------------------------------
if __name__ == "__main__":
    main()

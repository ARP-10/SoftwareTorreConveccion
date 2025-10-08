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

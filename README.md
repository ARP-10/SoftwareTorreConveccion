# 🧠 IT 03.2 – Transferencia de Calor por Convección Natural y Forzada

## Software de control y adquisición de datos (versión Python + PyQt6)

Desarrollado para el equipo IT 03.2 – Convección Natural y Forzada (DIKOIN Ingeniería).
Este programa permite comunicar, controlar y visualizar en tiempo real los parámetros del equipo a través del puerto USB.

---

## 📦 Características principales

- ✅ Comunicación automática con el microcontrolador (Arduino Mega 2560) mediante puerto serie USB.
- ✅ Detección automática del puerto COM.
- ✅ Lectura en tiempo real de 5 variables físicas:
     - Temperatura de entrada (TE)
     - Temperatura de salida (TS)
     - Termopar (TC)
     - Velocidad del aire (m/s)
     - Potencia eléctrica (W)
- ✅ Control remoto del sistema:
    - Ventilador (FAN)
    - Calefactor (HEAT)
- ✅ Gráfica en tiempo real con PyQtGraph.
- ✅ Registro manual de datos y exportación a Excel (.xlsx) o CSV.
- ✅ Gestión de idioma (ES / EN).
- ✅ Sistema de validación de licencia integrado.
- ✅ Verificación opcional de equipo y versión mediante API remota.
- ✅ Interfaz gráfica moderna desarrollada con PyQt6.
- ✅ Compatible con Windows 10 y Windows 11 (64 bits).
- ✅ Funciona tanto como script Python como ejecutable (.exe).

---

## 🔐 Sistema de licencias

El software incorpora un sistema de validación de licencia local, basado en:

- Número de serie detectado desde el equipo.
- Arhivo de licencia (<serial>.lic).
- Firma y validación criptográfica interna.

Comportamiento:

- Si no se encuentra una licencia válida, el usuario deberá seleccionar manualmente el archivo de licencia.
- La ruta seleccionada se guarda automáticamente para futuras ejecuciones.

- Sin licencia válida:

  - El software no permite iniciar mediciones ni controlar el equipo.
  - Se muestra un mensaje de error y el programa se cierra de forma segura.


---

## 🗂️ Estructura del proyecto
    it032_gui.py        # Interfaz gráfica (PyQt6 + PyQtGraph)
    core.py       # Lógica de comunicación y calibración
    style.qss
    translations.json #Textos multi-idioma
    icons/
    README.md           # Este archivo
    dist/
        it032_gui.exe   # Ejecutable compilado con PyInstaller

## 💻 Ejecución del programa

Desde la carpeta del proyecto:

python it032_gui.py


O ejecuta directamente el archivo compilado (si está disponible):

dist/it032_gui.exe

---
## 🧩 Recomendaciones

No desconectes el equipo mientras el programa esté recibiendo datos.

Mantén el baudrate definido en it032_core.py (9600 por defecto).

Si no detecta el equipo automáticamente, puedes comprobar el puerto COM en el Administrador de dispositivos.

## 👷 Créditos

**Desarrollado por:** Alejandra Rodríguez  
**Departamento Técnico – DIKOIN Ingeniería**  
**Versión:** 2.0.120  
**Referencia:** Arduino Firmware DKT032

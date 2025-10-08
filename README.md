# 🧠 IT 03.2 – Transferencia de Calor por Convección Natural y Forzada

## Software de control y adquisición de datos (versión Python + PyQt6)

Desarrollado para el equipo IT 03.2 – Convección Natural y Forzada (DIKOIN Ingeniería).
Este programa permite comunicar, controlar y visualizar en tiempo real los parámetros del equipo a través del puerto USB.

---

## 📦 Características principales

- ✅ Comunicación directa con el microcontrolador (Arduino Mega 2560) mediante puerto serie.
- ✅ Lectura y registro de 5 variables en tiempo real:
  - Temperatura de entrada (TE)
  - Temperatura de salida (TS)
  - Termopar (TC)
  - Velocidad del aire (m/s)
  - Potencia eléctrica (W)
- ✅ Control remoto del ventilador (FAN) y el calefactor (HEAT) desde la interfaz.
- ✅ Gráfica en tiempo real con PyQtGraph.
- ✅ Interfaz moderna e intuitiva desarrollada con PyQt6.
- ✅ Compatible con Windows 10 y Windows 11 (32/64 bits).
- ✅ Preparado para futura integración con servidor remoto (actualizaciones / prácticas online).


---

## 🧰 Requisitos de instalación

Asegúrate de tener Python 3.10 o superior instalado.
Luego instala las dependencias necesarias ejecutando en consola:

python -m pip install -r requirements.txt


Si no tienes el archivo requirements.txt, puedes instalar manualmente:

python -m pip install pyserial PyQt6 pyqtgraph

---

## 🗂️ Estructura del proyecto
    it032_gui.py        # Interfaz gráfica (PyQt6 + PyQtGraph)
    it032_core.py       # Lógica de comunicación y calibración
    icon.ico            # Icono del programa (opcional)
    README.md           # Este archivo
    dist/
        it032_gui.exe   # Ejecutable compilado con PyInstaller

## 💻 Ejecución del programa

Desde la carpeta del proyecto:

python it032_gui.py


O ejecuta directamente el archivo compilado (si está disponible):

dist/it032_gui.exe

---

## 🔌 Conexión y uso

1. Conecta el equipo **IT 03.2** al ordenador mediante cable USB.
2. Asegúrate de que el equipo esté en modo **PC** (selector físico).
3. Ejecuta el programa y pulsa **“Conectar”**.
4. Pulsa **“Iniciar”** para comenzar a recibir datos.
5. Controla el ventilador y el calefactor desde los controles de la derecha.
6. Observa en la gráfica y en las etiquetas las variables en tiempo real.
7. Pulsa **“Detener”** o **“Salir”** para cerrar la sesión de medición.

---

## 🧪 Calibración

Antes de iniciar una práctica, puedes usar el botón **“Calibrar”**:  
Esto toma muestras iniciales y aplica *offsets* para mejorar la estabilidad de lectura de los sensores.

---
## 🧱 Compilación a ejecutable (.exe)

Para generar el archivo ejecutable (sin necesidad de Python instalado):

Instala PyInstaller:

python -m pip install pyinstaller


Desde la carpeta del proyecto:

pyinstaller --noconfirm --onefile --windowed --icon=icon.ico it032_gui.py


El ejecutable aparecerá en:

dist/it032_gui.exe

## 🧩 Recomendaciones

No desconectes el equipo mientras el programa esté recibiendo datos.

Mantén el baudrate definido en it032_core.py (9600 por defecto).

Si no detecta el equipo automáticamente, puedes comprobar el puerto COM en el Administrador de dispositivos.

## 👷 Créditos

**Desarrollado por:** Alejandra Rodríguez  
**Departamento Técnico – DIKOIN Ingeniería**  
**Versión:** 2.0.120  
**Referencia:** Arduino Firmware DKT032

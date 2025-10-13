# it032_gui.py - versión con ruleta (fan), calefactor estilizado, gráfica con leyenda lateral y guardado de datos
# -------------------------------------------------------

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QGroupBox,
    QDial,
    QMessageBox,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QCheckBox,
    QFrame,
    QHeaderView,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon
import sys
import time
import pyqtgraph as pg
import it032_core as core
import pandas as pd
import json


# =======================================================
# Lectura de datos del equipo
# =======================================================
class ReaderThread(QThread):
    new_data = pyqtSignal(float, float, float, float, float)

    def __init__(self, ser, offsets):
        super().__init__()

        self.ser = ser
        self.offsets = offsets
        self._running = True

    def run(self):
        while self._running:
            valores = core.leer_linea(self.ser)
            if not valores:
                continue
            corregidos = [v - o for v, o in zip(valores, self.offsets)]
            te, ts, tc, vel, pot = corregidos
            self.new_data.emit(te, ts, tc, vel, pot)
            time.sleep(core.READ_DELAY)

    def stop(self):
        self._running = False


# =======================================================
# Ventana principal
# =======================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # --- Cargar traducciones ---
        with open("translations.json", "r", encoding="utf-8") as f:
            self.translations = json.load(f)

        self.current_lang = "en"  # idioma por defecto (puedes poner "es")

        self.setWindowTitle("IT 03.2 - Convección Natural y Forzada (DIKOIN)")
        self.setWindowIcon(
            QIcon(
                r"C:\Users\dikoi\Desktop\Alejandra\SoftwareTorreConveccion\fotos\dikoin_logo.jpg"
            )
        )

        self.resize(1500, 750)

        self.ser = None
        self.offsets = [0, 0, 0, 0, 0]
        self.reader_thread = None
        self.data_records = []

        font_title = QFont("Segoe UI", 14, QFont.Weight.Bold)
        font_value = QFont("Segoe UI", 12)

        # =======================================================
        # 📊 SECCIÓN: MEDIDAS EN TIEMPO REAL
        # =======================================================
        self.group_lecturas = QGroupBox("📊 Real-time measurements")
        self.group_lecturas.setFont(font_title)

        self.lbl_te = QLabel("Inlet (IT): 0.00 °C")
        self.lbl_ts = QLabel("Outlet (OT): 0.00 °C")
        self.lbl_tc = QLabel("Thermocouple (TC): 0.00 °C")
        self.lbl_vel = QLabel("Air velocity: 0.00 m/s")
        self.lbl_pot = QLabel("Power: 0.00 W")

        for lbl in [self.lbl_te, self.lbl_ts, self.lbl_tc, self.lbl_vel, self.lbl_pot]:
            lbl.setFont(font_value)
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)

        v_lecturas = QVBoxLayout()
        for lbl in [self.lbl_te, self.lbl_ts, self.lbl_tc, self.lbl_vel, self.lbl_pot]:
            v_lecturas.addWidget(lbl)
        self.group_lecturas.setLayout(v_lecturas)

        # =======================================================
        # ⚙️ SECCIÓN: CONTROL DEL EQUIPO
        # =======================================================
        self.group_control = QGroupBox("⚙️ Equipment Control")
        self.group_control.setFont(font_title)

        # Ventilador
        self.dial_fan = QDial()
        self.dial_fan.setRange(0, 255)
        self.dial_fan.setNotchesVisible(True)
        self.dial_fan.setFixedSize(180, 180)
        self.dial_fan.setWrapping(False)
        self.lbl_fan = QLabel("Fan (FAN): 0 %")
        font_small = QFont("Verdana", 11)
        self.lbl_fan.setFont(font_small)
        self.lbl_fan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dial_fan.valueChanged.connect(
            lambda v: self.lbl_fan.setText(f"Fan (FAN): {int(v/2.55):3d} %")
        )
        self.dial_fan.valueChanged.connect(
            lambda v: core.enviar_comando(self.ser, "FAN", v) if self.ser else None
        )
        v_fan = QVBoxLayout()
        v_fan.addWidget(self.lbl_fan)
        v_fan.addWidget(self.dial_fan, alignment=Qt.AlignmentFlag.AlignCenter)

        # Calefactor
        self.slider_heat = QSlider(Qt.Orientation.Vertical)
        self.slider_heat.setRange(0, 255)
        self.slider_heat.setFixedSize(90, 180)
        self.lbl_heat = QLabel("Heater (HEAT): 0 %")
        self.lbl_heat.setFont(font_small)
        self.lbl_heat.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider_heat.setStyleSheet(
            """
            QSlider::groove:vertical {
                width: 40px;
                border-radius: 10px;
                margin: 10px 0;
                background: qlineargradient(
                    x1:0, y1:1, x2:0, y2:0,
                    stop:0 #80D8FF,
                    stop:1 #007EB8
                );
            }
            QSlider::handle:vertical {
                background: #fff;
                border: 2px solid #007EB8;
                height: 22px;
                margin: -4px -14px;
                border-radius: 10px;
            }
        """
        )
        self.slider_heat.valueChanged.connect(
            lambda v: self.lbl_heat.setText(f"Heater (HEAT): {int(v/2.55):3d} %")
        )
        self.slider_heat.valueChanged.connect(
            lambda v: core.enviar_comando(self.ser, "HEAT", v) if self.ser else None
        )
        v_heat = QVBoxLayout()
        v_heat.addWidget(self.lbl_heat)
        v_heat.addWidget(self.slider_heat, alignment=Qt.AlignmentFlag.AlignCenter)

        h_control = QHBoxLayout()
        h_control.addLayout(v_fan)
        h_control.addLayout(v_heat)
        self.group_control.setLayout(h_control)

        # =======================================================
        # ⏱️ Temporizador para enviar comandos periódicos
        # =======================================================
        self.timer_comandos = QTimer()
        self.timer_comandos.setInterval(500)  # 500 ms
        self.timer_comandos.timeout.connect(self.enviar_comandos_periodicos)
        self.timer_comandos.start()

        # =======================================================
        # 📈 SECCIÓN: GRÁFICA EN TIEMPO REAL
        # =======================================================
        self.group_grafica = QGroupBox("📈 Real-Time Graph")
        self.group_grafica.setFont(font_title)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#FFFFFF")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("left", "Valor", color="#000000")
        self.plot_widget.setLabel("bottom", "Tiempo (s)", color="#000000")

        self.curve_te = self.plot_widget.plot(
            pen=pg.mkPen("#E74C3C", width=2), name="IT (Inlet)"
        )
        self.curve_ts = self.plot_widget.plot(
            pen=pg.mkPen("#3498DB", width=2), name="OT (Outlet)"
        )
        self.curve_tc = self.plot_widget.plot(
            pen=pg.mkPen("#27AE60", width=2), name="TC (Thermocouple)"
        )
        self.curve_vel = self.plot_widget.plot(
            pen=pg.mkPen("#F39C12", style=Qt.PenStyle.DotLine, width=2),
            name="Air Velocity",
        )
        self.curve_pot = self.plot_widget.plot(
            pen=pg.mkPen("#8E44AD", style=Qt.PenStyle.DashLine, width=2),
            name="Power",
        )

        # === Checkboxes con color y visibilidad ===
        def color_box(color):
            frame = QFrame()
            frame.setFixedSize(14, 14)
            frame.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
            return frame

        self.chk_te = QCheckBox("Inlet (IT)")
        self.chk_ts = QCheckBox("Outlet (OT)")
        self.chk_tc = QCheckBox("Thermocouple (TC)")
        self.chk_vel = QCheckBox("Air Velocity (m/s)")
        self.chk_pot = QCheckBox("Power (W)")

        for chk in [self.chk_te, self.chk_ts, self.chk_tc, self.chk_vel, self.chk_pot]:
            chk.setChecked(True)
            chk.setStyleSheet("color: #000000; font-size: 13px; font-weight: 500;")

        self.chk_te.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_ts.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_tc.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_vel.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_pot.stateChanged.connect(self.toggle_curve_visibility)

        # === Leyenda lateral compacta ===
        v_legend = QVBoxLayout()
        v_legend.setSpacing(2)  # menos espacio vertical entre filas
        v_legend.setContentsMargins(0, 0, 0, 0)

        for color, chk in zip(
            ["#E74C3C", "#3498DB", "#27AE60", "#F39C12", "#8E44AD"],
            [self.chk_te, self.chk_ts, self.chk_tc, self.chk_vel, self.chk_pot],
        ):
            row = QHBoxLayout()
            row.setSpacing(3)  # menos separación horizontal entre color y texto
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(color_box(color))
            row.addWidget(chk)
            v_legend.addLayout(row)

        # Contenedor de la leyenda (alineado arriba y ancho fijo)
        legend_widget = QWidget()
        legend_widget.setLayout(v_legend)
        legend_widget.setFixedWidth(200)
        legend_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # === Gráfica + leyenda lado a lado ===
        h_graf = QHBoxLayout()
        h_graf.setContentsMargins(10, 0, 0, 0)
        h_graf.setSpacing(5)  # pequeño espacio entre gráfica y leyenda
        h_graf.addWidget(self.plot_widget, stretch=1)
        h_graf.addWidget(legend_widget, alignment=Qt.AlignmentFlag.AlignTop)
        self.group_grafica.setLayout(h_graf)

        # =======================================================
        # 🧮 TABLA DE RESULTADOS + EXPORTACIÓN
        # =======================================================
        self.group_tabla = QGroupBox("📋 Practice Results")
        self.group_tabla.setFont(font_title)
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            [
                "#",
                "Date",
                "Time",
                "IT (°C)",
                "OT (°C)",
                "TC (°C)",
                "Vel (m/s)",
                "Pow (W)",
            ]
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # 🔹 Forzar columna # más estrecha
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 25)
        header.setMinimumSectionSize(10)
        header.setStretchLastSection(False)

        # 🔹 Resto de columnas elásticas
        for i in range(1, self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            """
            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #FFFFFF;
                gridline-color: #CCCCCC;
                color: #000000;
                selection-background-color: #E6F4FB;
                selection-color: #000000;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #007EB8;
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid #CCCCCC;
                padding: 4px;
            }
        """
        )

        self.btn_export = QPushButton("📗 Export to Excel")
        self.btn_export.setFixedWidth(180)
        self.btn_export.clicked.connect(self.export_excel)

        v_tabla = QVBoxLayout()
        v_tabla.addWidget(self.table)
        v_tabla.addWidget(self.btn_export)
        self.group_tabla.setLayout(v_tabla)

        # =======================================================
        # BOTONES GENERALES
        # =======================================================
        self.btn_conectar = QPushButton("🔌 Connect")
        self.btn_calibrar = QPushButton("🧭 Calibrate")
        self.btn_iniciar = QPushButton("▶️ Start")
        self.btn_detener = QPushButton("⏹️ Stop")
        self.btn_guardar = QPushButton("💾 Save Data")
        self.btn_salir = QPushButton("🚪 Exit")

        h_botones = QHBoxLayout()
        for b in [
            self.btn_conectar,
            self.btn_calibrar,
            self.btn_iniciar,
            self.btn_detener,
            self.btn_guardar,
            self.btn_salir,
        ]:
            b.setFixedHeight(32)
            h_botones.addWidget(b)

        # =======================================================
        # LAYOUT GENERAL
        # =======================================================
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.group_lecturas, 1)
        top_layout.addWidget(self.group_control, 1)

        left_layout = QVBoxLayout()
        left_layout.addLayout(top_layout)
        left_layout.addWidget(self.group_grafica)
        left_layout.addLayout(h_botones)

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout, 3)
        main_layout.addWidget(self.group_tabla, 2)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # === Menú de idioma ===
        menu_bar = self.menuBar()
        menu_language = menu_bar.addMenu("🌐 Language")

        action_en = menu_language.addAction("English")
        action_es = menu_language.addAction("Español")

        action_en.triggered.connect(lambda: self.set_language("en"))
        action_es.triggered.connect(lambda: self.set_language("es"))

        # =======================================================
        # CONEXIONES
        # =======================================================
        self.btn_conectar.clicked.connect(self.conectar)
        self.btn_calibrar.clicked.connect(self.calibrar)
        self.btn_iniciar.clicked.connect(self.iniciar_lectura)
        self.btn_detener.clicked.connect(self.detener_lectura)
        self.btn_guardar.clicked.connect(self.guardar_dato)
        self.btn_export.clicked.connect(self.export_excel)
        self.btn_salir.clicked.connect(self.cerrar_programa)

        # Variables de datos
        (
            self.data_x,
            self.data_te,
            self.data_ts,
            self.data_tc,
            self.data_vel,
            self.data_pot,
        ) = ([], [], [], [], [], [])
        self.t0 = time.time()

        self.set_language(self.current_lang)

    # =======================================================
    # FUNCIONES DE GUARDADO Y EXPORTACIÓN
    # =======================================================
    def guardar_dato(self):
        try:
            from datetime import datetime

            now = datetime.now()
            fecha = now.strftime("%d/%m/%Y")
            hora = now.strftime("%H:%M:%S")

            te = float(self.lbl_te.text().split(":")[1].replace("°C", "").strip())
            ts = float(self.lbl_ts.text().split(":")[1].replace("°C", "").strip())
            tc = float(self.lbl_tc.text().split(":")[1].replace("°C", "").strip())
            vel = float(self.lbl_vel.text().split(":")[1].replace("m/s", "").strip())
            pot = float(self.lbl_pot.text().split(":")[1].replace("W", "").strip())

            # Guardar también fecha y hora en data_records
            self.data_records.append([fecha, hora, te, ts, tc, vel, pot])

            # Actualizar tabla en pantalla
            self.table.setRowCount(len(self.data_records))
            i = len(self.data_records) - 1
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(fecha))
            self.table.setItem(i, 2, QTableWidgetItem(hora))
            for j, val in enumerate([te, ts, tc, vel, pot]):
                self.table.setItem(i, j + 3, QTableWidgetItem(f"{val:.2f}"))

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not save the data: {e}")

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel", "", "Excel Files (*.xlsx)"
        )
        if path:
            df = pd.DataFrame(
                self.data_records,
                columns=[
                    "Date",
                    "Time",
                    "IT (°C)",
                    "OT (°C)",
                    "TC (°C)",
                    "Vel (m/s)",
                    "Pow (W)",
                ],
            )

            df.index = df.index + 1
            df.index.name = "#"
            df.to_excel(path)
            QMessageBox.information(self, "Export", "Excel file saved successfully.")

    # =======================================================
    # FUNCIONES PRINCIPALES
    # =======================================================
    def conectar(self):
        port = core.detectar_puerto()
        if not port:
            QMessageBox.warning(
                self, "Connection Failed", "The device was not detected via USB."
            )
            return
        self.ser = core.serial.Serial(port, core.BAUD, timeout=core.COM_TIMEOUT)
        QMessageBox.information(self, "Connected", f"Device detected on {port}")

    def calibrar(self):
        if not self.ser:
            QMessageBox.warning(self, "Error", "You must connect the device first.")
            return
        self.offsets = core.calibrar_sensores(self.ser)
        QMessageBox.information(
            self, "Calibration", "Calibration completed successfully."
        )

    def iniciar_lectura(self):
        if not self.ser:
            QMessageBox.warning(self, "Error", "You must connect the device first.")
            return
        self.reader_thread = ReaderThread(self.ser, self.offsets)
        self.reader_thread.new_data.connect(self.actualizar_datos)
        self.reader_thread.start()
        QMessageBox.information(
            self, "Reading Started", "The device is transmitting data."
        )

    def detener_lectura(self):
        if self.reader_thread:
            self.reader_thread.stop()
            self.reader_thread.wait()
            QMessageBox.information(
                self, "Reading Stopped", "Data reading has been stopped."
            )

    def enviar_comandos_periodicos(self):
        if not self.ser:
            return  # no enviar si no hay conexión
        fan_value = self.dial_fan.value()
        heat_value = self.slider_heat.value()
        core.enviar_comando(self.ser, "FAN", fan_value)
        core.enviar_comando(self.ser, "HEAT", heat_value)

    def actualizar_datos(self, te, ts, tc, vel, pot):

        def es_valido(valor, lista):
            """Devuelve True si el valor está dentro del ±15% de la media"""
            if len(lista) < 5:  # aún pocos datos, no filtrar
                return True
            media = sum(lista) / len(lista)
            if media == 0:
                return True
            desviacion = abs(valor - media) / abs(media)
            return desviacion <= 0.15  # ✅ dentro del ±15 %

        # Comprobar cada variable
        if not all(
            [
                es_valido(te, self.data_te),
                es_valido(ts, self.data_ts),
                es_valido(tc, self.data_tc),
                es_valido(vel, self.data_vel),
                es_valido(pot, self.data_pot),
            ]
        ):
            # 🚫 Si alguna lectura es un despunte, se ignora totalmente
            print("⚠️ Despunte detectado, valor descartado.")
            return

        # --- Actualizar etiquetas ---
        self.lbl_te.setText(f"Inlet Temperature (IT): {te:.2f} °C")
        self.lbl_ts.setText(f"Outlet Temperature (OT): {ts:.2f} °C")
        self.lbl_tc.setText(f"Thermocouple (TC): {tc:.2f} °C")
        self.lbl_vel.setText(f"Air Velocity: {vel:.2f} m/s")
        self.lbl_pot.setText(f"Power: {pot:.2f} W")

        # --- Añadir a las listas y graficar ---
        t = time.time() - self.t0
        self.data_x.append(t)
        self.data_te.append(te)
        self.data_ts.append(ts)
        self.data_tc.append(tc)
        self.data_vel.append(vel)
        self.data_pot.append(pot)

        self.curve_te.setData(self.data_x, self.data_te)
        self.curve_ts.setData(self.data_x, self.data_ts)
        self.curve_tc.setData(self.data_x, self.data_tc)
        self.curve_vel.setData(self.data_x, self.data_vel)
        self.curve_pot.setData(self.data_x, self.data_pot)

    def toggle_curve_visibility(self):
        self.curve_te.setVisible(self.chk_te.isChecked())
        self.curve_ts.setVisible(self.chk_ts.isChecked())
        self.curve_tc.setVisible(self.chk_tc.isChecked())
        self.curve_vel.setVisible(self.chk_vel.isChecked())
        self.curve_pot.setVisible(self.chk_pot.isChecked())

    def mostrar_resultados(self):
        if not self.data_records:
            QMessageBox.warning(
                self, "No Data", "There are no saved records to display."
            )
            return
        self.results_window = ResultsWindow(self.data_records)
        self.results_window.show()

    # =======================================================
    # CAMBIO DE IDIOMA (desde translations.json)
    # =======================================================
    def set_language(self, lang):
        """Cambia todos los textos visibles de la interfaz."""
        if lang not in self.translations:
            print(f"⚠️ Idioma no encontrado en translations.json: {lang}")
            return

        self.current_lang = lang
        t = self.translations[lang]

        # --- Título de la ventana ---
        self.setWindowTitle(t["title"])

        # --- Títulos de los grupos ---
        self.group_lecturas.setTitle(t["measurements"])
        self.group_control.setTitle(t["control"])
        self.group_grafica.setTitle(t["graph"])
        self.group_tabla.setTitle(t["results"])

        # --- Botones principales ---
        self.btn_conectar.setText(t["connect"])
        self.btn_calibrar.setText(t["calibrate"])
        self.btn_iniciar.setText(t["start"])
        self.btn_detener.setText(t["stop"])
        self.btn_guardar.setText(t["save"])
        self.btn_salir.setText(t["exit"])
        self.btn_export.setText(t["export"])

        # --- Fan y Heater ---
        self.lbl_fan.setText(t["fan"].replace("{val}", "0"))
        self.lbl_heat.setText(t["heater"].replace("{val}", "0"))

        # --- Etiquetas de mediciones ---
        measure_texts = t["measure_labels"]
        for lbl, text in zip(
            [self.lbl_te, self.lbl_ts, self.lbl_tc, self.lbl_vel, self.lbl_pot],
            measure_texts,
        ):
            lbl.setText(text.format(val=0))

        # --- Encabezados de tabla ---
        self.table.setHorizontalHeaderLabels(t["table_headers"])

        # --- Ejes de la gráfica ---
        self.plot_widget.setLabel("left", t["graph_labels"]["y"], color="#000000")
        self.plot_widget.setLabel("bottom", t["graph_labels"]["x"], color="#000000")

        # --- Leyenda de la gráfica ---
        legend_texts = t.get("legend_labels", [])
        for chk, text in zip(
            [self.chk_te, self.chk_ts, self.chk_tc, self.chk_vel, self.chk_pot],
            legend_texts,
        ):
            chk.setText(text)

        print(f"✅ Idioma cambiado a: {lang.upper()}")

    def cerrar_programa(self):
        if self.reader_thread:
            self.reader_thread.stop()
            self.reader_thread.wait()
        if self.ser and self.ser.is_open:
            self.ser.close()
            time.sleep(1)
        self.close()

    # =======================================================
    # CIERRE DE PROGRAMA (al pulsar la X)
    # =======================================================
    def closeEvent(self, event):
        """Intercepta el cierre de la ventana principal (clic en la X)."""

        # --- 1️⃣ Verificar si ventilador o calefactor NO están a cero ---
        fan_value = self.dial_fan.value()
        heat_value = self.slider_heat.value()
        if fan_value > 0 or heat_value > 0:
            QMessageBox.warning(
                self,
                "Safety Warning",
                "⚠️ Before closing the program, make sure to set both the fan and the heater to 0.\n\n"
                "Please reduce both values to 0 before exiting.",
            )

            event.ignore()
            return

        # --- 2️⃣ Verificar si hay registros sin exportar ---
        if len(self.data_records) > 0:
            respuesta = QMessageBox.question(
                self,
                "Confirm Exit",
                "There are records in the table that may not have been exported.\n\n"
                "Are you sure you want to exit?\n"
                "Any data not exported to Excel will be lost.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if respuesta == QMessageBox.StandardButton.No:
                event.ignore()
                return

        # --- 3️⃣ Cerrar correctamente si pasa todas las verificaciones ---
        if self.reader_thread:
            self.reader_thread.stop()
            self.reader_thread.wait()
        if self.ser and self.ser.is_open:
            self.ser.close()
            time.sleep(1)
        event.accept()


# =======================================================
# Ventana de resultados
# =======================================================
class ResultsWindow(QWidget):
    def __init__(self, data_records):
        super().__init__()
        self.setWindowTitle("📊 Practice Results")
        self.resize(900, 600)
        self.data_records = data_records

        # --- Tabla de datos ---
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            [
                "#",
                "Date",
                "Time",
                "IT (°C)",
                "OT (°C)",
                "TC (°C)",
                "Vel (m/s)",
                "Pow (W)",
            ]
        )

        header = self.table.horizontalHeader()

        # Permitir tamaños por columna
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # Columna # fija y estrecha
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 40)  # o 36, como prefieras
        header.setMinimumSectionSize(20)  # permite columnas pequeñas

        self.update_table()

        # 💄 Estilo visual mejorado
        self.table.setStyleSheet(
            """
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #2a2a2a;
                gridline-color: #444;
                color: #f0f0f0;
                selection-background-color: #444;
                selection-color: white;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #333;
                color: #f0f0f0;
                font-weight: bold;
                border: 1px solid #444;
                padding: 4px;
            }
        """
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        # --- Ajuste del ancho de columnas ---
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)

        # --- Botones ---
        btn_export_xlsx = QPushButton("📗 Export to Excel")
        btn_close = QPushButton("🚪 Exit")

        btn_export_xlsx.setFixedWidth(150)
        btn_close.setFixedWidth(150)

        btn_export_xlsx.clicked.connect(self.export_excel)
        btn_close.clicked.connect(self.close)

        h_btns = QHBoxLayout()
        h_btns.addWidget(btn_export_xlsx)
        h_btns.addWidget(btn_close)
        h_btns.addStretch()

        # --- Layout general ---
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addLayout(h_btns)
        self.setLayout(layout)

    def update_table(self):
        """Actualiza la tabla con numeración y valores"""
        self.table.setRowCount(len(self.data_records))
        for i, record in enumerate(self.data_records):
            # Columna 0: número de fila
            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, num_item)

            # Resto de columnas
            for j, val in enumerate(record):
                if isinstance(val, (int, float)):
                    text = f"{val:.2f}"
                else:
                    text = str(val)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, j + 1, item)

    def export_excel(self):
        """Exporta los datos a Excel (.xlsx) incluyendo numeración"""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel", "", "Excel Files (*.xlsx)"
        )
        if path:
            df = pd.DataFrame(
                self.data_records,
                columns=[
                    "Date",
                    "Time",
                    "IT (°C)",
                    "OT (°C)",
                    "TC (°C)",
                    "Velocity (m/s)",
                    "Power (W)",
                ],
            )

            df.index = df.index + 1  # numeración desde 1
            df.index.name = "#"
            df.to_excel(path)
            QMessageBox.information(self, "Export", "Excel file saved successfully.")


# =======================================================
# EJECUCIÓN
# =======================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyleSheet(
        """
    QWidget {
        background-color: #FFFFFF;
        color: #000000;
        font-family: Verdana, Geneva, sans-serif;
    }

    QGroupBox {
        border: 1px solid #CCCCCC;
        border-radius: 6px;
        margin-top: 20px;
        padding-top: 16px;
        background-color: #FFFFFF;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 4px 12px;
        margin-top: -10px;
        color: #007EB8;
        font-weight: bold;
        font-size: 13pt;
        background-color: #FFFFFF;
    }

    QLabel {
        color: #000000;
    }

    QPushButton {
    background-color: #007EB8;
    color: white;
    border: 1px solid #006699;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 600;
    /* Simulación de profundidad con degradado */
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #009EE0,
                                stop:1 #006699);
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #00BFFF,
                                    stop:1 #0077A6);
    }
    QPushButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #005C87,
                                    stop:1 #004D70);
    }
    QPushButton:disabled {
        background-color: #CCCCCC;
        color: #666666;
        border: 1px solid #AAAAAA;
    }


    QSlider::groove:vertical {
        width: 40px;
        border-radius: 10px;
        background: qlineargradient(
            x1:0, y1:1, x2:0, y2:0,
            stop:0 #007EB8,
            stop:1 #E0F4FF
        );
    }
    QSlider::handle:vertical {
        background: white;
        border: 2px solid #007EB8;
        height: 20px;
        margin: -2px -16px;
        border-radius: 10px;
    }

    /* === TABLA CLARA === */
    QTableWidget {
        background-color: #FFFFFF;
        alternate-background-color: #FFFFFF;
        gridline-color: #DDDDDD;
        color: #000000;
        font-size: 12px;
        selection-background-color: #E6F4FB;
        selection-color: #000000;
    }
    QHeaderView::section {
        background-color: #007EB8;
        color: #FFFFFF;
        font-weight: bold;
        border: 1px solid #CCCCCC;
        padding: 4px;
    }

    QCheckBox {
        color: #000000;
        font-size: 13px;
    }

        /* === SCROLLBAR PERSONALIZADO === */
    QScrollBar:vertical {
        border: none;
        background: #F2F6F8;
        width: 10px;
        margin: 0px 0px 0px 0px;
        border-radius: 5px;
    }

    QScrollBar::handle:vertical {
        background: #007EB8;
        min-height: 20px;
        border-radius: 5px;
    }

    QScrollBar::handle:vertical:hover {
        background: #009EE0;
    }

    QScrollBar::handle:vertical:pressed {
        background: #005C87;
    }

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        border: none;
        background: none;
    }

    QScrollBar:horizontal {
        height: 10px;
        background: #F2F6F8;
        border: none;
        border-radius: 5px;
    }

    QScrollBar::handle:horizontal {
        background: #007EB8;
        border-radius: 5px;
    }

    QScrollBar::handle:horizontal:hover {
        background: #009EE0;
    }

    QScrollBar::handle:horizontal:pressed {
        background: #005C87;
    }

"""
    )

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

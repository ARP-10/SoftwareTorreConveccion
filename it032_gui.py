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
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QIcon
import sys
import time
import pyqtgraph as pg
import it032_core as core
import pandas as pd
from PyQt6.QtCore import QTimer


# =======================================================
# Hilo de lectura (datos del equipo)
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

    if __name__ == "__main__":
        app = QApplication(sys.argv)
        app.setWindowIcon(
            QIcon(
                r"C:\Users\dikoi\Desktop\Alejandra\SoftwareTorreConveccion\fotos\dikoin_logo.jpg"
            )
        )


# =======================================================
# Ventana principal
# =======================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IT 03.2 – Convección Natural y Forzada (DIKOIN)")
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
        # 📊 MEDIDAS EN TIEMPO REAL
        # =======================================================
        group_lecturas = QGroupBox("📊 Medidas en tiempo real")
        group_lecturas.setFont(font_title)
        self.lbl_te = QLabel("Entrada (TE): 0.00 °C")
        self.lbl_ts = QLabel("Salida (TS): 0.00 °C")
        self.lbl_tc = QLabel("Termopar (TC): 0.00 °C")
        self.lbl_vel = QLabel("Velocidad del aire: 0.00 m/s")
        self.lbl_pot = QLabel("Potencia: 0.00 W")

        for lbl in [self.lbl_te, self.lbl_ts, self.lbl_tc, self.lbl_vel, self.lbl_pot]:
            lbl.setFont(font_value)
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)

        v_lecturas = QVBoxLayout()
        for lbl in [self.lbl_te, self.lbl_ts, self.lbl_tc, self.lbl_vel, self.lbl_pot]:
            v_lecturas.addWidget(lbl)
        group_lecturas.setLayout(v_lecturas)

        # =======================================================
        # ⚙️ CONTROL DEL EQUIPO
        # =======================================================
        group_control = QGroupBox("⚙️ Control del equipo")
        group_control.setFont(font_title)

        # Ventilador (rueda)
        self.dial_fan = QDial()
        self.dial_fan.setRange(0, 255)
        self.dial_fan.setNotchesVisible(True)
        self.dial_fan.setFixedSize(180, 180)
        self.dial_fan.setWrapping(False)
        self.lbl_fan = QLabel("Ventilador (FAN): 0 %")
        font_small = QFont("Verdana", 11)
        self.lbl_fan.setFont(font_small)
        self.lbl_fan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dial_fan.valueChanged.connect(
            lambda v: self.lbl_fan.setText(f"Ventilador (FAN): {int(v/2.55):3d} %")
        )
        self.dial_fan.valueChanged.connect(
            lambda v: core.enviar_comando(self.ser, "FAN", v) if self.ser else None
        )
        v_fan = QVBoxLayout()
        v_fan.addWidget(self.lbl_fan)
        v_fan.addWidget(self.dial_fan, alignment=Qt.AlignmentFlag.AlignCenter)

        # Calefactor (slider vertical)
        self.slider_heat = QSlider(Qt.Orientation.Vertical)
        self.slider_heat.setRange(0, 255)
        self.slider_heat.setFixedSize(90, 180)
        self.lbl_heat = QLabel("Calefactor (HEAT): 0 %")
        font_small = QFont("Verdana", 11)
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
            lambda v: self.lbl_heat.setText(f"Calefactor (HEAT): {int(v/2.55):3d} %")
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
        group_control.setLayout(h_control)

        # =======================================================
        # ⏱️ Temporizador para envío periódico de comandos
        # =======================================================
        self.timer_comandos = QTimer()
        self.timer_comandos.setInterval(500)  # 500 ms
        self.timer_comandos.timeout.connect(self.enviar_comandos_periodicos)
        self.timer_comandos.start()

        # =======================================================
        # 📈 GRÁFICA
        # =======================================================
        group_grafica = QGroupBox("📈 Gráfica en tiempo real")
        group_grafica.setFont(font_title)

        self.plot_widget = pg.PlotWidget()
        # === Apariencia clara para la gráfica ===
        self.plot_widget.setBackground("#FFFFFF")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("left", "Valor", color="#000000")
        self.plot_widget.setLabel("bottom", "Tiempo (s)", color="#000000")

        # Actualiza los colores de las curvas
        self.curve_te = self.plot_widget.plot(
            pen=pg.mkPen("#E74C3C", width=2), name="TE (Entrada)"  # rojo vivo
        )
        self.curve_ts = self.plot_widget.plot(
            pen=pg.mkPen("#3498DB", width=2), name="TS (Salida)"  # azul medio
        )
        self.curve_tc = self.plot_widget.plot(
            pen=pg.mkPen("#27AE60", width=2), name="TC (Termopar)"  # verde intenso
        )
        self.curve_vel = self.plot_widget.plot(
            pen=pg.mkPen(
                "#F39C12", style=Qt.PenStyle.DotLine, width=2
            ),  # naranja punteado
            name="Velocidad",
        )
        self.curve_pot = self.plot_widget.plot(
            pen=pg.mkPen(
                "#8E44AD", style=Qt.PenStyle.DashLine, width=2
            ),  # violeta discontinuo
            name="Potencia",
        )

        # Checkboxes con color
        def color_box(color):
            frame = QFrame()
            frame.setFixedSize(16, 16)
            frame.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
            return frame

        self.chk_te = QCheckBox("Entrada (TE)")
        self.chk_ts = QCheckBox("Salida (TS)")
        self.chk_tc = QCheckBox("Termopar (TC)")
        self.chk_vel = QCheckBox("Velocidad (m/s)")
        self.chk_pot = QCheckBox("Potencia (W)")

        for chk in [self.chk_te, self.chk_ts, self.chk_tc, self.chk_vel, self.chk_pot]:
            chk.setChecked(True)
            chk.setStyleSheet("color: #000000; font-size: 13px; font-weight: 500;")

        self.chk_te.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_ts.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_tc.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_vel.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_pot.stateChanged.connect(self.toggle_curve_visibility)

        # Leyenda lateral a la derecha
        v_legend = QVBoxLayout()
        for color, chk in zip(
            ["#E74C3C", "#3498DB", "#27AE60", "#F39C12", "#8E44AD"],
            [self.chk_te, self.chk_ts, self.chk_tc, self.chk_vel, self.chk_pot],
        ):
            row = QHBoxLayout()
            row.addWidget(color_box(color))
            row.addSpacing(6)
            row.addWidget(chk)
            row.addStretch()
            v_legend.addLayout(row)
        v_legend.addStretch()

        # Gráfica + leyenda lado a lado
        h_graf = QHBoxLayout()
        h_graf.addWidget(self.plot_widget, stretch=4)
        h_graf.addLayout(v_legend, stretch=1)
        group_grafica.setLayout(h_graf)

        # =======================================================
        # 🧮 TABLA DE RESULTADOS
        # =======================================================
        group_tabla = QGroupBox("📋 Resultados de la práctica")
        group_tabla.setFont(font_title)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["#", "TE (°C)", "TS (°C)", "TC (°C)", "Vel (m/s)", "Pot (W)"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        # 💄 Estilo visual claro para la tabla
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

        header = self.table.horizontalHeader()
        from PyQt6.QtWidgets import QHeaderView

        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.btn_export = QPushButton("📗 Exportar Excel")
        self.btn_export.setFixedWidth(160)
        self.btn_export.clicked.connect(self.export_excel)

        v_tabla = QVBoxLayout()
        v_tabla.addWidget(self.table)
        v_tabla.addWidget(self.btn_export)
        group_tabla.setLayout(v_tabla)

        # =======================================================
        # BOTONES GENERALES
        # =======================================================
        self.btn_conectar = QPushButton("🔌 Conectar")
        self.btn_calibrar = QPushButton("🧭 Calibrar")
        self.btn_iniciar = QPushButton("▶️ Iniciar")
        self.btn_detener = QPushButton("⏹️ Detener")
        self.btn_guardar = QPushButton("💾 Guardar dato")
        self.btn_salir = QPushButton("🚪 Salir")

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

        # Parte superior: lecturas (izq) y control (der)
        top_layout = QHBoxLayout()
        top_layout.addWidget(group_lecturas, 1)
        top_layout.addWidget(group_control, 1)

        # Parte izquierda: bloque principal con top + gráfica + botones
        left_layout = QVBoxLayout()
        left_layout.addLayout(top_layout)  # lecturas + control lado a lado
        left_layout.addWidget(group_grafica)  # debajo la gráfica
        left_layout.addLayout(h_botones)  # botones al final

        # Layout principal: izquierda (funcional) + derecha (tabla)
        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout, 3)
        main_layout.addWidget(group_tabla, 2)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # =======================================================
        # EVENTOS
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

    # =======================================================
    # FUNCIONES DE GUARDADO Y EXPORTACIÓN
    # =======================================================
    def guardar_dato(self):
        try:
            te = float(self.lbl_te.text().split(":")[1].replace("°C", "").strip())
            ts = float(self.lbl_ts.text().split(":")[1].replace("°C", "").strip())
            tc = float(self.lbl_tc.text().split(":")[1].replace("°C", "").strip())
            vel = float(self.lbl_vel.text().split(":")[1].replace("m/s", "").strip())
            pot = float(self.lbl_pot.text().split(":")[1].replace("W", "").strip())

            self.data_records.append([te, ts, tc, vel, pot])
            self.table.setRowCount(len(self.data_records))
            i = len(self.data_records) - 1
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            for j, val in enumerate([te, ts, tc, vel, pot]):
                self.table.setItem(i, j + 1, QTableWidgetItem(f"{val:.2f}"))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo guardar el dato: {e}")

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Excel", "", "Excel Files (*.xlsx)"
        )
        if path:
            df = pd.DataFrame(
                self.data_records,
                columns=["TE (°C)", "TS (°C)", "TC (°C)", "Vel (m/s)", "Pot (W)"],
            )
            df.index = df.index + 1
            df.index.name = "#"
            df.to_excel(path)
            QMessageBox.information(
                self, "Exportación", "Archivo Excel guardado correctamente."
            )

    # =======================================================
    # FUNCIONES PRINCIPALES
    # =======================================================
    def conectar(self):
        port = core.detectar_puerto()
        if not port:
            QMessageBox.warning(
                self, "Conexión fallida", "No se detectó el equipo por USB."
            )
            return
        self.ser = core.serial.Serial(port, core.BAUD, timeout=core.COM_TIMEOUT)
        QMessageBox.information(self, "Conectado", f"Equipo detectado en {port}")

    def calibrar(self):
        if not self.ser:
            QMessageBox.warning(self, "Error", "Debe conectar el equipo primero.")
            return
        self.offsets = core.calibrar_sensores(self.ser)
        QMessageBox.information(
            self, "Calibración", "Calibración completada correctamente."
        )

    def iniciar_lectura(self):
        if not self.ser:
            QMessageBox.warning(self, "Error", "Debe conectar el equipo primero.")
            return
        self.reader_thread = ReaderThread(self.ser, self.offsets)
        self.reader_thread.new_data.connect(self.actualizar_datos)
        self.reader_thread.start()
        QMessageBox.information(
            self, "Lectura iniciada", "El equipo está transmitiendo datos."
        )

    def detener_lectura(self):
        if self.reader_thread:
            self.reader_thread.stop()
            self.reader_thread.wait()
            QMessageBox.information(
                self, "Lectura detenida", "La lectura de datos ha sido detenida."
            )

    def enviar_comandos_periodicos(self):
        if not self.ser:
            return  # no enviar si no hay conexión
        fan_value = self.dial_fan.value()
        heat_value = self.slider_heat.value()
        core.enviar_comando(self.ser, "FAN", fan_value)
        core.enviar_comando(self.ser, "HEAT", heat_value)

    def actualizar_datos(self, te, ts, tc, vel, pot):
        self.lbl_te.setText(f"Entrada (TE): {te:.2f} °C")
        self.lbl_ts.setText(f"Salida (TS): {ts:.2f} °C")
        self.lbl_tc.setText(f"Termopar (TC): {tc:.2f} °C")
        self.lbl_vel.setText(f"Velocidad del aire: {vel:.2f} m/s")
        self.lbl_pot.setText(f"Potencia: {pot:.2f} W")

        t = time.time() - self.t0
        self.data_x.append(t)
        self.data_te.append(te)
        self.data_ts.append(ts)
        self.data_tc.append(tc)
        self.data_vel.append(vel)
        self.data_pot.append(pot)

        # Evita que la memoria se sature (limitado a 200 puntos)
        # if len(self.data_x) > 200:
        #     self.data_x, self.data_te, self.data_ts, self.data_tc, self.data_vel, self.data_pot = [
        #         lst[-200:] for lst in [self.data_x, self.data_te, self.data_ts, self.data_tc, self.data_vel, self.data_pot]
        #     ]

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
                self, "Sin datos", "No hay datos guardados para mostrar."
            )
            return
        self.results_window = ResultsWindow(self.data_records)
        self.results_window.show()

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
                "Advertencia de seguridad",
                "⚠️ Antes de cerrar el programa, asegúrate de poner el ventilador y el calefactor en 0.\n\n"
                "Por favor, reduce ambos valores a 0 antes de salir.",
            )
            event.ignore()
            return

        # --- 2️⃣ Verificar si hay registros sin exportar ---
        if len(self.data_records) > 0:
            respuesta = QMessageBox.question(
                self,
                "Confirmar salida",
                "Hay datos registrados en la tabla que podrían no haberse exportado.\n\n"
                "¿Estás seguro de que deseas salir?\n"
                "Se perderán los datos no exportados al Excel.",
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
        self.setWindowTitle("📊 Resultados de la práctica")
        self.resize(900, 600)
        self.data_records = data_records

        # --- Tabla de datos ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["#", "TE (°C)", "TS (°C)", "TC (°C)", "Vel (m/s)", "Pot (W)"]
        )
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
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # --- Botones ---
        btn_export_xlsx = QPushButton("📗 Exportar Excel")
        btn_close = QPushButton("🚪 Cerrar")

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
                item = QTableWidgetItem(f"{val:.2f}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, j + 1, item)

    def export_excel(self):
        """Exporta los datos a Excel (.xlsx) incluyendo numeración"""
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Excel", "", "Excel Files (*.xlsx)"
        )
        if path:
            df = pd.DataFrame(
                self.data_records,
                columns=["TE (°C)", "TS (°C)", "TC (°C)", "Vel (m/s)", "Pot (W)"],
            )
            df.index = df.index + 1  # numeración desde 1
            df.index.name = "#"
            df.to_excel(path)
            QMessageBox.information(
                self, "Exportación", "Archivo Excel guardado correctamente."
            )


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

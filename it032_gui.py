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
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import sys
import time
import pyqtgraph as pg
import it032_core as core
import pandas as pd


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


# =======================================================
# Ventana principal
# =======================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IT 03.2 – Convección Natural y Forzada (DIKOIN)")
        self.resize(1100, 700)

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
        self.dial_fan.setWrapping(False)
        self.lbl_fan = QLabel("Ventilador (FAN): 0 %")
        self.lbl_fan.setFont(font_value)
        self.dial_fan.setFixedSize(180, 180)
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
        self.slider_heat.setSingleStep(5)
        self.slider_heat.setPageStep(10)
        self.slider_heat.setTickPosition(QSlider.TickPosition.TicksBothSides)
        self.slider_heat.setTickInterval(25)
        self.slider_heat.setInvertedAppearance(False)

        self.lbl_heat = QLabel("Calefactor (HEAT): 0 %")
        self.lbl_heat.setFont(font_value)
        self.lbl_heat.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Apariencia personalizada
        self.slider_heat.setStyleSheet("""
            QSlider {
                background: transparent;
            }
            QSlider::groove:vertical {
                width: 40px;
                border-radius: 10px;
                background: qlineargradient(
                    x1:0, y1:1, x2:0, y2:0,
                    stop:0 #e74c3c,
                    stop:1 #3a3a3a
                );
                margin: 6px;
            }
            QSlider::handle:vertical {
                background: #ffffff;
                border: 2px solid #e74c3c;
                height: 20px;
                margin: -2px -16px;
                border-radius: 10px;
            }
            QSlider::sub-page:vertical {
                background: #e74c3c;
                border-radius: 10px;
            }
        """)

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
        h_control.addSpacing(30)
        group_control.setLayout(h_control)

        # =======================================================
        # 📈 GRÁFICA
        # =======================================================
        group_grafica = QGroupBox("📈 Gráfica en tiempo real")
        group_grafica.setFont(font_title)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#1e1e2e")
        #self.plot_widget.addLegend()
        self.plot_widget.setLabel("left", "Temperatura (°C)")
        self.plot_widget.setLabel("bottom", "Tiempo (s)")

        pi = self.plot_widget.getPlotItem()
        legend = getattr(pi, "legend", None)
        if legend:
            try:
                legend.scene().removeItem(legend)
            except Exception:
                legend.hide()
            pi.legend = None

        # Curvas
        self.curve_te = self.plot_widget.plot(pen=pg.mkPen("r", width=2), name="TE (Entrada)")
        self.curve_ts = self.plot_widget.plot(pen=pg.mkPen("y", width=2), name="TS (Salida)")
        self.curve_tc = self.plot_widget.plot(pen=pg.mkPen("g", width=2), name="TC (Termopar)")
        self.curve_vel = self.plot_widget.plot(
            pen=pg.mkPen("c", style=Qt.PenStyle.DotLine, width=2), name="Velocidad (m/s)"
        )
        self.curve_pot = self.plot_widget.plot(
            pen=pg.mkPen("m", style=Qt.PenStyle.DashLine, width=2), name="Potencia (W)"
        )

        # Checkboxes + color de referencia (leyenda lateral)
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
            chk.setStyleSheet("color: white; font-size: 13px;")

        self.chk_te.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_ts.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_tc.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_vel.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_pot.stateChanged.connect(self.toggle_curve_visibility)

        v_legend = QVBoxLayout()
        for color, chk in zip(
            ["#ff4c4c", "#ffff66", "#66ff66", "#66ffff", "#ff66ff"],
            [self.chk_te, self.chk_ts, self.chk_tc, self.chk_vel, self.chk_pot],
        ):
            row = QHBoxLayout()
            row.addWidget(color_box(color))
            row.addSpacing(6)
            row.addWidget(chk)
            row.addStretch()
            v_legend.addLayout(row)
        v_legend.addStretch()

        h_graf = QHBoxLayout()
        h_graf.addWidget(self.plot_widget, stretch=4)
        h_graf.addLayout(v_legend, stretch=1)
        group_grafica.setLayout(h_graf)

        # =======================================================
        # BOTONES INFERIORES
        # =======================================================
        self.btn_conectar = QPushButton("🔌 Conectar")
        self.btn_calibrar = QPushButton("🧭 Calibrar")
        self.btn_iniciar = QPushButton("▶️ Iniciar")
        self.btn_detener = QPushButton("⏹️ Detener")
        self.btn_guardar = QPushButton("💾 Guardar dato")
        self.btn_resultados = QPushButton("📊 Ver resultados")
        self.btn_salir = QPushButton("🚪 Salir")

        for b in [
            self.btn_conectar,
            self.btn_calibrar,
            self.btn_iniciar,
            self.btn_detener,
            self.btn_guardar,
            self.btn_resultados,
            self.btn_salir,
        ]:
            b.setFixedHeight(32)
            b.setStyleSheet("font-size: 12px;")

        h_botones = QHBoxLayout()
        for b in [
            self.btn_conectar,
            self.btn_calibrar,
            self.btn_iniciar,
            self.btn_detener,
            self.btn_guardar,
            self.btn_resultados,
            self.btn_salir,
        ]:
            h_botones.addWidget(b)

        # =======================================================
        # LAYOUT GENERAL
        # =======================================================
        top_layout = QHBoxLayout()
        top_layout.addWidget(group_lecturas, 1)
        top_layout.addWidget(group_control, 1)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(group_grafica)
        main_layout.addLayout(h_botones)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # =======================================================
        # CONEXIÓN DE EVENTOS
        # =======================================================
        self.btn_conectar.clicked.connect(self.conectar)
        self.btn_calibrar.clicked.connect(self.calibrar)
        self.btn_iniciar.clicked.connect(self.iniciar_lectura)
        self.btn_detener.clicked.connect(self.detener_lectura)
        self.btn_guardar.clicked.connect(self.guardar_dato)
        self.btn_resultados.clicked.connect(self.mostrar_resultados)
        self.btn_salir.clicked.connect(self.cerrar_programa)

        # =======================================================
        # VARIABLES DE GRÁFICA
        # =======================================================
        self.data_x, self.data_te, self.data_ts, self.data_tc, self.data_vel, self.data_pot = [], [], [], [], [], []
        self.t0 = time.time()

    # =======================================================
    # FUNCIONES PRINCIPALES
    # =======================================================
    def conectar(self):
        port = core.detectar_puerto()
        if not port:
            QMessageBox.warning(self, "Conexión fallida", "No se detectó el equipo por USB.")
            return
        self.ser = core.serial.Serial(port, core.BAUD, timeout=core.COM_TIMEOUT)
        QMessageBox.information(self, "Conectado", f"Equipo detectado en {port}")

    def calibrar(self):
        if not self.ser:
            QMessageBox.warning(self, "Error", "Debe conectar el equipo primero.")
            return
        self.offsets = core.calibrar_sensores(self.ser)
        QMessageBox.information(self, "Calibración", "Calibración completada correctamente.")

    def iniciar_lectura(self):
        if not self.ser:
            QMessageBox.warning(self, "Error", "Debe conectar el equipo primero.")
            return
        self.reader_thread = ReaderThread(self.ser, self.offsets)
        self.reader_thread.new_data.connect(self.actualizar_datos)
        self.reader_thread.start()
        QMessageBox.information(self, "Lectura iniciada", "El equipo está transmitiendo datos.")

    def detener_lectura(self):
        if self.reader_thread:
            self.reader_thread.stop()
            self.reader_thread.wait()
            QMessageBox.information(self, "Lectura detenida", "La lectura de datos ha sido detenida.")

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

        if len(self.data_x) > 200:
            self.data_x, self.data_te, self.data_ts, self.data_tc, self.data_vel, self.data_pot = [
                lst[-200:] for lst in [self.data_x, self.data_te, self.data_ts, self.data_tc, self.data_vel, self.data_pot]
            ]

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

    def guardar_dato(self):
        try:
            te = float(self.lbl_te.text().split(":")[1].replace("°C", "").strip())
            ts = float(self.lbl_ts.text().split(":")[1].replace("°C", "").strip())
            tc = float(self.lbl_tc.text().split(":")[1].replace("°C", "").strip())
            vel = float(self.lbl_vel.text().split(":")[1].replace("m/s", "").strip())
            pot = float(self.lbl_pot.text().split(":")[1].replace("W", "").strip())
            self.data_records.append([te, ts, tc, vel, pot])
            QMessageBox.information(self, "Dato guardado", "Se ha guardado la lectura en la tabla.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo guardar el dato: {e}")

    def mostrar_resultados(self):
        if not self.data_records:
            QMessageBox.warning(self, "Sin datos", "No hay datos guardados para mostrar.")
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
# Ventana de resultados
# =======================================================
class ResultsWindow(QWidget):
    def __init__(self, data_records):
        super().__init__()
        self.setWindowTitle("📊 Resultados de la práctica")
        self.resize(900, 600)
        self.data_records = data_records

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["TE (°C)", "TS (°C)", "TC (°C)", "Vel (m/s)", "Pot (W)"])
        self.update_table()

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.addLegend()
        self.plot_widget.setBackground("#1e1e2e")
        self.plot_widget.setLabel("left", "Temperatura (°C)")
        self.plot_widget.setLabel("bottom", "Tiempo (s)")

        pi = self.plot_widget.getPlotItem()
        legend = getattr(pi, "legend", None)
        if legend:
            try:
                legend.scene().removeItem(legend)   # quita del gráfico
            except Exception:
                legend.hide()
            pi.legend = None
            
        self.plot_widget.setFixedHeight(220)
        self.update_plot()

        btn_export_xlsx = QPushButton("📗 Exportar Excel")
        btn_close = QPushButton("🚪 Cerrar")
        btn_export_xlsx.clicked.connect(self.export_excel)
        btn_close.clicked.connect(self.close)

        h_btns = QHBoxLayout()
        for b in [btn_export_xlsx, btn_close]:
            h_btns.addWidget(b)

        layout = QVBoxLayout()
        layout.addWidget(self.table, stretch=2)
        layout.addWidget(self.plot_widget, stretch=1)
        layout.addLayout(h_btns)
        self.setLayout(layout)

    def update_table(self):
        self.table.setRowCount(len(self.data_records))
        for i, record in enumerate(self.data_records):
            for j, val in enumerate(record):
                self.table.setItem(i, j, QTableWidgetItem(f"{val:.2f}"))

    def update_plot(self):
        self.plot_widget.clear()
        if not self.data_records:
            return
        df = pd.DataFrame(self.data_records, columns=["TE", "TS", "TC", "Vel", "Pot"])
        x = list(range(1, len(df) + 1))
        self.plot_widget.plot(x, df["TE"], pen=pg.mkPen("b", width=2), name="TE (°C)")
        self.plot_widget.plot(x, df["TS"], pen=pg.mkPen("r", width=2), name="TS (°C)")
        self.plot_widget.plot(x, df["TC"], pen=pg.mkPen("g", width=2), name="TC (°C)")
        self.plot_widget.plot(x, df["Vel"], pen=pg.mkPen("c", width=2, style=Qt.PenStyle.DotLine), name="Vel (m/s)")
        self.plot_widget.plot(x, df["Pot"], pen=pg.mkPen("m", width=2, style=Qt.PenStyle.DashLine), name="Pot (W)")

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Excel", "", "Excel Files (*.xlsx)")
        if path:
            df = pd.DataFrame(self.data_records, columns=["TE", "TS", "TC", "Vel", "Pot"])
            df.to_excel(path, index=False)
            QMessageBox.information(self, "Exportación", "Archivo Excel guardado correctamente.")


# =======================================================
# EJECUCIÓN
# =======================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyleSheet("""
        QWidget {
            background-color: #121212;
            color: #f0f0f0;
        }
        QGroupBox {
            border: 1px solid #333;
            border-radius: 6px;
            margin-top: 20px;
            padding-top: 16px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 4px 12px;
            margin-top: -10px;
            color: #e0e0e0;
            font-weight: bold;
            background-color: #121212;
        }
        QFrame {
            background: transparent;
        }
        QPushButton {
            background-color: #2c2c2c;
            color: white;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px 10px;
        }
        QPushButton:hover {
            background-color: #444;
        }
        QLabel {
            color: #f0f0f0;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

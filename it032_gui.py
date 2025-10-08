# it032_gui.py - versión con rueda (fan) y barra vertical (heat)
# -------------------------------------------------------

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QProgressBar,
    QGroupBox,
    QDial,
    QMessageBox,
    QSlider,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import sys
import time
import pyqtgraph as pg
import it032_core as core


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

        font_title = QFont("Segoe UI", 14, QFont.Weight.Bold)
        font_value = QFont("Segoe UI", 12)

        # =======================================================
        # 📊 MEDIDAS EN TIEMPO REAL (izquierda)
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
        # ⚙️ CONTROL DEL EQUIPO (derecha)
        # =======================================================
        group_control = QGroupBox("⚙️ Control del equipo")
        group_control.setFont(font_title)

        # --- Ventilador: rueda (QDial) ---
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

        # --- Calefactor: barra vertical (QSlider) ---
        self.slider_heat = QSlider(Qt.Orientation.Vertical)
        self.slider_heat.setFixedSize(60, 180)
        self.slider_heat.setFixedHeight(180)
        self.slider_heat.setRange(0, 255)
        self.slider_heat.setFixedSize(90, 180)
        self.lbl_heat = QLabel("Calefactor (HEAT): 0 %")
        self.lbl_heat.setFont(font_value)
        self.lbl_heat.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.slider_heat.valueChanged.connect(
            lambda v: self.lbl_heat.setText(f"Calefactor (HEAT): {int(v/2.55):3d} %")
        )
        self.slider_heat.valueChanged.connect(
            lambda v: core.enviar_comando(self.ser, "HEAT", v) if self.ser else None
        )

        v_heat = QVBoxLayout()
        v_heat.addWidget(self.lbl_heat)
        v_heat.addWidget(self.slider_heat, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Agrupar ambos controles horizontalmente ---
        h_control = QHBoxLayout()
        h_control.addLayout(v_fan)
        h_control.addLayout(v_heat)
        h_control.addSpacing(30)
        group_control.setLayout(h_control)

        # =======================================================
        # 📈 GRÁFICA
        # =======================================================
        group_grafica = QGroupBox("📈 Gráfica de temperaturas")
        group_grafica.setFont(font_title)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#1e1e2e")
        self.plot_widget.addLegend()
        self.plot_widget.setLabel("left", "Temperatura (°C)")
        self.plot_widget.setLabel("bottom", "Tiempo (s)")
        self.curve_te = self.plot_widget.plot(
            pen=pg.mkPen("r", width=2), name="Entrada (TE)"
        )
        self.curve_ts = self.plot_widget.plot(
            pen=pg.mkPen("y", width=2), name="Salida (TS)"
        )
        self.curve_tc = self.plot_widget.plot(
            pen=pg.mkPen("g", width=2), name="Termopar (TC)"
        )
        self.curve_vel = self.plot_widget.plot(
            pen=pg.mkPen("c", style=Qt.PenStyle.DotLine, width=2),
            name="Velocidad (m/s)"
        )
        self.curve_pot = self.plot_widget.plot(
            pen=pg.mkPen("m", style=Qt.PenStyle.DashLine, width=2),
            name="Potencia (W)"
        )
        v_graf = QVBoxLayout()
        v_graf.addWidget(self.plot_widget)
        group_grafica.setLayout(v_graf)

        # =======================================================
        # BOTONES INFERIORES
        # =======================================================
        self.btn_conectar = QPushButton("🔌 Conectar")
        self.btn_calibrar = QPushButton("🧭 Calibrar")
        self.btn_iniciar = QPushButton("▶️ Iniciar")
        self.btn_detener = QPushButton("⏹️ Detener")
        self.btn_salir = QPushButton("🚪 Salir")

        for b in [
            self.btn_conectar,
            self.btn_calibrar,
            self.btn_iniciar,
            self.btn_detener,
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
        # ESTILO VISUAL
        # =======================================================
        self.setStyleSheet(
            """
            QMainWindow { background-color: #1b1b1b; }
            QGroupBox {
                border: 2px solid #3e3e50;
                border-radius: 8px;
                margin-top: 10px;
                color: #ffffff;
                padding: 14px;
            }
            QGroupBox::title {
                padding-bottom: 8px;
                font-weight: bold;
                font-size: 15px;
            }
            QLabel { color: #dddddd; }
            QDial {
                background-color: #222;
            }
            QSlider::groove:vertical {
                width: 40px;
                background: qlineargradient(
                    x1:0, y1:1, x2:0, y2:0,
                    stop:0 #3a3a3a,
                    stop:1 #5a5a5a
                );
                border-radius: 6px;
                margin: 4px;
            }
            QSlider::handle:vertical {
                background: #e74c3c;
                border-radius: 8px;
                height: 18px;
                margin: -2px -10px;
            }
            QPushButton {
                background-color: #2b2b3c;
                border: 1px solid #3e3e50;
                border-radius: 6px;
                color: #ffffff;
                padding: 4px;
            }
            QPushButton:hover { background-color: #3d3d5c; }
        """
        )

        # =======================================================
        # CONEXIÓN DE EVENTOS
        # =======================================================
        self.btn_conectar.clicked.connect(self.conectar)
        self.btn_calibrar.clicked.connect(self.calibrar)
        self.btn_iniciar.clicked.connect(self.iniciar_lectura)
        self.btn_detener.clicked.connect(self.detener_lectura)
        self.btn_salir.clicked.connect(self.cerrar_programa)

        # =======================================================
        # VARIABLES DE GRÁFICA
        # =======================================================
        self.data_x, self.data_te, self.data_ts, self.data_tc, self.data_vel, self.data_pot = [], [], [], [], [], []
        self.t0 = time.time()

    # =======================================================
    # FUNCIONES
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
            self.data_x = self.data_x[-200:]
            self.data_te = self.data_te[-200:]
            self.data_ts = self.data_ts[-200:]
            self.data_tc = self.data_tc[-200:]
            self.data_vel = self.data_vel[-200:]
            self.data_pot = self.data_pot[-200:]

        self.curve_te.setData(self.data_x, self.data_te)
        self.curve_ts.setData(self.data_x, self.data_ts)
        self.curve_tc.setData(self.data_x, self.data_tc)
        self.curve_vel.setData(self.data_x, self.data_vel)
        self.curve_pot.setData(self.data_x, self.data_pot)


    def cerrar_programa(self):
        if self.reader_thread:
            self.reader_thread.stop()
            self.reader_thread.wait()
        if self.ser and self.ser.is_open:
            self.ser.close()
            time.sleep(1)
        self.close()


# =======================================================
# EJECUCIÓN
# =======================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

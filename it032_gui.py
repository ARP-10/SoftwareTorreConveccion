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
    QToolButton,
    QMenu,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon
import sys
import time
import pyqtgraph as pg
import it032_core as core
import pandas as pd
from PyQt6.QtGui import QIcon
from datetime import datetime
import json
from PyQt6.QtSvgWidgets import QSvgWidget


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

    if __name__ == "__main__":
        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon(r"fotos\dikoin_logo.jpg"))


# =======================================================
# Ventana principal
# =======================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # --- Cargar traducciones ---
        with open("translations.json", "r", encoding="utf-8") as f:
            self.translations = json.load(f)

        self.current_lang = "en"

        t = self.translations[self.current_lang]
        self.setWindowTitle(t["title"])

        self.setWindowIcon(QIcon(r"fotos\dikoin_logo.jpg"))

        self.resize(1500, 750)

        self.ser = None
        self.offsets = [0, 0, 0, 0, 0]
        self.reader_thread = None
        self.data_records = []

        # =======================================================
        # 📊 MEDIDAS EN TIEMPO REAL
        # =======================================================
        self.group_lecturas = QGroupBox(t["measurements"])
        self.group_lecturas.setObjectName("group_lecturas")
        self.lbl_te = QLabel(t["labels"]["te"].format(val=0))
        self.lbl_ts = QLabel(t["labels"]["ts"].format(val=0))
        self.lbl_tc = QLabel(t["labels"]["tc"].format(val=0))
        self.lbl_vel = QLabel(t["labels"]["vel"].format(val=0))
        self.lbl_pot = QLabel(t["labels"]["pot"].format(val=0))

        for lbl in [self.lbl_te, self.lbl_ts, self.lbl_tc, self.lbl_vel, self.lbl_pot]:
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)

        v_lecturas = QVBoxLayout()
        for lbl in [self.lbl_te, self.lbl_ts, self.lbl_tc, self.lbl_vel, self.lbl_pot]:
            v_lecturas.addWidget(lbl)
        self.group_lecturas.setLayout(v_lecturas)

        # =======================================================
        # ⚙️ CONTROL DEL EQUIPO
        # =======================================================
        self.group_control = QGroupBox(t["control"])
        self.group_control.setObjectName("group_control")

        # Ventilador (rueda)
        self.dial_fan = QDial()
        self.dial_fan.setRange(0, 255)
        self.dial_fan.setNotchesVisible(True)
        self.dial_fan.setFixedSize(160, 160)
        self.dial_fan.setWrapping(False)

        self.lbl_fan = QLabel(t["fan"].format(val=0))
        self.lbl_fan.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.dial_fan.valueChanged.connect(
            lambda v: self.lbl_fan.setText(t["fan"].format(val=int(v / 2.55)))
        )
        self.dial_fan.valueChanged.connect(
            lambda v: core.enviar_comando(self.ser, "FAN", v) if self.ser else None
        )

        fan_col = QWidget()
        fan_layout = QVBoxLayout(fan_col)
        fan_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fan_layout.setSpacing(8)
        fan_layout.addWidget(self.dial_fan, alignment=Qt.AlignmentFlag.AlignCenter)
        fan_layout.addWidget(self.lbl_fan, alignment=Qt.AlignmentFlag.AlignCenter)
        fan_col.setFixedWidth(180)

        # Calefactor (slider vertical)
        self.slider_heat = QSlider(Qt.Orientation.Vertical)
        self.slider_heat.setRange(0, 255)
        self.slider_heat.setFixedSize(70, 160)
        self.lbl_heat = QLabel(t["heater"].format(val=0))

        self.lbl_heat.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Reservar el ancho para el peor caso (100%)
        max_heat_text = t["heater"].format(val=100)  # ej: "Heater: 100%"
        fm = self.lbl_heat.fontMetrics()
        self.lbl_heat.setMinimumWidth(fm.horizontalAdvance(max_heat_text) + 24)
        self.lbl_heat.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
        )
        self.lbl_heat.setWordWrap(False)  # por si acaso, que no rompa línea

        self.slider_heat.valueChanged.connect(
            lambda v: self.lbl_heat.setText(t["heater"].format(val=int(v / 2.55)))
        )
        self.slider_heat.valueChanged.connect(
            lambda v: core.enviar_comando(self.ser, "HEAT", v) if self.ser else None
        )

        heat_col = QWidget()
        heat_layout = QVBoxLayout(heat_col)
        heat_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heat_layout.setSpacing(8)
        heat_layout.addWidget(self.slider_heat, alignment=Qt.AlignmentFlag.AlignCenter)
        heat_layout.addWidget(self.lbl_heat, alignment=Qt.AlignmentFlag.AlignCenter)
        heat_col.setFixedWidth(180)

        h_control = QHBoxLayout()
        h_control.addWidget(fan_col)
        h_control.addWidget(heat_col)
        h_control.addStretch(1)
        self.group_control.setLayout(h_control)

        # =======================================================
        # 📈 GRÁFICA
        # =======================================================
        self.group_grafica = QGroupBox(t["graph"])
        self.group_grafica.setObjectName("group_grafica")

        self.plot_widget = pg.PlotWidget()

        # === Apariencia clara para la gráfica ===
        self.plot_widget.setBackground("#FFFFFF")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # --- Etiquetas de los ejes desde el JSON ---
        graph_labels = t["graph_labels"]
        self.plot_widget.setLabel("left", graph_labels["y"], color="#000000")
        self.plot_widget.setLabel("bottom", graph_labels["x"], color="#000000")

        # === Curvas de la gráfica (colores y nombres dinámicos) ===
        legend_labels = t["legend_labels"]

        self.curve_te = self.plot_widget.plot(
            pen=pg.mkPen("#E74C3C", width=2), name=legend_labels[0]  # rojo vivo
        )
        self.curve_ts = self.plot_widget.plot(
            pen=pg.mkPen("#3498DB", width=2), name=legend_labels[1]  # azul medio
        )
        self.curve_tc = self.plot_widget.plot(
            pen=pg.mkPen("#27AE60", width=2), name=legend_labels[2]  # verde intenso
        )
        self.curve_vel = self.plot_widget.plot(
            pen=pg.mkPen(
                "#F39C12", style=Qt.PenStyle.DotLine, width=2
            ),  # naranja punteado
            name=legend_labels[3],
        )
        self.curve_pot = self.plot_widget.plot(
            pen=pg.mkPen(
                "#8E44AD", style=Qt.PenStyle.DashLine, width=2
            ),  # violeta discontinuo
            name=legend_labels[4],
        )

        # === Checkboxes con color y textos desde el JSON ===
        def color_box(color, line_style="solid"):
            frame = QFrame()
            frame.setFixedSize(30, 10)

            if line_style == "dot":
                border_style = "dotted"
            elif line_style == "dash":
                border_style = "dashed"
            else:
                border_style = "solid"

            frame.setStyleSheet(
                f"""
                QFrame {{
                    background-color: transparent;
                    border: 2px {border_style} {color};
                    border-radius: 2px;
                }}
                """
            )
            return frame

        # Los nombres vienen de las etiquetas de leyenda
        legend_labels = t["legend_labels"]

        self.chk_te = QCheckBox(legend_labels[0])
        self.chk_ts = QCheckBox(legend_labels[1])
        self.chk_tc = QCheckBox(legend_labels[2])
        self.chk_vel = QCheckBox(legend_labels[3])
        self.chk_pot = QCheckBox(legend_labels[4])

        for chk in [self.chk_te, self.chk_ts, self.chk_tc, self.chk_vel, self.chk_pot]:
            chk.setChecked(True)
            chk.setStyleSheet("color: #000000; font-size: 13px; font-weight: 500;")

        # Conexión de señales
        self.chk_te.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_ts.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_tc.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_vel.stateChanged.connect(self.toggle_curve_visibility)
        self.chk_pot.stateChanged.connect(self.toggle_curve_visibility)

        # Leyenda lateral a la derecha
        v_legend = QVBoxLayout()
        v_legend.setSpacing(2)
        v_legend.setContentsMargins(0, 0, 0, 0)

        for color, style, chk in zip(
            ["#E74C3C", "#3498DB", "#27AE60", "#F39C12", "#8E44AD"],
            ["solid", "solid", "solid", "dot", "dash"],
            [self.chk_te, self.chk_ts, self.chk_tc, self.chk_vel, self.chk_pot],
        ):
            row = QHBoxLayout()
            row.setSpacing(5)
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(color_box(color, style))
            row.addWidget(chk)
            v_legend.addLayout(row)

        v_legend.addStretch()

        # Leyenda
        legend_widget = QWidget()
        legend_widget.setLayout(v_legend)
        legend_widget.setFixedWidth(165)
        legend_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        h_graf = QHBoxLayout()
        h_graf.setContentsMargins(0, 20, 0, 0)
        h_graf.setSpacing(10)
        h_graf.addWidget(self.plot_widget, stretch=4)
        h_graf.addWidget(legend_widget, alignment=Qt.AlignmentFlag.AlignTop)
        self.group_grafica.setLayout(h_graf)

        # =======================================================
        # 🧮 TABLA DE RESULTADOS
        # =======================================================
        self.group_tabla = QGroupBox(t["results"])
        self.group_tabla.setObjectName("group_tabla")
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(t["table_headers"])

        header = self.table.horizontalHeader()

        # 🔹 Columna # fija y más estrecha
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 20)
        header.setMinimumSectionSize(20)

        # 🔹 Resto de columnas: mismas proporciones elásticas
        for i in range(1, self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        header.setStretchLastSection(False)

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()

        v_tabla = QVBoxLayout()
        v_tabla.addWidget(self.table)
        self.group_tabla.setLayout(v_tabla)

        self.btn_export = QPushButton(t["export"])
        self.btn_export.setFixedWidth(160)
        self.btn_export.clicked.connect(self.export_excel)

        # =======================================================
        # CREACIÓN DE BOTONES
        # =======================================================
        self.btn_conectar = QPushButton(t["connect"])
        self.btn_calibrar = QPushButton(t["calibrate"])
        self.btn_iniciar = QPushButton(t["start"])
        self.btn_detener = QPushButton(t["stop"])
        self.btn_guardar = QPushButton(t["save"])

        # Botón de idioma (solo una vez, no duplicar)
        self.btn_language = QToolButton()
        self.btn_language.setObjectName("btn_language")
        self.btn_language.setText("🌐 Language")
        self.btn_language.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        menu_language = QMenu(self)
        menu_language.addAction("English", lambda: self.set_language("en"))
        menu_language.addAction("Español", lambda: self.set_language("es"))
        self.btn_language.setMenu(menu_language)
        self.btn_language.setFixedHeight(32)

        # =======================================================
        # BOTONES GENERALES
        # =======================================================
        h_botones = QHBoxLayout()
        for b in [
            self.btn_conectar,
            self.btn_calibrar,
            self.btn_iniciar,
            self.btn_detener,
            self.btn_guardar,
            self.btn_export,
        ]:
            b.setFixedHeight(32)
            b.setFixedWidth(180)
            b.setMinimumWidth(100)
            h_botones.addWidget(b)
        h_botones.addStretch()

        # =======================================================
        # LAYOUT GENERAL
        # =======================================================

        # === Barra superior con el botón de idioma ===
        h_topbar = QHBoxLayout()
        h_topbar.addWidget(self.btn_language, alignment=Qt.AlignmentFlag.AlignLeft)
        h_topbar.addStretch()

        # --- Parte superior: lecturas (izq) y control (der)
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.group_lecturas, stretch=7)  # 🟢 más ancho
        top_layout.addWidget(self.group_control, stretch=3)  # 🔵 un poco más estrecho

        # Aseguramos proporciones
        top_layout.setStretch(0, 7)
        top_layout.setStretch(1, 3)

        self.group_lecturas.setMinimumWidth(350)

        # --- Parte izquierda: bloque principal con top + gráfica + botones
        left_layout = QVBoxLayout()
        left_layout.addLayout(h_topbar)
        left_layout.addLayout(top_layout)

        # 🔹 Contenedor para gráfica + botones alineados con el área del plot
        grafica_container = QWidget()
        grafica_container_layout = QVBoxLayout(grafica_container)
        grafica_container_layout.setContentsMargins(0, 0, 0, 0)
        grafica_container_layout.setSpacing(0)

        # 📉 Gráfica (dejamos su margen natural)
        grafica_container_layout.addWidget(self.group_grafica)

        # 📏 Botones alineados exactamente con la gráfica
        botones_container = QWidget()
        botones_layout = QHBoxLayout(botones_container)
        botones_layout.setContentsMargins(0, 0, 0, 0)
        botones_layout.setContentsMargins(
            10, 0, 0, 0
        )  # ⬅️ ajuste fino: mueve los botones a la izquierda
        botones_layout.setSpacing(10)
        botones_layout.addStretch(1)
        for b in [
            self.btn_conectar,
            self.btn_calibrar,
            self.btn_iniciar,
            self.btn_detener,
            self.btn_guardar,
            self.btn_export,
        ]:
            botones_layout.addWidget(b)
        botones_layout.addStretch()

        # 📏 Contenedor intermedio que centra los botones con respecto al área del plot
        botones_outer = QWidget()
        botones_outer_layout = QHBoxLayout(botones_outer)
        botones_outer_layout.setContentsMargins(0, 0, 0, 0)
        botones_outer_layout.setSpacing(0)

        # Añadimos los botones centrados dentro de la zona del plot (ignorando la leyenda)
        botones_outer_layout.addWidget(botones_container, alignment=Qt.AlignmentFlag.AlignHCenter)

        grafica_container_layout.addWidget(botones_outer)


        # Añadir el bloque completo al layout principal de la izquierda
        left_layout.addWidget(grafica_container)

        # --- Envolver la parte izquierda en un contenedor fijo
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        # --- Configurar políticas para mantener proporciones fijas ---
        self.group_tabla.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        # --- Evitar variación por textos traducidos ---
        left_widget.setMinimumWidth(800)
        self.group_tabla.setMinimumWidth(700)

        # --- Layout principal: izquierda (funcional) + derecha (tabla)
        main_layout = QHBoxLayout()
        main_layout.addWidget(left_widget, stretch=6)
        main_layout.addWidget(self.group_tabla, stretch=4)

        # Asegurar proporciones fijas
        main_layout.setStretch(0, 6)
        main_layout.setStretch(1, 4)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- Contenedor principal ---
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

    def load_translations(self):
        try:
            with open("translations.json", "r", encoding="utf-8") as f:
                self.translations = json.load(f)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudo cargar translations.json:\n{e}",
            )
            self.translations = {}

    # =======================================================
    # FUNCIONES DE GUARDADO Y EXPORTACIÓN
    # =======================================================
    def guardar_dato(self):
        try:
            now = datetime.now()
            fecha = now.strftime("%d/%m/%Y")
            hora = now.strftime("%H:%M:%S")

            te = float(self.lbl_te.text().split(":")[1].replace("°C", "").strip())
            ts = float(self.lbl_ts.text().split(":")[1].replace("°C", "").strip())
            tc = float(self.lbl_tc.text().split(":")[1].replace("°C", "").strip())
            vel = float(self.lbl_vel.text().split(":")[1].replace("m/s", "").strip())
            pot = float(self.lbl_pot.text().split(":")[1].replace("W", "").strip())

            self.data_records.append([fecha, hora, te, ts, tc, vel, pot])
            self.table.setRowCount(len(self.data_records))
            i = len(self.data_records) - 1
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(fecha))
            self.table.setItem(i, 2, QTableWidgetItem(hora))
            for j, val in enumerate([te, ts, tc, vel, pot]):
                self.table.setItem(i, j + 3, QTableWidgetItem(f"{val:.2f}"))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo guardar el dato: {e}")

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Excel" if self.current_lang == "es" else "Save Excel",
            "",
            "Excel Files (*.xlsx)",
        )
        if path:
            # Etiquetas de columnas según idioma actual
            if self.current_lang == "es":
                columnas = [
                    "Fecha",
                    "Hora",
                    "TE (°C)",
                    "TS (°C)",
                    "TC (°C)",
                    "Vel (m/s)",
                    "Pot (W)",
                ]
                mensaje = "Archivo Excel guardado correctamente."
                titulo = "Exportación"
            else:
                columnas = [
                    "Date",
                    "Time",
                    "TE (°C)",
                    "TS (°C)",
                    "TC (°C)",
                    "Velocity (m/s)",
                    "Power (W)",
                ]
                mensaje = "Excel file saved successfully."
                titulo = "Export"

            df = pd.DataFrame(self.data_records, columns=columnas)
            df.index = df.index + 1
            df.index.name = "#"
            df.to_excel(path)
            QMessageBox.information(self, titulo, mensaje)

    # =======================================================
    # CAMBIO DE IDIOMA (desde translations.json)
    # =======================================================
    def set_language(self, lang):
        if lang not in self.translations:
            print(f"⚠️ Idioma no encontrado en translations.json: {lang}")
            return

        self.current_lang = lang
        t = self.translations[lang]
        print(f"✅ Idioma cambiado a: {lang.upper()}")

        # --- Ventana principal ---
        self.setWindowTitle(t["title"])

        # --- Grupos ---
        self.group_lecturas.setTitle(t["measurements"])
        self.group_control.setTitle(t["control"])
        self.group_grafica.setTitle(t["graph"])
        self.group_tabla.setTitle(t["results"])

        # --- Etiquetas de medición ---
        self.lbl_te.setText(t["labels"]["te"].format(val=0))
        self.lbl_ts.setText(t["labels"]["ts"].format(val=0))
        self.lbl_tc.setText(t["labels"]["tc"].format(val=0))
        self.lbl_vel.setText(t["labels"]["vel"].format(val=0))
        self.lbl_pot.setText(t["labels"]["pot"].format(val=0))

        # --- Botones ---
        self.btn_conectar.setText(t["connect"])
        self.btn_calibrar.setText(t["calibrate"])
        self.btn_iniciar.setText(t["start"])
        self.btn_detener.setText(t["stop"])
        self.btn_guardar.setText(t["save"])
        self.btn_export.setText(t["export"])

        # --- Controles (ventilador y calefactor) ---
        fan_value = int(self.dial_fan.value() / 2.55)
        heat_value = int(self.slider_heat.value() / 2.55)
        self.lbl_fan.setText(t["fan"].format(val=fan_value))
        self.lbl_heat.setText(t["heater"].format(val=heat_value))

        # --- Tabla ---
        header_labels = t["table_headers"]
        for i, label in enumerate(header_labels):
            item = self.table.horizontalHeaderItem(i)
            if item:
                item.setText(label)
            else:
                self.table.setHorizontalHeaderItem(i, QTableWidgetItem(label))

        # --- Gráfica ---
        graph_labels = t["graph_labels"]
        self.plot_widget.setLabel("left", graph_labels["y"], color="#000000")
        self.plot_widget.setLabel("bottom", graph_labels["x"], color="#000000")

        # --- Leyenda y checkboxes ---
        legend_labels = t["legend_labels"]
        self.chk_te.setText(legend_labels[0])
        self.chk_ts.setText(legend_labels[1])
        self.chk_tc.setText(legend_labels[2])
        self.chk_vel.setText(legend_labels[3])
        self.chk_pot.setText(legend_labels[4])

        # Actualizar nombres de las curvas en la leyenda
        self.curve_te.opts["name"] = legend_labels[0]
        self.curve_ts.opts["name"] = legend_labels[1]
        self.curve_tc.opts["name"] = legend_labels[2]
        self.curve_vel.opts["name"] = legend_labels[3]
        self.curve_pot.opts["name"] = legend_labels[4]

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
        self.results_window = ResultsWindow(
            self.data_records, self.translations, self.current_lang
        )

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
        t = self.translations[self.current_lang]["dialogs_close"]

        # --- 1️⃣ Verificar si ventilador o calefactor NO están a cero ---
        fan_value = self.dial_fan.value()
        heat_value = self.slider_heat.value()
        if fan_value > 0 or heat_value > 0:
            QMessageBox.warning(self, t["safety_title"], t["safety_message"])
            event.ignore()
            return

        # --- 2️⃣ Verificar si hay registros sin exportar ---
        if len(self.data_records) > 0:
            msg = QMessageBox(self)
            msg.setWindowTitle(t["confirm_title"])
            msg.setText(t["confirm_message"])
            msg.setIcon(QMessageBox.Icon.Question)

            # Crear botones personalizados
            btn_yes = msg.addButton(t["yes"], QMessageBox.ButtonRole.YesRole)
            btn_no = msg.addButton(t["no"], QMessageBox.ButtonRole.NoRole)

            msg.setDefaultButton(btn_no)
            msg.exec()

            if msg.clickedButton() == btn_no:
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
# =======================================================
# Ventana de resultados
# =======================================================
class ResultsWindow(QWidget):
    def __init__(self, data_records, translations, current_lang):
        super().__init__()
        self.setObjectName("ResultsTable")
        self.translations = translations
        self.current_lang = current_lang

        # Obtener traducciones activas
        t = self.translations[self.current_lang]

        # Usar el texto traducido para el título
        self.setWindowTitle(t["results"])
        self.resize(900, 600)
        self.data_records = data_records

        # --- Tabla de datos ---
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(t["table_headers"])

        header = self.table.horizontalHeader()

        # 🔹 Columna # fija y más estrecha
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 20)
        header.setMinimumSectionSize(20)

        # 🔹 Resto de columnas: proporciones elásticas
        for i in range(1, self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        header.setStretchLastSection(False)

        self.update_table()

        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        # --- Botones ---
        btn_export_xlsx = QPushButton(t["export"])
        btn_close = QPushButton(t["exit"])

        btn_export_xlsx.setFixedWidth(160)
        btn_close.setFixedWidth(160)

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
            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, num_item)
            for j, val in enumerate(record):
                text = f"{val:.2f}" if isinstance(val, (int, float)) else str(val)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, j + 1, item)

    def export_excel(self):
        """Exporta los datos a Excel (.xlsx) incluyendo numeración"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.translations[self.current_lang]["export"],
            "",
            "Excel Files (*.xlsx)",
        )
        if path:
            t = self.translations[self.current_lang]
            df = pd.DataFrame(self.data_records, columns=t["table_headers"][1:])
            df.index = df.index + 1
            df.index.name = "#"
            df.to_excel(path)
            QMessageBox.information(self, t["export"], t["messages"]["export_ok"])


# =======================================================
# EJECUCIÓN
# =======================================================
def load_stylesheet(app, path="style.qss"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"[QSS] No se pudo cargar '{path}': {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Estilo base “WindowsVista” (permite que QSS controle títulos y botones)
    from PyQt6.QtWidgets import QStyleFactory

    app.setStyle(QStyleFactory.create("WindowsVista"))

    # Fondo blanco global (no toca botones ni textos; QSS los pinta)
    from PyQt6.QtGui import QPalette, QColor

    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor("#FFFFFF"))  # fondo de ventanas
    pal.setColor(
        QPalette.ColorRole.Base, QColor("#FFFFFF")
    )  # fondo de widgets (tables, edits)
    app.setPalette(pal)

    # Carga tu hoja de estilos
    with open("style.qss", "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

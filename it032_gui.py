# -----------------------------------------------------------------------------------------
# Autor: Alejandra Rodríguez
# Empresa: DIKOIN
# Año: 2025
# Descripción: Interfaz gráfica para control y adquisición de datos del equipo IT032.
# Derechos de autor reservados.
# -----------------------------------------------------------------------------------------


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
    QDialog,
    QLabel,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QSettings
from PyQt6.QtGui import QFont, QIcon, QMovie
import sys
import time
import pyqtgraph as pg
import pandas as pd
from PyQt6.QtSvgWidgets import QSvgWidget
from datetime import datetime, timezone
import json
import requests
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor
import core
import webbrowser
import base64
import hmac
import hashlib
from pathlib import Path as PPath
import sys
import os

_SECRET_MASK_B64 = "doipquDPxSVrMQN3X3N+/a+vNdTNXBSY/E28I72eZaU="
_SECRET_XOR_B64 = "g7VN9n8tZyQ5aw3dwWRddBGtk7+83vz97snRS54GW7A="


def get_embedded_secret_b64url() -> str:
    mask = base64.b64decode(_SECRET_MASK_B64)
    xval = base64.b64decode(_SECRET_XOR_B64)
    secret_bytes = bytes(a ^ b for a, b in zip(xval, mask))
    return base64.urlsafe_b64encode(secret_bytes).decode("ascii").rstrip("=")


API_BASE_URL = "https://iotnexus.dikoin.com/api"
APP_VERSION = "1.0.0"


class LoadingDialog(QDialog):
    def __init__(self, parent, text="Procesando..."):
        super().__init__(parent)

        self.setWindowTitle(text)
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.CustomizeWindowHint
        )

        self.setWindowIcon(QIcon("fotos/dikoin_logo.jpg"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Spinner animado (GIF)
        self.movie_label = QLabel()
        self.movie_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.movie = QMovie("icons/spinner.gif")  # añade tu spinner.gif en /icons
        self.movie.setScaledSize(QSize(64, 64))
        self.movie_label.setMovie(self.movie)
        self.movie.start()

        layout.addWidget(self.movie_label)

        self.setFixedSize(260, 160)


class ClearTableWorker(QThread):
    finished = pyqtSignal(bool, str)  # éxito / error, mensaje

    def __init__(self, run_id, local_results):
        super().__init__()
        self.run_id = run_id
        self.local_results = local_results

    def run(self):
        try:
            payload = {"run_id": self.run_id, "results": self.local_results}
            response = requests.post(f"{API_BASE_URL}/results/bulk", json=payload)

            if response.status_code == 201:
                requests.post(f"{API_BASE_URL}/runs/{self.run_id}/end")
                self.finished.emit(True, "OK")
            else:
                self.finished.emit(False, response.text)

        except Exception as e:
            self.finished.emit(False, str(e))


class CloseWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, run_id, local_results):
        super().__init__()
        self.run_id = run_id
        self.local_results = local_results

    def run(self):
        try:
            payload = {"run_id": self.run_id, "results": self.local_results}
            r = requests.post(f"{API_BASE_URL}/results/bulk", json=payload)

            if r.status_code == 201:
                requests.post(f"{API_BASE_URL}/runs/{self.run_id}/end")
                self.finished.emit(True, "OK")
            else:
                self.finished.emit(False, r.text)

        except Exception as e:
            self.finished.emit(False, str(e))


class AlertDialog(QDialog):
    def __init__(self, parent, title, text):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.CustomizeWindowHint  # sin botón X
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # --- ICONO DE ALERTA ---
        icon_label = QLabel()
        icon_pix = QIcon("icons/warning.png").pixmap(64, 64)
        icon_label.setPixmap(icon_pix)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(icon_label)

        # --- TEXTO QUE SE AJUSTA ---
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        text_label.setStyleSheet("font-size: 15px;")
        layout.addWidget(text_label, stretch=1)

        # --- TAMAÑO AUTOMÁTICO ---
        self.setMinimumWidth(420)
        self.adjustSize()


class NoDataDialog(QDialog):
    def __init__(self, parent, translations, lang):
        super().__init__(parent)

        t = translations[lang]["no_data_dialog"]

        self.setWindowTitle(t["title"])
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.CustomizeWindowHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel(t["message"])
        label.setWordWrap(True)
        layout.addWidget(label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_close = QPushButton(t["close_button"])
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

        self.btn_close.clicked.connect(self.close_app)

        self.result = None

    def close_app(self):
        self.result = "close"
        self.close()


class ManualModeDialog(QDialog):
    def __init__(self, parent, translations, lang):
        super().__init__(parent)

        t = translations[lang]["manual_mode_dialog"]

        self.setWindowTitle(t["title"])
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.CustomizeWindowHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel(t["message"])
        label.setWordWrap(True)
        layout.addWidget(label)

        # --- SOLO UN BOTÓN ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cerrar = QPushButton(t["close_button"])
        btn_layout.addWidget(self.btn_cerrar)

        layout.addLayout(btn_layout)

        self.btn_cerrar.clicked.connect(self.cerrar)

        self.result = None

    def cerrar(self):
        self.result = "cerrar"
        self.close()


def apply_shadow(widget, blur=40, x=0, y=12, alpha=180):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setXOffset(x)
    shadow.setYOffset(y)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)


def create_card(inner_widget):
    """Crea un contenedor tipo tarjeta con sombra y bordes redondeados."""
    card = QWidget()
    card.setObjectName("card")

    lay = QVBoxLayout(card)
    lay.setContentsMargins(18, 18, 18, 18)
    lay.addWidget(inner_widget)

    apply_shadow(card, blur=60, y=2, alpha=50)
    return card


# =======================================================
# Lectura de datos del equipo
# =======================================================
class ReaderThread(QThread):
    new_data = pyqtSignal(float, float, float, float, float, str)
    modo_manual = pyqtSignal()

    def __init__(self, ser, offsets, parent_window):
        super().__init__()
        self.ser = ser
        self.offsets = offsets
        self.parent_window = parent_window
        self._running = True

    def run(self):
        while self._running:
            valores = core.leer_linea(self.ser)
            # --- Detectar aviso de cambio a CONTROL MANUAL ---
            if valores == "SALIDA_PC":
                print("⚠️ Cambio a control manual detectado")
                self.modo_manual.emit()
                continue

            if not valores:
                continue

            te, ts, tc, vel, pot, serial_number = valores

            # Solo corregimos los 5 valores numéricos
            corregidos = [
                te - self.offsets[0],
                ts - self.offsets[1],
                tc - self.offsets[2],
                vel - self.offsets[3],
                pot - self.offsets[4],
            ]

            te, ts, tc, vel, pot = corregidos

            # 🚀 Imprimir número de serie solo la primera vez
            if not hasattr(self, "printed_serial"):
                print(f"🔑 Número de serie detectado: {serial_number}")
                self.printed_serial = True

            self.new_data.emit(te, ts, tc, vel, pot, serial_number)

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
        self.manual_mode_active = False
        self.language_change = False

        # --- Cargar traducciones ---
        with open("translations.json", "r", encoding="utf-8") as f:
            self.translations = json.load(f)

        self.is_closing = False
        self.update_checked = False

        self.settings = QSettings()
        self.current_lang = self.settings.value("ui/language", "en")

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

        # Labels
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

        # --- card ---
        self.card_lecturas = create_card(self.group_lecturas)

        # =======================================================
        # ⚙️ CONTROL DEL EQUIPO
        # =======================================================
        self.group_control = QGroupBox(t["control"])
        self.group_control.setObjectName("group_control")

        # --- Rueda del ventilador ---
        self.dial_fan = QDial()
        self.dial_fan.valueChanged.connect(self.actualizar_fan)
        self.dial_fan.setRange(0, 255)
        self.dial_fan.setFixedSize(160, 160)
        self.dial_fan.setNotchesVisible(True)

        self.lbl_fan = QLabel(t["fan"].format(val=0))
        self.lbl_fan.setMinimumWidth(120)
        self.lbl_fan.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.timer_fan = QTimer()
        self.timer_fan.setSingleShot(True)
        self.timer_fan.timeout.connect(self.enviar_fan_real)

        fan_col = QWidget()
        fan_layout = QVBoxLayout(fan_col)
        fan_layout.addWidget(self.dial_fan, alignment=Qt.AlignmentFlag.AlignCenter)
        fan_layout.addWidget(self.lbl_fan, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Slider del calentador ---
        self.slider_heat = QSlider(Qt.Orientation.Vertical)
        self.slider_heat.valueChanged.connect(self.actualizar_heat)
        self.slider_heat.setRange(0, 255)
        self.slider_heat.setFixedSize(70, 160)

        self.lbl_heat = QLabel(t["heater"].format(val=0))
        self.lbl_heat.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_heat.setMinimumWidth(120)

        self.timer_heat = QTimer()
        self.timer_heat.setSingleShot(True)
        self.timer_heat.timeout.connect(self.enviar_heat_real)

        heat_col = QWidget()
        heat_layout = QVBoxLayout(heat_col)
        heat_layout.addWidget(self.slider_heat, alignment=Qt.AlignmentFlag.AlignCenter)
        heat_layout.addWidget(self.lbl_heat, alignment=Qt.AlignmentFlag.AlignCenter)

        # Layout principal
        h_control = QHBoxLayout()
        h_control.addWidget(fan_col)
        h_control.addWidget(heat_col)
        h_control.addStretch()

        self.group_control.setLayout(h_control)

        # --- CARD ---
        self.card_control = create_card(self.group_control)

        # =======================================================
        # 📈 GRÁFICA
        # =======================================================
        self.group_grafica = QGroupBox(t["graph"])
        self.group_grafica.setObjectName("group_grafica")

        self.plot_widget = pg.PlotWidget()

        # Apariencia
        self.plot_widget.setBackground("#FFFFFF")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Etiquetas de ejes
        graph_labels = t["graph_labels"]
        self.plot_widget.setLabel("left", graph_labels["y"], color="#000000")
        self.plot_widget.setLabel("bottom", graph_labels["x"], color="#000000")

        # Curvas
        legend_labels = t["legend_labels"]

        self.curve_te = self.plot_widget.plot(
            pen=pg.mkPen("#E74C3C", width=2), name=legend_labels[0]
        )
        self.curve_ts = self.plot_widget.plot(
            pen=pg.mkPen("#3498DB", width=2), name=legend_labels[1]
        )
        self.curve_tc = self.plot_widget.plot(
            pen=pg.mkPen("#27AE60", width=2), name=legend_labels[2]
        )
        self.curve_vel = self.plot_widget.plot(
            pen=pg.mkPen("#F39C12", width=2, style=Qt.PenStyle.DotLine),
            name=legend_labels[3],
        )
        self.curve_pot = self.plot_widget.plot(
            pen=pg.mkPen("#8E44AD", width=2, style=Qt.PenStyle.DashLine),
            name=legend_labels[4],
        )

        # === Función auxiliar para líneas de colores ===
        def color_box(color, line_style="solid"):
            frame = QFrame()
            frame.setFixedSize(30, 3)

            border_style = {"solid": "solid", "dot": "dotted", "dash": "dashed"}.get(
                line_style, "solid"
            )

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

        # === Checkboxes ===
        self.chk_te = QCheckBox(legend_labels[0])
        self.chk_ts = QCheckBox(legend_labels[1])
        self.chk_tc = QCheckBox(legend_labels[2])
        self.chk_vel = QCheckBox(legend_labels[3])
        self.chk_pot = QCheckBox(legend_labels[4])

        for chk in [self.chk_te, self.chk_ts, self.chk_tc, self.chk_vel, self.chk_pot]:
            chk.setChecked(True)
            chk.setStyleSheet("color: #000000; font-size: 13px; font-weight: 500;")
            chk.stateChanged.connect(self.toggle_curve_visibility)

        # === Columna de leyenda ===
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
        legend_widget = QWidget()
        legend_widget.setLayout(v_legend)
        legend_widget.setFixedWidth(165)

        # === Layout interno de la gráfica ===
        h_graf = QHBoxLayout()
        h_graf.setContentsMargins(0, 0, 0, 0)
        h_graf.setSpacing(10)

        h_graf.addWidget(self.plot_widget, stretch=12)
        h_graf.addWidget(legend_widget, stretch=1)

        self.group_grafica.setLayout(h_graf)

        self.card_grafica = create_card(self.group_grafica)

        # =======================================================
        # 🧮 TABLA DE RESULTADOS
        # =======================================================
        self.group_tabla = QGroupBox(t["results"])
        self.group_tabla.setObjectName("group_tabla")

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(t["table_headers"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 20)

        for i in range(1, self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        v_tabla = QVBoxLayout()
        v_tabla.addWidget(self.table)
        self.group_tabla.setLayout(v_tabla)

        self.card_tabla = create_card(self.group_tabla)

        # =======================================================
        # CREACIÓN DE BOTONES
        # =======================================================
        self.btn_export = QPushButton(t["export"])
        self.btn_export.setIcon(QIcon("icons/export.png"))
        self.btn_export.setFixedWidth(160)
        self.btn_export.clicked.connect(self.export_excel)

        self.btn_conectar = QPushButton(t["connect"])
        self.btn_conectar.hide()
        self.btn_conectar.setEnabled(False)

        self.btn_iniciar = QPushButton(t["start"])
        self.btn_iniciar.setIcon(QIcon("icons/start.png"))

        self.btn_detener = QPushButton(t["stop"])
        self.btn_detener.setIcon(QIcon("icons/detener.png"))

        self.btn_guardar = QPushButton(t["save"])
        self.btn_guardar.setIcon(QIcon("icons/save.png"))

        # Botón de idioma
        self.btn_language = QToolButton()
        self.btn_language.setObjectName("btn_language")
        self.btn_language.setText(t["language_button"])
        self.btn_language.setIcon(QIcon("icons/language.png"))
        self.btn_language.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.btn_language.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self.btn_language.setIconSize(QSize(24, 24))

        self.btn_limpiar = QPushButton(
            t["clear_table"] if "clear_table" in t else "Limpiar tabla"
        )
        self.btn_limpiar.setIcon(QIcon("icons/clear.png"))
        self.btn_limpiar.setFixedWidth(160)
        self.btn_limpiar.clicked.connect(self.limpiar_tabla)

        # Menú de idiomas basado en JSON
        self.menu_language = QMenu(self)

        self.action_en = self.menu_language.addAction(t["lang_en"])
        self.action_es = self.menu_language.addAction(t["lang_es"])

        self.action_en.triggered.connect(lambda: self.set_language("en"))
        self.action_es.triggered.connect(lambda: self.set_language("es"))

        self.btn_language.setMenu(self.menu_language)
        self.btn_language.setFixedHeight(32)

        # ==========================
        # Botón ABOUT (menú)
        # ==========================
        self.btn_about = QToolButton()
        self.btn_about.setObjectName("btn_about")
        self.btn_about.setText(t.get("about_button", "About"))
        self.btn_about.setIcon(QIcon("icons/about.png"))
        self.btn_about.setIconSize(QSize(24, 24))
        self.btn_about.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        # MUY IMPORTANTE para que salga el menú al pulsar
        self.btn_about.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self.menu_about = QMenu(self)
        self.action_check_updates = self.menu_about.addAction(
            t.get("check_updates", "Check for updates")
        )
        self.action_check_updates.triggered.connect(
            lambda: self.check_for_updates(True)
        )
        self.btn_about.setMenu(self.menu_about)
        self.btn_about.setFixedHeight(32)

        # =======================================================
        # BOTONES GENERALES
        # =======================================================
        h_botones = QHBoxLayout()
        for b in [
            self.btn_conectar,
            self.btn_iniciar,
            self.btn_detener,
            self.btn_guardar,
            self.btn_export,
            self.btn_limpiar,
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
        h_topbar.setContentsMargins(22, 6, 0, 0)
        h_topbar.addWidget(self.btn_language, alignment=Qt.AlignmentFlag.AlignLeft)
        h_topbar.addSpacing(12)
        h_topbar.addWidget(self.btn_about, alignment=Qt.AlignmentFlag.AlignLeft)
        h_topbar.addStretch()

        # --- Parte superior: lecturas (izq) y control (der)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(self.card_lecturas, stretch=3)  # 🟢 más ancho
        top_layout.addWidget(self.card_control, stretch=3)  # 🔵 un poco más estrecho

        # Aseguramos proporciones
        top_layout.setStretch(0, 7)
        top_layout.setStretch(1, 3)

        self.group_lecturas.setMinimumWidth(350)

        # --- Parte izquierda: bloque principal con top + gráfica + botones
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addLayout(h_topbar)
        left_layout.addLayout(top_layout)

        # 🔹 Contenedor para gráfica + botones alineados con el área del plot
        grafica_container = QWidget()
        grafica_container_layout = QVBoxLayout(grafica_container)
        grafica_container_layout.setContentsMargins(0, 0, 0, 0)
        grafica_container_layout.setSpacing(2)

        grafica_container.setMinimumHeight(450)

        self.group_grafica.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # 📉 Gráfica (dejamos su margen natural)
        grafica_container_layout.addWidget(self.card_grafica)

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
            self.btn_iniciar,
            self.btn_detener,
            self.btn_guardar,
            self.btn_export,
            self.btn_limpiar,
        ]:
            botones_layout.addWidget(b)
        botones_layout.addStretch()

        # 📏 Contenedor intermedio que centra los botones con respecto al área del plot
        botones_outer = QWidget()
        botones_outer_layout = QHBoxLayout(botones_outer)
        botones_outer_layout.setContentsMargins(0, 0, 0, 0)
        botones_outer_layout.setSpacing(0)

        # Añadimos los botones centrados dentro de la zona del plot (ignorando la leyenda)
        botones_outer_layout.addWidget(
            botones_container, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        grafica_container_layout.addWidget(botones_outer)

        # Añadir el bloque completo al layout principal de la izquierda
        left_layout.addWidget(grafica_container, stretch=1)

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
        left_widget.setMinimumWidth(600)
        self.group_tabla.setMinimumWidth(620)

        # --- Layout principal: izquierda (funcional) + derecha (tabla)
        main_layout = QHBoxLayout()
        main_layout.addWidget(left_widget, stretch=6)
        main_layout.addWidget(self.card_tabla, stretch=4)

        # Asegurar proporciones fijas
        main_layout.setStretch(0, 6)
        main_layout.setStretch(1, 4)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # --- Contenedor principal ---
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # =======================================================
        # EVENTOS
        # =======================================================
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
        self.btn_iniciar.setEnabled(False)
        self.dial_fan.setEnabled(False)
        self.slider_heat.setEnabled(False)
        self.btn_detener.setEnabled(False)
        self.btn_limpiar.setEnabled(False)
        self.update_clear_button_state()

        # === TIMER PARA DETECCIÓN DE FALTA DE DATOS ===
        self.last_data_time = time.time()
        self.no_data_alert_shown = False
        self.data_monitoring_active = False

        self.timer_no_data = QTimer()
        self.timer_no_data.timeout.connect(self.check_no_data)
        self.timer_no_data.start(1000)

        # === AUTO-REINTENTO CONEXIÓN SERIE ===
        self.auto_connect_active = True
        self.auto_connect_interval_ms = 1500  # ajusta a gusto (1000–2000 va bien)
        self.auto_connect_alert_shown = False

        self.timer_auto_connect = QTimer(self)
        self.timer_auto_connect.timeout.connect(self.try_auto_connect)
        self.timer_auto_connect.start(self.auto_connect_interval_ms)

    @staticmethod
    def _parse_iso_dt(s: str):
        if not s or not isinstance(s, str):
            return None
        s = s.strip()
        try:
            if s.endswith("Z"):
                return datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)
            dt = datetime.fromisoformat(s)
            return dt
        except Exception:
            try:
                return datetime.strptime(s, "%Y-%m-%d")
            except Exception:
                return None

    @staticmethod
    def _check_license_dates(lic: dict):
        start_keys = ["valid_from", "start_date", "issued_at", "created_at"]
        end_keys = ["valid_to", "end_date", "expires_at", "expires_on", "expiry_date"]

        start_dt = None
        end_dt = None

        for k in start_keys:
            if k in lic:
                start_dt = MainWindow._parse_iso_dt(lic.get(k))
                if start_dt:
                    break

        for k in end_keys:
            if k in lic:
                end_dt = MainWindow._parse_iso_dt(lic.get(k))
                if end_dt:
                    break

        # Si no hay fechas, no bloqueamos
        if not start_dt and not end_dt:
            return

        now_utc = datetime.now(timezone.utc)

        def to_utc(dt):
            if dt is None:
                return None
            # si viene naive, la tratamos como local (si prefieres UTC estricto, se cambia)
            if dt.tzinfo is None:
                return dt
            return dt.astimezone(timezone.utc)

        start_cmp = to_utc(start_dt)
        end_cmp = to_utc(end_dt)

        if start_cmp and (
            (start_cmp.tzinfo is None and datetime.now() < start_cmp)
            or (start_cmp.tzinfo is not None and now_utc < start_cmp)
        ):
            raise RuntimeError(f"Licencia aún no válida (empieza: {start_dt}).")

        if end_cmp and (
            (end_cmp.tzinfo is None and datetime.now() > end_cmp)
            or (end_cmp.tzinfo is not None and now_utc > end_cmp)
        ):
            raise RuntimeError(f"Licencia caducada (caducó: {end_dt}).")

    def _candidate_license_paths(self, serial_number: str):
        serial_number = str(serial_number).strip()
        fname = f"{serial_number}.lic"

        paths = []

        # Carpeta del ejecutable (en EXE) o del script (en dev)
        if getattr(sys, "frozen", False):
            base_dir = PPath(sys.executable).parent
        else:
            base_dir = PPath(__file__).parent

        # ✅ 0) RUTA RELATIVA: .\licencias\<serial>.lic
        paths.append(base_dir / "licencias" / fname)

        # (Opcional) también probar junto al exe: .\<serial>.lic
        paths.append(base_dir / fname)

        # ...el resto de rutas que ya tenías...
        progdata = os.environ.get("PROGRAMDATA")
        if progdata:
            paths.append(PPath(progdata) / "HTlab" / fname)

        saved = self.settings.value("license/path", "")
        if saved:
            paths.append(PPath(saved))

        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(PPath(appdata) / "HTlab" / fname)

        paths.append(PPath.home() / "HTlab" / fname)

        # quitar duplicados
        uniq = []
        for p in paths:
            if p not in uniq:
                uniq.append(p)
        return uniq

    def verify_local_license(self, serial_number: str):
        try:
            serial_number = str(serial_number).strip()

            # 1) buscar en rutas candidatas
            lic_path = None
            tried = []
            for p in self._candidate_license_paths(serial_number):
                tried.append(str(p))
                if p.exists():
                    lic_path = p
                    break

            # 2) si no aparece, pedir al usuario que seleccione el .lic una vez
            if lic_path is None:
                selected, _ = QFileDialog.getOpenFileName(
                    self,
                    "Selecciona tu licencia (.lic)",
                    str(PPath.home()),
                    "License Files (*.lic);;All Files (*.*)",
                )
                if not selected:
                    raise RuntimeError("No se seleccionó ninguna licencia.")
                lic_path = PPath(selected)
                # guardar para próximas veces
                self.settings.setValue("license/path", str(lic_path))

            # 3) leer y validar (tu lógica)
            try:
                lic_data = json.loads(lic_path.read_text(encoding="utf-8"))
            except Exception as e:
                raise RuntimeError(f"El .lic no es JSON válido: {e}")

            serial_in_file = (
                lic_data.get("machine_serial")
                or lic_data.get("serial")
                or lic_data.get("serial_number")
            )
            if str(serial_in_file).strip() != serial_number:
                raise RuntimeError(
                    "El .lic no corresponde a esta máquina.\n"
                    f"Serial en archivo: {serial_in_file}\n"
                    f"Serial detectado: {serial_number}"
                )

            MainWindow._check_license_dates(lic_data)

            sig = lic_data.get("signature") or lic_data.get("sig")
            if not sig:
                raise RuntimeError("El .lic no contiene firma ('signature').")

            secret_b64url = get_embedded_secret_b64url()
            pad = "=" * (-len(secret_b64url) % 4)
            secret_bytes = base64.urlsafe_b64decode(secret_b64url + pad)

            payload = dict(lic_data)
            payload.pop("signature", None)
            payload.pop("sig", None)

            canonical = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")

            mac = hmac.new(secret_bytes, canonical, hashlib.sha256).digest()
            mac_b64url = base64.urlsafe_b64encode(mac).decode("ascii").rstrip("=")

            if not hmac.compare_digest(mac_b64url, str(sig).strip()):
                raise RuntimeError("Firma de licencia inválida.")

            print(f"✅ Licencia válida: {lic_path}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Licencia inválida",
                f"No se pudo validar la licencia:\n\n{e}",
            )
            self.bloquear_todo(True)
            self.close()

    def try_auto_connect(self):
        # No reintentar si estamos cerrando o ya hay conexión
        if self.is_closing:
            return
        if self.ser:  # ya conectado
            return
        if not getattr(self, "auto_connect_active", True):
            return

        t = self.translations[self.current_lang]

        port = core.detectar_puerto()

        if not port:
            # Mostrar aviso SOLO una vez (opcional)
            if not self.auto_connect_alert_shown:
                self.auto_connect_alert_shown = True
                # Mejor "information" (no warning) para no asustar
                QMessageBox.information(
                    self,
                    t["title"],
                    (
                        "Verifica que el equipo esté conectado por USB."
                        if self.current_lang == "es"
                        else "Please verify the device is connected via USB."
                    ),
                )
            return

        # Si encontramos puerto, conectamos
        try:
            self.ser = core.serial.Serial(port, core.BAUD, timeout=core.COM_TIMEOUT)
        except Exception as e:
            print("⚠️ No se pudo abrir el puerto:", e)
            return

        # Ya conectado: parar el timer o dejarlo (yo prefiero pararlo)
        self.timer_auto_connect.stop()

        QMessageBox.information(
            self, t["title"], t["messages"]["connected"].format(port=port)
        )

        self.btn_conectar.setEnabled(False)
        self.dial_fan.setEnabled(True)
        self.slider_heat.setEnabled(True)
        self.update_clear_button_state()

        # Arrancar lectura automáticamente
        self.iniciar_lectura()

    # ===========================
    # COMPROBACIÓN DE VERSIONES
    # ===========================
    @staticmethod
    def _parse_version(v: str):
        """
        Convierte '1.2.3' -> (1, 2, 3) para poder comparar versiones.
        Ignora letras tipo '1.2.3b'.
        """
        parts = str(v).split(".")
        nums = []
        for p in parts:
            num = ""
            for ch in p:
                if ch.isdigit():
                    num += ch
                else:
                    break
            nums.append(int(num or 0))
        while len(nums) < 3:
            nums.append(0)
        return tuple(nums[:3])

    def is_newer_version(self, remote_version: str) -> bool:
        """Devuelve True si remote_version > APP_VERSION."""
        try:
            return self._parse_version(remote_version) > self._parse_version(
                APP_VERSION
            )
        except Exception as e:
            print(f"⚠️ Error comparando versiones: {e}")
            return False

    def check_for_updates(self, show_up_to_date: bool = False):
        """Checks the API for a new version and alerts the user in the saved language."""
        if not hasattr(self, "serial_number_detected"):
            t = self.translations.get(
                self.current_lang, self.translations.get("en", {})
            )
            ud = t.get("update_dialog", {})

            title = ud.get("no_serial_title", ud.get("title", "Updates"))
            msg = ud.get(
                "no_serial_msg",
                "Serial number not detected yet. Connect and start reading first.",
            )

            QMessageBox.information(self, title, msg)
            return

        try:
            r = requests.get(
                f"{API_BASE_URL}/software/latest",
                params={"serial_number": self.serial_number_detected},
                timeout=5,
            )
        except Exception as e:
            print(f"⚠️ Unable to check for updates: {e}")
            return

        if r.status_code != 200:
            print(f"⚠️ Error retrieving version: {r.status_code} - {r.text}")
            return

        try:
            data = r.json()
        except Exception as e:
            print(f"⚠️ Invalid JSON response for update: {e}")
            return

        latest_version = data.get("version")
        download_url = data.get("download_url")
        mandatory = bool(data.get("mandatory", False))

        # --- changelog puede venir como dict (JSON) o string (compatibilidad) ---
        changelog_obj = data.get("changelog")
        changelog = ""

        # 1) Si viene como texto tipo JSON -> parsearlo
        if isinstance(changelog_obj, str):
            s = changelog_obj.strip()
            if (s.startswith("{") and s.endswith("}")) or (
                s.startswith("[") and s.endswith("]")
            ):
                try:
                    changelog_obj = json.loads(s)
                except Exception:
                    # si no es JSON válido, lo dejamos como string normal
                    pass

        # 2) Si ya es dict (o se ha parseado a dict), escoger idioma
        if isinstance(changelog_obj, dict):
            changelog = (
                changelog_obj.get(self.current_lang)
                or changelog_obj.get("en")
                or next(iter(changelog_obj.values()), "")
            )
        else:
            # 3) si es string normal, usarlo tal cual
            changelog = changelog_obj or ""

        if not latest_version:
            return

        if not self.is_newer_version(latest_version):
            # Solo mostrar cartel si el usuario lo pidió (botón "Buscar actualizaciones")
            if show_up_to_date:
                t = self.translations.get(
                    self.current_lang, self.translations.get("en", {})
                )
                ud = t.get("update_dialog", {})

                title = ud.get("no_serial_title", ud.get("title", "Updates"))
                msg = ud.get(
                    "up_to_date_msg",
                    "You already have the latest version.\n\nCurrent version: {current}",
                ).format(current=APP_VERSION)

                QMessageBox.information(self, title, msg)

            return

        # ===============================
        # Textos traducidos desde translations.json
        # ===============================
        t = self.translations.get(self.current_lang, self.translations.get("en", {}))

        # Crea estas keys en translations.json (recomendado)
        # update_dialog: { title, body, release_notes, mandatory_msg, optional_msg }
        ud = t.get("update_dialog", {})

        title = ud.get("title", "Update available")

        text = ud.get(
            "body",
            "A new version of the software is available.\n\n"
            "Current version: {current}\n"
            "Latest version: {latest}\n\n",
        ).format(current=APP_VERSION, latest=latest_version)

        if changelog:
            text += ud.get("release_notes", "Release notes:\n{changelog}\n\n").format(
                changelog=changelog
            )

        if mandatory:
            text += ud.get(
                "mandatory_msg",
                "This update is mandatory. The application will now close so you can install it.",
            )
            buttons = QMessageBox.StandardButton.Ok
            reply = QMessageBox.information(self, title, text, buttons)
            if download_url:
                webbrowser.open(download_url)
            self.close()
            return
        else:
            text += ud.get(
                "optional_msg",
                "Do you want to open the download page now?",
            )
            buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No

            reply = QMessageBox.question(self, title, text, buttons)

            if reply == QMessageBox.StandardButton.Yes and download_url:
                webbrowser.open(download_url)
                self.close()

    def auto_connect(self):
        try:
            self.conectar()  # Detecta puerto y abre conexión
            self.iniciar_lectura()  # Empieza la lectura
        except Exception as e:
            print("❌ Error en conexión automática:", e)

    def _finish_close(self, ok, message):
        self.loading_close.close()

        if not ok:
            QMessageBox.warning(self, "Error", f"Error enviando datos:\n{message}")

        # limpiar memoria de la run
        self.local_results = []
        self.run_id = None

        print("✔ Finalizado el envío. Cerrando aplicación.")

        QApplication.quit()  # 🔥 cierre aquí

    def check_no_data(self):
        if self.is_closing:
            return
        if self.manual_mode_active:
            return
        if getattr(self, "manual_mode_active", False):
            return

        if not self.data_monitoring_active:
            return

        if not self.ser:
            return

        if hasattr(self, "_startup_grace_period"):
            if time.time() - self._startup_grace_period < 5:
                return
            else:
                del self._startup_grace_period

        elapsed = time.time() - self.last_data_time

        if elapsed > 5 and not self.no_data_alert_shown:
            self.no_data_alert_shown = True

            try:
                if self.ser:
                    self.ser.write(b"FAN000\n")
                    self.ser.write(b"HEAT000\n")
                    print("[TX] FAN000 (no data)")
                    print("[TX] HEAT000 (no data)")
            except:
                print("⚠️ No se pudo enviar apagado (no data)")

            # Reset visual inmediato
            self.dial_fan.setValue(0)
            self.slider_heat.setValue(0)

            self.dialog_no_data = NoDataDialog(
                self, self.translations, self.current_lang
            )
            self.dialog_no_data.exec()

            if self.dialog_no_data.result == "close":
                self.close()
                return

            self.estado_botones_antes_fallo = {
                "conectar": self.btn_conectar.isEnabled(),
                "iniciar": self.btn_iniciar.isEnabled(),
                "detener": self.btn_detener.isEnabled(),
                "guardar": self.btn_guardar.isEnabled(),
                "export": self.btn_export.isEnabled(),
                "limpiar": self.btn_limpiar.isEnabled(),
                "dial_fan": self.dial_fan.isEnabled(),
                "slider_heat": self.slider_heat.isEnabled(),
            }

            # Bloquear botones
            self.bloquear_todo(True)

    def aviso_manual(self):
        if self.is_closing:
            return
        self.manual_mode_active = True
        self.estado_botones_antes_fallo = {
            "conectar": self.btn_conectar.isEnabled(),
            "iniciar": self.btn_iniciar.isEnabled(),
            "detener": self.btn_detener.isEnabled(),
            "guardar": self.btn_guardar.isEnabled(),
            "export": self.btn_export.isEnabled(),
            "limpiar": self.btn_limpiar.isEnabled(),
            "dial_fan": self.dial_fan.isEnabled(),
            "slider_heat": self.slider_heat.isEnabled(),
        }

        try:
            if self.ser:
                self.ser.write(b"FAN000\n")
                self.ser.write(b"HEAT000\n")
                print("[TX] FAN000 (manual mode)")
                print("[TX] HEAT000 (manual mode)")
        except:
            print("⚠️ No se pudieron enviar apagados al entrar en modo manual")

        # 💡 Actualizar interfaz
        self.dial_fan.setValue(0)
        self.slider_heat.setValue(0)

        # Si ya está abierto, no repetir
        if hasattr(self, "dialog_manual") and self.dialog_manual.isVisible():
            return

        # Mostrar diálogo personalizado
        self.dialog_manual = ManualModeDialog(
            self, self.translations, self.current_lang
        )
        self.dialog_manual.exec()

        if self.dialog_manual.result == "cerrar":
            print("🔴 Usuario eligió cerrar el programa.")
            self.close()
            return

        # Si cierra la ventana sin pulsar nada → simplemente esperar datos
        print("🟡 Esperando regreso a modo PC...")

    def bloquear_todo(self, estado):
        self.btn_iniciar.setEnabled(not estado)
        self.btn_detener.setEnabled(not estado)
        self.btn_guardar.setEnabled(not estado)
        self.btn_export.setEnabled(not estado)
        self.btn_limpiar.setEnabled(not estado)
        self.dial_fan.setEnabled(not estado)
        self.slider_heat.setEnabled(not estado)

    def update_clear_button_state(self):
        """Bloquea o habilita el botón Clear Table según si hay datos."""
        if len(self.data_records) == 0:
            self.btn_limpiar.setEnabled(False)
        else:
            self.btn_limpiar.setEnabled(True)

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

    def verify_machine_with_api(self, serial):
        print(f"📡 Consultando API por serial {serial}...")

        try:
            r = requests.get(f"{API_BASE_URL}/machines/by-serial/{serial}")

            if r.status_code == 200:
                data = r.json()
                self.machine_id = data["machine_id"]
                print(f"✅ Máquina encontrada en API: machine_id = {self.machine_id}")

                # 🔍 Comprobar actualizaciones SOLO una vez
                if not self.update_checked:
                    self.update_checked = True
                    self.check_for_updates()
            else:
                print("❌ Serial no registrado en API.")

        except Exception as e:
            print(f"❌ Error consultando API: {e}")

    def limpiar_tabla(self):
        if self.is_closing:
            return
        if len(self.data_records) == 0:
            self.table.setRowCount(0)
            self.data_records = []
            if hasattr(self, "local_results"):
                self.local_results = []
            print("🧹 Tabla vacía: no había registros. Nada que enviar.")
            self.btn_limpiar.setEnabled(False)
            return

        t = self.translations[self.current_lang]["dialogs_clear"]

        msg = QMessageBox(self)
        msg.setWindowTitle(t["title"])
        msg.setText(t["message"])
        msg.setIcon(QMessageBox.Icon.Warning)

        btn_yes = msg.addButton(t["yes"], QMessageBox.ButtonRole.YesRole)
        btn_no = msg.addButton(t["no"], QMessageBox.ButtonRole.NoRole)

        msg.exec()

        if msg.clickedButton() != btn_yes:
            return

        print("🧹 Limpiando tabla…")

        # SI hay run activa → enviar a API ANTES DE BORRAR
        if getattr(self, "run_id", None) and getattr(self, "local_results", []):

            print(
                f"📡 Enviando {len(self.local_results)} resultados al servidor antes de limpiar..."
            )

            # Mostrar spinner
            self.loading = LoadingDialog(
                self,
                ("Borrando tabla…" if self.current_lang == "es" else "Cleaning table…"),
            )
            self.loading.show()
            QApplication.processEvents()

            # Lanzar hilo asíncrono para no congelar UI
            self.worker = ClearTableWorker(self.run_id, self.local_results)
            self.worker.finished.connect(self._on_clear_finished)
            self.worker.start()

        else:
            # Sólo limpiar si no hay datos o run
            self._final_clear_table()

    def _on_clear_finished(self, ok, message):
        self.loading.close()

        if not ok:
            QMessageBox.warning(self, "Error", f"Error enviando datos:\n{message}")

        print("🧾 Datos enviados y run cerrada.")

        self._final_clear_table()

    def _final_clear_table(self):
        self.table.setRowCount(0)
        self.data_records = []
        self.local_results = []
        self.run_id = None
        self.btn_limpiar.setEnabled(False)
        self.update_clear_button_state()
        print("🧹 Tabla limpiada y RUN reiniciada")

    # =======================================================
    # FUNCIONES DE GUARDADO Y EXPORTACIÓN
    # =======================================================
    def guardar_dato(self):
        if self.is_closing:
            return
        # Crear la run solo cuando hay el PRIMER dato
        if not getattr(self, "run_id", None):
            print("⏳ No hay run activa, creando run...")
            self.start_run_on_server()

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
            self.update_clear_button_state()

            self.table.setRowCount(len(self.data_records))
            i = len(self.data_records) - 1
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(fecha))
            self.table.setItem(i, 2, QTableWidgetItem(hora))
            for j, val in enumerate([te, ts, tc, vel, pot]):
                self.table.setItem(i, j + 3, QTableWidgetItem(f"{val:.2f}"))

            if not hasattr(self, "local_results"):
                self.local_results = []

            self.local_results.append(
                {
                    "timestamp": now.isoformat(),
                    "metrics": {
                        "TE": te,
                        "TS": ts,
                        "TC": tc,
                        "Velocity": vel,
                        "Power": pot,
                    },
                }
            )

            print("💾 Guardado manual:", self.local_results[-1])

        except Exception as e:
            t = self.translations[self.current_lang]
            msg = t["messages"]["save_error"]
            QMessageBox.warning(self, t["results"], msg)

    def export_excel(self):
        # Preguntar formato al usuario
        t = self.translations[self.current_lang]

        msg = QMessageBox(self)
        msg.setWindowTitle(t["export"])
        msg.setText(
            "¿En qué formato deseas exportar?"
            if self.current_lang == "es"
            else "Which format do you want to export?"
        )
        msg.setIcon(QMessageBox.Icon.Question)

        btn_xls = msg.addButton("Excel (.xlsx)", QMessageBox.ButtonRole.YesRole)
        btn_csv = msg.addButton("CSV (.csv)", QMessageBox.ButtonRole.NoRole)
        btn_cancel = msg.addButton(
            t["messages"]["export_cancel"], QMessageBox.ButtonRole.RejectRole
        )

        msg.exec()

        if msg.clickedButton() == btn_cancel:
            return

        # Seleccionar extensión y filtro según formato elegido
        if msg.clickedButton() == btn_xls:
            file_filter = "Excel Files (*.xlsx)"
            default_ext = ".xlsx"
            export_type = "xlsx"
        else:
            file_filter = "CSV Files (*.csv)"
            default_ext = ".csv"
            export_type = "csv"

        # Diálogo de guardado
        path, _ = QFileDialog.getSaveFileName(
            self,
            t["export"],
            "",
            file_filter,
        )

        if not path:
            return

        # Asegurar extensión correcta
        if not path.lower().endswith(default_ext):
            path += default_ext

        # Construir DataFrame según el idioma
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
            mensaje_ok = "Archivo exportado correctamente."
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
            mensaje_ok = "File exported successfully."

        df = pd.DataFrame(self.data_records, columns=columnas)
        df.index = df.index + 1
        df.index.name = "#"

        # Guardado según formato
        try:
            if export_type == "xlsx":
                df.to_excel(path)
            else:
                df.to_csv(path, sep=";", decimal=",", index=True)

            QMessageBox.information(self, t["export"], mensaje_ok)

        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    # =======================================================
    # CAMBIO DE IDIOMA (desde translations.json)
    # =======================================================
    def set_language(self, lang):
        self.language_change = True
        if lang not in self.translations:
            print(f"⚠️ Idioma no encontrado en translations.json: {lang}")
            return

        self.current_lang = lang
        t = self.translations[lang]
        print(f"✅ Idioma cambiado a: {lang.upper()}")

        # Actualizar el menú
        self.action_en.setText(t["lang_en"])
        self.action_es.setText(t["lang_es"])

        # --- Ventana principal ---
        self.setWindowTitle(t["title"])

        self.msg = t["messages"]

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
        self.btn_iniciar.setText(t["start"])
        self.btn_detener.setText(t["stop"])
        self.btn_guardar.setText(t["save"])
        self.btn_export.setText(t["export"])
        self.btn_language.setText(t["language_button"])
        self.btn_limpiar.setText(t["clear_table"])

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

        self.update_clear_button_state()
        self.language_change = False
        self.settings.setValue("ui/language", lang)
        self.btn_about.setText(t.get("about_button", "About"))
        self.action_check_updates.setText(t.get("check_updates", "Check for updates"))

    # =======================================================
    # FUNCIONES PRINCIPALES
    # =======================================================
    def conectar(self):
        t = self.translations[self.current_lang]
        port = core.detectar_puerto()

        if not port:
            QMessageBox.warning(self, t["title"], t["messages"]["connection_failed"])
            return

        # Abrir puerto
        self.ser = core.serial.Serial(port, core.BAUD, timeout=core.COM_TIMEOUT)

        QMessageBox.information(
            self, t["title"], t["messages"]["connected"].format(port=port)
        )
        self.btn_conectar.setEnabled(False)
        self.dial_fan.setEnabled(True)
        self.slider_heat.setEnabled(True)
        self.update_clear_button_state()

    def iniciar_lectura(self):
        t = self.translations[self.current_lang]

        if not self.ser:
            QMessageBox.warning(self, t["title"], t["messages"]["must_connect_first"])
            return

        self.no_data_alert_shown = False
        self.last_data_time = time.time()

        self.reader_thread = ReaderThread(self.ser, self.offsets, self)
        self.reader_thread.new_data.connect(self.actualizar_datos)
        self.reader_thread.modo_manual.connect(self.aviso_manual)
        self.data_monitoring_active = True

        self.reader_thread.start()

        self._startup_grace_period = time.time()

        self.btn_conectar.setEnabled(False)
        self.btn_iniciar.setEnabled(False)
        self.btn_detener.setEnabled(True)
        self.dial_fan.setEnabled(True)
        self.slider_heat.setEnabled(True)
        self.update_clear_button_state()
        QMessageBox.information(self, t["title"], t["messages"]["reading_started"])

    def start_run_on_server(self):
        if not hasattr(self, "machine_id"):
            print("❌ ERROR: No hay machine_id aún.")
            return

        try:
            response = requests.post(
                f"{API_BASE_URL}/runs/start",
                json={
                    "machine_id": self.machine_id,
                    "app_version": APP_VERSION,
                },
            )
            if response.status_code == 201:

                self.run_id = response.json().get("run_id")
                print(f"🚀 Run iniciada: {self.run_id}")

                if hasattr(self, "buffer_results") and self.buffer_results:
                    if not hasattr(self, "local_results"):
                        self.local_results = []
                    self.local_results.extend(self.buffer_results)
                    print(
                        f"📦 {len(self.buffer_results)} valores movidos del buffer → local_results"
                    )
                    self.buffer_results.clear()

            else:
                print("⚠️ Error API:", response.text)

        except Exception as e:
            print("❌ Error API:", e)

    def detener_lectura(self):
        if self.reader_thread:
            # Cancelar aviso si estaba activo
            if self.no_data_alert_shown:
                self.no_data_alert_shown = False
                if hasattr(self, "dialog_no_data") and self.dialog_no_data.isVisible():
                    self.dialog_no_data.close()

            # Asegurar que no salte aviso tras detener
            self.data_monitoring_active = False

            self.reader_thread.stop()
            self.reader_thread.wait()
            t = self.translations[self.current_lang]

            # 🔥 1) FORZAR FAN Y HEAT A 0
            self.dial_fan.setValue(0)
            self.slider_heat.setValue(0)

            # 🔥 2) ENVIAR FAN000 Y HEAT000 AL EQUIPO
            try:
                if self.ser:
                    self.ser.write(b"FAN000\n")
                    self.ser.write(b"HEAT000\n")
                    print("[TX] FAN000")
                    print("[TX] HEAT000")
            except:
                print("⚠️ No se pudieron enviar los comandos de apagado.")

            self.dial_fan.setEnabled(False)
            self.slider_heat.setEnabled(False)
            self.btn_iniciar.setEnabled(True)
            self.btn_detener.setEnabled(False)
            self.update_clear_button_state()
            # 🧹 Resetear estados después de detener
            self.manual_mode_active = False
            self.no_data_alert_shown = False

            if hasattr(self, "estado_botones_antes_fallo"):
                del self.estado_botones_antes_fallo

            QMessageBox.information(self, t["title"], t["messages"]["reading_stopped"])

    def actualizar_datos(self, te, ts, tc, vel, pot, serial_number):
        if self.is_closing:
            return
        # Registrar que hemos recibido datos
        self.last_data_time = time.time()
        # Si vuelven los datos, desactivamos el modo manual
        if self.manual_mode_active:
            self.manual_mode_active = False

        # 🔹 Si había un aviso de NO DATOS → restaurar estado y cerrar popup
        if self.no_data_alert_shown:
            self.no_data_alert_shown = False
            if hasattr(self, "dialog_no_data") and self.dialog_no_data.isVisible():
                self.dialog_no_data.close()

                # Restaurar estado EXACTO antes del fallo
                if (
                    not self.language_change
                ):  # ⛔ NO restaurar si se está cambiando el idioma
                    if hasattr(self, "estado_botones_antes_fallo"):
                        self.btn_conectar.setEnabled(
                            self.estado_botones_antes_fallo["conectar"]
                        )
                        self.btn_iniciar.setEnabled(
                            self.estado_botones_antes_fallo["iniciar"]
                        )
                        self.btn_detener.setEnabled(
                            self.estado_botones_antes_fallo["detener"]
                        )
                        self.btn_guardar.setEnabled(
                            self.estado_botones_antes_fallo["guardar"]
                        )
                        self.btn_export.setEnabled(
                            self.estado_botones_antes_fallo["export"]
                        )
                        self.btn_limpiar.setEnabled(
                            self.estado_botones_antes_fallo["limpiar"]
                        )
                        self.dial_fan.setEnabled(
                            self.estado_botones_antes_fallo["dial_fan"]
                        )
                        self.slider_heat.setEnabled(
                            self.estado_botones_antes_fallo["slider_heat"]
                        )

        # 🔹 Si había un aviso de CONTROL MANUAL → restaurar también
        if hasattr(self, "dialog_manual"):

            # restaurar SIEMPRE que vuelva el modo PC (no dependemos de isVisible())
            if not self.language_change and hasattr(self, "estado_botones_antes_fallo"):

                self.btn_conectar.setEnabled(
                    self.estado_botones_antes_fallo["conectar"]
                )
                self.btn_iniciar.setEnabled(self.estado_botones_antes_fallo["iniciar"])
                self.btn_detener.setEnabled(self.estado_botones_antes_fallo["detener"])
                self.btn_guardar.setEnabled(self.estado_botones_antes_fallo["guardar"])
                self.btn_export.setEnabled(self.estado_botones_antes_fallo["export"])
                self.btn_limpiar.setEnabled(self.estado_botones_antes_fallo["limpiar"])
                self.dial_fan.setEnabled(self.estado_botones_antes_fallo["dial_fan"])
                self.slider_heat.setEnabled(
                    self.estado_botones_antes_fallo["slider_heat"]
                )

            # ahora sí cerramos el popup si está abierto
            if self.dialog_manual.isVisible():
                self.dialog_manual.close()

        # salir del estado manual
        self.manual_mode_active = False

        # Detectamos el número de serie SOLO una vez
        if not hasattr(self, "serial_number_detected"):
            self.serial_number_detected = serial_number
            print(f"🔍 Serial detectado: {serial_number}")

            # 🔐 VERIFICAR LICENCIA LOCAL
            self.verify_local_license(serial_number)

            # 🌐 API (opcional, no bloquea)
            self.verify_machine_with_api(serial_number)

        # --- Actualización visual normal ---
        t = self.translations[self.current_lang]["labels"]

        self.lbl_te.setText(t["te"].format(val=te))
        self.lbl_ts.setText(t["ts"].format(val=ts))
        self.lbl_tc.setText(t["tc"].format(val=tc))
        self.lbl_vel.setText(t["vel"].format(val=vel))
        if pot < 20:
            pot = 0
        self.lbl_pot.setText(t["pot"].format(val=pot))

        # --- Actualización de la gráfica ---
        tx = time.time() - self.t0
        self.data_x.append(tx)
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

    def actualizar_fan(self, value):
        if not self.ser:
            self.dial_fan.setValue(0)
            return

        t = self.translations[self.current_lang]
        percent = int(value / 2.55)
        self.lbl_fan.setText(t["fan"].format(val=percent))

        self._fan_pending_value = value
        self.timer_fan.start(120)

    def actualizar_heat(self, value):
        if not self.ser:
            self.slider_heat.setValue(0)
            return

        t = self.translations[self.current_lang]
        percent = int(value / 2.55)
        self.lbl_heat.setText(t["heater"].format(val=percent))

        self._heat_pending_value = value
        self.timer_heat.start(120)

    def enviar_fan_real(self):
        if not self.ser:
            return

        value = getattr(self, "_fan_pending_value", None)
        if value is None:
            return

        # Formato EXACTO para Arduino
        cmd = f"FAN{value:03d}\n"

        try:
            self.ser.write(cmd.encode())
            print(f"[TX] {cmd.strip()}")
        except Exception as e:
            print("Error enviando FAN:", e)

    def enviar_heat_real(self):
        if not self.ser:
            return

        raw_value = getattr(self, "_heat_pending_value", None)
        if raw_value is None:
            return

        # Si el slider está a 0 → apagar completamente
        if raw_value == 0:
            mapped_value = 0
        else:
            # Mapear 1–255 → 140–255 (lineal)
            mapped_value = int(140 + ((raw_value - 1) / 254) * (255 - 140))
            # Seguridad por si acaso
            mapped_value = max(140, min(mapped_value, 255))

        cmd = f"HEAT{mapped_value:03d}\n"

        try:
            self.ser.write(cmd.encode())
            print(f"[TX] {cmd.strip()}  (raw={raw_value}, mapped={mapped_value})")
        except Exception as e:
            print("Error enviando HEAT:", e)

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
        if self.is_closing:
            event.accept()
            return

        self.is_closing = True

        self.timer_no_data.stop()
        self.data_monitoring_active = False

        t = self.translations[self.current_lang]["dialogs_close"]

        # ===============================================
        # 1) Confirmación si hay datos
        # ===============================================
        if len(self.data_records) > 0:
            msg = QMessageBox(self)
            msg.setWindowTitle(t["confirm_title"])
            msg.setText(t["confirm_message"])
            msg.setIcon(QMessageBox.Icon.Warning)

            btn_yes = msg.addButton(t["yes"], QMessageBox.ButtonRole.YesRole)
            btn_no = msg.addButton(t["no"], QMessageBox.ButtonRole.NoRole)
            msg.exec()

            if msg.clickedButton() == btn_no:
                event.ignore()
                return

        # ===============================================
        # 2) Safety check FAN/HEAT
        # ===============================================
        if self.dial_fan.value() != 0 or self.slider_heat.value() != 0:
            QMessageBox.warning(self, t["safety_title"], t["safety_message"])
            event.ignore()
            return

        # ===============================================
        # 3) Cerrar correctamente hilo y puerto
        # ===============================================
        if self.reader_thread:
            self.reader_thread.stop()
            self.reader_thread.wait()

        if self.ser and self.ser.is_open:
            try:
                self.ser.write(b"FAN000\n")
                self.ser.write(b"HEAT000\n")
                print("[TX] FAN000 (shutdown)")
                print("[TX] HEAT000 (shutdown)")
            except:
                pass

            self.ser.close()

        # ===============================================
        # 4) Si no hay datos → cerrar normal
        # ===============================================
        if not getattr(self, "run_id", None) or not getattr(self, "local_results", []):
            print("No hay datos para enviar. Cerrando.")
            event.accept()
            return

        # ===============================================
        # 5) Mostrar GIF y lanzar hilo
        # ===============================================
        event.ignore()  # ⛔ EVITA que Qt cierre la app

        self.loading_close = LoadingDialog(
            self,
            (
                "Cerrando programa..."
                if self.current_lang == "es"
                else "Closing program…"
            ),
        )
        self.loading_close.show()
        QApplication.processEvents()

        # Hilo para el envío a la API
        self.close_worker = CloseWorker(self.run_id, self.local_results)
        self.close_worker.finished.connect(self._finish_close)
        self.close_worker.start()


# =======================================================
# Ventana de resultados
# =======================================================
class ResultsWindow(QWidget):
    def __init__(self, data_records, translations, current_lang):
        super().__init__()
        self.setObjectName("ResultsTable")
        self.translations = translations
        self.current_lang = current_lang

        self.update_checked = False

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

    QApplication.setOrganizationName("HTlab")
    QApplication.setApplicationName("GUI")

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

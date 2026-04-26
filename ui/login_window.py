# =============================================================================
# ui/login_window.py
# UDS Simulator — Login Window
# =============================================================================

import os
import sys

from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui  import QBrush, QColor, QPainter, QPixmap

from common.db_handler    import DatabaseHandler

from utils import resource_path
# =============================================================================
# Light theme — like the image
# =============================================================================
COLORS = {
    "bg"         : "#F6F8FA",   # light grey background
    "card"       : "#FFFFFF",   # white card
    "border"     : "#D0D7DE",   # light border
    "border_focus": "#0969DA",  # bleu focus
    "text_main"  : "#1F2328",   # noir textUDS Simulator
    "text_sub"   : "#26292D",   # grey subtitle
    "text_label" : "#3B3E42",   # field labels
    "accent"     : "#1F883D",   # vert — bouton connect
    "accent_hover": "#1A7F37",
    "accent_press": "#156430",
    "error"      : "#CF222E",   # rouge error
    "addr_orange": "#D4A017",   # orange bhal addr f image
}


class LoginWindow(QDialog):

    def __init__(self, db: DatabaseHandler, parent=None):
        super().__init__(parent)
        self.db          = db
        self.logged_role = None

        self._setup_window()
        self._build_ui()
        self._apply_styles()

    # -------------------------------------------------------------------------
    def _setup_window(self):
        self.setWindowTitle("UDS Simulator — Login")
        self.setFixedSize(600, 600)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2
        )

    # -------------------------------------------------------------------------
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame(self)
        self.card.setObjectName("card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 36, 40, 36)
        card_layout.setSpacing(0)

        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.card.setGraphicsEffect(shadow)

        # -- Top bar
        card_layout.addWidget(self._build_topbar())

        # -- Header
        card_layout.addLayout(self._build_header())
        card_layout.addSpacing(28)

        # -- Form
        card_layout.addLayout(self._build_form())
        card_layout.addSpacing(20)

        # -- Button
        self.btn_login = QPushButton("Connect")
        self.btn_login.setObjectName("btn_login")
        self.btn_login.setFixedHeight(36)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.clicked.connect(self._on_login)
        card_layout.addWidget(self.btn_login)

        card_layout.addSpacing(12)

        # -- Error
        self.lbl_error = QLabel("")
        self.lbl_error.setObjectName("lbl_error")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.setFixedHeight(20)
        card_layout.addWidget(self.lbl_error)

        card_layout.addStretch()
        main_layout.addWidget(self.card)

 # -------------------------------------------------------------------------
    # Top bar
    # -------------------------------------------------------------------------
    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(80)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 16, 0)
        layout.setSpacing(20)

        # Logo
        lbl_logo = QLabel()
        pixmap = QPixmap(resource_path("logo/logo.jpg"))
        if not pixmap.isNull():
            size = 60
            rounded = QPixmap(size, size)
            rounded.fill(Qt.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, size, size)
            painter.end()
            lbl_logo.setPixmap(rounded)
        else:
            lbl_logo.setText("⬡")
            lbl_logo.setStyleSheet(f"font-size: 30px;")
        layout.addWidget(lbl_logo)

        # Title
        lbl_title = QLabel("SIGMA Embedded")
        # set Sigma Embedded bigger and bolder than the header title
        lbl_title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['text_main']};")
        lbl_title.setObjectName("topbar_title")
        layout.addWidget(lbl_title)

        layout.addStretch()
        # seperate logo from next elements with some space
        layout.addSpacing(20)

        # layout.setSpacing(20)

        return bar        

    def _build_header(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.addSpacing(20)
        layout.setSpacing(20)

        # Monospace title like the image
        lbl_title = QLabel("UDS Simulator")
        lbl_title.setObjectName("lbl_title")
        lbl_title.setAlignment(Qt.AlignLeft)

        lbl_field = QLabel("Diagnostic Interface  —  ISO 14229")
        lbl_field.setObjectName("lbl_field")
        lbl_field.setAlignment(Qt.AlignLeft)

        # Header separator line like the image
        line = QFrame()
        line.setObjectName("header_line")
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(1)

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_field)
        layout.addSpacing(16)
        layout.addWidget(line)
        return layout

    def _build_form(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(6)

        lbl_user = QLabel("Username")
        lbl_user.setObjectName("lbl_field")
        self.input_username = QLineEdit()
        self.input_username.setObjectName("input_field")
        self.input_username.setFixedHeight(36)
        self.input_username.returnPressed.connect(self._on_login)

        lbl_pass = QLabel("Password")
        lbl_pass.setObjectName("lbl_field")
        self.input_password = QLineEdit()
        self.input_password.setObjectName("input_field")
        self.input_password.setEchoMode(QLineEdit.Password)
        self.input_password.setFixedHeight(36)
        self.input_password.returnPressed.connect(self._on_login)

        layout.addWidget(lbl_user)
        layout.addWidget(self.input_username)
        layout.addSpacing(10)
        layout.addWidget(lbl_pass)
        layout.addWidget(self.input_password)
        return layout

    # -------------------------------------------------------------------------
    def _apply_styles(self):
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {COLORS["card"]};
                border: 3px solid {COLORS["border"]};
                border-radius: 8px;
            }}

            QLabel#lbl_title {{
                font-family: 'Courier New';
                font-size: 32px;
                font-weight: bold;
                color: {COLORS["text_main"]};
            }}

            QFrame#header_line {{
                background-color: {COLORS["border"]};
                border: none;
            }}

            QLabel#lbl_field {{
                font-family: 'Courier New';
                font-size: 18px;
                color: {COLORS["text_label"]};
            }}

            QLineEdit#input_field {{
                background-color: {COLORS["card"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 6px;
                color: {COLORS["text_main"]};
                font-family: 'Courier New';
                font-size: 16px;
                padding: 0 10px;
            }}
            QLineEdit#input_field:focus {{
                border: 1px solid {COLORS["border_focus"]};
                outline: none;
            }}

            QPushButton#btn_login {{
                background-color: {COLORS["accent"]};
                color: white;
                border: none;
                border-radius: 6px;
                font-family: 'Courier New';
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton#btn_login:hover {{
                background-color: {COLORS["accent_hover"]};
            }}
            QPushButton#btn_login:pressed {{
                background-color: {COLORS["accent_press"]};
            }}

            QLabel#lbl_error {{
                font-family: 'Courier New';
                font-size: 18px;
                font-weight: bold;
                color: {COLORS["error"]};
            }}
        """)

    # -------------------------------------------------------------------------
    def _on_login(self):
        username = self.input_username.text().strip()
        password = self.input_password.text()

        if not username or not password:
            self._show_error("Username and password required")
            return

        role = self.db.authenticate_user(username, password)

        if role is None:
            self._show_error("Invalid username or password")
            self._shake()
            return

        self.logged_role = role
        self.accept()

    def _show_error(self, message: str):
        self.lbl_error.setText(f"{message}")

    def _shake(self):
        pos  = self.card.pos()
        anim = QPropertyAnimation(self.card, b"pos")
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.InOutSine)
        anim.setKeyValueAt(0.0,  pos)
        anim.setKeyValueAt(0.15, pos + QPoint(-10, 0))
        anim.setKeyValueAt(0.30, pos + QPoint( 10, 0))
        anim.setKeyValueAt(0.45, pos + QPoint(-8,  0))
        anim.setKeyValueAt(0.60, pos + QPoint( 8,  0))
        anim.setKeyValueAt(0.75, pos + QPoint(-4,  0))
        anim.setKeyValueAt(1.0,  pos)
        anim.start()
        self._shake_anim = anim

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPos() - self._drag_pos)
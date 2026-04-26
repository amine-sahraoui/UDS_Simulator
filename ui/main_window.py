# =============================================================================
# ui/main_window.py
# UDS Simulator — Main Window
# =============================================================================

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBitmap, QBrush, QColor, QFont, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from common.uds_constants import (
    ROLE_ADMIN,
    ROLE_READER,
    ROLE_TECHNICIAN,
    SESSION_DEFAULT,
    SESSION_EXTENDED,
    SESSION_PROGRAMMING,
    SID_DIAGNOSTIC_SESSION_CONTROL,
    SID_ECU_RESET,
    SID_READ_DATA_BY_IDENTIFIER,
    SID_SECURITY_ACCESS,
)
from utils import UDS_COLORS, build_uds_log_entry, resource_path

# =============================================================================
# Colors — light theme
# =============================================================================
C = {
    "bg": "#F6F8FA",
    "white": "#FFFFFF",
    "border": "#D0D7DE",
    "border_focus": "#0969DA",
    "text_main": "#1E252E",
    "text_sub": "#415568",
    "accent": "#1F883D",
    "accent_hover": "#1A7F37",
    "error": "#CF222E",
    "success": "#1F883D",
    "btn_active": "#0969DA",
    "warning": "#9A6700",
}

SESSION_COLORS = {
    SESSION_DEFAULT: "#1F883D",
    SESSION_EXTENDED: "#0969DA",
    SESSION_PROGRAMMING: "#9A6700",
}

ROLE_COLORS = {
    ROLE_ADMIN: "#921131",
    ROLE_TECHNICIAN: "#255993",
    ROLE_READER: "#2B9A4A",
}


class MainWindow(QMainWindow):
    def __init__(self, client, ecu, role: str, parent=None):
        super().__init__(parent)
        self.client = client
        self.ecu = ecu
        self.role = role

        self.ecu.on_frame_logged = self._append_log_entry
        self.client.on_frame_logged = self._append_log_entry

        self._setup_window()
        self._build_ui()
        self._apply_styles()
        self._update_session_indicator()

    # -------------------------------------------------------------------------
    def _setup_window(self):
        self.setWindowTitle("UDS Simulator")
        self.setMinimumSize(1000, 680)
        from PyQt5.QtWidgets import QApplication

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(
            (screen.width() - 1000) // 2,
            (screen.height() - 680) // 2,
            1000,
            680,
        )

    # =========================================================================
    # BUILD UI
    # =========================================================================
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. Top bar
        root.addWidget(self._build_topbar())

        # 2. Command area
        root.addWidget(self._build_command_area())

        # 3. Trace window
        root.addWidget(self._build_trace_window(), 1)

        # 4. Status bar
        root.addWidget(self._build_statusbar())

    # -------------------------------------------------------------------------
    # Top bar
    # -------------------------------------------------------------------------
    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(56)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # Logo
        lbl_logo = QLabel()
        pixmap = QPixmap(resource_path("logo/logo.jpg"))
        if not pixmap.isNull():
            size = 48
            rounded = QPixmap(size, size)
            rounded.fill(Qt.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(
                QBrush(
                    pixmap.scaled(
                        size,
                        size,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    ),
                ),
            )
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, size, size)
            painter.end()
            lbl_logo.setPixmap(rounded)
        else:
            lbl_logo.setText("⬡")
            lbl_logo.setStyleSheet(f"font-size: 30px; color: {C['btn_active']};")
        layout.addWidget(lbl_logo)

        # Title
        lbl_title = QLabel("SIGMA Embedded")
        lbl_title.setObjectName("topbar_title")
        layout.addWidget(lbl_title)

        layout.addStretch()

        # Session indicator
        self.lbl_session = QLabel("● Default Session")
        self.lbl_session.setObjectName("lbl_session")
        layout.addWidget(self.lbl_session)

        layout.addSpacing(12)

        # Engine indicator
        # add engine logo next to the engine status text
        self.lbl_engine = QLabel("● Engine Stopped")
        self.lbl_engine.setObjectName("lbl_engine")
        self.lbl_engine.setStyleSheet(
            f"color: {C['error']}; font-family: 'JetBrains Mono'; font-size: 14px; font-weight: bold;",
        )
        layout.addWidget(self.lbl_engine)
        layout.addSpacing(12)

        # Security indicator
        self.lbl_security = QLabel("🔒 Locked")
        self.lbl_security.setObjectName("lbl_security")
        self.lbl_security.setStyleSheet(
            f"color: {C['error']}; font-family: 'JetBrains Mono'; font-size: 14px; font-weight: bold;",
        )
        layout.addWidget(self.lbl_security)
        layout.addSpacing(16)

        # Role badge
        role_color = ROLE_COLORS.get(self.role, C["text_sub"])
        lbl_role = QLabel(f"  {self.role.upper()}  ")
        lbl_role.setFixedHeight(28)
        lbl_role.setStyleSheet(f"""
            QLabel {{
                color: white;
                background-color: {role_color};
                border-radius: 2px;
                font-family: 'JetBrains Mono';
                font-size: 14px;
                font-weight: bold;
                padding: 0 10px;
            }}
        """)
        layout.addWidget(lbl_role)

        return bar

    # -------------------------------------------------------------------------
    # Command area: (Like the image) input + send button
    # -------------------------------------------------------------------------
    def _build_command_area(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("command_area")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.input_cmd = QLineEdit()
        self.input_cmd.setPlaceholderText("Enter UDS Request")
        self.input_cmd.setFixedHeight(40)
        self.input_cmd.returnPressed.connect(self._send_command)
        input_row.addWidget(self.input_cmd, 1)

        btn_send = QPushButton("Send Request")
        btn_send.setObjectName("btn_send")
        btn_send.setFixedHeight(40)
        btn_send.setFixedWidth(140)
        btn_send.setCursor(Qt.PointingHandCursor)
        btn_send.clicked.connect(self._send_command)
        input_row.addWidget(btn_send)

        btn_clear = QPushButton("Clear")
        btn_clear.setObjectName("btn_clear")
        btn_clear.setFixedHeight(40)
        btn_clear.setFixedWidth(100)
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.clicked.connect(self._clear_log)
        input_row.addWidget(btn_clear)

        self.btn_engine = QPushButton("Start Engine")
        self.btn_engine.setObjectName("btn_engine")
        self.btn_engine.setFixedHeight(40)
        self.btn_engine.setFixedWidth(130)
        self.btn_engine.setCursor(Qt.PointingHandCursor)
        self.btn_engine.clicked.connect(self._toggle_engine)
        input_row.addWidget(self.btn_engine)

        layout.addLayout(input_row)

        # Result label

        return frame

    # -------------------------------------------------------------------------
    # Trace window — Like the image
    # -------------------------------------------------------------------------
    def _build_trace_window(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("trace_frame")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 0, 16, 8)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        lbl = QLabel("Trace window")
        lbl.setObjectName("trace_title")
        header.addWidget(lbl)
        header.addStretch()

        # Legend
        for name, color in [
            ("PCI", UDS_COLORS["pci"]),
            ("SID REQ", UDS_COLORS["sid_request"]),
            ("DID", UDS_COLORS["did"]),
            ("SID RESP", UDS_COLORS["sid_response"]),
            ("PAYLOAD", UDS_COLORS["payload"]),
            ("PADDING", UDS_COLORS["padding"]),
        ]:
            dot = QLabel(f"■ {name}")
            dot.setStyleSheet(
                f"color: {color}; font-family: 'JetBrains Mono'; font-size: 15px;",
            )
            header.addWidget(dot)
            header.addSpacing(2)

        layout.addLayout(header)

        # Table — 7 columns (like the image)
        self.log_table = QTableWidget()
        self.log_table.setObjectName("log_table")
        self.log_table.setColumnCount(7)
        self.log_table.setHorizontalHeaderLabels(
            [
                "Time",
                "Protocol Service",
                "Service",
                "CAN ID (HEX)",
                "Data Bytes (HEX)",
                "Sender",
                "Frame type",
            ],
        )

        hh = self.log_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Time
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Protocol Service
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Service
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # CAN ID
        hh.setSectionResizeMode(4, QHeaderView.Stretch)  # Data Bytes
        hh.setSectionResizeMode(5, QHeaderView.Fixed)
        self.log_table.horizontalHeader().resizeSection(5, 180)  # Sender
        hh.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Frame type

        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.log_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.log_table.setShowGrid(False)
        self.log_table.setAlternatingRowColors(True)
        layout.addWidget(self.log_table)

        return frame

    # -------------------------------------------------------------------------
    # Status bar
    # -------------------------------------------------------------------------
    def _build_statusbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("statusbar")
        bar.setFixedHeight(28)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("lbl_status")
        layout.addWidget(self.lbl_status)
        layout.addStretch()
        return bar

    # =========================================================================
    # COMMAND PARSER
    # =========================================================================
    def _send_command(self):
        """Parse user command and send it to ECU.

        Formats:
            0x1001          → DSC Default
            0x1002          → DSC Programming
            0x1003          → DSC Extended
            0x1101          → Reset Hard
            0x1102          → Reset KeyOff
            0x1103          → Reset Soft
            0x22F40D        → Read DID 0xF40D
            0x2EF190[value] → Write DID 0xF190 = value
        """
        raw = self.input_cmd.text().strip().replace(" ", "").upper()

        if not raw:
            return

        # Normalize — remove 0X prefix
        raw = raw.removeprefix("0X")

        if len(raw) < 2:
            try:
                padded = raw.ljust(2, "0")
                val = int(padded, 16)
                self.client.send_raw([val])
            except ValueError:
                pass
            return
        try:
            sid = int(raw[:2], 16)
        except ValueError:
            # Invalid hex — still send to ECU so it appears in trace
            self.client.send_raw([0x00])
            return

        # Dispatch
        if sid == SID_DIAGNOSTIC_SESSION_CONTROL:
            self._parse_dsc(raw)

        elif sid == SID_ECU_RESET:
            self._parse_reset(raw)

        elif sid == SID_READ_DATA_BY_IDENTIFIER:
            self._parse_read(raw)

        elif sid == SID_SECURITY_ACCESS:
            self._parse_security(raw)
        else:
            self.client.send_raw([sid])

    # ·········································································
    def _parse_dsc(self, raw: str):
        # raw = "1003" → sub = 0x03
        if len(raw) != 4:
            self.client.send_raw([0x10])
            return
        try:
            sub = int(raw[2:4], 16)
        except ValueError:
            return

        # if sub == SESSION_PROGRAMMING and self.ecu.is_engine_running():
        #     self._set_status("Programming session blocked while engine is running.")
        #     return

        result = self.client.change_session(sub)
        if result["success"]:
            self._update_session_indicator()

    def _parse_reset(self, raw: str):
        if len(raw) != 4:
            self.client.send_raw([0x11])
            return
        try:
            reset_type = int(raw[2:4], 16)
        except ValueError:
            self.client.send_raw([0x11])
            return

        result = self.client.reset_ecu(reset_type)
        if result["success"]:
            self._update_session_indicator()
            self._update_security_indicator()

    def _parse_read(self, raw: str):
        did_part = raw[2:]  # remove SID byte (22)

        if len(did_part) < 4:
            self.client.send_raw([0x22])
            return

        # Build full payload: SID + all remaining bytes as-is
        try:
            payload = [0x22]
            # parse every byte from did_part
            for i in range(0, len(did_part), 2):
                chunk = did_part[i : i + 2]
                if len(chunk) < 2:
                    # odd nibble at the end → send raw incomplete
                    self.client.send_raw([0x22])
                    return
                payload.append(int(chunk, 16))
            self.client.send_raw(payload)
        except ValueError:
            self.client.send_raw([0x22])

    def _parse_security(self, raw: str):
        # if len(raw) % 2 != 0  :
        #     self.client.send_raw([0x27])
        #     return

        if len(raw) < 4:
            self.client.send_raw([0x27])
            return

        try:
            sub = int(raw[2:4], 16)
        except ValueError:
            self.client.send_raw([0x27])
            return

        try:
            payload = [0x27]
            for i in range(2, len(raw), 2):
                chunk = raw[i : i + 2]
                if len(chunk) < 2:
                    self.client.send_raw([0x27, sub])
                    return
                payload.append(int(chunk, 16))
            self.client.send_raw(payload)
            self._update_security_indicator()
        except ValueError:
            self.client.send_raw([0x27, sub])

    # =========================================================================
    # LOG — append entry with 7 columns
    # =========================================================================
    def _append_log_entry(self, entry: dict):
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)
        self.log_table.setRowHeight(row, 20)

        payload = entry.get("bytes", [])

        # Col 0 — Time
        self._set_cell(row, 0, entry["time"], C["text_sub"])

        # Col 1 — Protocol Service
        self._set_cell(row, 1, entry.get("protocol", "UDS"), C["text_main"])

        # Col 2 — Service (sub-function)
        self._set_cell(row, 2, entry.get("service", ""), C["btn_active"])

        # Col 3 — CAN ID (HEX) in orange (like in the image)
        self._set_cell(row, 3, entry["addr"], UDS_COLORS["addr"])

        # Col 4 — Data Bytes with color coding
        bytes_widget = self._make_bytes_widget(payload)
        self.log_table.setCellWidget(row, 4, bytes_widget)

        # Col 5 — Sender
        self._set_cell(row, 5, entry["sender"], C["text_sub"])
        # Col 6 — Frame type
        self._set_cell(row, 6, entry["frame_type"], C["text_sub"])

        self.log_table.scrollToBottom()

    def _set_cell(self, row: int, col: int, text: str, color: str):
        item = QTableWidgetItem(text)
        item.setForeground(QBrush(QColor(color)))
        item.setFont(QFont("JetBrains Mono", 8))
        self.log_table.setItem(row, col, item)

    def _make_bytes_widget(self, bytes_list: list) -> QLabel:
        parts = [
            f"<span style='color:{b['color']};font-family:JetBrains Mono;font-size:18px;'>{b['value']}</span>"
            for b in bytes_list
        ]

        label = QLabel(" ".join(parts))
        label.setContentsMargins(6, 0, 6, 0)
        label.setStyleSheet("background: transparent;")
        return label

    def _get_service_names(self, sid: int) -> tuple:
        """Return (protocol_service, service_name) from SID."""
        # Response SID → request SID
        req_sid = sid - 0x40 if sid >= 0x40 and sid != 0x7F else sid

        service_map = {
            0x10: ("UDS", "DiagnosticSessionControl"),
            0x11: ("UDS", "ECUReset"),
            0x22: ("UDS", "ReadDataByIdentifier"),
            0x7F: ("UDS", "NegativeResponse"),
            0x27: ("UDS", "SecurityAccess"),
        }
        return service_map.get(req_sid, ("UDS", f"0x{sid:02X}"))

    def _clear_log(self):
        self.log_table.setRowCount(0)

    # =========================================================================
    # HELPERS
    # =========================================================================
    def _update_session_indicator(self):
        from common.uds_constants import SESSION_SERVICE_MATRIX

        session = self.ecu.get_current_session()
        name = self.ecu.get_session_name()
        color = SESSION_COLORS.get(session, C["text_sub"])
        self.lbl_session.setText(f"● {name.split('(')[0].strip()}")
        self.lbl_session.setStyleSheet(
            f"color: {color}; font-family: 'JetBrains Mono'; font-size: 16px; font-weight: bold;",
        )
        self._update_engine_indicator()

    def _update_engine_indicator(self):
        if self.ecu.is_engine_running():
            text = "Engine Running"
            color = C["accent"]
            engine_button_text = "Stop Engine"
        else:
            text = "Engine Stopped"
            color = C["error"]
            engine_button_text = "Start Engine"

        self.lbl_engine.setText(text)
        self.lbl_engine.setStyleSheet(
            f"color: {color}; font-family: 'JetBrains Mono'; font-size: 14px; font-weight: bold;",
        )

        if hasattr(self, "btn_engine"):
            self.btn_engine.setText(engine_button_text)

        self._update_security_indicator()

    def _update_security_indicator(self):
        if self.ecu.is_security_unlocked():
            text = "🔓 Unlocked"
            color = C["accent"]
        else:
            text = "🔒 Locked"
            color = C["error"]

        self.lbl_security.setText(text)
        self.lbl_security.setStyleSheet(
            f"color: {color}; font-family: 'JetBrains Mono'; font-size: 14px; font-weight: bold;",
        )

    def _set_status(self, message: str):
        self.lbl_status.setText(message)

    def _toggle_engine(self):
        if self.ecu.toggle_engine():
            self._set_status("Engine started.")
        else:
            self._set_status("Engine stopped.")
        self._update_engine_indicator()

    # =========================================================================
    # STYLES
    # =========================================================================
    def _apply_styles(self):
        self.setStyleSheet(f"""
            QWidget#central {{
                background-color: {C["bg"]};
            }}

            /* Top bar */
            QFrame#topbar {{
                background-color: {C["white"]};
                border-bottom: 1px solid {C["border"]};
            }}
            QLabel#topbar_title {{
                font-family: 'JetBrains Mono';
                font-size: 30px;
                font-weight: bold;
                color: {C["text_main"]};
            }}

            /* Command area */
            QFrame#command_area {{
                background-color: {C["white"]};
                border-bottom: 1px solid {C["border"]};
            }}
            QLabel#lbl_hint {{
                font-family: 'JetBrains Mono';
                font-size: 11px;
                color: {C["text_sub"]};
            }}
            QLineEdit#input_cmd {{
                background-color: {C["white"]};
                border: 1px solid {C["border"]};
                border-radius: 4px;
                color: {C["text_main"]};
                font-family: 'JetBrains Mono';
                font-size: 13px;
                padding: 0 10px;
            }}
            QLineEdit#input_cmd:focus {{
                border-color: {C["border_focus"]};
            }}
            QPushButton#btn_send {{
                background-color: {C["accent"]};
                color: white;
                border: none;
                border-radius: 4px;
                font-family: 'JetBrains Mono';
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton#btn_send:hover {{
                background-color: {C["accent_hover"]};
            }}
            QPushButton#btn_clear {{
                background-color: {C["white"]};
                color: {C["text_sub"]};
                border: 1px solid {C["border"]};
                border-radius: 2px;
                font-family: 'JetBrains Mono';
                font-size: 16px;
            }}
            QPushButton#btn_clear:hover {{
                border-color: {C["error"]};
                color: {C["error"]};
            }}
            QPushButton#btn_engine {{
                background-color: {C["btn_active"]};
                color: white;
                border: none;
                border-radius: 4px;
                font-family: 'JetBrains Mono';
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton#btn_engine:hover {{
                background-color: {C["border_focus"]};
            }}
            QLabel#lbl_security {{
                font-family: 'JetBrains Mono';
                font-size: 14px;
                font-weight: bold;
            }}


            /* Trace window */
            QFrame#trace_frame {{
                background-color: {C["bg"]};
            }}
            QLabel#trace_title {{
                font-family: 'JetBrains Mono';
                font-size: 14px;
                font-weight: bold;
                color: {C["text_main"]};
                padding: 4px 0;
            }}
            QTableWidget#log_table {{
                background-color: {C["white"]};
                alternate-background-color: {C["bg"]};
                gridline-color: {C["border"]};
                border: 1px solid {C["border"]};
                font-family: 'JetBrains Mono';
                font-size: 11px;
                color: {C["text_main"]};
                selection-background-color: #DDF4FF;
                selection-color: {C["text_main"]};
            }}
            QTableWidget#log_table QHeaderView::section {{
                background-color: {C["bg"]};
                color: {C["text_sub"]};
                font-family: 'JetBrains Mono';
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid {C["border"]};
                border-right: 1px solid {C["border"]};
            }}

            /* Status bar */
            QFrame#statusbar {{
                background-color: {C["white"]};
                border-top: 1px solid {C["border"]};
            }}
            QLabel#lbl_status {{
                font-family: 'JetBrains Mono';
                font-size: 10px;
                color: {C["text_sub"]};
            }}

            QScrollBar:vertical {{
                background: {C["bg"]};
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {C["border"]};
                border-radius: 3px;
            }}
        """)

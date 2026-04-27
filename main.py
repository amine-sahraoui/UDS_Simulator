# =============================================================================
# main.py
# UDS Simulator — Entry Point
# =============================================================================

import sys

from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QApplication, QDialog

from client.uds_client import UDSClient
from common.db_handler import DatabaseHandler
from ecu.ecu_simulator import ECUSimulator
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from utils import resource_path


def main() -> None:
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("logo_icon.ico")))
    app.setFont(QFont("Courier New", 10))

    # -- Init database
    db = DatabaseHandler(
        did_db_path="DIDs/did_database.json",
        users_path="DIDs/users.json",
    )

    # -- Login
    login = LoginWindow(db)
    if login.exec_() != QDialog.Accepted:
        sys.exit(0)

    role = login.logged_role
    # role = "admin"
    # -- Init ECU + Client
    ecu = ECUSimulator(db=db, role=role)
    client = UDSClient(ecu=ecu)

    # -- Main window
    window = MainWindow(client=client, ecu=ecu, role=role)
    window.setWindowIcon(QIcon(resource_path("logo_icon.ico")))
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

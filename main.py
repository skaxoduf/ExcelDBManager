
import sys

import sys
from PyQt6.QtWidgets import QApplication, QMessageBox

try:
    from src.gui import LoginDialog, MainWindow
except ImportError as e:
    # If GUI cannot be initialized due to missing modules in src.gui or its dependencies
    app = QApplication(sys.argv)
    QMessageBox.critical(None, "Import Error", f"Failed to import required modules.\nError: {e}\n\nPlease ensure 'sqlalchemy', 'pyodbc', 'pandas' are installed.")
    sys.exit(1)


def main():
    app = QApplication(sys.argv)
    # 주석테스트 
    
    login = LoginDialog()
    if login.exec() == LoginDialog.DialogCode.Accepted:
        window = MainWindow(login.db_manager)
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()





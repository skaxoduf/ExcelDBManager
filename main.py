
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
    
    # Apply Premium Dark Mode Stylesheet
    dark_style = """
    QWidget {
        background-color: #2b2b2b;
        color: #e0e0e0;
        font-family: 'Segoe UI', sans-serif;
        font-size: 10pt;
    }
    QLineEdit {
        background-color: #3a3a3a;
        border: 1px solid #555;
        border-radius: 5px;
        padding: 5px;
        selection-background-color: #3d8ec9;
    }
    QPushButton {
        background-color: #3d8ec9;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 8px 16px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #2b7ab0;
    }
    QPushButton:pressed {
        background-color: #1a5c85;
    }
    QMessageBox {
        background-color: #2b2b2b;
    }
    QLabel {
        font-weight: bold;
    }
    """
    app.setStyleSheet(dark_style)
    
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





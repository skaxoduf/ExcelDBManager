from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QMessageBox, QDialog, QFormLayout)
from src.db_manager import DBManager
from src.excel_handler import ExcelHandler
from src.crypto_utils import CryptoManager
import configparser
import os

CONFIG_FILE = "config.ini"

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MSSQL Database Connection")
        self.setFixedSize(400, 250)
        self.db_manager = None
        self.center_window()

    def center_window(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("e.g. localhost or IP")
        self.db_input = QLineEdit()
        self.db_input.setPlaceholderText("Database Name")
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Password")

        form_layout.addRow("Server:", self.server_input)
        form_layout.addRow("Database:", self.db_input)
        form_layout.addRow("User:", self.user_input)
        form_layout.addRow("Password:", self.password_input)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.try_connect)
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.connect_btn)
        btn_layout.addWidget(self.exit_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.load_config()

    def load_config(self):
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
            if 'MSSQL' in config:
                self.user_input.setText(config['MSSQL'].get('User', ''))
                
                # Decrypt password and other fields if they are encrypted
                # For this transition, we'll try to decrypt, if empty (meaning it was plain text or invalid),
                # we might need to handle it. But per request, we assume full encryption.
                # Let's fully implement decryption here.
                
                crypto = CryptoManager()
                
                # Helper to safely get and decrypt
                def get_decrypted(key):
                    val = config['MSSQL'].get(key, '')
                    decrypted = crypto.decrypt(val)
                    # Fallback: if decryption returns empty but val wasn't, it might be legacy plain text.
                    # Ideally we migrate. For now let's show decrypted.
                    return decrypted if decrypted else val

                self.server_input.setText(get_decrypted('Server'))
                self.db_input.setText(get_decrypted('Database'))
                self.user_input.setText(get_decrypted('User'))
                self.password_input.setText(get_decrypted('Password'))

    def save_config(self, server, db, user, password):
        config = configparser.ConfigParser()
        crypto = CryptoManager()
        
        config['MSSQL'] = {
            'Server': crypto.encrypt(server),
            'Database': crypto.encrypt(db),
            'User': crypto.encrypt(user),
            'Password': crypto.encrypt(password)
        }
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)

    def try_connect(self):
        server = self.server_input.text()
        db = self.db_input.text()
        user = self.user_input.text()
        password = self.password_input.text()

        if not all([server, db, user, password]):
            QMessageBox.warning(self, "Input Error", "All fields are required.")
            return

        manager = DBManager(server, db, user, password)
        if manager.connect():
            self.db_manager = manager
            self.save_config(server, db, user, password)
            QMessageBox.information(self, "Success", "Connected to database!")
            self.accept()
        else:
            QMessageBox.critical(self, "Connection Failed", "Could not connect to database.\nCheck your credentials.")

class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.setWindowTitle("Excel DB Manager")
        self.setGeometry(100, 100, 800, 600)
        self.center_window()   

    # 폼이 모니터 가운데에 위치..   
    def center_window(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)


        label = QLabel(f"Connected to: {self.db_manager.connection_string.split('@')[1]}") # Simple display
        layout.addWidget(label)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        self.export_btn = QPushButton("Export Schema to Excel")
        self.export_btn.clicked.connect(self.export_schema)
        self.sync_btn = QPushButton("Sync Excel to DB")
        self.sync_btn.clicked.connect(self.sync_schema)
        
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.sync_btn)
        layout.addLayout(btn_layout)

        self.statusBar().showMessage("Ready")

    def export_schema(self):
        self.statusBar().showMessage("Exporting schema...")
        
        try:
            # 1. Fetch Data
            schema_df = self.db_manager.get_all_schemas()
            routines_df = self.db_manager.get_procedures_and_functions()
            
            # 2. Export
            handler = ExcelHandler()
            success, msg = handler.export_schema(schema_df, routines_df)
            
            if success:
                QMessageBox.information(self, "Export Successful", msg)
                self.statusBar().showMessage("Export Completed")
                # Auto-open the file
                try:
                    os.startfile("ExcelDBManager.xlsx")
                except Exception as e:
                    self.statusBar().showMessage(f"Could not open file: {e}")
            else:
                QMessageBox.critical(self, "Export Failed", msg)
                self.statusBar().showMessage("Export Failed")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
            self.statusBar().showMessage("Error")

    def sync_schema(self):
        reply = QMessageBox.question(self, 'Sync Confirmation', 
                                     "This will update the database schema based on the Excel file.\n"
                                     "Are you sure you want to proceed?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.No:
            return

        self.statusBar().showMessage("Syncing schema from Excel...")
        
        try:
            # 1. Read Excel
            handler = ExcelHandler()
            df = handler.read_schema()
            
            if df is None:
                QMessageBox.warning(self, "Error", "Could not read 'ExcelDBManager.xlsx'.\nMake sure the file exists and is not open.")
                self.statusBar().showMessage("Sync Failed")
                return
                
            if df.empty:
                QMessageBox.warning(self, "Error", "Excel file seems empty.")
                self.statusBar().showMessage("Sync Failed")
                return

            # 2. Sync
            success, logs = self.db_manager.sync_schema(df)
            
            if success:
                # Show detailed logs if any
                msg = "\n".join(logs)
                if len(msg) > 500: msg = msg[:500] + "\n...(truncated)"
                
                QMessageBox.information(self, "Sync Successful", f"Database updated successfully.\n\nChanges:\n{msg}")
                self.statusBar().showMessage("Sync Completed")
            else:
                QMessageBox.critical(self, "Sync Failed", f"Errors occurred:\n{logs[0]}")
                self.statusBar().showMessage("Sync Failed")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unexpected error: {e}")
            self.statusBar().showMessage("Error")

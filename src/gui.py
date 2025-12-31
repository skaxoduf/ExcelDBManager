from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QMessageBox, QDialog, QFormLayout, QCheckBox)
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt
from src.db_manager import DBManager
from src.excel_handler import ExcelHandler
from src.crypto_utils import CryptoManager
import configparser
import os
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

CONFIG_FILE = "config.ini"

class ExcelFileHandler(FileSystemEventHandler, QObject):
    file_modified = pyqtSignal()

    def __init__(self, filename):
        super().__init__()
        # Store absolute path for robust comparison
        self.filename = os.path.abspath(filename)
        self.last_modified = time.time()

    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Check if the modified file matches our target
        if os.path.abspath(event.src_path) == self.filename:
            # Debounce: Prevent double events (which happen often with Excel)
            current_time = time.time()
            if current_time - self.last_modified > 1.0:
                self.last_modified = current_time
                # Emit signal to GUI thread
                self.file_modified.emit()

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MSSQL Database Connection")
        self.setFixedSize(400, 300)
        
        # Set Icon
        # Prioritize local file (dist folder) then dev path
        if os.path.exists("logo.png"):
            logo_path = "logo.png"
        elif os.path.exists("dist/logo.png"):
            logo_path = "dist/logo.png"
        else:
            logo_path = "src/assets/logo.png"

        if os.path.exists(logo_path):
             self.setWindowIcon(QIcon(logo_path))

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
        success, error_msg = manager.connect()
        if success:
            self.db_manager = manager
            self.save_config(server, db, user, password)
            QMessageBox.information(self, "Success", "Connected to database!")
            self.accept()
        else:
            QMessageBox.critical(self, "Connection Failed", f"Could not connect to database.\n\nError Details:\n{error_msg}\n\nPlease check your credentials and server status.")

class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.setWindowTitle("Excel DB Manager")
        
        # Set Icon
        if os.path.exists("logo.png"):
            self.setWindowIcon(QIcon("logo.png"))
        elif os.path.exists("dist/logo.png"):
            self.setWindowIcon(QIcon("dist/logo.png"))
        else:
            self.setWindowIcon(QIcon("src/assets/logo.png"))
            
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
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # 1. Logo & Title
        logo_label = QLabel()
        
        # Resolve logo path
        if os.path.exists("logo.png"):
            logo_path = "logo.png"
        elif os.path.exists("dist/logo.png"):
            logo_path = "dist/logo.png"
        else:
            logo_path = "src/assets/logo.png"
            
        logo_pixmap = QPixmap(logo_path)
             
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)

        title_label = QLabel("Excel DB Manager")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 24pt; font-weight: bold; color: #3d8ec9; margin-bottom: 20px;")
        layout.addWidget(title_label)
        
        # 2. Connection Info (Simplified)
        try:
            db_name = self.db_manager.connection_string.split('/')[3].split('?')[0]
        except:
            db_name = "Unknown DB"
            
        conn_label = QLabel(f"Connected to: {db_name}") 
        conn_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        conn_label.setStyleSheet("color: #888; font-size: 10pt;")
        layout.addWidget(conn_label)
        
        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.export_btn = QPushButton("Export Schema to Excel")
        self.export_btn.setMinimumHeight(50)
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self.export_schema)
        
        self.sync_btn = QPushButton("Sync Excel to DB")
        self.sync_btn.setMinimumHeight(50)
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.clicked.connect(lambda: self.sync_schema(auto=False))

        # Auto-Sync Checkbox
        self.auto_sync_chk = QCheckBox("Auto-Sync on Save")
        self.auto_sync_chk.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        self.auto_sync_chk.setToolTip("Automatically sync to DB when Excel file is saved.")
        
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.sync_btn)
        btn_layout.addWidget(self.auto_sync_chk)
        
        layout.addLayout(btn_layout)

        self.statusBar().showMessage("Ready")
        
        # Watchdog Observer
        self.observer = None
        self.watcher_handler = None
        self.current_excel_file = None

    def export_schema(self):
        self.statusBar().showMessage("Exporting schema...")
        
        try:
            # 1. Fetch Data
            schema_df = self.db_manager.get_all_schemas()
            routines_df = self.db_manager.get_procedures_and_functions()
            
            # 2. Export
            # Generate Filename: DBName_YYYYMMDD_HHMMSS.xlsx
            try:
                # Extract DB Name from connection string or input
                # connection_string format: mssql+pyodbc://user:pass@server/dbname?driver...
                # Simple parsing:
                db_name = self.db_manager.connection_string.split('/')[3].split('?')[0]
            except:
                db_name = "Database"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{db_name}_{timestamp}.xlsx"

            handler = ExcelHandler(filename=filename)
            success, msg = handler.export_schema(schema_df, routines_df)
            
            if success:
                QMessageBox.information(self, "Export Successful", msg)
                self.statusBar().showMessage("Export Completed")
                
                # Start Watching
                self.start_watching(filename)
                
                # Auto-open the file
                try:
                    os.startfile(filename)
                except Exception as e:
                    self.statusBar().showMessage(f"Could not open file: {e}")
            else:
                QMessageBox.critical(self, "Export Failed", msg)
                self.statusBar().showMessage("Export Failed")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
            self.statusBar().showMessage("Error")

    def start_watching(self, filename):
        # Stop existing observer
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.current_excel_file = os.path.abspath(filename)
        self.watcher_handler = ExcelFileHandler(self.current_excel_file)
        # Connect signal to slot
        self.watcher_handler.file_modified.connect(self.on_file_saved)
        
        self.observer = Observer()
        self.observer.schedule(self.watcher_handler, path=os.path.dirname(self.current_excel_file), recursive=False)
        self.observer.start()
        print(f"Started watching: {self.current_excel_file}")

    def on_file_saved(self):
        if self.auto_sync_chk.isChecked():
            # Add small delay to let Excel release lock fully
            QTimer.singleShot(500, lambda: self.sync_schema(auto=True))

    def sync_schema(self, auto=False):
        if not auto:
            reply = QMessageBox.question(self, 'Sync Confirmation', 
                                         "This will update the database schema based on the Excel file.\n"
                                         "Are you sure you want to proceed?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                         QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.No:
                return

        status_msg = "Auto-Syncing..." if auto else "Syncing schema from Excel..."
        self.statusBar().showMessage(status_msg)
        
        try:
            # If auto, use the current_excel_file known to watcher
            filename_to_read = "ExcelDBManager.xlsx"
            if auto and self.current_excel_file:
                 filename_to_read = self.current_excel_file
            
            # 1. Read Excel
            handler = ExcelHandler(filename=filename_to_read)
            df = handler.read_schema()
            
            if df is None:
                if not auto: 
                    QMessageBox.warning(self, "Error", f"Could not read '{filename_to_read}'.\nMake sure the file exists and is not open.")
                self.statusBar().showMessage("Sync Failed (File Read Error)")
                return
                
            if df.empty:
                if not auto:
                    QMessageBox.warning(self, "Error", "Excel file seems empty.")
                self.statusBar().showMessage("Sync Failed (Empty File)")
                return

            # 2. Sync
            success, logs = self.db_manager.sync_schema(df)
            
            if success:
                # Show detailed logs if any
                msg = "\n".join(logs)
                if len(msg) > 500: msg = msg[:500] + "\n...(truncated)"
                
                if not auto:
                    QMessageBox.information(self, "Sync Successful", f"Database updated successfully.\n\nChanges:\n{msg}")
                else:
                    print(f"Auto-Sync Log: {msg}") # Console log for auto
                    
                self.statusBar().showMessage("Sync Completed")
            else:
                if not auto:
                    QMessageBox.critical(self, "Sync Failed", f"Errors occurred:\n{logs[0]}")
                self.statusBar().showMessage("Sync Failed")
                
        except Exception as e:
            if not auto:
                QMessageBox.critical(self, "Error", f"Unexpected error: {e}")
            self.statusBar().showMessage(f"Error: {e}")

    def closeEvent(self, event):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        event.accept()

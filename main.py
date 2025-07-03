import sys
import os
import time
import threading
import requests
import mimetypes
import platform
import pygetwindow as gw
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, 
    QLineEdit, QMessageBox, QCheckBox, QHBoxLayout, QFormLayout, QToolButton
)
from PyQt5.QtGui import QFont, QMovie
from PyQt5.QtCore import Qt, QTimer
import pyautogui
import threading
from pynput import mouse, keyboard
from pynput.mouse import Listener as MouseListener
from pynput.keyboard import Listener as KeyboardListener
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QRunnable, pyqtSignal, QObject, QThreadPool
from PyQt5.QtCore import QThread, pyqtSignal, QObject

import json
from PyQt5.QtCore import QStandardPaths
try:
    from cryptography.fernet import Fernet
except ImportError:
    print("Warning: cryptography package not installed. Passwords will be stored in plain text.")
    Fernet = None
import base64
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

from dotenv import load_dotenv
load_dotenv()

import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Get the appropriate log directory
    if getattr(sys, 'frozen', False):
        # If the application is frozen (packaged by PyInstaller)
        log_dir = os.path.dirname(sys.executable)
    else:
        # If running in development
        log_dir = os.path.dirname(os.path.abspath(__file__))
    
    log_file = os.path.join(log_dir, 'effortraklog.log')
    
    # Create a logger
    logger = logging.getLogger('effortrak')
    logger.setLevel(logging.INFO)
    
    # Create a rotating file handler
    handler = RotatingFileHandler(
        log_file, 
        maxBytes=1024*1024,  # 1MB
        backupCount=5,
        encoding='utf-8'
    )
    
    # Create a formatter and add it to the handler
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(handler)
    
    return logger

# Initialize logger at module level
logger = setup_logging()



import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Global variables
USER_ID = None
ORG_ID = None
USER_NAME = None
LOGIN_TIME = None
API_BASE = None
ACCESS_TOKEN = None
DEVICE_TYPE = None


def reset_global_variables():
    """Reset all global variables to their initial state"""
    global USER_ID, ORG_ID, USER_NAME, LOGIN_TIME, ACCESS_TOKEN
    USER_ID = None
    ORG_ID = None
    USER_NAME = None
    LOGIN_TIME = None
    ACCESS_TOKEN = None
    
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

global HEADERS
HEADERS = {
    "Key": os.getenv("API_KEY"),
    "source": DEVICE_TYPE or "WINDOWS",
    "Content-Type": "application/json"
}

def set_device_type():
        global DEVICE_TYPE, HEADERS
        system = platform.system()
        release = platform.release()
        
        if system == "Windows":
            DEVICE_TYPE = f"WINDOWS_{release}"
        elif system == "Linux":
            DEVICE_TYPE = f"LINUX_{release}"
        elif system == "Darwin":
            DEVICE_TYPE = f"MACOS_{release}"
        else:
            DEVICE_TYPE = "DESKTOP"
            
        # Update headers with actual device type
        HEADERS["source"] = DEVICE_TYPE
        print(f"[DEBUG] Device type detected: {DEVICE_TYPE}")
        return DEVICE_TYPE

       
set_device_type()

class LoginThread(QThread):
    # Signal emits (success, message) as separate arguments
    finished = pyqtSignal(bool, str)
    
    def __init__(self, email, password):
        super().__init__()
        self.email = email
        self.password = password
        
    def run(self):
        try:
            # Test connection first
            connected, msg = test_api_connection()
            if not connected:
                self.finished.emit(False, msg)
                return
                
            # Perform login
            result = login_user(self.email, self.password)
            if result and result[0]:  # Check if user_id exists
                self.finished.emit(True, "Login successful")
            else:
                self.finished.emit(False, "Invalid credentials")
        except Exception as e:
            self.finished.emit(False, str(e))
            
class LoginSignals(QObject):
    result = pyqtSignal(tuple)
    error = pyqtSignal(str)

class LoginWorker(QRunnable):
    def __init__(self, email, password):
        super().__init__()
        self.email = email
        self.password = password
        self.signals = LoginSignals()
        self.setAutoDelete(True)
        
    def run(self):
        try:
            # Test API connection first with timeout
            connected, message = test_api_connection()
            if not connected:
                self.signals.error.emit(f"Connection failed: {message}")
                return
                
            # Perform login
            result = login_user(self.email, self.password)
            if result[0]:  # If user_id exists
                self.signals.result.emit(result)
            else:
                self.signals.error.emit("Invalid credentials")
        except requests.exceptions.Timeout:
            self.signals.error.emit("Connection timed out")
        except requests.exceptions.RequestException as e:
            self.signals.error.emit(f"Network error: {str(e)}")
        except Exception as e:
            self.signals.error.emit(f"Unexpected error: {str(e)}")


class APIUrlWindow(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.setWindowTitle("Effortrak")
        self.setFixedSize(600, 450)
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                font-family: Arial;
            }
            QLabel {
                color: #333333;
            }
            QLineEdit {
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 12px;
                font-size: 16px;
                min-width: 400px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 14px 35px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        # Check if we have all required credentials for auto-login
        saved_url = self.config.get("api_url")
        auto_login = self.config.get("auto_login", False)
        remember_creds = self.config.get("remember_credentials", False)
        has_credentials = self.config.get("saved_email") and self.config.get("saved_password")
        
        if saved_url and auto_login and has_credentials:
            global API_BASE
            API_BASE = saved_url.rstrip('/') + "/api/"
            
            # Show login window but don't show it - it will auto-login
            self.login_window = LoginWindow(self.config)
            self.login_window.show()
            self.close()  # Close the API URL window
            return
                    
        # If we get here, show the URL window
        self.initUI()
        
    def show_login_window(self):
        self.login_window = LoginWindow(self.config)
        self.login_window.show()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 40, 50, 40)
        layout.setSpacing(30)

        header = QLabel("Effortrak")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 32px; font-weight: bold;")

        subheader = QLabel("Welcome to Effortrak")
        subheader.setAlignment(Qt.AlignCenter)
        subheader.setStyleSheet("font-size: 20px; color: #555;")

        instruction = QLabel("Please enter your application location path to continue")
        instruction.setAlignment(Qt.AlignCenter)
        instruction.setStyleSheet("font-size: 16px; color: #666;")

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://tracker2.keylines.net")

        submit_btn = QPushButton("SUBMIT")
        submit_btn.clicked.connect(self.set_api_url)

        layout.addWidget(header)
        layout.addWidget(subheader)
        layout.addWidget(instruction)
        layout.addWidget(self.url_input, alignment=Qt.AlignCenter)
        layout.addWidget(submit_btn, alignment=Qt.AlignCenter)
        layout.addStretch()
        
        saved_url = self.config.get("api_url")
        if saved_url:
            self.url_input.setText(saved_url)
        

        self.setLayout(layout)


    def set_api_url(self):
        global API_BASE
        url = self.url_input.text().strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        clean_url = url.rstrip('/')
        API_BASE = clean_url + "/api/"
        
        print("[DEBUG] Entered set_api_url()")
        print(f"[DEBUG] Cleaned URL: {clean_url}")
        
        self.config.set("api_url", clean_url, autosave=False)  # don't freeze
        self.config.save_config()  # save manually when you're ready
        print("[DEBUG] Config manually saved after setting api_url")
        print("[DEBUG] Called config.set() for api_url")

        self.close()
        self.login_window = LoginWindow(self.config)
        self.login_window.show()  
        
def test_api_connection():
    """Test if the API endpoint is reachable"""
    if not API_BASE:
        return False, "API URL not set"

    try:
        test_url = API_BASE.replace("/api/", "/")
        response = requests.get(test_url, timeout=(3.05, 5))  # 3.05s connect, 5s read
        return True, "Connection successful"
    except requests.exceptions.Timeout:
        return False, "Connection timed out"
    except requests.exceptions.RequestException as e:
        return False, f"Connection failed: {str(e)}"
        
            
class LoginWindow(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.setWindowTitle("Effortrak")
        self.setFixedSize(600, 520)
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                font-family: Arial, sans-serif;
            }
            QLabel {
                color: #333333;
            }
            QLineEdit {
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 10px;
                font-size: 15px;
                min-width: 360px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 28px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QCheckBox {
                font-size: 14px;
            }
        """)
        
        self.initUI()
        self.setWindowFlags(Qt.Window)
        self.from_logout = False  # Add this flag
        
        if self.config.get("auto_login") and self.config.get("remember_credentials") and not self.from_logout:
            QTimer.singleShot(100, self.attempt_auto_login)
        
        
    def attempt_auto_login(self):
        if not self.config.get("auto_login") or not self.config.get("remember_credentials"):
            return
            
        email = self.config.get("saved_email")
        password = self.config.get("saved_password")
        
        if not email or not password:
            return

        # Hide the login window during auto-login attempt
        #self.hide()
        
        # Show a loading state
        self.email_input.setText(email)
        self.password_input.setText("*" * len(password))
        self.submit_btn.setEnabled(False) 
        self.submit_btn.setText("Logging in...")  
        
        # Perform login in a separate thread
        self.login_thread = LoginThread(email, password)
        self.login_thread.finished.connect(self.handle_login_result)
        self.login_thread.start()
            
                
    def perform_auto_login(self, email, password):
        user_id, org_id = login_user(email, password)
            
        if user_id:
            QTimer.singleShot(0, lambda: self.handle_successful_login(user_id, org_id))
        else:
            QTimer.singleShot(0, self.handle_failed_auto_login)
            
    def handle_successful_login(self, user_id, org_id):
        global USER_ID, ORG_ID
        USER_ID = user_id
        ORG_ID = org_id
        self.close()
        self.main_app = ScreenshotApp(self.config)
        self.main_app.show()

    def handle_failed_auto_login(self):
        self.submit_btn.setEnabled(True) 
        self.submit_btn.setText("SUBMIT")  
        self.password_input.clear()
        QMessageBox.warning(self, "Auto-Login Failed", "Could not log in with saved credentials")
            

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(50, 30, 50, 20)
        main_layout.setSpacing(20)

        # Header
        title = QLabel("Effortrak")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 30px; font-weight: bold;")

        subtitle = QLabel("Welcome to Effortrak")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 18px;")

        instruction = QLabel("Please enter your email and password to continue")
        instruction.setAlignment(Qt.AlignCenter)
        instruction.setStyleSheet("font-size: 14px; color: #555;")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addWidget(instruction)

        # Form layout
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        form_layout.setVerticalSpacing(15)
        form_layout.setHorizontalSpacing(15)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        form_layout.addRow("Email", self.email_input)
        
        password_container = QWidget()
        password_layout = QHBoxLayout(password_container)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(0)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        
        # Eye icon button
        self.toggle_password_btn = QToolButton()
        self.toggle_password_btn.setIcon(QIcon(resource_path('eye-closed.png')))  # Use your eye icon
        self.toggle_password_btn.setStyleSheet("""
            QToolButton {
                border: none;
                padding: 0 8px;
                background: transparent;
            }
            QToolButton:hover {
                background: rgba(0,0,0,0.1);
                border-radius: 4px;
            }
        """)
        self.toggle_password_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_password_btn.clicked.connect(self.toggle_password_visibility)
        
        password_layout.addWidget(self.password_input)
        password_layout.addWidget(self.toggle_password_btn)
        
        form_layout.addRow("Password", password_container)
        
        '''# Add remember me checkbox
        self.remember_check = QCheckBox("Remember me")
        self.remember_check.setChecked(self.config.get("remember_credentials", False))'''
        
        # Add auto-login checkbox (only enabled if remember me is checked)
        self.auto_login_check = QCheckBox("Auto-login")
        self.auto_login_check.setChecked(self.config.get("auto_login", False))
        
        main_layout.addLayout(form_layout)
        
        self.checkbox_layout = QHBoxLayout()
        self.checkbox_layout.addWidget(self.auto_login_check)
        self.checkbox_layout.addStretch()
        main_layout.addLayout(self.checkbox_layout)

        # Submit button
        self.submit_btn = QPushButton("SUBMIT")  # Store as instance variable
        self.submit_btn.setFixedWidth(140)
        self.submit_btn.clicked.connect(self.handle_login)
        main_layout.addWidget(self.submit_btn, alignment=Qt.AlignHCenter)

        # Links
        link_layout = QHBoxLayout()
        change_url = QLabel("<a href='#'>Change URL?</a>")
        change_url.linkActivated.connect(self.change_api_url)
        change_url.setOpenExternalLinks(False)
        
        mobile_login = QLabel("<a href='#'>Login with Mobile OTP</a>")
        mobile_login.linkActivated.connect(self.open_otp_login)

        link_layout.addWidget(change_url)
        link_layout.addStretch()
        link_layout.addWidget(mobile_login)
        main_layout.addLayout(link_layout)

        # Footer
        footer = QLabel("© 2002 – 2025 Keyline DigiTech All Rights Reserved")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("font-size: 12px; color: #999; margin-top: 20px;")
        main_layout.addStretch()
        main_layout.addWidget(footer)

        self.setLayout(main_layout)
        
    '''def on_remember_changed(self, state):
        # Enable/disable auto-login checkbox based on remember me state
        self.auto_login_check.setEnabled(state == Qt.Checked)'''
        
    def toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.Password:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.toggle_password_btn.setIcon(QIcon(resource_path('eye-open.png')))  # Open eye icon
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_password_btn.setIcon(QIcon(resource_path('eye-closed.png')))  # Closed eye icon
        
        
    def handle_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()

        if not email or not password:
            QMessageBox.warning(self, "Error", "Please enter both email and password")
            return

        # Disable UI
        print("[DEBUG] Login button clicked")
        self.set_ui_enabled(False)
    
        # Create and start thread
        self.login_thread = LoginThread(email, password)
        # Connect signal to slot with proper arguments
        self.login_thread.finished.connect(self.handle_login_result)
        self.login_thread.start()
        
    def handle_login_result(self, success, message):
        # Re-enable UI
        self.set_ui_enabled(True)

        if success:
            email = self.email_input.text().strip()
            password = self.password_input.text()  # Always get the current password
            
            # Check if password is masked (for auto-login case)
            if "*" in password:
                # If password is masked, use stored one
                password = self.config.get("saved_password")
                
            auto = self.auto_login_check.isChecked()
            
            # Only update config in memory
            self.config.set("saved_email", email, autosave=False)
            self.config.set("saved_password", password, autosave=False)
            self.config.set("remember_credentials", True, autosave=False)  # Always remember if login succeeds
            self.config.set("auto_login", auto, autosave=False)

            self.config.save_config()  # Explicit save only once

            print("[DEBUG] Config forcibly saved after login")
            
            # Proceed to load the main app
            global USER_ID, ORG_ID
            USER_ID, ORG_ID = login_user(email, password)
            self.close()
            self.main_app = ScreenshotApp(self.config)
            self.main_app.show()

    
    def handle_login_error(self, error):
        self.set_ui_enabled(True)
        QMessageBox.critical(self, "Error", f"Login failed: {error}")
        
    def set_ui_enabled(self, enabled):
        """Enable/disable UI elements"""
        self.email_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.auto_login_check.setEnabled(enabled)
        self.submit_btn.setEnabled(enabled)
        self.submit_btn.setText("SUBMIT" if enabled else "Logging in...")
    
        # Simple busy cursor feedback
        if enabled:
            QApplication.restoreOverrideCursor()
        else:
            QApplication.setOverrideCursor(Qt.WaitCursor)
    
        QApplication.processEvents()
        
    def open_otp_login(self):
        self.close()
        self.otp_window = OTPLoginWindow(self.config)
        self.otp_window.show()


    def change_api_url(self):
        self.close()
        self.api_window = APIUrlWindow(self.config)
        self.api_window.show()
        
    def closeEvent(self, event):
        # Clean up thread if running
        if hasattr(self, 'login_thread') and self.login_thread.isRunning():
            self.login_thread.quit()
            self.login_thread.wait(1000)  # Wait up to 1 second
        event.accept()

def login_user(email, password):
    global USER_NAME, LOGIN_TIME, ACCESS_TOKEN
    payload = {
        "email": email,
        "password": password,
        "device_token": "windows_pyqt",
        "fcm_token": "dummy_fcm"
    }
    
    try:
        if not API_BASE:
            raise ValueError("API base URL is not set")
            
        logger.info(f"Attempting login for email: {email}")
        response = requests.post(
            API_BASE + "signin",
            headers=HEADERS,
            json=payload,
            timeout=(3.05, 10) 
        )
        logger.debug(f"Login response status: {response.status_code}")
        print(f"[DEBUG] Login response status: {response.status_code}")
        response.raise_for_status()
         
        data = response.json()
        if not data.get("success"):
            logger.error(f"Login failed. Response: {data}")
            print(f"Login failed. Response: {data}")
            return None, None
            
        user_data = data["data"]
        USER_NAME = user_data.get("name", "Employee")
        LOGIN_TIME = datetime.now().strftime("%H:%M")
        ACCESS_TOKEN = user_data["app_access_token"]
        logger.info(f"Login successful for user: {USER_NAME}")
        return user_data["user_id"], user_data.get("org_id", 1)
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        print(f"Login error: {str(e)}")
        return None, None
    

class OTPLoginWindow(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.setWindowTitle("Effortrak - OTP Login")
        self.setFixedSize(600, 400)
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                font-family: Arial;
            }
            QLabel {
                color: #333333;
            }
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 10px;
                font-size: 15px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 28px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.otp_sent = False
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 40, 50, 20)
        layout.setSpacing(25)

        title = QLabel("Login with OTP")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Enter your mobile number")
        layout.addWidget(self.phone_input)

        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("Enter OTP")
        self.otp_input.setEchoMode(QLineEdit.Password)
        self.otp_input.setEnabled(False)
        layout.addWidget(self.otp_input)

        self.send_btn = QPushButton("Send OTP")
        self.send_btn.clicked.connect(self.send_otp)
        layout.addWidget(self.send_btn)

        self.verify_btn = QPushButton("Verify & Login")
        self.verify_btn.setEnabled(False)
        self.verify_btn.clicked.connect(self.verify_otp)
        layout.addWidget(self.verify_btn)

        back_btn = QPushButton("Back to Password Login")
        back_btn.clicked.connect(self.back_to_login)
        layout.addWidget(back_btn)

        self.setLayout(layout)

    def send_otp(self):
        phone = self.phone_input.text().strip()
        if not phone.isdigit() or len(phone) < 10:
            QMessageBox.warning(self, "Invalid", "Enter a valid 10-digit phone number.")
            return
        try:
            url = API_BASE + "signin-with-mobile"
            payload = {"phone": phone}
            response = requests.post(url, headers=HEADERS, json=payload)
            print("[DEBUG] OTP Send:", response.status_code, response.text)
            if response.status_code == 200 and response.json().get("success"):
                QMessageBox.information(self, "OTP Sent", "OTP sent successfully to your phone.")
                self.otp_input.setEnabled(True)
                self.verify_btn.setEnabled(True)
            else:
                QMessageBox.critical(self, "Error", "Failed to send OTP.")
        except Exception as e:
            QMessageBox.critical(self, "Exception", str(e))

    def verify_otp(self):
        phone = self.phone_input.text().strip()
        otp = self.otp_input.text().strip()
        try:
            url = API_BASE + "signin-validate-mobile"
            payload = {
                "phone": phone,
                "otp": otp,
                "device_token": "windows_pyqt",
                "fcm_token": "dummy_fcm"
            }
            response = requests.post(url, headers=HEADERS, json=payload)
            print("[DEBUG] OTP Verify:", response.status_code, response.text)
            if response.status_code == 200 and response.json().get("success"):
                data = response.json()["data"]
                global USER_ID, ORG_ID, USER_NAME, LOGIN_TIME, ACCESS_TOKEN
                USER_ID = data["user_id"]
                ORG_ID = data.get("org_id", 1)
                USER_NAME = data.get("name", "Employee")
                LOGIN_TIME = datetime.now().strftime("%H:%M")
                ACCESS_TOKEN = data.get("app_access_token")  # ✅ now correctly placed
                self.close()
                self.main_app = ScreenshotApp(self.config)
                self.main_app.show()
            else:
                QMessageBox.critical(self, "Invalid", "Incorrect OTP.")
        except Exception as e:
            QMessageBox.critical(self, "Exception", str(e))


    def back_to_login(self):
        self.close()
        self.login_window = LoginWindow(self.config)
        self.login_window.show()


def send_screenshot(user_id, org_id, file_path=None, idle_status=0):
    if not API_BASE or not ACCESS_TOKEN:
        logger.error("API base or token not set for screenshot upload")
        print("[ERROR] API base or token not set")
        return

    url = API_BASE.replace("/api/", "/api/screenshot/upload")
    logger.debug(f"Uploading screenshot to: {url}")
    print(f"[DEBUG] Uploading to: {url}")

    try:
        # Get active window title (app name)
        active_window = gw.getActiveWindow()
        app_name = active_window.title if active_window else "Unknown Application"
        logger.debug(f"Active window: {app_name}")
    except Exception as e:
        print(f"[WARNING] Could not get active window: {str(e)}")
        logger.warning(f"Could not get active window: {str(e)}")
        app_name = "Effortrak Screenshot App"

    data = {
        "user_id": str(user_id),
        "org_id": str(org_id),
        "app_name": app_name[:100],  # Truncate if too long
        "app_url": "",
        "idle_status": str(idle_status),
        "is_idle_notification": "true" if idle_status else "false"
    }

    print(f"[DEBUG] Payload data: {data}")
    logger.debug(f"Screenshot payload data: {data}")
    
    headers = {
        "Key": os.getenv("API_KEY"),
        "source": DEVICE_TYPE or "DESKTOP",
        "Authorization": ACCESS_TOKEN
    }

    try:
        if idle_status:
            # For idle status, we just send the data without any image
            response = requests.post(url, headers=headers, data=data)
        else:
            # For active screenshots, send the image as before
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "image/jpeg"
                
            with open(file_path, 'rb') as f:
                files = {
                    'image': (os.path.basename(file_path), f, mime_type)
                }
                response = requests.post(url, headers=headers, data=data, files=files)
        
        logger.info(f"Upload response - Status: {response.status_code}, Response: {response.text}")
        print("[API] Upload response:", response.status_code, response.text)
    except Exception as e:
        print("[ERROR] Upload failed:", str(e))
        logger.error(f"Upload error: {str(e)}")

'''def create_idle_image():
    """Create a static idle image if it doesn't exist"""
    idle_path = os.path.join("screenshots", "idle.jpg")
    if not os.path.exists(idle_path):
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (1280, 720), color='gray')
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            font = ImageFont.load_default()
        draw.text((400, 300), "USER IDLE", fill="white", font=font)
        img.save(idle_path, "JPEG", quality=50)
    return idle_path'''

class IdleMonitor:
    def __init__(self, parent):
        self.parent = parent
        self.last_activity = time.time()
        self.running = True
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.monitor_activity, daemon=True)
        self.thread.start()
        
    def monitor_activity(self):
        while self.running:
            with self.lock:
                idle_time = time.time() - self.last_activity
                # Update both the display and internal state
                self.parent.update_idle_state(idle_time)
            time.sleep(1)
            
    def report_activity(self):
        with self.lock:
            self.last_activity = time.time()
            
    def stop(self):
        self.running = False
        self.thread.join(timeout=1)

class InputListener:
    def __init__(self, idle_monitor):
        self.idle_monitor = idle_monitor
        self.mouse_listener = None
        self.keyboard_listener = None
        self._running = True
        
    def start(self):
        def on_activity(*args, **kwargs):
            if not self._running:
                return False  # Signal listener to stop
            self.idle_monitor.report_activity()
        
        # Mouse listener
        self.mouse_listener = MouseListener(
            on_move=on_activity,
            on_click=on_activity
        )
        self.mouse_listener.start()
        
        # Keyboard listener
        self.keyboard_listener = KeyboardListener(
            on_press=on_activity
        )
        self.keyboard_listener.start()
        
    def stop(self):
        self._running = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        # Ensure listeners are really stopped
        time.sleep(0.1)
        
class ScreenshotApp(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.setWindowTitle("Effortrak Screenshot App")
        self.setFixedSize(300, 500)
        self.setStyleSheet("background-color: white;")
        self.mouse_listener = None
        self.keyboard_listener = None
        self.screenshot_active = False
        self.thread = None
        self.idle_seconds = 0
        self.screenshot_interval = 300 # 5 minutes
        self.idle_threshold = 180  # 180 seconds
        self.was_idle = False
        self.last_input_time = time.time()
        self.idle_timer = QTimer()
        self.idle_timer.timeout.connect(self.reset_idle_timer)
        self.idle_timer.start(1000)
        self.tray_icon = None
        self.create_tray_icon()
        self.initUI()
        set_device_type()
        self.idle_monitor = IdleMonitor(self)
        self.input_listener = InputListener(self.idle_monitor)
        self.input_listener.start()
        self.load_window_geometry()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self._shutting_down = False
    
    def load_window_geometry(self):
        geometry = self.config.get("window_geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def save_window_geometry(self):
        self.config.set("window_geometry", self.saveGeometry())    
    
    def update_idle_display(self, idle_time):
        mins, secs = divmod(int(round(idle_time)), 60)
        self.idle_label.setText(f"Idle for: {mins:02}:{secs:02}")
        
        is_idle = idle_time >= self.idle_threshold
        
        # Update UI and state only when idle status changes
        if is_idle != self.was_idle:
            self.was_idle = is_idle
            if is_idle:
                self.active_circle.setText("Idle")
                self.active_circle.setStyleSheet("""
                    background-color: #42A5F5; 
                    color: white; 
                    font-size: 20px; 
                    border-radius: 75px;
                """)
            else:
                self.active_circle.setText("Running")
                self.active_circle.setStyleSheet("""
                    background-color: #4CAF50; 
                    color: white; 
                    font-size: 20px; 
                    border-radius: 75px;
                """)
        
    '''def set_device_type(self):
        global DEVICE_TYPE, HEADERS
        system = platform.system()
        release = platform.release()
        
        if system == "Windows":
            DEVICE_TYPE = f"WINDOWS_{release}"
        elif system == "Linux":
            DEVICE_TYPE = f"LINUX_{release}"
        elif system == "Darwin":
            DEVICE_TYPE = f"MACOS_{release}"
        else:
            DEVICE_TYPE = "DESKTOP"
            
        # Update headers with actual device type
        HEADERS["source"] = DEVICE_TYPE
        print(f"[DEBUG] Device type detected: {DEVICE_TYPE}")'''

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        self.setWindowIcon(QIcon(resource_path('icon.ico')))

        header = QLabel("Effortrak")
        header.setFont(QFont("Arial", 20, QFont.Bold))
        version = QLabel("(V1.0.1)")
        version.setFont(QFont("Arial", 10))

        header_layout = QHBoxLayout()
        header_layout.addWidget(header)
        header_layout.addWidget(version)
        main_layout.addLayout(header_layout)

        name = QLabel(f"{USER_NAME}")
        name.setFont(QFont("Arial", 11))
        self.checked_in = QLabel(f"Checked in today at {LOGIN_TIME} hrs")
        self.checked_in.setStyleSheet("color: gray;")

        main_layout.addWidget(name)
        main_layout.addWidget(self.checked_in)

        # Status Circle
        self.active_circle = QLabel("Inactive")
        self.active_circle.setAlignment(Qt.AlignCenter)
        self.active_circle.setFixedSize(150, 150)
        self.active_circle.setStyleSheet("""
            background-color: #A9A9A9; 
            color: white; 
            font-size: 20px; 
            border-radius: 75px;
        """)
        main_layout.addWidget(self.active_circle, alignment=Qt.AlignCenter)

        # Idle time label
        self.idle_label = QLabel("Idle for: 00:00")
        self.idle_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.idle_label)

        # Single toggle button (Start/Stop)
        self.toggle_btn = QPushButton("Start")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                border-radius: 20px;
                padding: 10px 20px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_screenshot)
        main_layout.addWidget(self.toggle_btn, alignment=Qt.AlignCenter)

        # Logout button
        logout_btn = QPushButton("LOGOUT")
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 14px;
                border-radius: 20px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        main_layout.addWidget(logout_btn)

        self.setLayout(main_layout)

    def create_tray_icon(self):
        # Create the tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.ico"))  # Make sure you have an icon file
        
        # Create a context menu
        tray_menu = QMenu()
        
        # Toggle action
        self.toggle_action = QAction("Start", self)
        self.toggle_action.triggered.connect(self.toggle_screenshot)
        tray_menu.addAction(self.toggle_action)
        
        # Open action
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.show_normal)
        tray_menu.addAction(open_action)
        
        # Logout action
        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self.logout)
        tray_menu.addAction(logout_action)
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
        
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # Left click
            self.show_normal()

    def show_normal(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()
        
    def closeEvent(self, event):
        # Minimize to tray instead of closing
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Effortrak",
            "Application is still running in the system tray",
            QSystemTrayIcon.Information,
            2000
        )

    def toggle_screenshot(self):
        if not self.screenshot_active:
            logger.info("Starting screenshot capture")
            # Start screenshot capture
            self.screenshot_active = True
            self.active_circle.setText("Running")
            self.active_circle.setStyleSheet("""
                background-color: #4CAF50; 
                color: white; 
                font-size: 20px; 
                border-radius: 75px;
            """)
            self.toggle_btn.setText("Stop")
            self.toggle_action.setText("Stop")
            self.thread = threading.Thread(target=self.screenshot_loop, daemon=True)
            self.thread.start()
        else:
            # Stop screenshot capture
            logger.info("Stopping screenshot capture")
            self.screenshot_active = False
            self.active_circle.setText("Inactive")
            self.active_circle.setStyleSheet("""
                background-color: #A9A9A9; 
                color: white; 
                font-size: 20px; 
                border-radius: 75px;
            """)
            self.toggle_btn.setText("Start")
            self.toggle_action.setText("Start")

    def logout(self):
        print("Logging out...")
        logger.info("User initiated logout")
        self._shutting_down = True
        
        # Disable auto-login for next time
        self.config.set("auto_login", False, autosave=False)
        self.config.save_config()
        
        # Stop screenshot capture
        self.screenshot_active = False
        
        # Stop monitoring
        if hasattr(self, 'input_listener'):
            self.input_listener.stop()
        
        if hasattr(self, 'idle_monitor'):
            self.idle_monitor.stop()
        
        # Safely check and stop thread
        if hasattr(self, 'thread') and self.thread is not None:
            if self.thread.is_alive():
                self.thread.join(0.5)  # Reduced timeout
        
        # Hide tray icon
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.hide()
        
        reset_global_variables()
        
        # Create and show login window
        self.login_window = LoginWindow(self.config)
        self.login_window.from_logout = True
        self.login_window.show()
        
        # Close current window
        self.close()

    def update_idle_state(self, idle_time):
        if not self.screenshot_active:
            self.active_circle.setText("Inactive")
            self.active_circle.setStyleSheet("""
                background-color: #A9A9A9;
                color: white;
                font-size: 20px;
                border-radius: 75px;
            """)
            self.was_idle = False
            return
        
        self.update_idle_display(idle_time)

        """Centralized method to handle idle state changes"""
        # Add hysteresis - only change state if difference is significant
        is_idle = idle_time >= self.idle_threshold
        
        # Only update if state changed
        if is_idle != self.was_idle:
            # Add small delay for state change from idle to active
            if not is_idle and self.was_idle:
                time.sleep(1)  # 1 second delay before switching back from idle
                # Recheck after delay
                with self.idle_monitor.lock:
                    is_idle = (time.time() - self.idle_monitor.last_activity) >= self.idle_threshold
                if is_idle:  # Still idle after delay
                    return
            
            self.was_idle = is_idle
            mins, secs = divmod(int(idle_time), 60)
            self.idle_label.setText(f"Idle for: {mins:02}:{secs:02}")
            
            if is_idle:
                self.active_circle.setText("Idle")
                self.active_circle.setStyleSheet("""
                    background-color: #42A5F5; 
                    color: white; 
                    font-size: 20px; 
                    border-radius: 75px;
                """)
            else:
                self.active_circle.setText("Running")
                self.active_circle.setStyleSheet("""
                    background-color: #4CAF50; 
                    color: white; 
                    font-size: 20px; 
                    border-radius: 75px;
                """)

    def screenshot_loop(self):
        os.makedirs("screenshots", exist_ok=True)
        target_size = (1280, 720)
        last_upload_time = 0
        idle_image_sent = False

        while self.screenshot_active and not self._shutting_down:
            try:
                # Get synchronized idle status
                with self.idle_monitor.lock:
                    is_idle = (time.time() - self.idle_monitor.last_activity) >= self.idle_threshold

                current_time = time.time()
                
                if is_idle:
                    if not idle_image_sent or (current_time - last_upload_time) >= self.screenshot_interval:  # 5 minutes
                        # Send idle image at reduced frequency
                        send_screenshot(USER_ID, ORG_ID, idle_status=1)
                        idle_image_sent = True
                        last_upload_time = current_time
                else:
                    # Only capture if not idle and enough time has passed
                    if (current_time - last_upload_time) >= 300:  # 300 seconds between active screenshots
                        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                        final_file = f"screenshots/{USER_ID}_{ORG_ID}_{timestamp}.jpg"
                        
                        # Capture and save screenshot
                        screenshot = pyautogui.screenshot()
                        screenshot = screenshot.resize(target_size)
                        screenshot.save(final_file, "JPEG", optimize=True, quality=50)
                        
                        # Upload and update state
                        send_screenshot(USER_ID, ORG_ID, final_file)
                        last_upload_time = current_time
                        idle_image_sent = False
                
                time.sleep(1)  # More frequent checking with logic-controlled uploads
                
            except Exception as e:
                logger.error(f"Screenshot error: {e}")
                time.sleep(5)

    def reset_idle_timer(self, *args):
        try:
            current_time = time.time()
            # Only update if significant time has passed (at least 1 second)
            if current_time - self.last_input_time >= 1:
                self.last_input_time = current_time
                if self.was_idle and self.screenshot_active:
                    # Add small delay before updating to running state
                    time.sleep(1)
                    # Recheck state after delay
                    with self.idle_monitor.lock:
                        is_idle = (time.time() - self.idle_monitor.last_activity) >= self.idle_threshold
                    if not is_idle:
                        self.active_circle.setText("Running")
                        self.active_circle.setStyleSheet("""
                            background-color: #4CAF50; 
                            color: white; 
                            font-size: 20px; 
                            border-radius: 75px;
                        """)
                        self.was_idle = False
        except Exception as e:
            print(f"Error in reset_idle_timer: {e}")
            
class ConfigManager:
    def __init__(self):
        self.lock = threading.Lock()
        # Get appropriate config directory based on OS
        config_dir = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
        if not config_dir:
            config_dir = os.path.expanduser("~")
        
        # Create config directory if it doesn't exist
        self.config_dir = config_dir
        os.makedirs(self.config_dir, exist_ok=True)
        
        self.config_file = os.path.join(self.config_dir, "config.json")
        self._init_crypto()
        self.config = self._load_config()
        
        
    def _init_crypto(self):
        """Initialize encryption key"""
        key_path = os.path.join(self.config_dir, ".encryption_key")
        
        # Try to load existing key or generate new one
        try:
            if os.path.exists(key_path):
                with open(key_path, 'rb') as f:
                    self.crypto_key = f.read()
            else:
                self.crypto_key = Fernet.generate_key()
                with open(key_path, 'wb') as f:
                    f.write(self.crypto_key)
        except Exception as e:
            print(f"Error initializing encryption: {e}")
            self.crypto_key = None
    
    def _encrypt(self, data):
        """Encrypt data if crypto is available"""
        if not self.crypto_key or not data or Fernet is None:
            return data
            
        try:
            f = Fernet(self.crypto_key)
            return f.encrypt(data.encode()).decode()
        except Exception as e:
            print(f"Encryption failed: {e}")
            return data

    def _decrypt(self, data):
        """Decrypt data if crypto is available"""
        if not self.crypto_key or not data or Fernet is None:
            return data
            
        try:
            f = Fernet(self.crypto_key)
            return f.decrypt(data.encode()).decode()
        except Exception as e:
            print(f"Decryption failed: {e}")
            return data
        
    def _load_config(self):
        """Load configuration from file or return defaults"""
        defaults = {
            "api_url": "",
            "remember_credentials": True,
            "saved_email": "",
            "saved_password": "",  # This will be encrypted
            "auto_login": False,
            "window_geometry": None
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    
                    # Decrypt password if it exists
                    if "saved_password" in loaded and loaded["saved_password"]:
                        loaded["saved_password"] = self._decrypt(loaded["saved_password"])
                        print("[DEBUG] Decrypted password:", loaded["saved_password"])
                    
                    return {**defaults, **loaded}
        except Exception as e:
            print(f"Error loading config: {e}")
        
        return defaults

    def save_config(self):
        with self.lock:
            """Save current configuration to file"""
            try:
                # Make a copy of config to encrypt password
                to_save = self.config.copy()
                if "saved_password" in to_save:
                    to_save["saved_password"] = self._encrypt(to_save["saved_password"])
            
                with open(self.config_file, 'w') as f:
                    json.dump(to_save, f, indent=4)
                    print("[DEBUG] Config saved to:", self.config_file)
                    print("[DEBUG] Saved contents:", to_save)
            except Exception as e:
                print(f"Error saving config: {e}")
    
    def get(self, key, default=None):
        with self.lock:
            return self.config.get(key, default)

    def set(self, key, value, autosave=True):
        with self.lock:
            self.config[key] = value
            if autosave:
                self.save_config()



if __name__ == "__main__":
    if platform.system() == 'Windows' and not is_admin():
        logger.info("Restarting as admin")
        run_as_admin()
        sys.exit(0)
        
    logger.info("Application starting")
    QThreadPool.globalInstance().setMaxThreadCount(5)
    reset_global_variables()
    app = QApplication(sys.argv)
    
    app.setApplicationName("Effortrak")
    app.setApplicationDisplayName("Effortrak")
    app.setOrganizationName("Keyline DigiTech")
    
    config_manager = ConfigManager()
    logger.info("Configuration loaded")
    
    # Check if we have all required info for auto-login
    saved_url = config_manager.get("api_url")
    auto_login = config_manager.get("auto_login", False)
    remember_creds = config_manager.get("remember_credentials", False)
    has_credentials = config_manager.get("saved_email") and config_manager.get("saved_password")
    
    if saved_url and auto_login and remember_creds and has_credentials:
        logger.info("Attempting auto-login")
        API_BASE = saved_url.rstrip('/') + "/api/"
        login_window = LoginWindow(config_manager)
        login_window.show()
    else:
        # Either no saved URL or not set to auto-login - show URL window
        logger.info("Showing API URL window (no auto-login)")
        url_window = APIUrlWindow(config_manager)
        url_window.show()
    
    sys.exit(app.exec_())
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
    QLineEdit, QMessageBox, QCheckBox, QHBoxLayout, QFormLayout
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
import pyautogui
import threading
from pynput import mouse, keyboard
from pynput.mouse import Listener as MouseListener
from pynput.keyboard import Listener as KeyboardListener
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction

from dotenv import load_dotenv
load_dotenv()

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


HEADERS = {
    "Key": os.getenv('EFFORTRAK_API_KEY'),
    "source": os.getenv('DEVICE_TYPE', 'DESKTOP'),
    "Content-Type": "application/json"
}


class APIUrlWindow(QWidget):
    def __init__(self):
        super().__init__()
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
        self.initUI()

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
        

        self.setLayout(layout)


    def set_api_url(self):
        global API_BASE
        url = self.url_input.text().strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        API_BASE = url.rstrip('/') + "/api/"
        self.close()
        self.login_window = LoginWindow()
        self.login_window.show()

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
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

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password", self.password_input)

        main_layout.addLayout(form_layout)

        # Submit button
        submit_btn = QPushButton("SUBMIT")
        submit_btn.setFixedWidth(140)
        submit_btn.clicked.connect(self.handle_login)
        main_layout.addWidget(submit_btn, alignment=Qt.AlignHCenter)

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
        
    def open_otp_login(self):
        self.close()
        self.otp_window = OTPLoginWindow()
        self.otp_window.show()



    def handle_login(self):
        global USER_ID, ORG_ID
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        user_id, org_id = login_user(email, password)

        if user_id:
            USER_ID = user_id
            ORG_ID = org_id
            self.close()
            self.main_app = ScreenshotApp()
            self.main_app.show()
        else:
            QMessageBox.critical(self, "Login Failed", "Invalid credentials.")

    def change_api_url(self):
        self.close()
        self.api_window = APIUrlWindow()
        self.api_window.show()

def login_user(email, password):
    global USER_NAME, LOGIN_TIME, ACCESS_TOKEN
    payload = {
        "email": email,
        "password": password,
        "device_token": "windows_pyqt",
        "fcm_token": "dummy_fcm"
    }
    try:
        response = requests.post(API_BASE + "signin", headers=HEADERS, json=payload)
        if response.status_code == 200 and response.json().get("success"):
            data = response.json()["data"]
            USER_NAME = data.get("name", "Employee")
            LOGIN_TIME = datetime.now().strftime("%H:%M")
            ACCESS_TOKEN = data["app_access_token"]  # Store the token
            print(f"[DEBUG] Login successful, token: {ACCESS_TOKEN}")
            return data["user_id"], data.get("org_id", 1)
    except Exception as e:
        print(f"Login error: {str(e)}")
    return None, None

class OTPLoginWindow(QWidget):
    def __init__(self):
        super().__init__()
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
                self.main_app = ScreenshotApp()
                self.main_app.show()
            else:
                QMessageBox.critical(self, "Invalid", "Incorrect OTP.")
        except Exception as e:
            QMessageBox.critical(self, "Exception", str(e))


    def back_to_login(self):
        self.close()
        self.login_window = LoginWindow()
        self.login_window.show()


def send_screenshot(user_id, org_id, file_path):
    if not API_BASE or not ACCESS_TOKEN:
        print("[ERROR] API base or token not set")
        return

    url = API_BASE.replace("/api/", "/api/screenshot/upload")
    print(f"[DEBUG] Uploading to: {url}")

    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "image/jpeg"

    try:
        # Get active window title (app name)
        active_window = gw.getActiveWindow()
        app_name = active_window.title if active_window else "Unknown Application"
    except Exception as e:
        print(f"[WARNING] Could not get active window: {str(e)}")
        app_name = "Effortrak Screenshot App"

    data = {
        "user_id": str(user_id),
        "org_id": str(org_id),
        "app_name": app_name[:100],  # Truncate if too long
        "app_url": ""
    }

    print(f"[DEBUG] Payload data: {data}")

    headers = {
        "Key": "4e1c3ee6861ac425437fa8b662651cde",
        "source": DEVICE_TYPE or "DESKTOP",  # Use actual device type or fallback
        "Authorization": ACCESS_TOKEN
    }

    try:
        with open(file_path, 'rb') as f:
            files = {
                'image': (os.path.basename(file_path), f, mime_type)
            }
            response = requests.post(url, headers=headers, data=data, files=files)
            print("[API] Screenshot upload:", response.status_code, response.text)
    except Exception as e:
        print("[ERROR] Upload failed:", str(e))

class IdleMonitor:
    def __init__(self, parent):
        self.parent = parent
        self.last_activity = time.time()
        self.running = True
        self.lock = threading.Lock()
        
        # Start monitoring thread
        self.thread = threading.Thread(target=self.monitor_activity, daemon=True)
        self.thread.start()
        
    def monitor_activity(self):
        while self.running:
            with self.lock:
                idle_time = time.time() - self.last_activity
                self.parent.update_idle_display(idle_time)
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
        
    def start(self):
        # Mouse listener
        self.mouse_listener = mouse.Listener(
            on_move=self.on_activity,
            on_click=self.on_activity
        )
        self.mouse_listener.start()
        
        # Keyboard listener
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_activity
        )
        self.keyboard_listener.start()
        
    def on_activity(self, *args, **kwargs):
        self.idle_monitor.report_activity()
        
    def stop(self):
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        
class ScreenshotApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Effortrak Screenshot App")
        self.setFixedSize(300, 500)
        self.setStyleSheet("background-color: white;")
        self.mouse_listener = None
        self.keyboard_listener = None
        self.screenshot_active = False
        self.thread = None
        self.idle_seconds = 0
        self.idle_threshold = 10  # 3 minutes in seconds
        self.was_idle = False
        self.last_input_time = time.time()
        self.idle_timer = QTimer()
        self.idle_timer.timeout.connect(self.reset_idle_timer)
        self.idle_timer.start(1000)
        self.tray_icon = None
        self.create_tray_icon()
        self.initUI()
        self.start_input_listeners()
        self.set_device_type()
        self.idle_monitor = IdleMonitor(self)
        self.input_listener = InputListener(self.idle_monitor)
        self.input_listener.start()
        
    
    def update_idle_display(self, idle_time):
        mins, secs = divmod(int(idle_time), 60)
        self.idle_label.setText(f"Idle for: {mins:02}:{secs:02}")
        
        if idle_time >= self.idle_threshold:
            if not self.was_idle:
                self.was_idle = True
                self.active_circle.setText("Idle")
                self.active_circle.setStyleSheet("""
                    background-color: #f44336; 
                    color: white; 
                    font-size: 20px; 
                    border-radius: 75px;
                """)
        else:
            if self.was_idle and self.screenshot_active:
                self.was_idle = False
                self.active_circle.setText("Running")
                self.active_circle.setStyleSheet("""
                    background-color: #FFA500; 
                    color: white; 
                    font-size: 20px; 
                    border-radius: 75px;
                """)
        
    def set_device_type(self):
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

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        self.setWindowIcon(QIcon(resource_path('your_icon.ico')))

        header = QLabel("Effortrak")
        header.setFont(QFont("Arial", 20, QFont.Bold))
        version = QLabel("(V1.2.3)")
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
        try:
            if hasattr(self, 'input_listener') and self.input_listener:
                self.input_listener.stop()
        except:
            pass
        
        try:
            if hasattr(self, 'idle_monitor') and self.idle_monitor:
                self.idle_monitor.stop()
        except:
            pass
            
        if not self.tray_icon or not self.tray_icon.isVisible():
            # Perform full logout
            self.screenshot_active = False
            if hasattr(self, 'thread') and self.thread and self.thread.is_alive():
                self.thread.join(timeout=1)
    
            reset_global_variables()
    
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.hide()
    
            self.login_window = LoginWindow()
            self.login_window.show()
        else:
            # Minimize to tray behavior
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Effortrak",
                "The app is still running in the system tray",
                QSystemTrayIcon.Information,
                2000
            )

    def toggle_screenshot(self):
        # Update the existing toggle_screenshot method to also update tray menu text
        if not self.screenshot_active:
            # Start screenshot capture
            self.screenshot_active = True
            self.active_circle.setText("Running")
            self.active_circle.setStyleSheet("""
                background-color: #FFA500; 
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
        self.input_listener.stop()
        self.idle_monitor.stop()
            
        # Stop any ongoing screenshot capture
        self.screenshot_active = False
    
        # Wait for the screenshot thread to finish if it's running
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
    
        # Hide the tray icon if it exists
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.hide()
            
        reset_global_variables()
        # Close the current window
        self.close()
    
        # Show the login window
        self.login_window = LoginWindow()
        self.login_window.show()

    def screenshot_loop(self):
        os.makedirs("screenshots", exist_ok=True)
        target_size = (1280, 720)

        while self.screenshot_active:
            current_idle_time = time.time() - self.last_input_time
            
            # Only take screenshot if not idle
            if current_idle_time < self.idle_threshold:
                timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                final_file = f"screenshots/{USER_ID}_{ORG_ID}_{timestamp}.jpg"

                screenshot = pyautogui.screenshot()
                screenshot = screenshot.resize(target_size)
                screenshot.save(final_file, "JPEG", optimize=True, quality=50)

                send_screenshot(USER_ID, ORG_ID, final_file)
                print(f"[📸] Screenshot saved and sent: {final_file}")
            else:
                print("[⏸️] User idle - skipping screenshot")
                
            time.sleep(5)


    def reset_idle_timer(self, *args):
        try:
            self.last_input_time = time.time()
            if self.was_idle and self.screenshot_active:
                self.active_circle.setText("Running")
                self.active_circle.setStyleSheet("""
                    background-color: #FFA500; 
                    color: white; 
                    font-size: 20px; 
                    border-radius: 75px;
                """)
                self.was_idle = False
        except Exception as e:
            print(f"Error in reset_idle_timer: {e}")

    def start_input_listeners(self):
        """Start mouse and keyboard listeners with proper error handling"""
        def on_move(x, y):
            self.reset_idle_timer()

        def on_click(x, y, button, pressed):
            self.reset_idle_timer()

        def on_press(key):
            self.reset_idle_timer()

        # Initialize listeners first
        self.mouse_listener = None
        self.keyboard_listener = None

        # Start mouse listener
        try:
            self.mouse_listener = MouseListener(
                on_move=on_move,
                on_click=on_click
            )
            self.mouse_listener.start()
        except Exception as e:
            print(f"Error starting mouse listener: {e}")
            self.mouse_listener = None

        # Start keyboard listener
        try:
            self.keyboard_listener = KeyboardListener(
                on_press=on_press
            )
            self.keyboard_listener.start()
        except Exception as e:
            print(f"Error starting keyboard listener: {e}")
            self.keyboard_listener = None

if __name__ == "__main__":
    reset_global_variables()  # Initialize all globals to None
    app = QApplication(sys.argv)
    login = APIUrlWindow()
    login.show()
    sys.exit(app.exec_())
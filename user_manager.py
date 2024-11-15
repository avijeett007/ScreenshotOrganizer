import os
import json
from datetime import datetime
import webbrowser
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                            QMessageBox, QWidget, QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Import platform-specific settings from app.py
try:
    from app import get_config_path, get_app_data_dir
except ImportError:
    # Fallback if app.py is not available
    import platform
    def get_app_data_dir():
        if platform.system() == "Windows":
            app_data = os.getenv('APPDATA')
            base_dir = os.path.join(app_data, 'ScreenshotOrganizer')
        elif platform.system() == "Darwin":  # macOS
            base_dir = os.path.expanduser('~/Library/Application Support/ScreenshotOrganizer')
        else:  # Linux/Unix
            base_dir = os.path.expanduser('~/.screenshotorganizer')
        os.makedirs(base_dir, exist_ok=True)
        return base_dir

    def get_config_path(filename):
        return os.path.join(get_app_data_dir(), filename)

class UserRegistrationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Screenshot Organizer by kno2gether")
        self.setModal(True)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Welcome title with styling
        title = QLabel("Welcome to Screenshot Organizer")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #1565C0;
                margin-bottom: 10px;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Creator info container
        creator_widget = QWidget()
        creator_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border: 1px solid #BBDEFB;
                border-radius: 8px;
                margin: 10px 0;
            }
            QLabel {
                color: #1565C0;
            }
        """)
        creator_layout = QHBoxLayout(creator_widget)
        creator_layout.setContentsMargins(15, 10, 15, 10)
        creator_layout.setSpacing(10)

        # Channel icon/logo
        channel_icon = QLabel("🎥")
        channel_icon.setStyleSheet("font-size: 24px;")
        creator_layout.addWidget(channel_icon)

        # Channel name and description
        channel_info = QVBoxLayout()
        channel_info.setSpacing(2)
        
        channel_name = QLabel("kno2gether")
        channel_name.setStyleSheet("font-size: 18px; font-weight: bold;")
        channel_info.addWidget(channel_name)
        
        channel_desc = QLabel("AI & Tech Tutorials")
        channel_desc.setStyleSheet("font-size: 12px; color: #666;")
        channel_info.addWidget(channel_desc)
        
        creator_layout.addLayout(channel_info)
        
        # YouTube button
        youtube_btn = QPushButton("Subscribe")
        youtube_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF0000;
                color: white;
                padding: 6px 15px;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
        """)
        youtube_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        youtube_btn.clicked.connect(self.open_youtube)
        creator_layout.addWidget(youtube_btn)

        layout.addWidget(creator_widget)

        # Instructions container
        instructions_widget = QWidget()
        instructions_widget.setStyleSheet("""
            QWidget {
                background-color: #E3F2FD;
                border: 1px solid #90CAF9;
                border-radius: 10px;
                padding: 20px;
            }
            QLabel {
                color: #424242;
                font-size: 14px;
                line-height: 1.4;
            }
        """)
        instructions_layout = QVBoxLayout(instructions_widget)
        
        instructions = QLabel(
            "Welcome to Screenshot Organizer!\n\n"
            "To get started, please complete these steps:\n"
            "1. Register using the form below\n"
            "2. Subscribe to our YouTube channel for tips and tutorials\n"
            "3. Click 'Done' to start using the application"
        )
        instructions.setWordWrap(True)
        instructions_layout.addWidget(instructions)
        layout.addWidget(instructions_widget)

        # Buttons container with styling
        button_container = QWidget()
        button_container.setStyleSheet("""
            QWidget {
                margin-top: 20px;
            }
        """)
        button_layout = QHBoxLayout()
        button_container.setLayout(button_layout)

        # Common button style
        button_style = """
            QPushButton {
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                color: white;
                min-width: 150px;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
        """

        # Register button
        register_btn = QPushButton("📝 Register Now")
        register_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #4CAF50;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        register_btn.clicked.connect(self.open_registration_form)

        # Done button
        done_btn = QPushButton("✅ Done")
        done_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #2196F3;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        done_btn.clicked.connect(self.accept)

        # Cancel button
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #f44336;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        # Add buttons to layout
        button_layout.addWidget(register_btn)
        button_layout.addWidget(done_btn)
        button_layout.addWidget(cancel_btn)

        layout.addWidget(button_container)
        self.setLayout(layout)

        # Set a minimum size for the dialog
        self.setMinimumWidth(700)
        self.setMinimumHeight(400)

    def open_registration_form(self):
        webbrowser.open('https://knolabs.biz/community')

    def open_youtube(self):
        webbrowser.open('https://www.youtube.com/@kno2gether')

class PromotionalDialog(QDialog):
    def __init__(self, parent=None, promo_data=None):
        super().__init__(parent)
        self.promo_data = promo_data
        self.setWindowTitle(promo_data["title"])
        self.setModal(True)
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Message label
        message_label = QLabel(promo_data["message"])
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(message_label)
        
        # Details label
        if "details" in promo_data:
            details_label = QLabel(promo_data["details"])
            details_label.setWordWrap(True)
            details_label.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 20px;")
            layout.addWidget(details_label)
        
        # Button container
        button_container = QWidget()
        button_layout = QHBoxLayout()
        button_container.setLayout(button_layout)
        
        # Open Offer button
        open_offer_btn = QPushButton("Open Offer")
        open_offer_btn.clicked.connect(self.open_offer)
        open_offer_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        button_layout.addWidget(open_offer_btn)
        button_layout.addWidget(close_btn)
        
        layout.addWidget(button_container)
        self.setLayout(layout)
    
    def open_offer(self):
        webbrowser.open(self.promo_data["form_url"])

class UserManager:
    def __init__(self):
        self.user_data_file = get_config_path('user_data.json')
        self.load_user_data()
        
    def load_user_data(self):
        if os.path.exists(self.user_data_file):
            with open(self.user_data_file, 'r') as f:
                self.user_data = json.load(f)
        else:
            self.user_data = {
                "registered": False,
                "registration_date": None,
                "last_promo_shown": None,
                "promo_history": []
            }
            self.save_user_data()
    
    def save_user_data(self):
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.user_data_file), exist_ok=True)
        with open(self.user_data_file, 'w') as f:
            json.dump(self.user_data, f)
    
    def is_registered(self):
        return self.user_data.get("registered", False)
    
    def mark_registered(self):
        self.user_data["registered"] = True
        self.user_data["registration_date"] = datetime.now().isoformat()
        self.save_user_data()
    
    def should_show_promo(self):
        """Check if it's time to show a promotional message"""
        last_shown = self.user_data.get("last_promo_shown")
        if not last_shown:
            return True
            
        last_shown_date = datetime.fromisoformat(last_shown)
        days_since_last = (datetime.now() - last_shown_date).days
        
        # Show promos every 7 days
        return days_since_last >= 7
    
    def record_promo_shown(self, promo_id):
        """Record that a promotional message was shown"""
        self.user_data["last_promo_shown"] = datetime.now().isoformat()
        self.user_data["promo_history"].append({
            "promo_id": promo_id,
            "shown_at": datetime.now().isoformat()
        })
        self.save_user_data()

def show_promotional_message(parent, promo_data):
    """Show a promotional message dialog and open the form URL in browser if clicked"""
    dialog = QMessageBox(parent)
    dialog.setWindowTitle(f"kno2gether - {promo_data['title']}")
    dialog.setText(promo_data["message"])
    if "details" in promo_data:
        dialog.setInformativeText(promo_data["details"])
    
    # Set icon based on promotion type
    dialog.setIcon(QMessageBox.Icon.Information)
    
    # Add custom buttons with styling
    button_style = """
        QPushButton {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            color: white;
            min-width: 100px;
        }
        QPushButton:hover {
            opacity: 0.9;
        }
    """
    
    # Create and style the OK button
    ok_button = QPushButton("View Offer")
    ok_button.setStyleSheet(button_style + """
        QPushButton {
            background-color: #4CAF50;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
    """)
    dialog.addButton(ok_button, QMessageBox.ButtonRole.AcceptRole)
    
    # Create and style the Cancel button
    cancel_button = QPushButton("Cancel")
    cancel_button.setStyleSheet(button_style + """
        QPushButton {
            background-color: #757575;
        }
        QPushButton:hover {
            background-color: #616161;
        }
    """)
    dialog.addButton(cancel_button, QMessageBox.ButtonRole.RejectRole)
    
    # Store the URL to be opened
    target_url = promo_data.get("form_url", "")
    logger.info(f"Promotion dialog created for URL: {target_url}")
    
    # Set default button
    dialog.setDefaultButton(ok_button)
    
    # Show dialog and handle response
    clicked_button = dialog.exec()
    
    # Check which button was clicked and open the URL from promotions.json
    if dialog.clickedButton() == ok_button and target_url:
        logger.info(f"Opening promotion URL: {target_url}")
        webbrowser.open(target_url)
    
    return True

import os
import json
from datetime import datetime
import webbrowser
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                            QMessageBox, QWidget, QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices

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
        self.setMinimumSize(500, 300)
        
        layout = QVBoxLayout()
        
        # Add branding
        branding = QLabel("Screenshot Organizer")
        branding.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2196F3;
                margin: 10px;
                text-align: center;
            }
        """)
        branding.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(branding)
        
        # Add creator info
        creator = QLabel("Created by kno2gether")
        creator.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #666;
                margin-bottom: 20px;
                text-align: center;
            }
        """)
        creator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(creator)
        
        # Add instructions
        instructions = QLabel(
            "Welcome to Screenshot Organizer! \n\n"
            "To get started, please complete these steps:\n"
            "1. Register using the form below\n"
            "2. Subscribe to our YouTube channel for tips and tutorials\n"
            "3. Click 'Done' to start using the application"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #333;
                margin: 10px;
                padding: 15px;
                background-color: #f0f0f0;
                border-radius: 5px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(instructions)
        
        # Button container
        button_container = QWidget()
        button_layout = QHBoxLayout()
        button_container.setLayout(button_layout)
        
        # Register button
        register_btn = QPushButton("")
        register_btn.clicked.connect(self.open_registration_form)
        register_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        # YouTube button
        youtube_btn = QPushButton("")
        youtube_btn.clicked.connect(self.open_youtube)
        youtube_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF0000;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
        """)
        
        # Done button
        done_btn = QPushButton("")
        done_btn.clicked.connect(self.accept)
        done_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        # Cancel button
        cancel_btn = QPushButton("")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        button_layout.addWidget(register_btn)
        button_layout.addWidget(youtube_btn)
        button_layout.addWidget(done_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addWidget(button_container)
        
        # Add footer
        footer = QLabel("Subscribe to kno2gether on YouTube for AI tutorials and tech tips!")
        footer.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #666;
                margin-top: 20px;
                text-align: center;
                font-style: italic;
            }
        """)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)
        
        self.setLayout(layout)
    
    def open_registration_form(self):
        webbrowser.open("https://knolabs.biz/affiliate-demo")
    
    def open_youtube(self):
        webbrowser.open("https://www.youtube.com/@kno2gether")

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
    msg = QMessageBox(parent)
    msg.setWindowTitle(f"kno2gether - {promo_data['title']}")
    msg.setText(promo_data["message"])
    if "details" in promo_data:
        msg.setInformativeText(promo_data["details"])
    
    # Add custom buttons
    if "form_url" in promo_data:
        if "youtube" in promo_data["form_url"].lower():
            action_btn = msg.addButton("", QMessageBox.ButtonRole.ActionRole)
        else:
            action_btn = msg.addButton("", QMessageBox.ButtonRole.ActionRole)
    close_btn = msg.addButton("", QMessageBox.ButtonRole.RejectRole)
    
    msg.exec()
    
    # Check if the user clicked the action button
    if msg.clickedButton() == action_btn and "form_url" in promo_data:
        webbrowser.open(promo_data["form_url"])
    
    return True

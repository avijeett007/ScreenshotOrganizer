import sys
import os
import json
import platform
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QComboBox, QSystemTrayIcon, QMenu, QMessageBox,
                            QFileDialog, QStackedWidget, QDialog, QCheckBox, QScrollArea)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QAction
import pystray
from PIL import Image
from screenshot_organizer import process_screenshots
from user_manager import UserManager, UserRegistrationDialog, show_promotional_message
from datetime import datetime
import logging
import traceback
import webbrowser

# Set up logging
logger = logging.getLogger(__name__)

# Platform-specific settings
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

def get_app_data_dir():
    """Get the appropriate directory for storing application data"""
    if IS_WINDOWS:
        app_data = os.getenv('APPDATA')
        base_dir = os.path.join(app_data, 'ScreenshotOrganizer')
    elif IS_MAC:
        base_dir = os.path.expanduser('~/Library/Application Support/ScreenshotOrganizer')
    else:  # Linux/Unix
        base_dir = os.path.expanduser('~/.screenshotorganizer')
    
    # Create directory if it doesn't exist
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def get_config_path(filename):
    """Get the full path for a configuration file"""
    return os.path.join(get_app_data_dir(), filename)

def get_default_screenshot_dir():
    """Get the default screenshots directory for the current platform"""
    if IS_WINDOWS:
        return os.path.expanduser('~/Pictures/Screenshots')
    elif IS_MAC:
        return os.path.expanduser('~/Desktop')  # macOS typically saves screenshots to Desktop
    else:
        return os.path.expanduser('~/Pictures')

class ProcessingThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, folders):
        super().__init__()
        self.folders = folders
        self.is_running = True

    def run(self):
        try:
            for folder in self.folders:
                if not self.is_running:
                    break
                if not os.path.exists(folder):
                    self.error.emit(f"Folder not found: {folder}")
                    continue
                self.progress.emit(f"Processing folder: {folder}")
                try:
                    process_screenshots(folder)
                except Exception as e:
                    self.error.emit(f"Error processing folder {folder}: {str(e)}")
                    logger.error(f"Error processing folder {folder}: {str(e)}")
                    logger.error(traceback.format_exc())
                    continue
            self.finished.emit()
        except Exception as e:
            error_msg = f"Error during processing: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error.emit(error_msg)

    def stop(self):
        self.is_running = False

class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.loadSettings()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Title
        title = QLabel("Settings")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #1565C0;
                margin-bottom: 20px;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Settings Container
        settings_widget = QWidget()
        settings_layout = QVBoxLayout()
        settings_widget.setLayout(settings_layout)
        settings_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border: 1px solid #BBDEFB;
                border-radius: 10px;
                padding: 20px;
            }
            QLabel {
                color: #424242;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #BBDEFB;
                border-radius: 4px;
                background-color: #FFFFFF;
                color: #424242;
                min-width: 300px;
            }
            QLineEdit:focus {
                border: 2px solid #1976D2;
            }
            QComboBox {
                padding: 8px;
                border: 1px solid #BBDEFB;
                border-radius: 4px;
                background-color: #FFFFFF;
                color: #424242;
                min-width: 200px;
            }
            QComboBox:focus {
                border: 2px solid #1976D2;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #424242;
                margin-right: 8px;
            }
        """)

        # Provider selection
        provider_layout = QHBoxLayout()
        provider_label = QLabel("AI Provider:")
        provider_label.setStyleSheet("font-size: 14px; min-width: 120px; font-weight: bold;")
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Together AI", "Ollama"])
        self.provider_combo.currentTextChanged.connect(self.onProviderChanged)
        provider_layout.addWidget(provider_label)
        provider_layout.addWidget(self.provider_combo)
        provider_layout.addStretch()
        settings_layout.addLayout(provider_layout)

        # Model name
        model_layout = QHBoxLayout()
        model_label = QLabel("Model Name:")
        model_label.setStyleSheet("font-size: 14px; min-width: 120px; font-weight: bold;")
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Llama-3.2-11B-Vision-Instruct-Turbo")
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_input)
        model_layout.addStretch()
        settings_layout.addLayout(model_layout)

        # Together AI settings
        self.together_url_layout = QHBoxLayout()
        self.together_url_label = QLabel("Together AI URL:")
        self.together_url_label.setStyleSheet("font-size: 14px; min-width: 120px; font-weight: bold;")
        self.together_url_input = QLineEdit()
        self.together_url_input.setPlaceholderText("https://api.together.xyz")
        self.together_url_layout.addWidget(self.together_url_label)
        self.together_url_layout.addWidget(self.together_url_input)
        self.together_url_layout.addStretch()
        settings_layout.addLayout(self.together_url_layout)

        self.together_key_layout = QHBoxLayout()
        self.together_key_label = QLabel("Together AI Key:")
        self.together_key_label.setStyleSheet("font-size: 14px; min-width: 120px; font-weight: bold;")
        self.together_key_input = QLineEdit()
        self.together_key_layout.addWidget(self.together_key_label)
        self.together_key_layout.addWidget(self.together_key_input)
        self.together_key_layout.addStretch()
        settings_layout.addLayout(self.together_key_layout)

        # Ollama settings
        self.ollama_url_layout = QHBoxLayout()
        self.ollama_url_label = QLabel("Ollama Base URL:")
        self.ollama_url_label.setStyleSheet("font-size: 14px; min-width: 120px; font-weight: bold;")
        self.ollama_url_input = QLineEdit()
        self.ollama_url_input.setPlaceholderText("http://localhost:11434")
        self.ollama_url_layout.addWidget(self.ollama_url_label)
        self.ollama_url_layout.addWidget(self.ollama_url_input)
        self.ollama_url_layout.addStretch()
        settings_layout.addLayout(self.ollama_url_layout)

        self.ollama_key_layout = QHBoxLayout()
        self.ollama_key_label = QLabel("Ollama API Key:")
        self.ollama_key_label.setStyleSheet("font-size: 14px; min-width: 120px; font-weight: bold;")
        self.ollama_key_input = QLineEdit()
        self.ollama_key_input.setPlaceholderText("Optional")
        self.ollama_key_layout.addWidget(self.ollama_key_label)
        self.ollama_key_layout.addWidget(self.ollama_key_input)
        self.ollama_key_layout.addStretch()
        settings_layout.addLayout(self.ollama_key_layout)

        layout.addWidget(settings_widget)

        # Save button
        save_btn = QPushButton(" Save Settings")
        save_btn.clicked.connect(self.saveSettings)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                min-width: 150px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #388E3C;
            }
        """)
        save_btn_layout = QHBoxLayout()
        save_btn_layout.addStretch()
        save_btn_layout.addWidget(save_btn)
        save_btn_layout.addStretch()
        layout.addLayout(save_btn_layout)

        # Add stretch to push everything to the top
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Initially hide Ollama settings
        self.hideOllamaSettings()

    def onProviderChanged(self, provider):
        if provider == "Ollama":
            self.hideTogetherSettings()
            self.showOllamaSettings()
        else:
            self.showTogetherSettings()
            self.hideOllamaSettings()

    def hideTogetherSettings(self):
        self.together_url_label.hide()
        self.together_url_input.hide()
        self.together_key_label.hide()
        self.together_key_input.hide()

    def showTogetherSettings(self):
        self.together_url_label.show()
        self.together_url_input.show()
        self.together_key_label.show()
        self.together_key_input.show()

    def hideOllamaSettings(self):
        self.ollama_url_label.hide()
        self.ollama_url_input.hide()
        self.ollama_key_label.hide()
        self.ollama_key_input.hide()

    def showOllamaSettings(self):
        self.ollama_url_label.show()
        self.ollama_url_input.show()
        self.ollama_key_label.show()
        self.ollama_key_input.show()

    def loadSettings(self):
        config_path = get_config_path('settings.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                settings = json.load(f)
                self.provider_combo.setCurrentText(settings.get('provider', 'Together AI'))
                self.model_input.setText(settings.get('model', 'Llama-3.2-11B-Vision-Instruct-Turbo'))
                
                # Together AI settings
                self.together_url_input.setText(settings.get('together_url', 'https://api.together.xyz'))
                self.together_key_input.setText(settings.get('together_api_key', ''))
                
                # Ollama settings
                self.ollama_url_input.setText(settings.get('ollama_url', 'http://localhost:11434'))
                self.ollama_key_input.setText(settings.get('ollama_api_key', ''))
                
                # Ensure correct fields are shown/hidden
                self.onProviderChanged(settings.get('provider', 'Together AI'))

    def saveSettings(self):
        config_path = get_config_path('settings.json')
        settings = {
            'provider': self.provider_combo.currentText(),
            'model': self.model_input.text() or 'Llama-3.2-11B-Vision-Instruct-Turbo',
            'together_url': self.together_url_input.text() or 'https://api.together.xyz',
            'together_api_key': self.together_key_input.text(),
            'ollama_url': self.ollama_url_input.text() or 'http://localhost:11434',
            'ollama_api_key': self.ollama_key_input.text()
        }
        with open(config_path, 'w') as f:
            json.dump(settings, f)
        QMessageBox.information(self, "Success", "Settings saved successfully!")

class FolderWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.folders = []
        self.initUI()
        self.loadFolders()

    def initUI(self):
        layout = QVBoxLayout()
        
        # Folder selection buttons and labels
        self.folder_layouts = []
        for i in range(3):
            h_layout = QHBoxLayout()
            label = QLabel(f"Folder {i+1}:")
            path_label = QLabel("No folder selected")
            browse_btn = QPushButton("Browse")
            browse_btn.clicked.connect(lambda checked, x=i: self.browseFolderPath(x))
            
            h_layout.addWidget(label)
            h_layout.addWidget(path_label)
            h_layout.addWidget(browse_btn)
            layout.addLayout(h_layout)
            self.folder_layouts.append((path_label, browse_btn))

        # Save button
        save_btn = QPushButton("Save Folders")
        save_btn.clicked.connect(self.saveFolders)
        layout.addWidget(save_btn)

        self.setLayout(layout)

    def browseFolderPath(self, index):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            if index >= len(self.folders):
                self.folders.append(folder)
            else:
                self.folders[index] = folder
            self.folder_layouts[index][0].setText(folder)

    def loadFolders(self):
        config_path = get_config_path('folders.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.folders = json.load(f)
                for i, folder in enumerate(self.folders[:3]):
                    self.folder_layouts[i][0].setText(folder)

    def saveFolders(self):
        config_path = get_config_path('folders.json')
        with open(config_path, 'w') as f:
            json.dump(self.folders, f)
        QMessageBox.information(self, "Success", "Folders saved successfully!")

class DashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.loadStats()

    def initUI(self):
        # Create a scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Create main widget for scroll area
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Welcome Section
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout()
        welcome_widget.setLayout(welcome_layout)
        welcome_widget.setStyleSheet("""
            QWidget {
                background-color: #E3F2FD;
                border: 1px solid #90CAF9;
                border-radius: 10px;
                padding: 15px;
            }
        """)

        # Title and creator in one row
        title_layout = QHBoxLayout()
        
        title = QLabel("Welcome to Screenshot Organizer")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1565C0;")
        title_layout.addWidget(title)
        
        creator_layout = QHBoxLayout()
        creator_layout.setSpacing(5)
        
        by_label = QLabel("by")
        by_label.setStyleSheet("color: #666; font-size: 14px;")
        creator_layout.addWidget(by_label)
        
        channel_label = QLabel("kno2gether")
        channel_label.setStyleSheet("color: #1565C0; font-size: 14px; font-weight: bold;")
        creator_layout.addWidget(channel_label)
        
        youtube_btn = QPushButton("Subscribe")
        youtube_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF0000;
                color: white;
                padding: 4px 12px;
                border: none;
                border-radius: 3px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
        """)
        youtube_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        youtube_btn.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/channel/UCxgkN3luQgLQOd_L7tbOdhQ/join'))
        creator_layout.addWidget(youtube_btn)
        
        creator_layout.addStretch()
        title_layout.addLayout(creator_layout)
        welcome_layout.addLayout(title_layout)

        layout.addWidget(welcome_widget)

        # Stats Section
        stats_widget = QWidget()
        stats_layout = QVBoxLayout()
        stats_widget.setLayout(stats_layout)
        stats_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border: 1px solid #BBDEFB;
                border-radius: 10px;
                padding: 15px;
            }
        """)

        stats_title = QLabel("Statistics")
        stats_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1565C0;")
        stats_layout.addWidget(stats_title)

        self.stats_label = QLabel()
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("font-size: 14px; line-height: 1.4; color: #424242;")
        stats_layout.addWidget(self.stats_label)

        layout.addWidget(stats_widget)

        # Getting Started Section
        guide_widget = QWidget()
        guide_layout = QVBoxLayout()
        guide_widget.setLayout(guide_layout)
        guide_widget.setStyleSheet("""
            QWidget {
                background-color: #FFF3E0;
                border: 1px solid #FFE0B2;
                border-radius: 10px;
                padding: 15px;
            }
        """)

        guide_title = QLabel("Getting Started")
        guide_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #E65100;")
        guide_layout.addWidget(guide_title)

        steps = [
            "1. Go to Settings and configure your AI provider (Together AI or Ollama)",
            "2. Click on Folders to select up to 3 folders for organizing screenshots",
            "3. Review and accept the AI processing consent",
            "4. Click Start Processing to begin organizing your screenshots"
        ]
        
        for step in steps:
            step_label = QLabel(step)
            step_label.setStyleSheet("font-size: 14px; margin: 3px 0; color: #424242;")
            guide_layout.addWidget(step_label)

        layout.addWidget(guide_widget)

        # Consent Section
        consent_widget = QWidget()
        consent_layout = QVBoxLayout()
        consent_widget.setLayout(consent_layout)
        consent_widget.setStyleSheet("""
            QWidget {
                background-color: #FFEBEE;
                border: 1px solid #FFCDD2;
                border-radius: 10px;
                padding: 15px;
            }
        """)

        consent_title = QLabel("Processing Consent")
        consent_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #C62828;")
        consent_layout.addWidget(consent_title)

        self.consent_checkbox = QCheckBox(
            "I consent to:\n"
            "• Sending screenshots to AI services for processing\n"
            "• Allowing the app to organize files into subfolders"
        )
        self.consent_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                line-height: 1.4;
                color: #424242;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #C62828;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #C62828;
                border: 2px solid #C62828;
                border-radius: 3px;
            }
        """)
        consent_layout.addWidget(self.consent_checkbox)

        layout.addWidget(consent_widget)
        
        # Set the main widget as the scroll area's widget
        scroll.setWidget(main_widget)
        
        # Create the final layout
        final_layout = QVBoxLayout(self)
        final_layout.setContentsMargins(0, 0, 0, 0)
        final_layout.addWidget(scroll)
        
        self.setLayout(final_layout)

    def loadStats(self):
        config_path = get_config_path('settings.json')
        try:
            with open(config_path, 'r') as f:
                settings = json.load(f)
                stats = settings.get('stats', {})
                
                total_images = stats.get('total_images_processed', 0)
                last_processed = stats.get('last_processed_date')
                categories = stats.get('categories_created', [])
                
                if total_images == 0:
                    stats_text = "No images have been processed yet.\n\nFollow the Getting Started guide below to begin organizing your screenshots!"
                else:
                    stats_text = f"Total Images Processed: {total_images}\n"
                    if last_processed:
                        stats_text += f"Last Processed: {last_processed}\n"
                    if categories:
                        stats_text += f"Categories Created: {', '.join(categories)}"
                
                self.stats_label.setText(stats_text)
        except Exception as e:
            self.stats_label.setText("No processing history available.\n\nFollow the Getting Started guide below to begin organizing your screenshots!")

    def hasConsent(self):
        return self.consent_checkbox.isChecked()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize configuration files first
        initialize_config_files()
        
        # Initialize user manager and check registration
        self.user_manager = UserManager()
        if not self.check_registration():
            sys.exit()
            
        self.initUI()
        self.processing_thread = None
        
        # Set up promotional timer
        self.promo_timer = QTimer()
        self.promo_timer.timeout.connect(self.check_promotions)
        self.promo_timer.start(3600000)  # Check every hour
        
        # Check promotions on startup (delayed by 5 seconds)
        QTimer.singleShot(5000, self.check_promotions)

    def check_registration(self):
        """Check if user is registered, if not show registration dialog"""
        if not self.user_manager.is_registered():
            dialog = UserRegistrationDialog(self)
            result = dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                self.user_manager.mark_registered()
                return True
            return False
        return True

    def check_promotions(self):
        if not self.user_manager.should_show_promo():
            return
            
        try:
            config_path = get_config_path('promotions.json')
            with open(config_path, 'r') as f:
                promo_data = json.load(f)
                
            for promo in promo_data.get('promotions', []):
                # Check if promotion is currently active
                start_date = datetime.strptime(promo['start_date'], '%Y-%m-%d')
                end_date = datetime.strptime(promo['end_date'], '%Y-%m-%d')
                current_date = datetime.now()
                
                if start_date <= current_date <= end_date:
                    show_promotional_message(self, promo)
                    self.user_manager.record_promo_shown(promo['id'])
                    break  # Show only one promotion at a time
        except Exception as e:
            print(f"Error showing promotion: {e}")

    def initUI(self):
        self.setWindowTitle('Screenshot Organizer by kno2gether')
        # Set a reasonable default size that works well on most screens
        self.setGeometry(100, 100, 900, 700)
        self.setMinimumSize(800, 600)  # Set minimum window size

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create stacked widget for different screens
        self.stacked_widget = QStackedWidget()
        
        # Add widgets to stacked widget
        self.dashboard_widget = DashboardWidget()
        self.settings_widget = SettingsWidget()
        self.folder_widget = FolderWidget()
        
        self.stacked_widget.addWidget(self.dashboard_widget)
        self.stacked_widget.addWidget(self.settings_widget)
        self.stacked_widget.addWidget(self.folder_widget)
        
        # Navigation buttons container with styling
        nav_container = QWidget()
        nav_container.setStyleSheet("""
            QWidget {
                background-color: #E3F2FD;
                border: 1px solid #BBDEFB;
                border-radius: 5px;
            }
        """)
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(10, 5, 10, 5)
        nav_layout.setSpacing(10)

        # Navigation button style
        button_style = """
            QPushButton {
                background-color: #1976D2;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:checked {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BBDEFB;
                color: #78909C;
            }
        """

        # Create navigation buttons
        self.dashboard_btn = QPushButton("🏠 Dashboard")
        self.settings_btn = QPushButton("⚙️ Settings")
        self.folders_btn = QPushButton("📁 Folders")
        
        # Make buttons checkable for visual feedback
        for btn in [self.dashboard_btn, self.settings_btn, self.folders_btn]:
            btn.setCheckable(True)
            btn.setStyleSheet(button_style)

        self.dashboard_btn.clicked.connect(lambda: self.switchPage(0))
        self.settings_btn.clicked.connect(lambda: self.switchPage(1))
        self.folders_btn.clicked.connect(lambda: self.switchPage(2))
        
        nav_layout.addWidget(self.dashboard_btn)
        nav_layout.addWidget(self.settings_btn)
        nav_layout.addWidget(self.folders_btn)
        nav_layout.addStretch()

        # Add processing control buttons
        self.start_btn = QPushButton("▶️ Start")
        self.stop_btn = QPushButton("⏹️ Stop")
        self.start_btn.clicked.connect(self.startProcessing)
        self.stop_btn.clicked.connect(self.stopProcessing)
        self.stop_btn.setEnabled(False)
        
        for btn in [self.start_btn, self.stop_btn]:
            btn.setStyleSheet(button_style)
        
        nav_layout.addWidget(self.start_btn)
        nav_layout.addWidget(self.stop_btn)

        # Add navigation and stacked widget to main layout
        layout.addWidget(nav_container)
        layout.addWidget(self.stacked_widget)

        # Status bar for showing processing status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #424242;
                padding: 5px;
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.status_label)

        # Set up system tray
        self.setupSystemTray()
        
        # Start with dashboard selected
        self.switchPage(0)

    def switchPage(self, index):
        # Update button states
        self.dashboard_btn.setChecked(index == 0)
        self.settings_btn.setChecked(index == 1)
        self.folders_btn.setChecked(index == 2)
        
        # Switch to the selected page
        self.stacked_widget.setCurrentIndex(index)

    def setupSystemTray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.png"))
        
        # Create tray menu
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.quitApplication)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def startProcessing(self):
        if not os.path.exists(get_config_path('folders.json')):
            QMessageBox.warning(self, "Warning", "Please configure folders first!")
            self.switchPage(2)  # Switch to folders page
            return
            
        if not self.dashboard_widget.hasConsent():
            QMessageBox.warning(self, "Warning", "Please accept the AI processing consent!")
            self.switchPage(0)  # Switch to dashboard page
            return
            
        with open(get_config_path('folders.json'), 'r') as f:
            folders = json.load(f)
            
        if not folders:
            QMessageBox.warning(self, "Warning", "No folders configured!")
            self.switchPage(2)  # Switch to folders page
            return
            
        self.processing_thread = ProcessingThread(folders)
        self.processing_thread.progress.connect(self.updateStatus)
        self.processing_thread.error.connect(self.showError)
        self.processing_thread.finished.connect(self.processingFinished)
        self.processing_thread.start()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stopProcessing(self):
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop()
            self.status_label.setText("Stopping...")

    def updateStatus(self, message):
        self.status_label.setText(message)

    def processingFinished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Processing completed")

    def showError(self, error_msg):
        logger.error(f"Processing error: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)
        self.status_label.setText(f"Error: {error_msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Screenshot Organizer",
            "Application minimized to system tray",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def quitApplication(self):
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop()
            self.processing_thread.wait()
        QApplication.quit()

def initialize_config_files():
    """Initialize configuration files with default values if they don't exist"""
    app_dir = get_app_data_dir()
    
    # Default settings
    settings_path = get_config_path('settings.json')
    if not os.path.exists(settings_path):
        default_settings = {
            "provider": "Together AI",
            "model": "Llama-3.2-11B-Vision-Instruct-Turbo",
            "together_url": "https://api.together.xyz",
            "together_api_key": "",
            "ollama_url": "http://localhost:11434",
            "ollama_api_key": "",
            "stats": {
                "total_images_processed": 0,
                "last_processed_date": None,
                "categories_created": []
            }
        }
        with open(settings_path, 'w') as f:
            json.dump(default_settings, f, indent=4)
    
    # Default promotions
    promo_path = get_config_path('promotions.json')
    if not os.path.exists(promo_path):
        default_promos = {
            "promotions": [
                {
                    "id": "youtube_channel",
                    "title": "Subscribe to kno2gether YouTube Channel!",
                    "message": "🎥 Enhance your learning journey with kno2gether!\\n\\nGet more AI tips, tutorials, and exclusive content by subscribing to our YouTube channel.",
                    "details": "Join our growing community of tech enthusiasts and stay updated with the latest AI developments and practical tutorials.",
                    "form_url": "https://www.youtube.com/@kno2gether",
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31"
                }
            ]
        }
        with open(promo_path, 'w') as f:
            json.dump(default_promos, f, indent=4)

def main():
    app = QApplication(sys.argv)
    
    # Initialize configuration files
    initialize_config_files()
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

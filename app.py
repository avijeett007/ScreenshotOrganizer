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

def get_config_path(filename):
    """Get the platform-specific path for config files"""
    if platform.system() == "Windows":
        config_dir = os.path.join(os.getenv('APPDATA'), 'ScreenshotOrganizer')
    elif platform.system() == "Darwin":  # macOS
        config_dir = os.path.join(os.path.expanduser('~/Library/Application Support/ScreenshotOrganizer'))
    else:  # Linux
        config_dir = os.path.expanduser('~/.screenshotorganizer')
    
    # Create config directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    
    # Return full path to the config file
    return os.path.join(config_dir, filename)

def initialize_config_files():
    """Initialize default configuration files if they don't exist"""
    # Default settings
    settings = {
        'provider': 'Together AI',
        'model': 'Llama-3.2-11B-Vision-Instruct-Turbo',
        'together_url': 'https://api.together.xyz',
        'together_api_key': '',
        'ollama_url': 'http://localhost:11434',
        'ollama_api_key': '',
        'stats': {
            'total_images_processed': 0,
            'last_processed_date': None,
            'categories_created': []
        }
    }
    
    settings_path = get_config_path('settings.json')
    if not os.path.exists(settings_path):
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=4)
            logger.info(f"Created default settings at {settings_path}")
    
    # Create other necessary config files
    config_files = {
        'user_data.json': {'registered': False, 'last_promo_check': None},
        'folders.json': [],
        'promotions.json': {"promotions": []}
    }
    
    for filename, default_content in config_files.items():
        file_path = get_config_path(filename)
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump(default_content, f, indent=4)
                logger.info(f"Created {filename} at {file_path}")

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

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Provider Selection
        provider_group = QWidget()
        provider_group.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border: 1px solid #BBDEFB;
                border-radius: 10px;
                padding: 15px;
            }
            QLabel {
                color: #1565C0;
            }
            QComboBox {
                padding: 8px;
                border: 1px solid #BBDEFB;
                border-radius: 4px;
                min-width: 200px;
                color: #424242;
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #424242;
                selection-background-color: #E3F2FD;
                selection-color: #1565C0;
            }
        """)
        provider_layout = QVBoxLayout(provider_group)

        provider_label = QLabel("AI Provider:")
        provider_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        provider_layout.addWidget(provider_label)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Together AI", "Ollama"])
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        provider_layout.addWidget(self.provider_combo)

        layout.addWidget(provider_group)

        # Model Settings
        model_group = QWidget()
        model_group.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border: 1px solid #BBDEFB;
                border-radius: 10px;
                padding: 15px;
            }
            QLabel {
                color: #1565C0;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #BBDEFB;
                border-radius: 4px;
                color: #424242;
                background-color: white;
            }
        """)
        model_layout = QVBoxLayout(model_group)

        # Model Name
        model_label = QLabel("Model Name:")
        model_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        model_layout.addWidget(model_label)

        self.model_input = QLineEdit()
        model_layout.addWidget(self.model_input)

        # Base URL
        url_label = QLabel("Base URL:")
        url_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        model_layout.addWidget(url_label)

        self.url_input = QLineEdit()
        model_layout.addWidget(self.url_input)

        # API Key
        api_label = QLabel("API Key:")
        api_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        model_layout.addWidget(api_label)

        self.api_input = QLineEdit()
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        model_layout.addWidget(self.api_input)

        layout.addWidget(model_group)

        # Save Button
        save_btn = QPushButton("Save Settings")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

        layout.addStretch()
        self.setLayout(layout)
        
        # Load existing settings
        self.load_settings()

    def load_settings(self):
        try:
            settings_path = get_config_path('settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    
                self.provider_combo.setCurrentText(settings.get('provider', 'Together AI'))
                self.model_input.setText(settings.get('model', ''))
                
                # Set URL based on provider
                if settings['provider'] == 'Together AI':
                    self.url_input.setText(settings.get('together_url', 'https://api.together.xyz'))
                    self.api_input.setText(settings.get('together_api_key', ''))
                else:
                    self.url_input.setText(settings.get('ollama_url', 'http://localhost:11434'))
                    self.api_input.setText(settings.get('ollama_api_key', ''))
                    
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
            QMessageBox.warning(self, "Error", "Could not load settings. Using defaults.")

    def save_settings(self):
        try:
            settings = {
                'provider': self.provider_combo.currentText(),
                'model': self.model_input.text(),
                'together_url': self.url_input.text() if self.provider_combo.currentText() == 'Together AI' else 'https://api.together.xyz',
                'together_api_key': self.api_input.text() if self.provider_combo.currentText() == 'Together AI' else '',
                'ollama_url': self.url_input.text() if self.provider_combo.currentText() == 'Ollama' else 'http://localhost:11434',
                'ollama_api_key': self.api_input.text() if self.provider_combo.currentText() == 'Ollama' else ''
            }
            
            settings_path = get_config_path('settings.json')
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=4)
            
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not save settings: {str(e)}")

    def on_provider_changed(self, provider):
        if provider == "Together AI":
            self.model_input.setText("Llama-3.2-11B-Vision-Instruct-Turbo")
            self.url_input.setText("https://api.together.xyz")
        else:
            self.model_input.setText("llama2-vision")
            self.url_input.setText("http://localhost:11434")
        self.api_input.clear()

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

def main():
    app = QApplication(sys.argv)
    
    # Initialize configuration files
    initialize_config_files()
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

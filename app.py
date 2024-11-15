import sys
import os
import json
import platform
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QComboBox, QSystemTrayIcon, QMenu, QMessageBox,
                            QFileDialog, QStackedWidget, QDialog, QCheckBox, QScrollArea,
                            QTabWidget)
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
import time
import threading

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
    
    # Create config directory if it doesn't exist
    if platform.system() == "Windows":
        config_dir = os.path.join(os.getenv('APPDATA'), 'ScreenshotOrganizer')
    elif platform.system() == "Darwin":  # macOS
        config_dir = os.path.join(os.path.expanduser('~/Library/Application Support/ScreenshotOrganizer'))
    else:  # Linux
        config_dir = os.path.expanduser('~/.screenshotorganizer')
    
    os.makedirs(config_dir, exist_ok=True)
    
    # Initialize settings.json if it doesn't exist
    settings_path = os.path.join(config_dir, 'settings.json')
    if not os.path.exists(settings_path):
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=4)
            logger.info(f"Created default settings at {settings_path}")
    
    # Initialize user_data.json if it doesn't exist
    user_data_path = os.path.join(config_dir, 'user_data.json')
    if not os.path.exists(user_data_path):
        with open(user_data_path, 'w') as f:
            json.dump({'registered': False, 'last_promo_check': None}, f, indent=4)
            logger.info(f"Created user_data.json at {user_data_path}")
    
    # Initialize folders.json if it doesn't exist
    folders_path = os.path.join(config_dir, 'folders.json')
    if not os.path.exists(folders_path):
        with open(folders_path, 'w') as f:
            json.dump([], f, indent=4)
            logger.info(f"Created folders.json at {folders_path}")
    
    # Copy promotions.json from repo if it exists, otherwise create default
    repo_promotions_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'promotions.json')
    config_promotions_path = os.path.join(config_dir, 'promotions.json')
    
    if not os.path.exists(config_promotions_path):
        if os.path.exists(repo_promotions_path):
            # Copy from repo
            with open(repo_promotions_path, 'r') as src, open(config_promotions_path, 'w') as dst:
                content = json.load(src)
                json.dump(content, dst, indent=4)
                logger.info(f"Copied promotions.json from repo to {config_promotions_path}")
        else:
            # Create default
            with open(config_promotions_path, 'w') as f:
                json.dump({"promotions": []}, f, indent=4)
                logger.info(f"Created default promotions.json at {config_promotions_path}")

class FolderWatcher(QThread):
    new_file_detected = pyqtSignal(str)
    
    def __init__(self, folders):
        super().__init__()
        self.folders = folders
        self.is_running = True
        self.processed_files = set()
        self.last_check = {}
        
        # Initialize last check time for each folder
        for folder in folders:
            self.last_check[folder] = datetime.now()
    
    def run(self):
        while self.is_running:
            for folder in self.folders:
                if not os.path.exists(folder):
                    continue
                    
                try:
                    # Check for new files
                    for filename in os.listdir(folder):
                        if not self.is_running:
                            break
                            
                        file_path = os.path.join(folder, filename)
                        
                        # Skip if not an image or already processed
                        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                            continue
                        if file_path in self.processed_files:
                            continue
                            
                        # Check if file is new since last check
                        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if mod_time > self.last_check[folder]:
                            # Wait a bit to ensure file is completely written
                            time.sleep(1)
                            self.new_file_detected.emit(file_path)
                            self.processed_files.add(file_path)
                    
                    # Update last check time
                    self.last_check[folder] = datetime.now()
                    
                except Exception as e:
                    logger.error(f"Error watching folder {folder}: {str(e)}")
                    continue
            
            # Sleep before next check
            time.sleep(2)
    
    def stop(self):
        self.is_running = False


class ProcessingThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    stats_updated = pyqtSignal(dict)
    
    def __init__(self, folders):
        super().__init__()
        self.folders = folders
        self.is_running = True
        self.queue = []
        self.queue_lock = threading.Lock()
    
    def add_to_queue(self, file_path):
        """Add a file to the processing queue"""
        with self.queue_lock:
            if file_path not in self.queue:
                self.queue.append(file_path)
    
    def run(self):
        try:
            # Initial processing of existing files
            for folder in self.folders:
                if not self.is_running:
                    break
                    
                if not os.path.exists(folder):
                    self.error.emit(f"Folder not found: {folder}")
                    continue
                
                self.progress.emit(f"Processing existing files in: {folder}")
                try:
                    process_screenshots(folder, callback=self.process_callback)
                except Exception as e:
                    self.error.emit(f"Error processing folder {folder}: {str(e)}")
                    logger.error(f"Error processing folder {folder}: {str(e)}")
                    logger.error(traceback.format_exc())
                    continue
            
            # Start watching for new files
            self.watcher = FolderWatcher(self.folders)
            self.watcher.new_file_detected.connect(self.add_to_queue)
            self.watcher.start()
            
            # Process queue
            while self.is_running:
                with self.queue_lock:
                    if self.queue:
                        file_path = self.queue.pop(0)
                        folder = os.path.dirname(file_path)
                        try:
                            process_screenshots(folder, callback=self.process_callback)
                        except Exception as e:
                            self.error.emit(f"Error processing file {file_path}: {str(e)}")
                            logger.error(f"Error processing file {file_path}: {str(e)}")
                            logger.error(traceback.format_exc())
                
                time.sleep(1)  # Prevent CPU overuse
            
            # Stop the watcher
            if hasattr(self, 'watcher'):
                self.watcher.stop()
                self.watcher.wait()
            
            if self.is_running:  # Only emit finished if not stopped
                self.finished.emit()
                
        except Exception as e:
            error_msg = f"Error during processing: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error.emit(error_msg)
    
    def process_callback(self, data):
        """Callback for processing updates"""
        if not self.is_running:
            return False
            
        if isinstance(data, dict):
            status = data.get('status', '')
            
            if status == 'error':
                self.error.emit(data.get('error', 'Unknown error'))
            elif status == 'processing':
                self.progress.emit(f"Processed: {data['file']} -> {data['category']}/{data['subcategory']}")
            elif status == 'checking':
                self.progress.emit("Checking for new files...")
            elif status == 'complete':
                self.progress.emit("Processing complete")
            
            if 'stats' in data:
                # Convert set to list for JSON serialization
                stats = data['stats'].copy()
                if isinstance(stats.get('categories_created'), set):
                    stats['categories_created'] = list(stats['categories_created'])
                self.stats_updated.emit(stats)
        
        return self.is_running
    
    def stop(self):
        """Stop processing"""
        logger.info("Stopping processing...")
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
        self.setWindowTitle("Screenshot Organizer")
        self.setMinimumSize(800, 600)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # Initialize widgets
        self.dashboard_widget = DashboardWidget()
        self.settings_widget = SettingsWidget()
        self.folder_widget = FolderWidget()
        
        # Add tabs
        self.tab_widget.addTab(self.dashboard_widget, "Dashboard")
        self.tab_widget.addTab(self.settings_widget, "Settings")
        self.tab_widget.addTab(self.folder_widget, "Folders")
        
        # Status bar for processing status
        self.status_label = QLabel("")
        self.statusBar().addWidget(self.status_label)
        
        # Processing control buttons
        self.setup_control_buttons()
        
        # Initialize processing thread
        self.processing_thread = None
        
        # Load initial stats
        self.dashboard_widget.loadStats()
        
        # Setup system tray
        self.setupSystemTray()

    def setupSystemTray(self):
        """Setup system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(self)
        icon = QIcon("icon.png")
        self.tray_icon.setIcon(icon)
        
        # Create tray menu
        tray_menu = QMenu()
        
        # Add menu items
        show_action = tray_menu.addAction("Show Window")
        show_action.triggered.connect(self.showNormal)
        
        start_action = tray_menu.addAction("Start Processing")
        start_action.triggered.connect(self.startProcessing)
        
        stop_action = tray_menu.addAction("Stop Processing")
        stop_action.triggered.connect(self.stopProcessing)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.quitApplication)
        
        # Set the menu
        self.tray_icon.setContextMenu(tray_menu)
        
        # Show the tray icon
        self.tray_icon.show()
        
        # Connect tray icon activation
        self.tray_icon.activated.connect(self.trayIconActivated)

    def trayIconActivated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

    def closeEvent(self, event):
        """Handle window close event"""
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "Screenshot Organizer",
                "Application will keep running in the system tray",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            event.ignore()
        else:
            self.quitApplication()

    def quitApplication(self):
        """Properly quit the application"""
        # Stop processing if running
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop()
            self.processing_thread.wait()
        
        # Remove tray icon
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        
        # Quit application
        QApplication.quit()

    def setup_control_buttons(self):
        """Setup processing control buttons"""
        # Create buttons container
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        
        # Create buttons
        self.start_btn = QPushButton("Start Processing")
        self.stop_btn = QPushButton("Stop Processing")
        self.stop_btn.setEnabled(False)
        
        # Style buttons
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
        self.start_btn.setStyleSheet(button_style)
        self.stop_btn.setStyleSheet(button_style)
        
        # Connect buttons
        self.start_btn.clicked.connect(self.startProcessing)
        self.stop_btn.clicked.connect(self.stopProcessing)
        
        # Add buttons to layout
        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.stop_btn)
        
        # Add buttons container to main layout
        self.statusBar().addWidget(buttons_container)

    def startProcessing(self):
        if not os.path.exists(get_config_path('folders.json')):
            QMessageBox.warning(self, "Warning", "Please configure folders first!")
            self.tab_widget.setCurrentIndex(2)  # Switch to folders page
            return
            
        if not self.dashboard_widget.hasConsent():
            QMessageBox.warning(self, "Warning", "Please accept the AI processing consent!")
            self.tab_widget.setCurrentIndex(0)  # Switch to dashboard page
            return
            
        with open(get_config_path('folders.json'), 'r') as f:
            folders = json.load(f)
            
        if not folders:
            QMessageBox.warning(self, "Warning", "No folders configured!")
            self.tab_widget.setCurrentIndex(2)  # Switch to folders page
            return
            
        self.processing_thread = ProcessingThread(folders)
        self.processing_thread.progress.connect(self.updateStatus)
        self.processing_thread.error.connect(self.showError)
        self.processing_thread.finished.connect(self.processingFinished)
        self.processing_thread.stats_updated.connect(self.updateStats)
        self.processing_thread.start()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stopProcessing(self):
        """Stop the processing thread"""
        if self.processing_thread and self.processing_thread.isRunning():
            logger.info("User requested to stop processing")
            self.processing_thread.stop()
            self.status_label.setText("Stopping processing...")
            self.stop_btn.setEnabled(False)  # Disable stop button while stopping
            
            # Wait for the thread to finish with a timeout
            if not self.processing_thread.wait(5000):  # 5 second timeout
                logger.warning("Processing thread did not stop gracefully")
                self.processing_thread.terminate()  # Force termination if necessary
            
            self.status_label.setText("Processing stopped by user")
            self.start_btn.setEnabled(True)
            logger.info("Processing stopped successfully")

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

    def updateStats(self, stats):
        """Update statistics in settings file"""
        try:
            config_path = get_config_path('settings.json')
            with open(config_path, 'r') as f:
                settings = json.load(f)
            
            # Ensure stats is a dictionary
            if not isinstance(stats, dict):
                logger.error(f"Invalid stats format: {stats}")
                return
                
            # Convert any sets to lists
            if isinstance(stats.get('categories_created'), set):
                stats['categories_created'] = list(stats['categories_created'])
            
            # Update settings with new stats
            if 'stats' not in settings:
                settings['stats'] = {}
            
            settings['stats'].update({
                'total_images_processed': stats.get('total_images_processed', 0),
                'last_processed_date': stats.get('last_processed_date'),
                'categories_created': stats.get('categories_created', [])
            })
            
            # Write updated settings
            with open(config_path, 'w') as f:
                json.dump(settings, f, indent=4)
            
            # Reload dashboard stats
            self.dashboard_widget.loadStats()
            
        except Exception as e:
            logger.error(f"Error updating stats: {str(e)}")
            logger.error(traceback.format_exc())

def main():
    app = QApplication(sys.argv)
    
    # Initialize configuration files
    initialize_config_files()
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

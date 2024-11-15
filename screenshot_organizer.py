import os
import datetime
import base64
from dotenv import load_dotenv
from PIL import Image
import re
import shutil
import json
import requests
import logging
import traceback
from pathlib import Path
import platform

# Set up logging
log_dir = os.path.join(os.path.expanduser('~/Library/Application Support/ScreenshotOrganizer'), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'screenshot_organizer.log')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # This will print to terminal
    ]
)

logger = logging.getLogger(__name__)

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

class ImageProcessor:
    def __init__(self):
        self.load_settings()
        
    def load_settings(self):
        settings_path = get_config_path('settings.json')
        logger.info(f"Loading settings from: {settings_path}")
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                self.settings = json.load(f)
                logger.info(f"Loaded settings: {self.settings}")
        else:
            self.settings = {
                'provider': 'Together AI',
                'model': 'Llama-3.2-11B-Vision-Instruct-Turbo',
                'together_url': 'https://api.together.xyz',
                'together_api_key': '',
                'ollama_url': 'http://localhost:11434',
                'ollama_api_key': ''
            }
            logger.info("Using default settings")

    def get_image_description(self, image_path):
        logger.info(f"Processing image: {image_path}")
        prompt = """Analyze the given image and provide a category and subcategory. 
        Respond in the format: 'Category: [category], Subcategory: [subcategory]'
        
        Examples:
        Category: code, Subcategory: python_script
        Category: receipt, Subcategory: payment
        Category: document, Subcategory: identity_docs
        Category: document, Subcategory: sensitive
        Category: document, Subcategory: finance

        Analyze the given image and provide the category and subcategory in the specified format."""
        
        try:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
            
            if self.settings['provider'] == 'Together AI':
                if not self.settings.get('together_api_key'):
                    raise Exception("Together AI API key is not set. Please configure it in settings.")
                logger.info("Using Together AI provider")
                return self._together_ai_process(prompt, base64_image)
            else:
                logger.info("Using Ollama provider")
                return self._ollama_process(prompt, base64_image, image_path)
        except Exception as e:
            logger.error(f"Error in get_image_description: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def _together_ai_process(self, prompt, base64_image):
        try:
            # Only import Together when needed
            from together import Together
            client = Together(api_key=self.settings['together_api_key'])
            logger.info("Making Together AI API call")
            response = client.chat.completions.create(
                model=self.settings['model'],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                },
                            },
                        ],
                    }
                ],
                stream=False
            )
            
            content = response.choices[0].message.content.strip()
            logger.info(f"Together AI response: {content}")
            return self._parse_response(content, "Together AI response")
        except Exception as e:
            logger.error(f"Error in Together AI processing: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def _ollama_process(self, prompt, base64_image, image_path):
        url = f"{self.settings['ollama_url']}/api/generate"
        logger.info(f"Making Ollama API call to: {url}")
        
        headers = {}
        if self.settings.get('ollama_api_key'):
            headers['Authorization'] = f"Bearer {self.settings['ollama_api_key']}"
        
        try:
            # Convert image to base64
            with Image.open(image_path) as img:
                # Ensure the image is in RGB mode
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large (Ollama has size limits)
                max_size = 1024
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            data = {
                "model": self.settings['model'],
                "prompt": prompt,
                "stream": False,
                "images": [base64_image]
            }
            
            logger.info(f"Ollama request data: {data}")
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code != 200:
                error_msg = f"Ollama API error: Status {response.status_code}"
                try:
                    error_details = response.json()
                    error_msg += f", Details: {error_details}"
                except:
                    error_msg += f", Response: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            content = response.json().get('response', '')
            logger.info(f"Ollama response: {content}")
            return self._parse_response(content, "Ollama response")
            
        except requests.exceptions.ConnectionError:
            error_msg = "Could not connect to Ollama. Please ensure Ollama is running and try again."
            logger.error(error_msg)
            raise Exception(error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            logger.error(f"Ollama request error: {error_msg}")
            logger.error(traceback.format_exc())
            
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    error_msg = f"Model '{self.settings['model']}' not found. Please pull the model first using 'ollama pull {self.settings['model']}'"
                else:
                    try:
                        error_details = e.response.json()
                        error_msg = f"Ollama API error: {error_details}"
                    except:
                        error_msg = f"Ollama API error: {e.response.text}"
            
            logger.error(error_msg)
            raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"Error processing with Ollama: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            raise Exception(error_msg)

    def _parse_response(self, content, source):
        try:
            logger.info(f"Parsing response from {source}: {content}")
            category_match = re.search(r'Category:\s*(\w+)', content)
            subcategory_match = re.search(r'Subcategory:\s*(\w+)', content)
            
            if not category_match or not subcategory_match:
                logger.warning(f"Could not parse category/subcategory from response: {content}")
                return {"category": "unknown", "subcategory": "unclassified"}
            
            result = {
                "category": category_match.group(1).lower(),
                "subcategory": subcategory_match.group(1).lower()
            }
            logger.info(f"Parsed result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            logger.error(traceback.format_exc())
            return {"category": "unknown", "subcategory": "error"}

def get_creation_date(file_path):
    return datetime.datetime.fromtimestamp(os.path.getctime(file_path))

def sanitize_filename(filename):
    return re.sub(r'[^\w\-_\. ]', '_', filename)

def process_screenshots(folder_path, callback=None):
    """Process screenshots in the given folder with progress callback"""
    processor = ImageProcessor()
    stats = {
        'total_images_processed': 0,
        'categories_created': set(),
        'last_processed_date': None
    }
    
    try:
        for filename in os.listdir(folder_path):
            # Check if processing should stop
            if callback and not callback():
                logger.info("Processing stopped by user")
                break
                
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                file_path = os.path.join(folder_path, filename)
                try:
                    # Get image category
                    result = processor.get_image_description(file_path)
                    category = result["category"]
                    subcategory = result["subcategory"]
                    
                    # Create category folder
                    category_folder = os.path.join(folder_path, f"{category}_{subcategory}")
                    os.makedirs(category_folder, exist_ok=True)
                    
                    # Generate unique filename
                    creation_date = get_creation_date(file_path)
                    base_name = os.path.splitext(filename)[0]
                    extension = os.path.splitext(filename)[1]
                    new_filename = sanitize_filename(f"{base_name}_{creation_date.strftime('%Y%m%d_%H%M%S')}{extension}")
                    
                    # Define new file path in the category subfolder
                    new_file_path = os.path.join(category_folder, new_filename)
                    
                    # Move the file
                    shutil.move(file_path, new_file_path)
                    logger.info(f"Moved {filename} to {new_file_path}")
                    
                    # Update statistics
                    stats['total_images_processed'] += 1
                    stats['categories_created'].add(f"{category}_{subcategory}")
                    stats['last_processed_date'] = datetime.datetime.now().isoformat()
                    
                    # Update settings file with new statistics
                    settings_path = get_config_path('settings.json')
                    if os.path.exists(settings_path):
                        with open(settings_path, 'r') as f:
                            settings = json.load(f)
                        
                        # Update stats in settings
                        if 'stats' not in settings:
                            settings['stats'] = {}
                        settings['stats']['total_images_processed'] = (
                            settings['stats'].get('total_images_processed', 0) + 1
                        )
                        settings['stats']['last_processed_date'] = stats['last_processed_date']
                        settings['stats']['categories_created'] = list(set(
                            settings['stats'].get('categories_created', []) + 
                            [f"{category}_{subcategory}"]
                        ))
                        
                        with open(settings_path, 'w') as f:
                            json.dump(settings, f, indent=4)
                    
                    # Call progress callback if provided
                    if callback:
                        callback({
                            'file': filename,
                            'category': category,
                            'subcategory': subcategory,
                            'stats': stats
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing {filename}: {str(e)}")
                    logger.error(traceback.format_exc())
                    if callback:
                        callback({
                            'error': f"Error processing {filename}: {str(e)}",
                            'stats': stats
                        })
                    continue
    
    except Exception as e:
        logger.error(f"Error processing folder {folder_path}: {str(e)}")
        logger.error(traceback.format_exc())
        if callback:
            callback({
                'error': f"Error processing folder: {str(e)}",
                'stats': stats
            })
    
    return stats

if __name__ == "__main__":
    screenshot_folder = input("Enter the path to your screenshot folder: ")
    process_screenshots(screenshot_folder)
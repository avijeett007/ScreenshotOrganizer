import os
import datetime
import base64
from dotenv import load_dotenv
from together import Together
from PIL import Image
import re
import shutil

# Load environment variables from .env file
load_dotenv()

# Initialize the Together client with API key from .env
api_key = os.getenv('TOGETHER_API_KEY')
if not api_key:
    raise ValueError("TOGETHER_API_KEY not found in .env file")
client = Together(api_key=api_key)

# Function to get the creation date of a file
def get_creation_date(file_path):
    return datetime.datetime.fromtimestamp(os.path.getctime(file_path))

# Function to call the Together API and get image description
def get_image_description(image_path):
    prompt = """Analyze the given image and provide a category and subcategory. 
    Respond in the format: 'Category: [category], Subcategory: [subcategory]'
    
    Examples:
    Category: code, Subcategory: python_script
    Category: receipt, Subcategory: payment
    Category: document, Subcategory: identity_docs
    Category: document, Subcategory: sensitive
    Category: document, Subcategory: finance

    Analyze the given image and provide the category and subcategory in the specified format."""
    
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')
    
    response = client.chat.completions.create(
        model="meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
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
    
    # Parse the response
    category_match = re.search(r'Category:\s*(\w+)', content)
    subcategory_match = re.search(r'Subcategory:\s*(\w+)', content)
    
    if category_match and subcategory_match:
        return {
            "category": category_match.group(1),
            "subcategory": subcategory_match.group(1)
        }
    else:
        print(f"Error parsing response for {image_path}. Raw response: {content}")
        return {"category": "unknown", "subcategory": "error"}

# Function to sanitize filename
def sanitize_filename(filename):
    return re.sub(r'[^\w\-_\. ]', '_', filename)

# Main function to process screenshots in a folder
def process_screenshots(folder_path):
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            file_path = os.path.join(folder_path, filename)
            
            # Get image description
            description = get_image_description(file_path)
            
            # Get creation date
            creation_date = get_creation_date(file_path)
            date_string = creation_date.strftime("%Y%m%d_%H%M%S")
            
            # Create new filename
            new_filename = f"{sanitize_filename(description['subcategory'])}_{date_string}{os.path.splitext(filename)[1]}"
            
            # Create category subfolder if it doesn't exist
            category_folder = os.path.join(folder_path, sanitize_filename(description['category']))
            os.makedirs(category_folder, exist_ok=True)
            
            # Define new file path in the category subfolder
            new_file_path = os.path.join(category_folder, new_filename)
            
            # Move and rename the file
            shutil.move(file_path, new_file_path)
            print(f"Moved and renamed: {filename} -> {os.path.join(description['category'], new_filename)}")

# Usage
if __name__ == "__main__":
    screenshot_folder = input("Enter the path to your screenshot folder: ")
    process_screenshots(screenshot_folder)
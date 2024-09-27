# Screenshot Organizer Setup and Usage Guide

## Prerequisites

- Python 3.6 or higher
- pip (Python package installer)
- A Together AI account and API key

## Setup Steps

1. **Install Python:**
   If you don't have Python installed, download and install it from [python.org](https://www.python.org/downloads/).

2. **Set up a virtual environment (recommended):**
   Open a terminal or command prompt and run:
   ```
   python -m venv screenshot_organizer_env
   ```
   Activate the virtual environment:
   - On Windows:
     ```
     screenshot_organizer_env\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source screenshot_organizer_env/bin/activate
     ```

3. **Install required packages:**
   With the virtual environment activated, run:
   ```
   pip install together pillow python-dotenv
   ```

4. **Set up .env file with Together AI API key:**
   - Sign up for an account at [together.ai](https://www.together.ai/) if you haven't already.
   - Obtain your API key from your account dashboard.
   - Create a new file named `.env` in the same directory as your script.
   - Add the following line to the `.env` file:
     ```
     TOGETHER_API_KEY=your_api_key_here
     ```
   - Replace `your_api_key_here` with your actual API key.

5. **Prepare the script:**
   - Copy the provided Python script into a new file, e.g., `screenshot_organizer.py`.
   - Save it in the same directory as your `.env` file.

## Running the Script

1. Ensure your virtual environment is activated.

2. Navigate to the directory containing the script and `.env` file:
   ```
   cd path/to/script/directory
   ```

3. Run the script:
   ```
   python screenshot_organizer.py
   ```

4. When prompted, enter the full path to your screenshot folder.

5. The script will process each image in the folder, rename it based on the AI-generated category, and display the results.

## Notes

- The script will rename files in place. Make sure you have a backup of your screenshots before running the script.
- Processing time may vary depending on the number and size of the images in your folder.
- Ensure you have a stable internet connection, as the script needs to communicate with the Together AI API for each image.

## Troubleshooting

- If you encounter a `ModuleNotFoundError`, make sure you've installed all required packages and your virtual environment is activated.
- If you get an API error, check that your `TOGETHER_API_KEY` is set correctly in the `.env` file and that you have sufficient credits in your Together AI account.
- For any JSON decoding errors, the script will default to categorizing the image as "unknown_error". Check the console output for more details on these errors.
- Make sure the `.env` file is in the same directory as your script.

If you encounter any other issues or need further assistance, please refer to the Together AI documentation or seek help in relevant Python forums.
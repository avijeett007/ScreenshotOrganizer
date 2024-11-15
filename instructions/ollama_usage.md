This is how ollama can be used with the Llama 3.2 Vision model.

Python Library
To use Llama 3.2 Vision with the Ollama Python library:

import ollama

response = ollama.chat(
    model='llama3.2-vision',
    messages=[{
        'role': 'user',
        'content': 'What is in this image?',
        'images': ['image.jpg']
    }]
)

print(response)
JavaScript Library
To use Llama 3.2 Vision with the Ollama JavaScript library:

import ollama from 'ollama'

const response = await ollama.chat({
  model: 'llama3.2-vision',
  messages: [{
    role: 'user',
    content: 'What is in this image?',
    images: ['image.jpg']
  }]
})

console.log(response)
cURL
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2-vision",
  "messages": [
    {
      "role": "user",
      "content": "what is in this image?",
      "images": ["<base64-encoded image data>"]
    }
  ]
}'

# Using Ollama with Screenshot Organizer

## Prerequisites

1. Install Ollama on your system:
   - Visit [Ollama's website](https://ollama.ai)
   - Download and install the appropriate version for your OS
   - Start the Ollama service

2. Pull the required model:
   ```bash
   ollama pull llama2-vision
   ```

## Configuration in Screenshot Organizer

1. In the Settings screen:
   - Select "Ollama" as the AI Provider
   - Set Model Name to "llama2-vision"
   - Base URL: "http://localhost:11434" (default)
   - API Key: Leave empty (not required for local Ollama)

## Troubleshooting

1. Ensure Ollama is running:
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   ```

2. Common Issues:
   - "Connection refused": Ollama service not running
   - "Model not found": Need to pull the model first
   - API errors: Check if the model supports vision tasks

## Recommended Models

- llama2-vision: Best for general image understanding
- bakllava: Alternative vision model
- llava: Another option for vision tasks

## Performance Notes

- First run may be slower as Ollama loads the model
- Subsequent runs will be faster
- Processing speed depends on your hardware
- GPU acceleration is recommended for better performance
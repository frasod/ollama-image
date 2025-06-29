# Image Descriptor with Ollama

A PyQt6 application that uses Ollama's LLaVA model to generate detailed descriptions of images.

## Prerequisites

1. Python 3.8 or higher
2. Ollama installed and running locally (https://ollama.ai)
3. LLaVA model pulled in Ollama (run `ollama pull llava`)

## Setup

1. Install the required Python packages:
```bash
pip install -r requirements.txt
```

2. Make sure Ollama is running on your system (it should be accessible at http://localhost:11434)

## Usage

1. Run the application:
```bash
python image_descriptor.py
```

2. Click the "Upload Image" button to select an image file
3. The application will display the image and generate a description using Ollama's LLaVA model
4. The description will appear in the text area below the image

## Features

- Modern PyQt6-based user interface
- Support for common image formats (PNG, JPG, JPEG, BMP, GIF)
- Automatic image resizing for optimal processing
- Asynchronous processing to keep the UI responsive
- Error handling and user feedback

## Notes

- The application requires Ollama to be running locally
- Large images will be automatically resized to optimize processing
- The LLaVA model must be pulled in Ollama before using the application 
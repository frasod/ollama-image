# Ollama Image Descriptor

A desktop app that uses Ollama's LLaVA model to generate detailed, natural-language descriptions of images. The app is built with PyQt6 for the user interface and can run natively on Windows or in Docker (with X11 support for GUI).

---

## What Does This App Do?
- Lets you upload or drag-and-drop an image.
- Sends the image to your local Ollama server (using the LLaVA model).
- Generates a thorough, human-readable description of everything visible in the image.
- Shows the result in a modern, easy-to-use window.

---

## Components Explained
- **main.py**: Entry point for the app. Starts the PyQt6 GUI.
- **ui.py**: Contains the main PyQt6 window and all UI logic.
- **ollama_api.py**: Handles communication with the Ollama server (model listing, health check, etc.).
- **workers.py**: Background threads for sending images/text to Ollama and processing responses.
- **constants.py**: Shared style and prompt constants.
- **gpu_info.py**: Gets GPU info for display in the app.
- **image_to_prompt.py**: (Legacy/alt) Standalone script for image-to-prompt conversion.
- **Dockerfile**: Builds the Docker image for the app.
- **docker-compose.yml**: Runs the app container, connecting to a native Ollama instance.
- **requirements.txt**: Python dependencies.
- **start_local.bat**: Runs the app natively on Windows (no Docker, no VcXsrv needed).
- **start_vcxsrv_docker.bat**: Starts VcXsrv (if needed) and runs the app in Docker (Windows only).

---

## Installation & Setup

### Native (Recommended for Windows)
1. **Install Python 3.8+**
   - Download from https://www.python.org/downloads/
2. **Install dependencies**
   - Open Command Prompt in your project folder:
     ```
     pip install -r requirements.txt
     ```
3. **Install and start Ollama**
   - Download and install from https://ollama.ai
   - Start Ollama (it should run in the background)
   - Pull the LLaVA model:
     ```
     ollama pull llava
     ```
4. **Run the app**
   - Double-click `start_local.bat` or run:
     ```
     python main.py
     ```
5. **Use the app**
   - Upload an image and get a description!

### Docker (App Only, Ollama Native)
1. **Install Docker Desktop**
   - Download from https://www.docker.com/products/docker-desktop
   - Start Docker Desktop and wait for it to be running.
2. **Install and start Ollama natively** (see above)
3. **Build the Docker image**
   - In your project folder:
     ```
     docker build -t ollama-image .
     ```
4. **Windows Only: Start VcXsrv**
   - Run XLaunch (VcXsrv) with:
     - Multiple windows
     - Display number: 0
     - Start no client
     - **Check "Disable access control"**
   - Make sure you see the "X" icon in your system tray.
5. **Start the app container**
   - Double-click `start_vcxsrv_docker.bat` (recommended on Windows)
   - Or run:
     ```
     docker compose up
     ```
6. **Use the app**
   - The GUI should appear. Upload an image and get a description!

---

## Troubleshooting
- **No GUI appears (Windows):**
  - Make sure VcXsrv is running and listening on port 6000 (`netstat -an | find "6000"`)
  - Check Windows Firewall (allow VcXsrv on all networks)
  - DISPLAY in Docker must match your host IP and use `:0`
- **Ollama connection errors:**
  - Make sure Ollama is running natively and you can access http://localhost:11434
  - The app container must use `OLLAMA_BASE_URL=http://host.docker.internal:11434`
- **Model not found:**
  - Run `ollama pull llava` on your host
- **Docker errors:**
  - Make sure Docker Desktop is running
  - Rebuild the image if you change requirements: `docker build -t ollama-image .`

---

## Workflow Summary
- Ollama runs natively on your host (Windows, Mac, or Linux)
- The app can run natively or in Docker
- On Windows, VcXsrv is required for Docker GUI
- The app connects to Ollama using the correct base URL
- All models and data stay on your machine

---

## Developer Log
See `devlog.md` for a full history of changes and improvements.

---
For more, see the source repo: https://github.com/frasod/ollama-image 
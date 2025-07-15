# Developer Log for Ollama Image Descriptor

## 2024-06-09
- Added Docker support and updated Dockerfile to use main.py as entry point.
- Improved README with plain-language explanations and step-by-step Docker instructions.
- Updated default prompt for clarity.
- Documented VcXsrv X11 server setup for Windows users running Docker GUI apps.
- Docker Compose now only runs the app container, which connects to a host Ollama instance for model access and persistence.

## 2024-06-10
- Final cleanup: removed redundant Docker Compose Ollama service, clarified all documentation, and ensured clear instructions for both native and Docker workflows. Added detailed component explanations and troubleshooting tips to README.

## 2024-06-08
- Initial version: PyQt6 interface, image upload, Ollama LLaVA integration, and prompt generation. 
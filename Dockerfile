# Use an official Python base image
FROM python:3.11-slim

# Install system dependencies for PyQt and GUI
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-pyqt6 \
        libgl1-mesa-glx \
        libglib2.0-0 \
        x11-apps \
        libxkbcommon-x11-0 \
        && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements if present, else install basics
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || true

# Copy the rest of the app
COPY . .

# Set environment variable for PyQt
ENV QT_X11_NO_MITSHM=1

# Default command to run the app
CMD ["python", "image_to_prompt.py"] 
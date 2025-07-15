# Use an official Python base image
FROM python:3.11

# Install system dependencies for PyQt and GUI
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1-mesa-glx \
        libegl1 \
        libglib2.0-0 \
        libdbus-1-3 \
        libx11-xcb1 \
        libxcb1 \
        libxcb-util1 \
        libxcb-cursor0 \
        libxcb-shape0 \
        libxcb-xinerama0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-render-util0 \
        libxcb-xkb1 \
        libxkbcommon-x11-0 \
        x11-apps \
        && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements if present, else install basics
COPY requirements.txt ./
RUN pip cache purge
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Set environment variable for PyQt
ENV QT_X11_NO_MITSHM=1

# Default command to run the app
CMD ["python", "main.py"]

# Set DISPLAY environment variable for Windows X11 support
ENV DISPLAY=host.docker.internal:0.0
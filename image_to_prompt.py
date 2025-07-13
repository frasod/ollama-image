import sys
import requests
import json
import base64
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFileDialog, QTextEdit, QMessageBox, QComboBox, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
from PIL import Image
import io
import GPUtil

class DragDropImageLabel(QLabel):
    image_dropped = pyqtSignal(str)  # Signal to emit the image path

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Drag and drop an image here\nor click Upload Image")
        self.setWordWrap(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and event.mimeData().urls()[0].toLocalFile().lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        file_path = event.mimeData().urls()[0].toLocalFile()
        self.image_dropped.emit(file_path)

def check_ollama():
    try:
        # Check if Ollama is running
        response = requests.get("http://localhost:11434/api/version")
        if response.status_code != 200:
            return False, "Ollama is not responding correctly"
        
        # Check if gemma3:4b is available
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code != 200:
            return False, "Could not get list of models"
            
        models = response.json().get("models", [])
        model_names = [model.get("name") for model in models]
        
        if "gemma3:4b" not in model_names:
            return False, "gemma3:4b model not found. Please install it using: ollama pull gemma3:4b"
            
        return True, ["gemma3:4b"]
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to Ollama. Please make sure Ollama is running."
    except Exception as e:
        return False, f"Error checking Ollama: {str(e)}"

class PromptWorker(QThread):
    finished = pyqtSignal(tuple)  # Will emit (sdxl_prompt, flux_prompt)
    error = pyqtSignal(str)

    def __init__(self, image_path, model_name, prompt):
        super().__init__()
        self.image_path = image_path
        self.model_name = model_name
        self.prompt = prompt

    def run(self):
        try:
            print(f"Starting image processing using {self.model_name}...")  # Debug print
            
            # Open and convert image to base64
            with Image.open(self.image_path) as img:
                print(f"Image opened: {img.size}, mode: {img.mode}")  # Debug print
                
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    print("Converted to RGB")  # Debug print
                
                # Resize if too large (Ollama has limits)
                max_size = 800
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    print(f"Resized to: {new_size}")  # Debug print
                
                # Convert to bytes and then to base64
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                img_byte_arr = img_byte_arr.getvalue()
                img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
                print(f"Image converted to base64, size: {len(img_base64)}")  # Debug print

            # Prepare the request to Ollama
            url = "http://localhost:11434/api/generate"
            headers = {"Content-Type": "application/json"}
            
            data = {
                "model": self.model_name,
                "prompt": self.prompt,
                "stream": False,
                "images": [img_base64],
                "options": {
                    "vision": True,
                    "temperature": 0.3,
                    "num_predict": 500
                }
            }

            print("Sending request to Ollama...")  # Debug print
            
            # Make the request
            response = requests.post(url, headers=headers, json=data)
            print(f"Response status code: {response.status_code}")  # Debug print
            
            if response.status_code != 200:
                print(f"Error response: {response.text}")  # Debug print
                raise Exception(f"Ollama returned status code {response.status_code}: {response.text}")
                
            response.raise_for_status()
            
            # Extract the prompt
            response_data = response.json()
            print(f"Response data: {json.dumps(response_data, indent=2)}")  # Debug print
            
            response_text = response_data["response"]
            
            # Clean up formatting for ComfyUI Flux
            response_text = response_text.replace("  ", " ").strip()
            response_text = response_text.replace("*", "")  # Remove asterisks
            response_text = response_text.replace("(", "").replace(")", "")  # Remove parentheses
            response_text = response_text.replace("[", "").replace("]", "")  # Remove brackets
            response_text = response_text.replace("{", "").replace("}", "")  # Remove braces
            response_text = response_text.replace("<", "").replace(">", "")  # Remove angle brackets
            response_text = response_text.replace("FLUX:", "").strip()  # Remove FLUX: prefix if present
            
            # Remove any remaining special characters that might cause issues in ComfyUI
            response_text = ''.join(c for c in response_text if c.isalnum() or c.isspace() or c in ',.-_')
            
            print("Successfully generated prompt")  # Debug print
            self.finished.emit(("", response_text))  # Keep tuple format for compatibility

        except Exception as e:
            print(f"Error in worker: {str(e)}")  # Debug print
            self.error.emit(str(e))

class PromptWorkerTextOnly(QThread):
    finished = pyqtSignal(tuple)
    error = pyqtSignal(str)

    def __init__(self, text, model_name):
        super().__init__()
        self.text = text
        self.model_name = model_name

    def run(self):
        try:
            url = "http://localhost:11434/api/generate"
            headers = {"Content-Type": "application/json"}
            data = {
                "model": self.model_name,
                "prompt": self.text,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 500
                }
            }
            response = requests.post(url, headers=headers, json=data)
            if response.status_code != 200:
                raise Exception(f"Ollama returned status code {response.status_code}: {response.text}")
            response.raise_for_status()
            response_data = response.json()
            response_text = response_data["response"]
            # Clean up formatting for ComfyUI Flux
            response_text = response_text.replace("  ", " ").strip()
            response_text = response_text.replace("*", "")
            response_text = response_text.replace("(", "").replace(")", "")
            response_text = response_text.replace("[", "").replace("]", "")
            response_text = response_text.replace("{", "").replace("}", "")
            response_text = response_text.replace("<", "").replace(">", "")
            response_text = response_text.replace("FLUX:", "").strip()
            response_text = ''.join(c for c in response_text if c.isalnum() or c.isspace() or c in ',.-_')
            self.finished.emit(("", response_text))
        except Exception as e:
            self.error.emit(str(e))

class ImageToPromptApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image to FLUX Prompt Generator")
        self.setMinimumSize(1600, 900)
        self.resize(1600, 900)
        
        # Optionally, start maximized:
        # self.showMaximized()
        
        # Define style constants
        self.FONT_SIZE = "12pt"
        self.LAVENDER_LIGHT = "#E6E6FA"
        self.LAVENDER_MID = "#9B8FCC"
        self.LAVENDER_DARK = "#7B68EE"
        
        # Set application style
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.LAVENDER_LIGHT};
            }}
            QLabel {{
                font-size: {self.FONT_SIZE};
                color: #2E2E2E;
                padding: 5px;
            }}
            QPushButton {{
                font-size: {self.FONT_SIZE};
                background-color: {self.LAVENDER_MID};
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                color: white;
            }}
            QPushButton:hover {{
                background-color: {self.LAVENDER_DARK};
            }}
            QPushButton:checked {{
                background-color: {self.LAVENDER_DARK};
            }}
            QTextEdit {{
                font-size: {self.FONT_SIZE};
                background-color: white;
                border: 1px solid {self.LAVENDER_MID};
                border-radius: 4px;
                padding: 5px;
            }}
        """)
        
        # Check Ollama status
        status_ok, result = check_ollama()
        if not status_ok:
            QMessageBox.critical(self, "Error", result)
            sys.exit(1)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create left panel for image and controls
        left_panel = QVBoxLayout()
        
        # Create drag and drop image label
        self.image_label = DragDropImageLabel()
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setStyleSheet(f"""
            QLabel {{
                border: 2px dashed {self.LAVENDER_MID};
                background-color: white;
                border-radius: 8px;
            }}
        """)
        self.image_label.image_dropped.connect(self.handle_image_drop)
        left_panel.addWidget(self.image_label)
        
        # Additional text input below image
        self.extra_text_label = QLabel("Additional Notes (optional):")
        left_panel.addWidget(self.extra_text_label)
        self.extra_text_input = QTextEdit()
        self.extra_text_input.setPlaceholderText("Enter any extra description or notes here...")
        self.extra_text_input.setFixedHeight(60)
        left_panel.addWidget(self.extra_text_input)

        # Text Only Input section
        self.text_only_label = QLabel("Text Only Input:")
        left_panel.addWidget(self.text_only_label)
        self.text_only_input = QTextEdit()
        self.text_only_input.setPlaceholderText("Enter a description or prompt here to generate without an image...")
        self.text_only_input.setFixedHeight(80)
        left_panel.addWidget(self.text_only_input)
        self.text_only_button = QPushButton("Generate from Text Only")
        self.text_only_button.clicked.connect(self.handle_text_only_generate)
        left_panel.addWidget(self.text_only_button)
        
        # Create controls layout
        controls_layout = QHBoxLayout()
        
        # Create upload button
        self.upload_button = QPushButton("Upload Image")
        self.upload_button.clicked.connect(self.upload_image)
        controls_layout.addWidget(self.upload_button)
        
        left_panel.addLayout(controls_layout)
        main_layout.addLayout(left_panel)
        
        # Create right panel for prompts
        right_panel = QVBoxLayout()
        
        # Create prompt input
        prompt_label = QLabel("Default prompt:")
        right_panel.addWidget(prompt_label)
        
        self.prompt_text = QTextEdit()
        self.prompt_text.setPlaceholderText("Enter prompt here...")
        self.prompt_text.setText("Provide a detailed description of ONLY what is visible in this image to be used for recreation in Flux (Stable Diffusion). Do not make up or assume any details that aren't clearly visible. Include precise details about the hairstyle, hair color, length, texture, and parting that you can actually see. Describe the facial features including eye shape, eye color, eyebrow thickness and shape, nose size and shape, lips, jawline, cheekbones, and expression that are visible in the image. Specify skin tone, any notable marks or makeup that you can see. Include body type, body proportions, visible muscle tone, posture, and pose that are clearly shown. Describe clothing in full detail, including style, fit, length, fabric type, color, and texture that are visible. Include any accessories such as jewelry, belts, or shoes that you can see. Avoid symbols or formatting not typically used in ComfyUI Flux prompts. Keep the description natural, fluent, and comprehensive, but ONLY include details that are actually visible in the image. No additional comments, restrict output to the actual prompt only.")
        self.prompt_text.setMinimumHeight(200)
        right_panel.addWidget(self.prompt_text)
        
        # Model selection dropdown
        self.model_combo = QComboBox()
        self.model_combo.setStyleSheet(f"font-size: {self.FONT_SIZE}; padding: 5px;")
        right_panel.addWidget(QLabel("Select Ollama Model:"))
        right_panel.addWidget(self.model_combo)
        self.populate_model_combo()
        self.model_combo.currentIndexChanged.connect(self.handle_model_change)
        
        # Create send button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_prompt)
        self.send_button.setEnabled(False)  # Disabled until image is loaded
        right_panel.addWidget(self.send_button)
        
        # Create FLUX prompt text area
        flux_label = QLabel("FLUX Prompt:")
        right_panel.addWidget(flux_label)
        self.flux_text = QTextEdit()
        self.flux_text.setReadOnly(True)
        self.flux_text.setPlaceholderText("FLUX prompt will appear here...")
        self.flux_text.setMinimumHeight(300)
        right_panel.addWidget(self.flux_text)

        # Add a horizontal line separator
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.Shape.HLine)
        self.separator.setFrameShadow(QFrame.Shadow.Sunken)
        right_panel.addWidget(self.separator)
        right_panel.addSpacing(10)

        # Add stretch to push GPU/model info to the bottom
        right_panel.addStretch(1)
        right_panel.addSpacing(10)

        # Create a styled QFrame for GPU/model info
        self.info_frame = QFrame()
        self.info_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.info_frame.setStyleSheet('''
            QFrame {
                background-color: #f5f5fa;
                border: 1px solid #bdbdd7;
                border-radius: 8px;
                padding: 10px;
                margin-top: 8px;
            }
            QLabel {
                font-size: 9pt;
                color: #333;
            }
            QPushButton {
                font-size: 9pt;
                padding: 4px 8px;
            }
        ''')
        info_layout = QVBoxLayout(self.info_frame)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(4)

        # Ollama loaded models info (bold title)
        self.ollama_models_label = QLabel("<b>Ollama Loaded Models:</b> <i>Loading...</i>")
        self.ollama_models_label.setTextFormat(Qt.TextFormat.RichText)
        self.ollama_models_label.setMinimumHeight(24)
        info_layout.addWidget(self.ollama_models_label)

        # GPU Info Section (bold title)
        self.gpu_info_label = QLabel("<b>GPU Info:</b> <i>Loading...</i>")
        self.gpu_info_label.setTextFormat(Qt.TextFormat.RichText)
        self.gpu_info_label.setMinimumHeight(24)
        info_layout.addWidget(self.gpu_info_label)

        # Refresh button
        self.gpu_refresh_button = QPushButton("Refresh GPU/Model Info")
        self.gpu_refresh_button.clicked.connect(self.update_gpu_and_model_info)
        info_layout.addWidget(self.gpu_refresh_button)
        info_layout.setAlignment(self.gpu_refresh_button, Qt.AlignmentFlag.AlignRight)

        right_panel.addWidget(self.info_frame)
        
        main_layout.addLayout(right_panel)
        
        # Set layout proportions
        main_layout.setStretch(0, 4)  # Left panel
        main_layout.setStretch(1, 6)  # Right panel
        
        # Initialize variables
        self.current_image_path = None
        self.worker = None

        # Add spacing between elements
        main_layout.setSpacing(20)
        left_panel.setSpacing(15)
        right_panel.setSpacing(10)
        controls_layout.setSpacing(10)
        
        # Add margins to layouts
        main_layout.setContentsMargins(20, 20, 20, 20)
        left_panel.setContentsMargins(0, 0, 0, 0)
        right_panel.setContentsMargins(0, 0, 0, 0)
        controls_layout.setContentsMargins(0, 10, 0, 10)

        # Add status label at the bottom of the left panel
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {self.LAVENDER_DARK}; font-size: {self.FONT_SIZE}; padding: 5px;")
        left_panel.addWidget(self.status_label)

    def handle_image_drop(self, image_path):
        self.current_image_path = image_path
        self.display_image(image_path)
        self.send_button.setEnabled(True)

    def upload_image(self):
        # Check Ollama status before uploading
        status_ok, result = check_ollama()
        if not status_ok:
            QMessageBox.critical(self, "Error", result)
            return
            
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_name:
            self.current_image_path = file_name
            self.display_image(file_name)
            self.send_button.setEnabled(True)

    def display_image(self, image_path):
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)

    def send_prompt(self):
        if self.current_image_path:
            self.generate_prompt(self.current_image_path)

    def generate_prompt(self, image_path):
        # Disable buttons while processing
        self.upload_button.setEnabled(False)
        self.send_button.setEnabled(False)
        self.flux_text.setText("Analyzing image...")
        
        # Get current prompt - no additional formatting
        current_prompt = self.prompt_text.toPlainText()
        
        # Get selected model
        selected_model = self.model_combo.currentText()
        
        # Create and start worker thread
        self.worker = PromptWorker(image_path, selected_model, current_prompt)
        self.worker.finished.connect(self.handle_prompt)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def handle_prompt(self, prompts):
        _, flux_prompt = prompts
        self.flux_text.setText(flux_prompt)
        self.upload_button.setEnabled(True)
        self.send_button.setEnabled(True)

    def handle_error(self, error_message):
        QMessageBox.critical(self, "Error", f"Failed to generate prompt: {error_message}")
        self.upload_button.setEnabled(True)
        self.send_button.setEnabled(True)

    def handle_text_only_generate(self):
        text = self.text_only_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "No Text", "Please enter a description in the Text Only Input window.")
            return
        self.prompt_text.setText("")
        self.flux_text.setText("")
        self.status_label.setText("Generating prompt from text only...")
        self.text_only_button.setEnabled(False)
        selected_model = self.model_combo.currentText()
        self.worker = PromptWorkerTextOnly(text, selected_model)
        self.worker.finished.connect(self.handle_worker_finished)
        self.worker.error.connect(self.handle_worker_error)
        self.worker.start()

    def handle_worker_finished(self, prompts):
        _, flux_prompt = prompts
        self.flux_text.setText(flux_prompt)
        self.status_label.setText("Prompt generated from text.")
        self.text_only_button.setEnabled(True)

    def handle_worker_error(self, error_message):
        QMessageBox.critical(self, "Error", f"Failed to generate prompt: {error_message}")
        self.text_only_button.setEnabled(True)

    def update_gpu_and_model_info(self):
        # Update GPU info
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                gpu_info_html = "<b>GPU Info:</b> <i>No GPU detected.</i>"
            else:
                info_lines = ["<b>GPU Info:</b>"]
                for gpu in gpus:
                    info_lines.append(
                        f"<b>GPU {gpu.id}:</b> {gpu.name}<br>"
                        f"&nbsp;&nbsp;Load: {gpu.load*100:.1f}%<br>"
                        f"&nbsp;&nbsp;Memory: {gpu.memoryUsed:.1f}MB / {gpu.memoryTotal:.1f}MB ({gpu.memoryUtil*100:.1f}%)<br>"
                        f"&nbsp;&nbsp;Temperature: {gpu.temperature}°C<br>"
                    )
                gpu_info_html = "<div style='line-height:1.5;'>" + "".join(info_lines) + "</div>"
            self.gpu_info_label.setText(gpu_info_html)
        except Exception as e:
            self.gpu_info_label.setText(f"<b>GPU Info:</b> <span style='color:#b00;'><i>Error: {e}</i></span>")
            print(f"[ERROR] GPU Info: {e}")
        # Update Ollama loaded models info
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                if models:
                    model_names = [model.get("name", "") for model in models]
                    self.ollama_models_label.setText("<b>Ollama Loaded Models:</b> " + ", ".join(model_names))
                else:
                    self.ollama_models_label.setText("<b>Ollama Loaded Models:</b> <i>None detected.</i>")
            else:
                self.ollama_models_label.setText(f"<b>Ollama Loaded Models:</b> <span style='color:#b00;'><i>Error: {response.status_code}</i></span>")
        except Exception as e:
            self.ollama_models_label.setText(f"<b>Ollama Loaded Models:</b> <span style='color:#b00;'><i>Error: {e}</i></span>")
            print(f"[ERROR] Ollama Models: {e}")

    def populate_model_combo(self):
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                self.model_combo.clear()
                for model in models:
                    name = model.get("name", "")
                    if name:
                        self.model_combo.addItem(name)
                if self.model_combo.count() > 0:
                    self.model_combo.setCurrentIndex(0)
            else:
                self.model_combo.clear()
                self.model_combo.addItem("Error loading models")
        except Exception as e:
            self.model_combo.clear()
            self.model_combo.addItem(f"Error: {e}")

    def handle_model_change(self):
        # Optionally update UI or status when model changes
        pass

def main():
    app = QApplication(sys.argv)
    window = ImageToPromptApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 
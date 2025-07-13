from typing import Optional
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QComboBox,
    QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent

from constants import FONT_SIZE, LAVENDER_LIGHT, LAVENDER_MID, LAVENDER_DARK, DEFAULT_PROMPT
from ollama_api import check_ollama, get_available_models
from gpu_info import get_gpu_info_html
from workers import PromptWorker, PromptWorkerTextOnly


class DragDropImageLabel(QLabel):
    image_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Drag and drop an image here\nor click Upload Image")
        self.setWordWrap(True)

    # Drag-and-drop overrides
    def dragEnterEvent(self, event: QDragEnterEvent):
        if (
            event.mimeData().hasUrls()
            and event.mimeData().urls()[0].toLocalFile().lower().endswith(
                (".png", ".jpg", ".jpeg", ".bmp", ".gif")
            )
        ):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        file_path = event.mimeData().urls()[0].toLocalFile()
        self.image_dropped.emit(file_path)


class ImageToPromptApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image to FLUX Prompt Generator")
        self.setMinimumSize(1800, 1000)
        self.resize(1800, 1000)

        # App-wide stylesheet
        self.setStyleSheet(
            f"""
            QMainWindow {{ background-color: {LAVENDER_LIGHT}; }}
            QLabel {{ font-size: {FONT_SIZE}; color: #2E2E2E; padding: 5px; }}
            QPushButton {{ font-size: {FONT_SIZE}; background-color: {LAVENDER_MID}; border: none; padding: 8px 15px; border-radius: 4px; color: white; }}
            QPushButton:hover {{ background-color: {LAVENDER_DARK}; }}
            QTextEdit {{ font-size: {FONT_SIZE}; background-color: white; border: 1px solid {LAVENDER_MID}; border-radius: 4px; padding: 5px; }}
        """
        )

        # Ensure Ollama available
        status_ok, result = check_ollama()
        if not status_ok:
            QMessageBox.critical(self, "Error", result)
            sys.exit(1)

        # Central widget + layouts
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # ---- Left panel ----
        left = QVBoxLayout()
        main_layout.addLayout(left)

        # Image preview + drag/drop
        self.image_label = DragDropImageLabel()
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setStyleSheet(
            f"QLabel {{ border: 2px dashed {LAVENDER_MID}; background-color: white; border-radius: 8px; }}"
        )
        self.image_label.image_dropped.connect(self._on_image_dropped)
        left.addWidget(self.image_label)

        # Extra notes
        left.addWidget(QLabel("Additional Notes (optional):"))
        self.extra_text = QTextEdit()
        self.extra_text.setFixedHeight(60)
        left.addWidget(self.extra_text)

        # Text-only input
        left.addWidget(QLabel("Text Only Input:"))
        self.text_only_input = QTextEdit()
        self.text_only_input.setFixedHeight(80)
        left.addWidget(self.text_only_input)
        self.text_only_btn = QPushButton("Generate from Text Only")
        self.text_only_btn.clicked.connect(self._on_text_only_generate)
        left.addWidget(self.text_only_btn)

        # Controls row
        controls = QHBoxLayout()
        left.addLayout(controls)
        upload_btn = QPushButton("Upload Image")
        upload_btn.clicked.connect(self._on_upload_image)
        controls.addWidget(upload_btn)
        self.upload_btn = upload_btn

        # ---- Right panel ----
        right = QVBoxLayout()
        main_layout.addLayout(right)

        # Prompt template
        right.addWidget(QLabel("Default prompt:"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setText(DEFAULT_PROMPT)
        self.prompt_edit.setMinimumHeight(200)
        right.addWidget(self.prompt_edit)

        # Model picker
        right.addWidget(QLabel("Select Ollama Model:"))
        self.model_combo = QComboBox()
        self._populate_models()
        right.addWidget(self.model_combo)

        # Send button
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send_prompt)
        self.send_btn.setEnabled(False)
        right.addWidget(self.send_btn)

        # FLUX prompt out
        right.addWidget(QLabel("FLUX Prompt:"))
        self.flux_out = QTextEdit()
        self.flux_out.setReadOnly(True)
        self.flux_out.setMinimumHeight(300)
        right.addWidget(self.flux_out)

        # Info frame
        self._build_info_frame(right)

        # Timer for auto-refresh
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_info)
        self.refresh_timer.start(10000)

        # Populate info panel immediately
        self._refresh_info()

        # State vars
        self.current_image: Optional[str] = None
        self.worker = None

    # ---------------------------------------------------------------------
    # UI helpers
    def _build_info_frame(self, parent_layout: QVBoxLayout):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet(
            """
            QFrame { background-color: #f5f5fa; border: 1px solid #bdbdd7; border-radius: 8px; padding: 10px; }
            QLabel { font-size: 9pt; color: #333; }
            """
        )
        info_layout = QVBoxLayout(frame)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(4)

        self.models_label = QLabel("<b>Ollama Loaded Models:</b> <i>Loading...</i>")
        self.models_label.setTextFormat(Qt.TextFormat.RichText)
        info_layout.addWidget(self.models_label)

        self.gpu_label = QLabel("<b>GPU Info:</b> <i>Loading...</i>")
        self.gpu_label.setTextFormat(Qt.TextFormat.RichText)
        info_layout.addWidget(self.gpu_label)

        refresh_btn = QPushButton("Refresh GPU/Model Info")
        refresh_btn.setStyleSheet("font-size: 9pt; padding: 4px 8px;")
        refresh_btn.clicked.connect(self._refresh_info)
        info_layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)

        parent_layout.addWidget(frame)

    # ------------------------------------------------------------------
    # Event handlers
    def _on_image_dropped(self, path: str):
        self.current_image = path
        self._display_image(path)
        self.send_btn.setEnabled(True)

    def _on_upload_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_name:
            self._on_image_dropped(file_name)

    def _on_send_prompt(self):
        if not self.current_image:
            return
        self.flux_out.setText("Analyzing image...")
        self.send_btn.setEnabled(False)
        self.upload_btn.setEnabled(False)
        model = self.model_combo.currentText()
        prompt = self.prompt_edit.toPlainText()
        self.worker = PromptWorker(Path(self.current_image), model, prompt)
        self.worker.finished.connect(self._on_prompt_done)
        self.worker.error.connect(self._on_worker_error)
        self.worker.start()

    def _on_prompt_done(self, prompts):
        _, flux_prompt = prompts
        self.flux_out.setText(flux_prompt)
        self.send_btn.setEnabled(True)
        self.upload_btn.setEnabled(True)

    def _on_worker_error(self, msg: str):
        QMessageBox.critical(self, "Error", f"Failed: {msg}")
        self.send_btn.setEnabled(True)
        self.upload_btn.setEnabled(True)

    def _on_text_only_generate(self):
        text = self.text_only_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "No Text", "Please enter a description.")
            return
        self.text_only_btn.setEnabled(False)
        self.flux_out.clear()
        model = self.model_combo.currentText()
        self.worker = PromptWorkerTextOnly(text, model)
        self.worker.finished.connect(self._on_text_only_done)
        self.worker.error.connect(self._on_worker_error)
        self.worker.start()

    def _on_text_only_done(self, prompts):
        _, flux_prompt = prompts
        self.flux_out.setText(flux_prompt)
        self.text_only_btn.setEnabled(True)

    # ------------------------------------------------------------------
    def _display_image(self, path: str):
        pix = QPixmap(path)
        scaled = pix.scaled(
            self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

    def _populate_models(self):
        self.model_combo.clear()
        for name in get_available_models():
            self.model_combo.addItem(name)
        if self.model_combo.count() == 0:
            self.model_combo.addItem("<none>")

    def _refresh_info(self):
        # Update models
        names = get_available_models()
        if names:
            model_text = "<b>Ollama Loaded Models:</b> " + ", ".join(names)
            self.models_label.setText(model_text)
            self.models_label.show()
        else:
            self.models_label.hide()
        # Update GPU
        gpu_text = get_gpu_info_html()
        print("[DEBUG] Setting gpu_label to:", gpu_text)
        self.gpu_label.setText(gpu_text)


def main():
    app = QApplication(sys.argv)
    win = ImageToPromptApp()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 
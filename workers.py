import base64
import io
import json
from pathlib import Path
from typing import Tuple

from PyQt6.QtCore import QThread, pyqtSignal
from PIL import Image
import requests

from constants import DEFAULT_PROMPT
from ollama_api import OLLAMA_BASE_URL


class PromptWorker(QThread):
    """Thread that sends an image + prompt to Ollama and returns cleaned response."""

    finished = pyqtSignal(tuple)  # (sdxl_prompt, flux_prompt)
    error = pyqtSignal(str)

    def __init__(self, image_path: str | Path, model_name: str, prompt: str = DEFAULT_PROMPT):
        super().__init__()
        self.image_path = str(image_path)
        self.model_name = model_name
        self.prompt = prompt or DEFAULT_PROMPT

    def run(self):
        try:
            with Image.open(self.image_path) as img:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                # Resize if very large (>800px in any dimension)
                max_size = 800
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format="JPEG")
                img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode()

            url = f"{OLLAMA_BASE_URL}/api/generate"
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": self.model_name,
                "prompt": self.prompt,
                "stream": False,
                "images": [img_base64],
                "options": {
                    "vision": True,
                    "temperature": 0.3,
                    "num_predict": 500,
                },
            }
            resp = requests.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama returned {resp.status_code}: {resp.text}")

            response_text = resp.json()["response"]
            cleaned = _clean_response(response_text)
            self.finished.emit(("", cleaned))
        except Exception as exc:
            self.error.emit(str(exc))


class PromptWorkerTextOnly(QThread):
    finished = pyqtSignal(tuple)
    error = pyqtSignal(str)

    def __init__(self, text: str, model_name: str):
        super().__init__()
        self.text = text
        self.model_name = model_name

    def run(self):
        try:
            url = f"{OLLAMA_BASE_URL}/api/generate"
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": self.model_name,
                "prompt": self.text,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 500},
            }
            resp = requests.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama returned {resp.status_code}: {resp.text}")
            response_text = resp.json()["response"]
            cleaned = _clean_response(response_text)
            self.finished.emit(("", cleaned))
        except Exception as exc:
            self.error.emit(str(exc))


def _clean_response(text: str) -> str:
    """Remove unwanted characters for Flux compatibility."""
    for repl in [
        ("  ", " "),
        ("*", ""),
        ("(", ""), (")", ""),
        ("[", ""), ("]", ""),
        ("{", ""), ("}", ""),
        ("<", ""), (">", ""),
        ("FLUX:", ""),
    ]:
        text = text.replace(*repl)
    text = "".join(c for c in text if c.isalnum() or c.isspace() or c in ",.-_")
    return text.strip() 
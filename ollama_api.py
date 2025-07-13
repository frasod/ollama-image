import requests
from typing import Tuple, List, Union

OLLAMA_BASE_URL = "http://localhost:11434"

def check_ollama() -> Tuple[bool, Union[str, List[str]]]:
    """Check if Ollama is running and return available model names.

    Returns
    -------
    (bool, str | list[str])
        First element indicates success. Second element is either an error message or a list of model names.
    """
    try:
        # Check server health
        if requests.get(f"{OLLAMA_BASE_URL}/api/version").status_code != 200:
            return False, "Ollama is not responding correctly"

        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if resp.status_code != 200:
            return False, "Could not get list of models"

        models = resp.json().get("models", [])
        model_names = [m.get("name") for m in models]
        return True, model_names
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to Ollama. Please make sure Ollama is running."
    except Exception as exc:
        return False, f"Error checking Ollama: {exc}"

def get_available_models(timeout: int = 2) -> list[str]:
    """Return a list of model names available in Ollama. Empty list if none or error."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=timeout)
        print("[DEBUG] Ollama /api/tags response:", resp.text)
        if resp.status_code != 200:
            return []
        data = resp.json()
        models = data.get("models", [])
        # Handle if models is a dict (single model) instead of a list
        if isinstance(models, dict):
            models = [models]
        if not isinstance(models, list):
            print("[DEBUG] Unexpected models type:", type(models))
            return []
        names = [m.get("name", "") for m in models if isinstance(m, dict) and m.get("name")]
        print("[DEBUG] Parsed model names:", names)
        return names
    except Exception as e:
        print("[DEBUG] Ollama get_available_models error:", e)
        return [] 
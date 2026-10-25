import threading
import requests
from typing import Optional
from src.config.settings import settings

class SequentialOllamaClient:
    """Thread-safe sequential Ollama client ensuring only 1 LLM runs at a time to stay within memory limits."""

    _lock = threading.Lock()

    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        num_predict: int = 512,
        stop: Optional[list[str]] = None
    ) -> str:
        model = model or settings.LLM_REASONING_MODEL

        options = {
            "temperature": temperature,
            "num_predict": num_predict
        }
        if stop:
            options["stop"] = stop

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options
        }
        if system_prompt:
            payload["system"] = system_prompt

        with self._lock:
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=settings.MAX_LLM_TIMEOUT_SECONDS
                )
                if response.status_code == 200:
                    return response.json().get("response", "").strip()
                else:
                    return f"Error from Ollama ({response.status_code}): {response.text}"
            except Exception as e:
                return f"Error contacting Ollama service: {str(e)}"

ollama_client = SequentialOllamaClient()

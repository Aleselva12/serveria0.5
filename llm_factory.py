import os

from langchain_ollama import ChatOllama

DEFAULT_OLLAMA_MODEL = "gpt-oss:20b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11435"


def get_ollama_model_name(model: str | None = None) -> str:
    """Return the configured local model name for the project."""
    return model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


def get_ollama_base_url() -> str:
    """Return the configured base URL for the local Ollama server."""
    return os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)


def ChatGroq(*args, model=None, api_key=None, temperature=0, **kwargs):
    """Always use the local Ollama runtime; no cloud API keys are required."""
    del args
    del api_key

    return ChatOllama(
        model=get_ollama_model_name(model),
        base_url=get_ollama_base_url(),
        temperature=temperature,
        **kwargs,
    )

"""
Zentrale Embedding-API

Aktuell: Ollama-Backend
Später: leicht austauschbar (OpenAI, lokales Modell, ...)

Verwendung:
    from lib.embeddings import get_embedding

    vec = get_embedding("mein text")
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

import numpy as np

try:
    import ollama
except ImportError as e:
    raise ImportError(
        "Das 'ollama'-Python-Paket ist nicht installiert. "
        "Bitte mit 'pip install ollama' nachinstallieren."
    ) from e

from lib.config import get_config_value


# Modellname zentral konfigurierbar (ENV > config.toml > Default)
DEFAULT_MODEL = get_config_value("embeddings", "model", "PKMS_EMBED_MODEL", "nomic-embed-text")
OLLAMA_URL = get_config_value("embeddings", "ollama_url", "OLLAMA_HOST", "http://localhost:11434")


def _select_model(model: str | None) -> str:
    """Wähle Modell: explizit übergebenes oder DEFAULT_MODEL."""
    return model or DEFAULT_MODEL


@lru_cache(maxsize=1024)
def _raw_embedding_cached(text: str, model: str) -> tuple[float, ...]:
    """
    Holen eines einzelnen Embeddings von Ollama (roh, als Tuple).

    LRU-Cache:
      - Key ist (text, model)
      - Rückgabe ist hashbares Tuple, damit der Cache funktioniert.
    """
    if not text:
        # Leerer Text → leeres Embedding
        return tuple()

    response = ollama.embed(
        model=model,
        input=text,
    )

    # Ollama-Response: response["embeddings"] ist Liste von Embeddings
    # (bei single input meist Länge 1)
    if "embeddings" in response:
        embs = response["embeddings"]
        if not embs:
            raise RuntimeError("Ollama embed: leere 'embeddings'-Liste erhalten.")
        emb = embs[0]
    elif "embedding" in response:
        # Ältere/alternative API-Form
        emb = response["embedding"]
    else:
        raise RuntimeError(
            f"Ollama embed: keine 'embeddings' oder 'embedding' im Response. "
            f"Keys: {list(response.keys())}"
        )

    return tuple(float(x) for x in emb)


def get_embedding(text: str, model: str | None = None) -> np.ndarray:
    """
    Hauptfunktion für die SearchEngine:
    text -> 1D np.ndarray[float32]

    Beispiel:
        from lib.embeddings import get_embedding
        vec = get_embedding("Hallo Welt")
    """
    model_name = _select_model(model)
    raw = _raw_embedding_cached(text, model_name)

    # Falls text leer war, gibt _raw_embedding_cached ein leeres Tuple zurück.
    if not raw:
        return np.zeros((0,), dtype=np.float32)

    return np.fromiter(raw, dtype=np.float32)


def get_embeddings(texts: List[str], model: str | None = None) -> np.ndarray:
    """
    Batch-Variante: mehrere Texte auf einmal.

    Rückgabe: 2D-Array (N, dim)

    Hinweis:
      - Kein Cache, weil in der Praxis meist einmalige Texte.
      - Kannst du später leicht erweitern, falls du es brauchst.
    """
    model_name = _select_model(model)

    # Filter leere Liste früh
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)

    response = ollama.embed(
        model=model_name,
        input=texts,
    )

    if "embeddings" in response:
        embs = response["embeddings"]
    elif "embedding" in response:
        # Falls das Backend wider Erwarten nur ein Embedding liefert
        embs = [response["embedding"]]
    else:
        raise RuntimeError(
            f"Ollama embed (batch): keine 'embeddings' oder 'embedding' im Response. "
            f"Keys: {list(response.keys())}"
        )

    arr = np.asarray(embs, dtype=np.float32)
    return arr


def embedding_dim(model: str | None = None) -> int:
    """
    Praktische Hilfsfunktion: ermittelt die Dimension des Embeddings,
    indem ein kurzer Test-Text eingebettet wird.
    """
    vec = get_embedding("dimension probe", model=model)
    return int(vec.shape[0]) if vec.ndim == 1 else 0


if __name__ == "__main__":
    # Kleiner Selbsttest
    text = "Hallo Ollama, was ist die Embedding-Dimension?"
    vec = get_embedding(text)
    print(f"Text: {text!r}")
    print(f"Embedding-Dimension: {vec.shape[0]}")
    print(f"Erste 5 Werte: {vec[:5]}")

"""Image embedding helpers for visual artwork matching."""

from __future__ import annotations

import hashlib
import logging
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import numpy as np
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_KEY = f"{settings.visual_embedding_model}:{settings.visual_embedding_pretrained}"


class VisualEmbeddingError(RuntimeError):
    """Raised when embeddings cannot be computed."""


class EmbeddingBackend(Protocol):
    def embed_image(self, image: Image.Image) -> list[float]: ...


def cosine_similarity(left: list[float] | np.ndarray, right: list[float] | np.ndarray) -> float:
    left_vec = np.asarray(left, dtype=np.float32)
    right_vec = np.asarray(right, dtype=np.float32)
    if left_vec.size == 0 or right_vec.size == 0:
        return 0.0
    left_norm = np.linalg.norm(left_vec)
    right_norm = np.linalg.norm(right_vec)
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return float(np.dot(left_vec, right_vec) / (left_norm * right_norm))


def normalize_vector(values: list[float] | np.ndarray) -> list[float]:
    vec = np.asarray(values, dtype=np.float32)
    norm = np.linalg.norm(vec)
    if norm == 0.0:
        return vec.tolist()
    return (vec / norm).tolist()


class TestEmbeddingBackend:
    """Deterministic lightweight embeddings for unit tests (not semantic)."""

    dimensions = 128

    def embed_image(self, image: Image.Image) -> list[float]:
        thumb = image.convert("RGB").resize((32, 32))
        pixels = np.asarray(thumb, dtype=np.float32).reshape(-1)
        digest = hashlib.sha256(pixels.tobytes()).digest()
        seed = np.frombuffer(digest, dtype=np.uint8).astype(np.float32)
        repeated = np.resize(seed, self.dimensions)
        return normalize_vector(repeated.tolist())


def _resolve_torch_device(torch) -> str:
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class OpenCLIPEmbeddingBackend:
    def __init__(self, model_name: str, pretrained: str) -> None:
        import open_clip
        import torch

        self._torch = torch
        self._device = _resolve_torch_device(torch)
        self._model, _, self._preprocess = open_clip.create_model_and_transforms(
            model_name,
            pretrained=pretrained,
        )
        self._model = self._model.to(self._device)
        self._model.eval()
        logger.info("OpenCLIP embedding backend using device=%s", self._device)

    def embed_image(self, image: Image.Image) -> list[float]:
        rgb = image.convert("RGB")
        tensor = self._preprocess(rgb).unsqueeze(0).to(self._device)
        with self._torch.no_grad():
            features = self._model.encode_image(tensor)
            features = features / features.norm(dim=-1, keepdim=True)
        return normalize_vector(features.squeeze(0).detach().cpu().numpy().tolist())


@lru_cache(maxsize=1)
def get_embedding_backend() -> EmbeddingBackend:
    backend_name = settings.visual_embedding_backend.strip().lower()
    if backend_name == "test":
        return TestEmbeddingBackend()

    try:
        return OpenCLIPEmbeddingBackend(
            settings.visual_embedding_model,
            settings.visual_embedding_pretrained,
        )
    except ImportError as exc:
        raise VisualEmbeddingError(
            "Visual embedding model is unavailable. Install requirements-visual.txt "
            "or set VISUAL_EMBEDDING_BACKEND=test for local development."
        ) from exc


def embed_pil_image(image: Image.Image) -> list[float]:
    return get_embedding_backend().embed_image(image)


def embed_image_path(path: Path) -> list[float]:
    if not path.is_file():
        raise VisualEmbeddingError(f"Image file not found: {path}")
    with Image.open(path) as image:
        return embed_pil_image(image)


def embed_image_bytes(data: bytes) -> list[float]:
    from io import BytesIO

    with Image.open(BytesIO(data)) as image:
        return embed_pil_image(image)


def resolve_artwork_image_path(image_url: str | None) -> Path:
    if not image_url or not image_url.strip():
        raise VisualEmbeddingError("Artwork has no image to match.")

    normalized = image_url.strip()
    if normalized.startswith("http://") or normalized.startswith("https://"):
        raise VisualEmbeddingError("Remote artwork URLs are not supported for visual matching yet.")

    relative = normalized.removeprefix("/uploads/").lstrip("/")
    path = (Path(settings.upload_dir).resolve() / relative).resolve()
    upload_root = Path(settings.upload_dir).resolve()
    if upload_root not in path.parents and path != upload_root:
        raise VisualEmbeddingError("Artwork image path is outside the upload directory.")
    if not path.is_file():
        raise VisualEmbeddingError("Artwork image file is missing on disk.")
    return path

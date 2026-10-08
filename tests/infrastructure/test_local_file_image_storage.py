# Checks that uploaded images are stored locally and return correct metadata.
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.infrastructure.storage.local_file_image_storage import (
    InvalidImageKeyError,
    LocalFileImageStorage,
)


def _png_bytes() -> bytes:
    image = Image.new("RGB", (8, 6), color=(40, 80, 120))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_default_storage_root_is_inside_backend_repo(monkeypatch):
    monkeypatch.delenv("FQC_IMAGE_STORAGE_ROOT", raising=False)
    storage = LocalFileImageStorage.from_environment()
    backend_root = Path(__file__).resolve().parents[2]

    assert storage._root == backend_root / "storage" / "images"


def test_local_storage_ignores_client_filename_and_rejects_traversal(tmp_path):
    root = tmp_path / "private-images"
    storage = LocalFileImageStorage(root)
    stored = storage.store(
        inspection_id="INS-00001",
        view_id="top",
        filename="..\\..\\outside.png",
        content=_png_bytes(),
    )

    assert stored.key is not None
    assert ".." not in stored.key
    assert (root / stored.key).is_file()
    with pytest.raises(InvalidImageKeyError):
        storage.retrieve("../outside.png")
    with pytest.raises(InvalidImageKeyError):
        storage.retrieve("inspections\\..\\outside.png")

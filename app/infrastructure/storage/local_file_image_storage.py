# Stores uploaded inspection images as local files and provides their metadata.
import os
import mimetypes
from io import BytesIO
from pathlib import Path, PurePosixPath
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from app.infrastructure.storage.data_uri_image_storage import InvalidImageError
from app.infrastructure.storage.interfaces import RetrievedImage, StoredImage


class InvalidImageKeyError(ValueError):
    pass


class LocalFileImageStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_environment(cls) -> "LocalFileImageStorage":
        backend_root = Path(__file__).resolve().parents[3]
        configured_root = os.getenv("FQC_IMAGE_STORAGE_ROOT", "storage/images")
        root = Path(configured_root).expanduser()
        if not root.is_absolute():
            root = backend_root / root
        return cls(root)

    def store(
        self,
        *,
        inspection_id: str,
        view_id: str,
        filename: str,
        content: bytes,
    ) -> StoredImage:
        del view_id, filename
        width, height, _, extension = _inspect_image(content)
        key = f"inspections/{inspection_id}/views/{uuid4().hex}{extension}"
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as image_file:
                image_file.write(content)
        except OSError:
            path.unlink(missing_ok=True)
            raise
        return StoredImage(
            url=f"/api/v1/images/{key}",
            width=width,
            height=height,
            key=key,
        )

    def retrieve(self, key: str) -> RetrievedImage | None:
        path = self._resolve(key)
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            return None
        _, _, media_type, _ = _inspect_image(content)
        return RetrievedImage(content=content, media_type=media_type)

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        path.unlink(missing_ok=True)

    def _resolve(self, key: str) -> Path:
        if "\\" in key or "\x00" in key:
            raise InvalidImageKeyError("Invalid image storage key")
        relative_path = PurePosixPath(key)
        if relative_path.is_absolute() or not relative_path.parts:
            raise InvalidImageKeyError("Invalid image storage key")
        if any(part in {".", ".."} for part in relative_path.parts):
            raise InvalidImageKeyError("Invalid image storage key")
        resolved = self._root.joinpath(*relative_path.parts).resolve()
        if not resolved.is_relative_to(self._root):
            raise InvalidImageKeyError("Invalid image storage key")
        return resolved


def _inspect_image(content: bytes) -> tuple[int, int, str, str]:
    try:
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
            image_format = image.format
            media_type = image.get_format_mimetype()
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise InvalidImageError(
            "Uploaded file is not a valid supported image"
        ) from error

    if image_format is None or media_type is None:
        raise InvalidImageError("Uploaded image format is not supported")
    extension = mimetypes.guess_extension(media_type)
    if extension is None:
        raise InvalidImageError("Uploaded image format is not supported")
    return width, height, media_type, extension

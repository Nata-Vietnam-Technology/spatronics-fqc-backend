# Defines the image storage port, data shapes, and shared storage errors.
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StoredImage:
    url: str
    width: int
    height: int
    key: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievedImage:
    content: bytes
    media_type: str


class InvalidImageError(ValueError):
    """Raised when uploaded image content is invalid or unsupported."""


class InvalidImageKeyError(ValueError):
    """Raised when an image storage key is invalid."""


class ImageStorage(Protocol):
    def store(
        self,
        *,
        inspection_id: str,
        view_id: str,
        filename: str,
        content: bytes,
    ) -> StoredImage: ...

    def retrieve(self, key: str) -> RetrievedImage | None: ...

    def delete(self, key: str) -> None: ...

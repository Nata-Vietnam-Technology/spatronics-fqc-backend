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


class ImageStorage(Protocol):
    def store(
        self,
        *,
        inspection_id: str,
        view_id: str,
        filename: str,
        content: bytes,
    ) -> StoredImage:
        ...

    def retrieve(self, key: str) -> RetrievedImage | None:
        ...

    def delete(self, key: str) -> None:
        ...
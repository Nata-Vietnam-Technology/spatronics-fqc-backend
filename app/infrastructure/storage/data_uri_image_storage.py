# Stores images as data URIs for lightweight application setups.
import base64
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.infrastructure.storage.interfaces import RetrievedImage, StoredImage


class InvalidImageError(ValueError):
    pass


class DataUriImageStorage:
    def store(
        self,
        *,
        inspection_id: str,
        view_id: str,
        filename: str,
        content: bytes,
    ) -> StoredImage:
        del inspection_id, view_id, filename
        try:
            with Image.open(BytesIO(content)) as image:
                width, height = image.size
                media_type = image.get_format_mimetype()
                image.verify()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            raise InvalidImageError(
                "Uploaded file is not a valid supported image"
            ) from error

        if media_type is None:
            raise InvalidImageError("Uploaded image format is not supported")

        encoded = base64.b64encode(content).decode("ascii")
        return StoredImage(
            url=f"data:{media_type};base64,{encoded}",
            width=width,
            height=height,
        )

    def retrieve(self, key: str) -> RetrievedImage | None:
        del key
        return None

    def delete(self, key: str) -> None:
        del key

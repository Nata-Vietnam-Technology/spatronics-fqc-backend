from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.infrastructure.storage.local_file_image_storage import InvalidImageKeyError
from app.infrastructure.storage.interfaces import ImageStorage

router = APIRouter(prefix="/api/v1/images", tags=["images"])


def get_image_storage(request: Request) -> ImageStorage:
    return request.app.state.image_storage


@router.get("/{image_key:path}", include_in_schema=False)
def get_stored_image(
    image_key: str,
    storage: Annotated[ImageStorage, Depends(get_image_storage)],
) -> Response:
    try:
        image = storage.retrieve(image_key)
    except InvalidImageKeyError as error:
        raise HTTPException(status_code=404, detail="Image not found") from error
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=image.content, media_type=image.media_type)
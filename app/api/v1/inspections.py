from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.infrastructure.storage.data_uri_image_storage import InvalidImageError
from app.schemas.inspection import Inspection
from app.services.inspection_service import (
    InspectionInputError,
    InspectionService,
    UploadedImage,
)

router = APIRouter(prefix="/api/v1/inspections", tags=["inspections"])


def get_inspection_service(request: Request) -> InspectionService:
    return request.app.state.inspection_service


@router.post("", response_model=Inspection)
async def create_inspection(
    sku_code: Annotated[str, Form()],
    station_id: Annotated[str, Form()],
    shift_id: Annotated[str, Form()],
    view_ids: Annotated[str, Form()],
    images: Annotated[
        list[UploadFile],
        File(json_schema_extra={"items": {"type": "string", "format": "binary"}}),
    ],
    service: Annotated[InspectionService, Depends(get_inspection_service)],
) -> Inspection:
    uploaded_images = [
        UploadedImage(
            filename=image.filename or "upload",
            content=await image.read(),
        )
        for image in images
    ]
    try:
        return service.create_inspection(
            sku_code=sku_code,
            station_id=station_id,
            shift_id=shift_id,
            view_ids_json=view_ids,
            images=uploaded_images,
        )
    except InspectionInputError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except InvalidImageError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{inspection_id}", response_model=Inspection)
def get_inspection(
    inspection_id: str,
    service: Annotated[InspectionService, Depends(get_inspection_service)],
) -> Inspection:
    inspection = service.get_inspection(inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return inspection
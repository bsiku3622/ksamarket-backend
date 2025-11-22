from io import BytesIO
from fastapi import HTTPException, Response, UploadFile, File, Form
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.models import *
from db.connection import get_db
import os
import uuid
from PIL import Image
from pathlib import Path

router = APIRouter()

# UPLOAD_DIR = "images/"
UPLOAD_DIR = Path(__file__).parent.parent / "statics" / "images"
if not UPLOAD_DIR.exists():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/items/{item_id}/images")
async def upload_images(
    item_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    item = db.query(Item).filter(Item.id == item_id, Item.image_url == None).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    today = datetime.now().date().strftime("%Y/%m/%d/")
    output_path = UPLOAD_DIR / today / f"{item_id}.webp"
    os.makedirs(output_path.parent, exist_ok=True)

    if output_path.exists():
        raise HTTPException(
            status_code=400, detail="Images for this item already exist"
        )

    output_path = str(output_path)

    try:
        file_bytes = await file.read()
        img = Image.open(BytesIO(file_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")

    try:
        img.save(output_path, "WEBP", quality=80)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")

    item.image_url = output_path  # type: ignore
    db.commit()
    return Response(status_code=201)

import os
import shutil
import zipfile
from datetime import datetime
from io import BytesIO

import cv2
from app.deps import get_current_user
from app.ml.clothing_detector import get_clothes_from_img
from app.models.user import User
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/clothing", tags=["clothing"])


@router.post("/detect-clothes/")
async def detect_clothes(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint to detect clothes in an uploaded image.
    Returns a zip file containing all detected clothing items.
    """
    temp_dir = None
    try:
        # Create temporary directory for this request
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = os.path.join("app/storage/clothing_detection", f"temp_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)

        # Save uploaded file temporarily
        temp_path = os.path.join(temp_dir, file.filename)
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Get detected clothes
        detected_clothes = get_clothes_from_img(temp_path)

        if not detected_clothes:
            raise HTTPException(status_code=404, detail="No clothing items detected")

        # Create zip file in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            # Save each detected clothing item to the zip
            for cloth in detected_clothes:
                # Save cloth to temporary file
                cloth_path = os.path.join(temp_dir, f"{cloth[0]}.png")
                cv2.imwrite(cloth_path, cloth[1])
                # Add to zip
                zip_file.write(cloth_path, f"{cloth[0]}.png")

        # Prepare zip file for sending
        zip_buffer.seek(0)

        # Return the zip file
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": 'attachment; filename="detected_clothes.zip"'
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temporary directory and files
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

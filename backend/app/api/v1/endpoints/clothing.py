from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import cv2
import numpy as np
import os
from typing import List
import uuid
from datetime import datetime
import zipfile
from io import BytesIO
import shutil

from app.ml.clothing_detector import get_clothes_from_img

router = APIRouter(prefix="/clothing", tags=["clothing"])

@router.post("/detect-clothes/")
async def detect_clothes(file: UploadFile = File(...)):
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
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
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
            headers={"Content-Disposition": 'attachment; filename="detected_clothes.zip"'}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Clean up temporary directory and files
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

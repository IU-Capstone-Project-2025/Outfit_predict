import os
import shutil
import zipfile
from datetime import datetime
from io import BytesIO

import cv2
from app.core.logging import get_logger
from app.deps import get_current_user
from app.ml.outfit_processing import get_clothes_from_img
from app.models.user import User
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

# Initialize logger for clothing operations
logger = get_logger("app.api.clothing")

router = APIRouter(prefix="/clothing", tags=["clothing"])


@router.post("/detect-clothes/")
async def detect_clothes(
    file: UploadFile = File(...), current_user: User = Depends(get_current_user)
):
    """
    Detects individual clothing items in an uploaded image and returns them as a ZIP archive.

    This endpoint processes an image to identify and segment clothing items, such as shirts,
    pants, and shoes. Each detected item is saved as a PNG image and packaged into a
    single ZIP file.

    - **file**: The uploaded image file (e.g., JPEG, PNG).
    - **current_user**: The authenticated user making the request.

    Returns a ZIP file containing the detected clothing items. If no items are detected,
    a 404 error is returned.
    """
    logger.info(f"Clothing detection started for user {current_user.email}")
    logger.debug(
        f"Upload details - filename: {file.filename}, content_type: {file.content_type}"
    )

    temp_dir = None
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            logger.warning(
                f"Invalid file type for clothing detection by user {current_user.email}:"
                f"{file.content_type}"
            )
            raise HTTPException(status_code=400, detail="File must be an image")

        # Create temporary directory for this request
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = os.path.join("app/storage/clothing_detection", f"temp_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)
        logger.debug(f"Created temporary directory: {temp_dir}")

        # Save uploaded file temporarily
        temp_path = os.path.join(temp_dir, file.filename)
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        logger.debug(f"Saved uploaded file to: {temp_path}")

        # Get detected clothes
        logger.info(f"Starting ML clothing detection for user {current_user.email}")
        detected_clothes = get_clothes_from_img(temp_path)

        if not detected_clothes:
            logger.warning(f"No clothing items detected for user {current_user.email}")
            raise HTTPException(status_code=404, detail="No clothing items detected")

        logger.info(
            f"Successfully detected {len(detected_clothes)} clothing items for user {current_user.email}"
        )

        # Create zip file in memory
        logger.debug("Creating ZIP file with detected clothing items")
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            # Save each detected clothing item to the zip
            for i, cloth in enumerate(detected_clothes):
                try:
                    # Save cloth to temporary file
                    cloth_name = cloth[0] if cloth[0] else f"clothing_item_{i}"
                    cloth_path = os.path.join(temp_dir, f"{cloth_name}.png")
                    cv2.imwrite(cloth_path, cloth[1])

                    # Add to zip
                    zip_file.write(cloth_path, f"{cloth_name}.png")
                    logger.debug(f"Added {cloth_name}.png to ZIP file")

                except Exception as item_error:
                    logger.warning(
                        f"Failed to process clothing item {i}"
                        f"for user {current_user.email}: {str(item_error)}"
                    )
                    continue

        # Prepare zip file for sending
        zip_buffer.seek(0)
        logger.info(
            f"ZIP file created successfully with clothing items for user {current_user.email}"
        )

        # Return the zip file
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": 'attachment; filename="detected_clothes.zip"'
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error in clothing detection for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temporary directory and files
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temporary directory: {temp_dir}")
        logger.info(f"Clothing detection completed for user {current_user.email}")

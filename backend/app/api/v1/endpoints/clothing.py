from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
import os
import shutil
import zipfile
from datetime import datetime
from io import BytesIO
import base64
import traceback

import cv2
from app.core.logging import get_logger
from app.deps import get_current_user
from app.ml.outfit_processing import get_clothes_from_img
from app.models.user import User
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from app.ml.image_search_google import search_images_google
from app.ml.ml_models import fashion_segmentation_model

# Initialize logger for clothing operations
logger = get_logger("app.api.clothing")

router = APIRouter(prefix="/clothing", tags=["clothing"])


@router.post("/detect-clothes/")
async def detect_clothes(
    file: UploadFile = File(...), current_user: User = Depends(get_current_user)
):
    """
    Endpoint to detect clothes in an uploaded image.
    Returns a zip file containing all detected clothing items.
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


@router.post("/detect-clothes-with-captions/")
async def detect_clothes_with_captions(file: UploadFile = File(...)):
    """
    Endpoint to detect clothes and generate captions for each item.
    Returns a JSON with name, caption, and base64 image for each detected clothing item.
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

        # Get detected clothes with captions
        detected_clothes = fashion_segmentation_model.get_segment_images_with_captions(temp_path)

        if not detected_clothes:
            raise HTTPException(status_code=404, detail="No clothing items detected")

        result = []
        for item in detected_clothes:
            # item: {"image": np.ndarray, "class_name": ..., "caption": ..., "short_caption": ...}
            _, buffer = cv2.imencode('.png', item["image"])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            result.append({
                "name": item["class_name"],
                "caption": item["caption"],
                "short_caption": item["short_caption"],
                "image_base64": img_base64
            })
        return JSONResponse(content={"clothes": result})
    
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@router.get("/search-google/")
async def search_google_images(query: str = Query(..., description="Text description of clothing"), num: int = Query(5, ge=1, le=10)):
    """
    Search for similar clothing items on the internet using Google Custom Search API.
    Returns a list of image URLs.
    """
    try:
        results = search_images_google(query, num=num)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/detect-clothes-search-google/")
async def detect_clothes_search_google(file: UploadFile = File(...)):
    """
    Endpoint: сегментирует вещи, генерирует описание (caption) и ищет по нему в Google Search.
    Возвращает для каждой вещи: class_name, caption, short_caption, image_base64, google_results (список ссылок).
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

        # Сегментируем и получаем описания
        detected_clothes = fashion_segmentation_model.get_segment_images_with_captions(temp_path)
        if not detected_clothes:
            raise HTTPException(status_code=404, detail="No clothing items detected")

        result = []
        for item in detected_clothes:
            _, buffer = cv2.imencode('.png', item["image"])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            # Поиск по short_caption (или caption)
            google_results = []
            try:
                if item["short_caption"]:
                    google_results = search_images_google(item["short_caption"])
            except Exception as e:
                google_results = []
            result.append({
                "name": item["class_name"],
                "caption": item["caption"],
                "short_caption": item["short_caption"],
                "image_base64": img_base64,
                "google_results": google_results
            })
        return JSONResponse(content={"clothes": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
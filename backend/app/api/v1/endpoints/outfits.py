from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.deps import get_db, get_minio
from app.crud import outfit as outfit_crud
from app.schemas.outfit import OutfitRead
from app.storage.minio_client import MinioService
from app.ml.outfit_search import OutfitSearchEngine
from fastapi.responses import StreamingResponse
from uuid import UUID
from PIL import Image
import io

router = APIRouter(prefix="/outfits", tags=["outfits"])

# Initialize the search engine
search_engine = OutfitSearchEngine()

@router.post("/upload/", response_model=OutfitRead)
async def upload_outfit(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio)
):
    """Upload a new outfit image."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Upload to MinIO
    object_name = minio.save_file(await file.read(), content_type=file.content_type)
    
    # Create outfit record
    outfit = await outfit_crud.create_outfit(db, object_name)
    
    # Build proxy URL
    proxy_url = request.url_for("get_outfit_file", object_name=outfit.object_name)
    
    # Convert to schema
    return OutfitRead(
        id=outfit.id,
        object_name=outfit.object_name,
        created_at=outfit.created_at,
        url=str(proxy_url)
    )

@router.get("/", response_model=List[OutfitRead])
async def get_outfits(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get a list of outfits."""
    outfits = await outfit_crud.list_outfits(db, skip=skip, limit=limit)
    return [
        OutfitRead(
            id=outfit.id,
            object_name=outfit.object_name,
            created_at=outfit.created_at,
            url=str(request.url_for("get_outfit_file", object_name=outfit.object_name))
        )
        for outfit in outfits
    ]

@router.get("/{outfit_id}", response_model=OutfitRead)
async def get_outfit(
    request: Request,
    outfit_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific outfit by ID."""
    outfit = await outfit_crud.get_outfit(db, outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return OutfitRead(
        id=outfit.id,
        object_name=outfit.object_name,
        created_at=outfit.created_at,
        url=str(request.url_for("get_outfit_file", object_name=outfit.object_name))
    )

@router.get("/file/{object_name}", name="get_outfit_file")
async def get_outfit_file(
    object_name: str,
    minio: MinioService = Depends(get_minio)
):
    """Stream an outfit image from MinIO."""
    try:
        obj = minio.get_stream(object_name)
        
        # Build generator to cleanly close the connection afterwards
        def iter_data():
            for chunk in obj.stream(32 * 1024):
                yield chunk
            obj.close()
            
        headers = {
            "Content-Disposition": f'inline; filename="{object_name}"',
            "Content-Length": obj.headers.get("Content-Length", "0"),
        }
        media_type = obj.headers.get("Content-Type", "application/octet-stream")
        return StreamingResponse(iter_data(), media_type=media_type, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=404, detail="File not found")

@router.post("/search-similar/")
async def search_similar_outfits(
    request: Request,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio)
):
    """
    Search for similar outfits based on uploaded images.
    Accepts 1-8 images and returns the most similar outfits from the database.
    """
    if not 1 <= len(files) <= 8:
        raise HTTPException(
            status_code=400,
            detail="Number of images must be between 1 and 8"
        )

    # Convert uploaded files to PIL Images
    images = []
    for file in files:
        if not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} must be an image"
            )
        
        content = await file.read()
        try:
            image = Image.open(io.BytesIO(content))
            images.append(image)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Could not process image {file.filename}: {str(e)}"
            )

    # Find similar outfits
    similar_outfits = await search_engine.find_similar_outfits(
        images=images,
        db=db,
        minio=minio
    )

    # Get outfit details for each result
    results = []
    for outfit_id, score in similar_outfits:
        outfit = await outfit_crud.get_outfit(db, UUID(outfit_id))
        if outfit:
            proxy_url = request.url_for("get_outfit_file", object_name=outfit.object_name)
            results.append({
                "outfit": OutfitRead(
                    id=outfit.id,
                    object_name=outfit.object_name,
                    created_at=outfit.created_at,
                    url=str(proxy_url)
                ),
                "similarity_score": score
            })

    return results 
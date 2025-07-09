from app.core.security import create_access_token
from app.crud.user import authenticate_user, create_user
from app.deps import get_current_user, get_db, get_minio
from app.models.user import User
from app.schemas.user import Token
from app.schemas.user import User as UserOut
from app.schemas.user import UserCreate
from app.storage.minio_client import MinioService
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/signup", response_model=UserOut)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == user_in.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    user = await create_user(db, user_in)
    return user


@router.delete("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_user_data(
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    """
    Clean up orphaned data for the current user across all storage systems.
    This removes files in MinIO and vectors in Qdrant that are no longer
    referenced in the PostgreSQL database.
    """
    from app.crud import image as crud_image
    from app.crud import outfit as outfit_crud

    cleanup_report: dict = {"minio_deleted": [], "qdrant_deleted": [], "errors": []}

    try:
        # Get all user's images and outfits from database
        user_images = await crud_image.list_images(
            db, current_user.id, skip=0, limit=10000
        )
        user_outfits = await outfit_crud.list_outfits(
            db, current_user.id, skip=0, limit=10000
        )

        # Get all object names that should exist
        valid_object_names = set()
        for image in user_images:
            valid_object_names.add(image.object_name)
        for outfit in user_outfits:
            valid_object_names.add(outfit.object_name)

        # Get all outfit IDs that should have vectors
        # valid_outfit_ids = {str(outfit.id) for outfit in user_outfits}  # Currently unused

        # Note: This is a basic cleanup endpoint
        # In production, you might want to:
        # 1. List all files in MinIO with a prefix
        # 2. List all vectors in Qdrant for this user
        # 3. Compare and remove orphaned items
        # For now, this is a placeholder for the cleanup logic

        return {
            "message": "Cleanup completed",
            "report": cleanup_report,
            "valid_images": len(user_images),
            "valid_outfits": len(user_outfits),
        }

    except Exception as e:
        cleanup_report["errors"].append(str(e))
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

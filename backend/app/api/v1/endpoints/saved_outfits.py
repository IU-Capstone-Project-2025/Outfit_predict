from typing import List
from uuid import UUID

from app.core.logging import get_logger
from app.core.url_utils import build_url
from app.crud import outfit as outfit_crud
from app.crud import saved_outfit as saved_outfit_crud
from app.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.saved_outfit import (
    SavedOutfitCreate,
    SavedOutfitRead,
    SavedOutfitWithDetails,
)
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

# Initialize logger for saved outfit operations
logger = get_logger("app.api.saved_outfits")

router = APIRouter(prefix="/saved-outfits", tags=["saved-outfits"])


@router.post("/", response_model=SavedOutfitRead)
async def save_outfit(
    outfit_data: SavedOutfitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save an outfit to the user's saved collection."""
    logger.info(f"Saving outfit {outfit_data.outfit_id} for user {current_user.email}")

    try:
        # Verify outfit exists
        outfit = await outfit_crud.get_outfit_by_id_any(db, outfit_data.outfit_id)
        if not outfit:
            logger.warning(
                f"Outfit {outfit_data.outfit_id} not found for user {current_user.email}"
            )
            raise HTTPException(status_code=404, detail="Outfit not found")

        # Save the outfit
        saved_outfit = await saved_outfit_crud.save_outfit(
            db, current_user.id, outfit_data
        )

        logger.info(
            f"Successfully saved outfit {outfit_data.outfit_id} for user {current_user.email}"
        )

        return SavedOutfitRead(
            id=saved_outfit.id,
            user_id=saved_outfit.user_id,
            outfit_id=saved_outfit.outfit_id,
            completeness_score=saved_outfit.completeness_score,
            matches=saved_outfit.matches,
            created_at=saved_outfit.created_at,
        )

    except ValueError as e:
        logger.warning(
            f"Failed to save outfit {outfit_data.outfit_id} for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error saving outfit {outfit_data.outfit_id} for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error saving outfit",
        )


@router.get("/", response_model=List[SavedOutfitWithDetails])
async def get_saved_outfits(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all saved outfits for the current user with outfit details."""
    logger.info(
        f"Retrieving saved outfits for user {current_user.email} (skip={skip}, limit={limit})"
    )

    try:
        saved_outfits = await saved_outfit_crud.list_saved_outfits(
            db, current_user.id, skip=skip, limit=limit
        )

        logger.info(
            f"Found {len(saved_outfits)} saved outfits for user {current_user.email}"
        )

        result = []
        for saved_outfit in saved_outfits:
            # Get outfit details
            outfit = await outfit_crud.get_outfit_by_id_any(db, saved_outfit.outfit_id)
            if not outfit:
                logger.warning(
                    f"Outfit {saved_outfit.outfit_id} not found, skipping saved outfit {saved_outfit.id}"
                )
                continue

            # Build outfit URL
            outfit_url = build_url(
                request, "get_outfit_file", object_name=outfit.object_name
            )

            outfit_details = {
                "id": str(outfit.id),
                "url": outfit_url,
                "object_name": outfit.object_name,
                "created_at": outfit.created_at.isoformat(),
            }

            result.append(
                SavedOutfitWithDetails(
                    id=saved_outfit.id,
                    user_id=saved_outfit.user_id,
                    outfit_id=saved_outfit.outfit_id,
                    completeness_score=saved_outfit.completeness_score,
                    matches=saved_outfit.matches,
                    created_at=saved_outfit.created_at,
                    outfit=outfit_details,
                )
            )

        logger.info(
            f"Returning {len(result)} saved outfits for user {current_user.email}"
        )
        return result

    except Exception as e:
        logger.error(
            f"Error retrieving saved outfits for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving saved outfits",
        )


@router.delete("/{saved_outfit_id}")
async def delete_saved_outfit(
    saved_outfit_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a saved outfit."""
    logger.info(
        f"Deleting saved outfit {saved_outfit_id} for user {current_user.email}"
    )

    try:
        deleted = await saved_outfit_crud.delete_saved_outfit(
            db, saved_outfit_id, current_user.id
        )

        if not deleted:
            logger.warning(
                f"Saved outfit {saved_outfit_id} not found for user {current_user.email}"
            )
            raise HTTPException(status_code=404, detail="Saved outfit not found")

        logger.info(
            f"Successfully deleted saved outfit {saved_outfit_id} for user {current_user.email}"
        )
        return {"message": "Saved outfit deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error deleting saved outfit {saved_outfit_id} for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting saved outfit",
        )

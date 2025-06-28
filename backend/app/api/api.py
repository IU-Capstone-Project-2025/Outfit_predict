from app.api.endpoints import outfits
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(outfits.router, prefix="/outfits", tags=["outfits"])

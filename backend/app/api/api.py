from fastapi import APIRouter
from app.api.endpoints import outfits

api_router = APIRouter()
api_router.include_router(outfits.router, prefix="/outfits", tags=["outfits"]) 
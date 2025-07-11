import uvicorn
from app.api.v1.endpoints import auth as auth_router
from app.api.v1.endpoints import clothing as clothing_router
from app.api.v1.endpoints import image as image_router
from app.api.v1.endpoints import outfits as outfits_router
from app.core.config import get_settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Picture Storage API")

origins = [
    "http://localhost:3000",  # Frontend URL , local host
    "https://outfitpredict.ru",  # Production frontend
    "http://outfitpredict.ru",  # HTTP redirect (if needed)
]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Use specific origins instead of "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers
app.include_router(image_router.router, prefix=get_settings().api_prefix)
app.include_router(clothing_router.router, prefix=get_settings().api_prefix)
app.include_router(outfits_router.router, prefix=get_settings().api_prefix)
app.include_router(auth_router.router, prefix=get_settings().api_prefix)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

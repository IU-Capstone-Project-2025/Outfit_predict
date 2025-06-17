import uvicorn
from app.api.v1.endpoints import image as image_router
from app.api.v1.endpoints import clothing as clothing_router
from app.core.config import get_settings
from app.db.database import Base, engine, vector_db
from fastapi import FastAPI

app = FastAPI(title="Picture Storage API")

# Routers
app.include_router(image_router.router, prefix=get_settings().api_prefix)
app.include_router(clothing_router.router, prefix=get_settings().api_prefix)

@app.on_event("startup")
async def on_startup() -> None:
    # Create tables (better to use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

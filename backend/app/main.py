import time
import traceback

import uvicorn
from app.api.v1.endpoints import auth as auth_router
from app.api.v1.endpoints import clothing as clothing_router
from app.api.v1.endpoints import image as image_router
from app.api.v1.endpoints import outfits as outfits_router
from app.api.v1.endpoints import saved_outfits as saved_outfits_router
from app.api.v1.endpoints import utilities as utilities_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Setup logging first
logger = setup_logging()

app = FastAPI(title="Picture Storage API")


# Add request logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()

    # Log incoming request
    api_logger = get_logger("app.api")
    api_logger.info(
        f"Incoming request: {request.method} {request.url} "
        f"from {request.client.host if request.client else 'unknown'}"
    )

    try:
        response = await call_next(request)

        # Calculate request duration
        process_time = time.time() - start_time

        # Log response
        api_logger.info(
            f"Request completed: {request.method} {request.url} "
            f"- Status: {response.status_code} - Duration: {process_time:.3f}s"
        )

        return response

    except Exception as e:
        # Log error
        process_time = time.time() - start_time
        api_logger.error(
            f"Request failed: {request.method} {request.url} "
            f"- Duration: {process_time:.3f}s - Error: {str(e)}"
        )
        api_logger.debug(f"Traceback: {traceback.format_exc()}")

        # Return error response
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )


origins = [
    "http://localhost:3000",  # Frontend URL , local host
    "https://outfitpredict.ru",  # Production frontend
    "http://outfitpredict.ru",  # HTTP redirect (if needed)
]

logger.info(f"Configuring CORS for origins: {origins}")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Use specific origins instead of "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("CORS middleware configured successfully")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {request.method} {request.url} - {str(exc)}")
    logger.debug(f"Exception traceback: {traceback.format_exc()}")

    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info("Starting Picture Storage API")
    logger.info("=" * 50)
    logger.info(f"Environment: {get_settings().api_prefix}")
    logger.info("Registering routers...")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Picture Storage API")


# Routers
logger.info("Registering image router...")
app.include_router(image_router.router, prefix=get_settings().api_prefix)

logger.info("Registering clothing router...")
app.include_router(clothing_router.router, prefix=get_settings().api_prefix)

logger.info("Registering outfits router...")
app.include_router(outfits_router.router, prefix=get_settings().api_prefix)

logger.info("Registering saved outfits router...")
app.include_router(saved_outfits_router.router, prefix=get_settings().api_prefix)

logger.info("Registering auth router...")
app.include_router(auth_router.router, prefix=get_settings().api_prefix)

logger.info("Registering utilities router...")
app.include_router(utilities_router.router, prefix=get_settings().api_prefix)

logger.info("All routers registered successfully")


# Health check endpoint
@app.get("/health")
async def health_check():
    logger.debug("Health check requested")
    return {"status": "healthy", "service": "Picture Storage API"}


if __name__ == "__main__":
    logger.info("Starting application in development mode")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

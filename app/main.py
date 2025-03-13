from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging

settings = get_settings()
logger = get_logger(__name__)

# 确保日志目录存在
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle application startup and shutdown events using the recommended
    lifespan context manager approach in FastAPI
    """
    # Setup logging
    setup_logging()
    logger.info("Starting application")
    
    # Additional startup operations would go here
    
    yield
    
    # Shutdown operations would go here
    logger.info("Shutting down application")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Azure Calculator backend API",
    version="0.0.1",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)


# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Global exception handlers
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> Any:
    """
    Global exception handler for SQLAlchemy errors
    """
    logger.error(f"Database error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "A database error occurred"},
    )


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root() -> dict:
    """
    Root endpoint - health check
    """
    return {"status": "online", "app": settings.PROJECT_NAME, "version": "0.0.1"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
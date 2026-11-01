from fastapi import FastAPI
from sqlalchemy import text

from app.config import settings
from app.database import engine


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered customer support SaaS platform.",
)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to SupportFlow AI API",
        "version": settings.app_version,
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "application": settings.app_name,
    }


@app.get("/health/database", tags=["Health"])
def database_health_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }
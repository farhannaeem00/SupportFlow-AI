from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    organizations,
    team,
    customers,
    conversations,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(team.router)
api_router.include_router(customers.router)
api_router.include_router(conversations.router)
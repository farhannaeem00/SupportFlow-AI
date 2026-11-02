from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    organizations,
    team,
    customers,
    conversations,
    widget,
    ai_settings,
    knowledge_bases,
    knowledge_documents,
)
from app.api.v1.endpoints import knowledge_search


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(team.router)
api_router.include_router(customers.router)
api_router.include_router(conversations.router)
api_router.include_router(widget.router)
api_router.include_router(ai_settings.router)
api_router.include_router(knowledge_bases.router)
api_router.include_router(knowledge_documents.router)
api_router.include_router(knowledge_search.router)
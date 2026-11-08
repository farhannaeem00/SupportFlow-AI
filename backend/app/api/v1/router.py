from fastapi import APIRouter, Depends

from app.services.auth_rate_limit_service import (
    enforce_global_api_rate_limit,
)

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
    knowledge_search,
    audit_logs,
    webhooks,
    exports,
)

api_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(enforce_global_api_rate_limit)],
)

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
api_router.include_router(audit_logs.router)
api_router.include_router(webhooks.router)
api_router.include_router(exports.router)
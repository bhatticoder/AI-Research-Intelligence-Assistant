from routes.auth import router as auth_router
from routes.documents import router as documents_router
from routes.chat import router as chat_router
from routes.obsidian import router as obsidian_router
from routes.graph import router as graph_router
from routes.reports import router as reports_router
from routes.admin import router as admin_router

__all__ = [
    "auth_router",
    "documents_router",
    "chat_router",
    "obsidian_router",
    "graph_router",
    "reports_router",
    "admin_router",
]

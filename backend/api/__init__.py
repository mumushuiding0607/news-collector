"""
API Router
"""
from backend.api.news import router as news_router
from backend.api.rag import router as rag_router
from backend.api.auth import router as auth_router
from backend.api.subscription import router as subscription_router
from backend.api.feedback import router as feedback_router

router = news_router  # 默认 router

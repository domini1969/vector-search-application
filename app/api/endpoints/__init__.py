# app/api/endpoints/__init__.py
# API endpoints package initialization
# Empty file to avoid circular imports

from app.api.endpoints import search, document, admin, health

__all__ = ["search", "document", "admin", "health"]
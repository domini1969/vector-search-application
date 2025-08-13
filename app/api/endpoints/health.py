# app/api/endpoints/health.py

import os
import platform
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.services.document_service import document_service
from app.core.errors import DatabaseError
from app.core.logging import logger

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Health check",
    description="Check the health of the API"
)
async def health_check():
    """Check the health of the API and its components."""
    try:
        # Check database connection
        doc_count = document_service.get_document_count()
        
        # Get system info
        system_info = {
            "os": platform.system(),
            "version": platform.version(),
            "python_version": platform.python_version(),
        }
        
        # Get application info
        app_info = {
            "api_version": settings.API_VERSION,
            "chroma_db_path": settings.CHROMA_DB_PATH,
            "embedding_model": settings.EMBEDDING_MODEL,
        }
        
        # Check if import paths exist
        paths_info = {
            "import_path_full_exists": os.path.isdir(settings.IMPORT_PATH_FULL),
            "import_path_delta_exists": os.path.isdir(settings.IMPORT_PATH_DELTA),
            "export_path_dir_exists": os.path.isdir(os.path.dirname(settings.EXPORT_PATH)),
        }
        
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "document_count": doc_count,
            "system_info": system_info,
            "app_info": app_info,
            "paths_info": paths_info,
        }
    except DatabaseError as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "component": "database",
        }
    except Exception as e:
        logger.error(f"Unexpected error during health check: {str(e)}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }

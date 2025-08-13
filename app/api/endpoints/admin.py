# app/api/endpoints/admin.py

from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Query, HTTPException, Path, Body, status, Depends

from app.api.models.document import OperationResponse
from app.services.document_service import document_service
from app.core.errors import (
    DatabaseError,
    FileOperationError,
    ValidationError
)
from app.core.logging import logger

router = APIRouter(tags=["admin"])


@router.get(
    "/import",
    response_model=OperationResponse,
    summary="Import documents",
    description="Empty the database and import documents from the full import path with optimized batch processing"
)
async def import_documents():
    """Import documents from the full import path."""
    try:
        count = document_service.import_full()
        return OperationResponse(
            success=True,
            message=f"Successfully imported {count} documents",
            details={"count": count}
        )
    except (DatabaseError, FileOperationError) as e:
        logger.error(f"Import operation failed: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error during import: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import operation failed: {str(e)}")


@router.get(
    "/importdelta",
    response_model=OperationResponse,
    summary="Import delta documents",
    description="Import delta documents without resetting the database"
)
async def import_delta():
    """Import delta documents without resetting the database."""
    try:
        count = document_service.import_delta()
        return OperationResponse(
            success=True,
            message=f"Successfully imported {count} delta documents",
            details={"count": count}
        )
    except (DatabaseError, FileOperationError) as e:
        logger.error(f"Delta import operation failed: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error during delta import: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Delta import operation failed: {str(e)}")


@router.get(
    "/export",
    response_model=OperationResponse,
    summary="Export documents",
    description="Export all documents to a JSON file"
)
async def export_documents():
    """Export all documents to a JSON file."""
    try:
        export_path = document_service.export_documents()
        return OperationResponse(
            success=True,
            message=f"Successfully exported documents to {export_path}",
            details={"export_path": export_path}
        )
    except (DatabaseError, FileOperationError) as e:
        logger.error(f"Export operation failed: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error during export: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export operation failed: {str(e)}")


@router.get(
    "/reset",
    response_model=OperationResponse,
    summary="Reset database",
    description="Clear all stored vectors from the database"
)
async def reset_database():
    """Clear all stored vectors from the database."""
    try:
        document_service.reset_collection()
        return OperationResponse(
            success=True,
            message="Database reset successfully",
            details={}
        )
    except DatabaseError as e:
        logger.error(f"Reset operation failed: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error during reset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Reset operation failed: {str(e)}")


@router.get(
    "/reload_whitelist",
    response_model=OperationResponse,
    summary="Reload spellcheck whitelist",
    description="Reload the spellcheck whitelist from the config file without restarting the application"
)
async def reload_spellcheck_whitelist():
    """Reload the spellcheck whitelist from file."""
    try:
        from app.services.search_service import search_service
        
        whitelist_count = search_service.reload_whitelist()
        
        return OperationResponse(
            success=True,
            message=f"Successfully reloaded spellcheck whitelist with {whitelist_count} terms",
            details={"whitelist_count": whitelist_count}
        )
    except Exception as e:
        logger.error(f"Failed to reload spellcheck whitelist: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to reload spellcheck whitelist: {str(e)}"
        )
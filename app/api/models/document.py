# app/api/models/document.py
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.config import settings


class SearchResult(BaseModel):
    """Model for search results."""
    id: str
    score: float
    payload: Dict[str, Any]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "abc123",
                "score": 0.96312,
                "payload": {
                    "text": "Sample document text",
                    "metadata": {"source": "example"}
                }
            }
        }
    )


class DocumentBase(BaseModel):
    """Base model for document data."""
    model_config = ConfigDict(extra="allow")  # Allow extra fields


class DocumentResponse(DocumentBase):
    """Model for document responses."""
    id: str
    vector: List[float]
    payload: Dict[str, Any]
    
    model_config = ConfigDict(
        extra="allow",
        validate_by_name=True,
    )


class DocumentCreate(DocumentBase):
    """Model for creating a document."""
    text: str
    metadata: Optional[Dict[str, Any]] = None


class DocumentUpdate(DocumentBase):
    """Model for updating a document."""
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CollectionInfo(BaseModel):
    """Model for collection information."""
    name: str
    vectors_count: int
    points_count: int
    segments_count: int
    config: Dict[str, Any]


class OperationResponse(BaseModel):
    """Model for operation responses."""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


# NEW: Missing models that document_service.py needs
class ImportStatus(BaseModel):
    """Model for import status tracking."""
    model_config = ConfigDict(from_attributes=True)
    
    status: str = Field(default="pending", description="Import status (pending, processing, completed, failed)")
    progress: float = Field(default=0.0, description="Import progress percentage", ge=0.0, le=100.0)
    message: Optional[str] = Field(default=None, description="Status message")
    started_at: Optional[str] = Field(default=None, description="Import start time (ISO format)")
    completed_at: Optional[str] = Field(default=None, description="Import completion time (ISO format)")
    total_documents: Optional[int] = Field(default=None, description="Total documents to import", ge=0)
    processed_documents: int = Field(default=0, description="Documents processed so far", ge=0)
    failed_documents: List[Dict[str, Any]] = Field(default_factory=list, description="Documents that failed to import")
    errors: List[str] = Field(default_factory=list, description="List of import errors")
    
    # Additional fields for document_service compatibility
    last_successful_import: Optional[str] = Field(default=None, description="Last successful import timestamp")
    total_files: int = Field(default=0, description="Total files to process", ge=0)
    processed_files: int = Field(default=0, description="Files processed so far", ge=0)
    is_complete: bool = Field(default=False, description="Whether import is complete")
    error_message: Optional[str] = Field(default=None, description="Error message if import failed")


class ImportResult(BaseModel):
    """Model for import operation results."""
    model_config = ConfigDict(from_attributes=True)
    
    success: bool = Field(..., description="Whether import was successful")
    message: str = Field(..., description="Import result message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional import details")
    status: Optional[ImportStatus] = Field(default=None, description="Import status object")
    failed_documents: List[Dict[str, Any]] = Field(default_factory=list, description="Documents that failed to import")
    
    # Additional fields
    total_documents: Optional[int] = Field(default=None, description="Total documents processed", ge=0)
    successful_imports: Optional[int] = Field(default=None, description="Number of successful imports", ge=0)
    failed_imports: Optional[int] = Field(default=None, description="Number of failed imports", ge=0)
    duration_seconds: Optional[float] = Field(default=None, description="Import duration in seconds", ge=0)
    warnings: List[str] = Field(default_factory=list, description="List of import warnings")
    import_id: Optional[str] = Field(default=None, description="Unique import operation ID")
    started_at: Optional[datetime] = Field(default=None, description="Import start time")
    completed_at: Optional[datetime] = Field(default=None, description="Import completion time")


class ExportStatus(BaseModel):
    """Model for export status tracking."""
    model_config = ConfigDict(from_attributes=True)
    
    status: str = Field(default="pending", description="Export status (pending, processing, completed, failed)")
    progress: float = Field(default=0.0, description="Export progress percentage", ge=0.0, le=100.0)
    message: Optional[str] = Field(default=None, description="Status message")
    started_at: Optional[str] = Field(default=None, description="Export start time (ISO format)")
    completed_at: Optional[str] = Field(default=None, description="Export completion time (ISO format)")
    total_documents: int = Field(default=0, description="Total documents to export", ge=0)
    processed_documents: int = Field(default=0, description="Documents exported so far", ge=0)
    export_path: Optional[str] = Field(default=None, description="Path to exported file")
    file_size_bytes: Optional[int] = Field(default=None, description="Size of exported file in bytes", ge=0)
    export_format: str = Field(default="json", description="Export file format")
    
    # Additional fields for document_service compatibility
    start_time: Optional[str] = Field(default=None, description="Start time (ISO format)")
    end_time: Optional[str] = Field(default=None, description="End time (ISO format)")
    is_complete: bool = Field(default=False, description="Whether export is complete")
    error_message: Optional[str] = Field(default=None, description="Error message if export failed")


class ExportResult(BaseModel):
    """Model for export operation results."""
    model_config = ConfigDict(from_attributes=True)
    
    success: bool = Field(..., description="Whether export was successful")
    total_documents: int = Field(..., description="Total documents exported", ge=0)
    file_path: str = Field(..., description="Path to exported file")
    file_size_bytes: int = Field(..., description="Size of exported file in bytes", ge=0)
    duration_seconds: float = Field(..., description="Export duration in seconds", ge=0)
    export_format: str = Field(..., description="Export file format")
    export_id: Optional[str] = Field(default=None, description="Unique export operation ID")
    started_at: datetime = Field(..., description="Export start time")
    completed_at: datetime = Field(..., description="Export completion time")
    download_url: Optional[str] = Field(default=None, description="URL to download the exported file")


# Additional models for comprehensive document API support
class DocumentHistoryResponse(BaseModel):
    """Model for document history responses."""
    model_config = ConfigDict(from_attributes=True)
    
    versions: List[Dict[str, Any]] = Field(..., description="List of document versions")
    count: int = Field(..., description="Total number of versions")


class DocumentVersionResponse(BaseModel):
    """Model for document version responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="Document ID")
    version: int = Field(..., description="Version number", ge=1)
    created_at: datetime = Field(..., description="Version creation timestamp")
    changes: Optional[str] = Field(default=None, description="Description of changes")
    author: Optional[str] = Field(default=None, description="Author of this version")
    content: Optional[str] = Field(default=None, description="Document content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Document metadata")


class DocumentCount(BaseModel):
    """Model for document count responses."""
    model_config = ConfigDict(from_attributes=True)
    
    count: int = Field(..., description="Total number of documents", ge=0)
# app/core/errors.py

from typing import Any, Dict, Optional


class BaseAppException(Exception):
    """Base exception for application-specific errors."""
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DocumentNotFoundError(BaseAppException):
    """Exception raised when a document is not found."""
    def __init__(
        self, 
        doc_id: str, 
        message: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None
    ):
        message = message or f"Document with ID '{doc_id}' not found"
        details = details or {"doc_id": doc_id}
        super().__init__(message, status_code=404, details=details)


class DocumentConflictError(BaseAppException):
    """Exception raised when there's a conflict with document operations."""
    def __init__(
        self, 
        doc_id: str, 
        message: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None
    ):
        message = message or f"Conflict with document ID '{doc_id}'"
        details = details or {"doc_id": doc_id}
        super().__init__(message, status_code=409, details=details)


class FileOperationError(BaseAppException):
    """Exception raised when file operations fail."""
    def __init__(
        self, 
        file_path: str, 
        operation: str, 
        message: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None
    ):
        message = message or f"File operation '{operation}' failed for '{file_path}'"
        details = details or {"file_path": file_path, "operation": operation}
        super().__init__(message, status_code=500, details=details)


class ValidationError(BaseAppException):
    """Exception raised for data validation errors."""
    def __init__(
        self, 
        message: str = "Validation error", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status_code=400, details=details)


class ConfigurationError(BaseAppException):
    """Exception raised for configuration errors."""
    def __init__(
        self, 
        message: str = "Configuration error", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status_code=500, details=details)

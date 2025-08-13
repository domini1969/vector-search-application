# app/services/version_service.py

from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from app.core.database import db_client
from app.core.errors import DocumentNotFoundError, DatabaseError
from app.core.logging import logger
from app.config import settings


class VersionService:
    """Service for handling document versioning."""
    
    VERSION_FIELD = "version"
    CREATED_AT_FIELD = "created_at"
    UPDATED_AT_FIELD = "updated_at"
    VERSION_HISTORY_FIELD = "version_history"
    
    def __init__(self, collection_name: Optional[str] = None):
        """Initialize the version service with a collection name."""
        self.collection_name = collection_name or settings.COLLECTION_NAME
        # Use a separate collection for version history
        self.history_collection = f"{self.collection_name}_history"
    
    def _get_timestamp(self) -> str:
        """Get the current timestamp in ISO format."""
        return datetime.utcnow().isoformat()
    
    def _prepare_document_for_insert(self, document: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
        """Add versioning metadata to a document."""
        doc_copy = document.copy()
        
        timestamp = self._get_timestamp()
        
        if not is_update:
            # New document
            doc_copy[self.VERSION_FIELD] = 1
            doc_copy[self.CREATED_AT_FIELD] = timestamp
            doc_copy[self.UPDATED_AT_FIELD] = timestamp
        else:
            # Updated document
            current_version = doc_copy.get(self.VERSION_FIELD, 0)
            doc_copy[self.VERSION_FIELD] = current_version + 1
            doc_copy[self.UPDATED_AT_FIELD] = timestamp
        
        return doc_copy
    
    def create_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document with versioning metadata."""
        doc_id = str(document[settings.ID_FIELD])
        
        try:
            # First check if document already exists
            try:
                db_client.get_document(doc_id, self.collection_name)
                # If we get here, document exists - update instead
                return self.update_document(doc_id, document)
            except DocumentNotFoundError:
                # Document doesn't exist, proceed with creation
                pass
            
            # Add versioning metadata
            versioned_doc = self._prepare_document_for_insert(document)
            
            # Add to main collection
            db_client.add_documents([versioned_doc], self.collection_name)
            
            logger.info(f"Created document '{doc_id}' with initial version")
            return versioned_doc
            
        except Exception as e:
            error_msg = f"Failed to create versioned document '{doc_id}': {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg, details={"doc_id": doc_id})
    
    def update_document(self, doc_id: str, document: Dict[str, Any]) -> Dict[str, Any]:
        """Update a document while maintaining version history."""
        try:
            # Get current document
            current_doc = db_client.get_document(doc_id, self.collection_name)
            
            # Store current version in history collection
            self._archive_version(current_doc)
            
            # Update version information
            updated_doc = document.copy()
            updated_doc[settings.ID_FIELD] = doc_id
            
            # Preserve creation timestamp if it exists
            if self.CREATED_AT_FIELD in current_doc:
                updated_doc[self.CREATED_AT_FIELD] = current_doc[self.CREATED_AT_FIELD]
            
            # Update version metadata
            updated_doc = self._prepare_document_for_insert(updated_doc, is_update=True)
            
            # Update in main collection
            db_client.update_document(doc_id, updated_doc, self.collection_name)
            
            logger.info(f"Updated document '{doc_id}' to version {updated_doc[self.VERSION_FIELD]}")
            return updated_doc
            
        except DocumentNotFoundError:
            # If document doesn't exist, create it instead
            document[settings.ID_FIELD] = doc_id
            return self.create_document(document)
        except Exception as e:
            error_msg = f"Failed to update versioned document '{doc_id}': {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg, details={"doc_id": doc_id})
    
    def _archive_version(self, document: Dict[str, Any]) -> None:
        """Archive a document version to the history collection."""
        doc_id = str(document[settings.ID_FIELD])
        version = document.get(self.VERSION_FIELD, 0)
        
        # Create a history document ID that includes the version
        history_id = f"{doc_id}_v{version}"
        
        try:
            # Add to history collection
            history_doc = document.copy()
            history_doc[settings.ID_FIELD] = history_id
            history_doc["original_id"] = doc_id
            
            db_client.get_or_create_collection(self.history_collection)
            db_client.add_documents([history_doc], self.history_collection)
            
            logger.debug(f"Archived version {version} of document '{doc_id}'")
            
        except Exception as e:
            # Log error but don't fail the update operation
            error_msg = f"Failed to archive version {version} of document '{doc_id}': {str(e)}"
            logger.error(error_msg)
    
    def get_document_history(self, doc_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the version history of a document."""
        try:
            # First check if current document exists
            db_client.get_document(doc_id, self.collection_name)
            
            # Get history collection
            history_collection = db_client.get_or_create_collection(self.history_collection)
            
            # Query for versions
            results = history_collection.query(
                query_texts=[""],  # Empty query to match by filter only
                where={"original_id": doc_id},
                n_results=limit,
                include=["metadatas", "documents"]
            )
            
            # Format results
            history = []
            for i, history_id in enumerate(results["ids"][0]):
                version_doc = results["metadatas"][0][i]
                version_doc[settings.TEXT_FIELD] = results["documents"][0][i]
                version_doc[settings.ID_FIELD] = version_doc.get("original_id")
                history.append(version_doc)
            
            # Sort by version descending
            history.sort(key=lambda x: x.get(self.VERSION_FIELD, 0), reverse=True)
            
            return history
            
        except DocumentNotFoundError:
            raise  # Re-raise document not found errors
        except Exception as e:
            error_msg = f"Failed to get history for document '{doc_id}': {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg, details={"doc_id": doc_id})
    
    def get_document_version(self, doc_id: str, version: int) -> Dict[str, Any]:
        """Get a specific version of a document."""
        try:
            # Check if requested version is the current one
            current_doc = db_client.get_document(doc_id, self.collection_name)
            current_version = current_doc.get(self.VERSION_FIELD, 0)
            
            if current_version == version:
                return current_doc
            
            # Otherwise look in history
            history_id = f"{doc_id}_v{version}"
            history_collection = db_client.get_or_create_collection(self.history_collection)
            
            try:
                version_doc = db_client.get_document(history_id, self.history_collection)
                # Restore original ID
                version_doc[settings.ID_FIELD] = doc_id
                return version_doc
            except DocumentNotFoundError:
                error_msg = f"Version {version} not found for document '{doc_id}'"
                logger.error(error_msg)
                raise DocumentNotFoundError(
                    doc_id, 
                    message=error_msg, 
                    details={"version": version}
                )
                
        except DocumentNotFoundError:
            raise  # Re-raise document not found errors
        except Exception as e:
            error_msg = f"Failed to get version {version} of document '{doc_id}': {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg, details={"doc_id": doc_id, "version": version})
    
    def delete_document(self, doc_id: str, delete_history: bool = False) -> None:
        """Delete a document and optionally its version history."""
        try:
            # Delete from main collection
            db_client.delete_document(doc_id, self.collection_name)
            logger.info(f"Deleted document '{doc_id}' from main collection")
            
            # Optionally delete history
            if delete_history:
                # Get history collection
                history_collection = db_client.get_or_create_collection(self.history_collection)
                
                # Find all history documents for this ID
                results = history_collection.query(
                    query_texts=[""],  # Empty query to match by filter only
                    where={"original_id": doc_id},
                    n_results=100,  # Reasonable limit for history
                    include=["metadatas"]
                )
                
                # Delete each history document
                for history_id in results["ids"][0]:
                    db_client.delete_document(history_id, self.history_collection)
                
                logger.info(f"Deleted all history versions for document '{doc_id}'")
                
        except DocumentNotFoundError:
            raise  # Re-raise document not found errors
        except Exception as e:
            error_msg = f"Failed to delete document '{doc_id}': {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg, details={"doc_id": doc_id})


# Create global version service instance
version_service = VersionService()

# app/services/document_service.py

import os
import json
import glob
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import pickle
from pathlib import Path

# Import with error handling
try:
    from app.config import settings
except ImportError:
    class MockSettings:
        COLLECTION_NAME = "products_fast"
        ID_FIELD = "id"
        TEXT_FIELD = "text"
        IMPORT_PATH_FULL = "./data/import/full"
        IMPORT_PATH_DELTA = "./data/import/delta"
        EXPORT_PATH = "./data/export/export.json"
        EXPORT_MAX_DOCUMENTS = 0
        EXPORT_BATCH_SIZE = 100
        BATCH_SIZE = 100  # Use this instead of effective_packet_size for Qdrant
        MAX_WORKERS = 4
    settings = MockSettings()

try:
    from app.core.database import db_client
except ImportError:
    class MockDBClient:
        def get_document(self, doc_id: str, collection_name: str):
            raise Exception("Database client not available")
        def add_documents(self, docs: List[Dict], collection_name: str):
            pass
        def get_documents(self, limit: int, offset: int, collection_name: str):
            return []
        def get_collection_count(self, collection_name: str):
            return 0
        def reset_collection(self, collection_name: str):
            pass
    db_client = MockDBClient()

try:
    from app.core.errors import (
        DocumentNotFoundError, 
        DatabaseError, 
        FileOperationError,
        ValidationError
    )
except ImportError:
    class DocumentNotFoundError(Exception):
        def __init__(self, message: str):
            self.message = message
            self.status_code = 404
    
    class DatabaseError(Exception):
        def __init__(self, message: str, details: Dict = None):
            self.message = message
            self.status_code = 500
            self.details = details or {}
    
    class FileOperationError(Exception):
        def __init__(self, file_path: str, operation: str, message: str):
            self.message = message
            self.status_code = 500
            self.file_path = file_path
            self.operation = operation
    
    class ValidationError(Exception):
        def __init__(self, message: str):
            self.message = message
            self.status_code = 400

try:
    from app.core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from app.services.version_service import version_service
except ImportError:
    class MockVersionService:
        def create_document(self, document: Dict[str, Any]):
            return {"id": "mock", "version": 1}
        def update_document(self, doc_id: str, document: Dict[str, Any]):
            return {"id": doc_id, "version": 1}
        def get_document_version(self, doc_id: str, version: int):
            return {"id": doc_id, "version": version}
        def get_document_history(self, doc_id: str, limit: int):
            return []
        def delete_document(self, doc_id: str, delete_history: bool):
            pass
    version_service = MockVersionService()

# Import models with fallback
try:
    from app.api.models.document import ImportStatus, ImportResult, ExportStatus
except ImportError:
    from pydantic import BaseModel, Field
    from typing import List
    
    class ImportStatus(BaseModel):
        status: str = "pending"
        progress: float = 0.0
        message: Optional[str] = None
        started_at: Optional[str] = None
        completed_at: Optional[str] = None
        total_documents: Optional[int] = None
        processed_documents: int = 0
        failed_documents: List[Dict[str, Any]] = Field(default_factory=list)
        errors: List[str] = Field(default_factory=list)
        last_successful_import: Optional[str] = None
        total_files: int = 0
        processed_files: int = 0
        is_complete: bool = False
        error_message: Optional[str] = None
    
    class ImportResult(BaseModel):
        success: bool
        message: str
        details: Optional[Dict[str, Any]] = None
        status: Optional[ImportStatus] = None
        failed_documents: List[Dict[str, Any]] = Field(default_factory=list)
    
    class ExportStatus(BaseModel):
        status: str = "pending"
        progress: float = 0.0
        message: Optional[str] = None
        started_at: Optional[str] = None
        completed_at: Optional[str] = None
        total_documents: int = 0
        processed_documents: int = 0
        export_path: Optional[str] = None
        file_size_bytes: Optional[int] = None
        export_format: str = "json"
        start_time: Optional[str] = None
        end_time: Optional[str] = None
        is_complete: bool = False
        error_message: Optional[str] = None


class DocumentService:
    """Service for document management operations."""
    
    def __init__(self, collection_name: Optional[str] = None):
        """Initialize the document service."""
        self.collection_name = collection_name or getattr(settings, 'COLLECTION_NAME', 'products_fast')
        self.import_status = ImportStatus()
        
        # Use appropriate batch size for Qdrant (not ChromaDB)
        self.batch_size = getattr(settings, 'BATCH_SIZE', 100)  # Default to 100 for Qdrant
        if not hasattr(settings, 'BATCH_SIZE'):
            # If no batch size is configured, use a safe default for Qdrant
            self.batch_size = 100
            
        self.max_workers = getattr(settings, 'MAX_WORKERS', 4)  # Configurable number of parallel workers
        self.import_state_file = Path("./data/import_state.pkl")
        self.import_state_file.parent.mkdir(parents=True, exist_ok=True)
        self.export_status = ExportStatus()
    
    def _validate_document(self, document: Dict[str, Any]) -> bool:
        """Validate that a document has required fields."""
        if not isinstance(document, dict):
            raise ValidationError("Document must be a dictionary")
        
        if not hasattr(settings, 'ID_FIELD'):
            # Fallback ID field for Qdrant
            if hasattr(doc, 'get') and doc.get('id'):
                pass  # Document has 'id' field
            elif hasattr(doc, 'get') and doc.get('partNumber_airgas_text'):
                pass  # Document has part number field
            else:
                raise ValidationError("Document must have 'id' or 'partNumber_airgas_text' field")
        elif settings.ID_FIELD not in document:
            raise ValidationError(f"Document must have '{settings.ID_FIELD}' field")
        
        if not hasattr(settings, 'TEXT_FIELD'):
            # Check for common text fields in Qdrant/product data
            text_fields = ['text', 'shortDescription_airgas_text', 'description', 'content']
            if not any(field in document for field in text_fields):
                raise ValidationError(f"Document must have one of these text fields: {text_fields}")
        elif settings.TEXT_FIELD not in document:
            raise ValidationError(f"Document must have '{settings.TEXT_FIELD}' field")
        
        return True
    
    def _load_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load and validate documents from a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Ensure data is a list
            if not isinstance(data, list):
                raise ValidationError(f"JSON file must contain an array of objects: {file_path}")
            
            # Validate each document
            for i, doc in enumerate(data):
                try:
                    self._validate_document(doc)
                except ValidationError as e:
                    logger.warning(f"Skipping invalid document at index {i} in {file_path}: {str(e)}")
                    data.pop(i)
            
            logger.info(f"Loaded {len(data)} valid documents from {file_path}")
            return data
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise FileOperationError(file_path, "read", error_msg)
        except IOError as e:
            error_msg = f"Failed to read file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise FileOperationError(file_path, "read", error_msg)
    
    def create_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document with versioning."""
        self._validate_document(document)
        return version_service.create_document(document)
    
    def update_document(self, doc_id: str, document: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing document with versioning."""
        self._validate_document(document)
        return version_service.update_document(doc_id, document)
    
    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """Get a document by ID."""
        return db_client.get_document(doc_id, self.collection_name)
    
    def get_document_version(self, doc_id: str, version: int) -> Dict[str, Any]:
        """Get a specific version of a document."""
        return version_service.get_document_version(doc_id, version)
    
    def get_document_history(self, doc_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the version history of a document."""
        return version_service.get_document_history(doc_id, limit)
    
    def delete_document(self, doc_id: str, delete_history: bool = False) -> None:
        """Delete a document and optionally its history."""
        return version_service.delete_document(doc_id, delete_history)
    
    def get_documents(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get multiple documents with pagination."""
        return db_client.get_documents(limit, offset, self.collection_name)
    
    def get_documents_batch(self, batch_size: int = 100) -> Generator[List[Dict[str, Any]], None, None]:
        """Get documents in batches using a generator for memory-efficient processing."""
        total_docs = self.get_document_count()
        offset = 0
        
        while offset < total_docs:
            batch = db_client.get_documents(batch_size, offset, self.collection_name)
            if not batch:
                break
                
            yield batch
            offset += len(batch)
            
            # If we got fewer documents than requested, we've reached the end
            if len(batch) < batch_size:
                break
    
    def get_document_count(self) -> int:
        """Get the total number of documents in the collection."""
        return db_client.get_collection_count(self.collection_name)
    
    def reset_collection(self) -> None:
        """Delete all documents in the collection."""
        return db_client.reset_collection(self.collection_name)
    
    def load_documents_from_path(self, path: str) -> int:
        """Load documents from JSON files in a directory."""
        if not os.path.isdir(path):
            raise FileOperationError(path, "read", f"Directory not found: {path}")
        
        # Get all JSON files in the directory
        json_files = glob.glob(os.path.join(path, "*.json"))
        if not json_files:
            logger.warning(f"No JSON files found in {path}")
            return 0
        
        logger.info(f"Found {len(json_files)} JSON files in {path}")
        
        # Process each file
        total_docs = 0
        for file_path in json_files:
            try:
                documents = self._load_json_file(file_path)
                
                # Add documents to collection with versioning
                for doc in documents:
                    self.create_document(doc)
                
                total_docs += len(documents)
                logger.info(f"Processed {len(documents)} documents from {file_path}")
                
            except (FileOperationError, ValidationError) as e:
                logger.error(f"Failed to process file {file_path}: {str(e)}")
                # Continue with next file
        
        logger.info(f"Loaded total of {total_docs} documents from {path}")
        return total_docs
    
    def _save_import_state(self):
        """Save current import state for recovery."""
        try:
            with open(self.import_state_file, 'wb') as f:
                pickle.dump(self.import_status, f)
        except Exception as e:
            logger.warning(f"Failed to save import state: {e}")

    def _load_import_state(self) -> Optional[ImportStatus]:
        """Load previous import state if exists."""
        try:
            if self.import_state_file.exists():
                with open(self.import_state_file, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            logger.warning(f"Failed to load import state: {e}")
        return None

    def _get_document_hash(self, doc: Dict[str, Any]) -> str:
        """Generate a hash for document content comparison."""
        # Sort the dictionary to ensure consistent hashing
        sorted_dict = dict(sorted(doc.items()))
        return hashlib.sha256(json.dumps(sorted_dict).encode()).hexdigest()

    def _process_document_batch(self, documents: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Process a batch of documents with error tracking."""
        successful = []
        failed = []
        
        try:
            # Validate all documents in batch
            valid_docs = []
            for doc in documents:
                try:
                    self._validate_document(doc)
                    valid_docs.append(doc)
                except ValidationError as e:
                    failed.append({"doc": doc, "error": str(e)})
            
            if valid_docs:
                # Batch insert into ChromaDB
                db_client.add_documents(valid_docs, self.collection_name)
                successful.extend(valid_docs)
                
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            failed.extend([{"doc": doc, "error": str(e)} for doc in documents])
            
        return successful, failed

    def _process_file(self, file_path: str, is_delta: bool = False) -> Tuple[int, List[Dict[str, Any]]]:
        """Process a single file with batch processing."""
        try:
            documents = self._load_json_file(file_path)
            successful_count = 0
            failed_documents = []
            
            # Process in batches
            for i in range(0, len(documents), self.batch_size):
                batch = documents[i:i + self.batch_size]
                
                if is_delta:
                    # For delta imports, check if documents already exist or have changed
                    batch = [doc for doc in batch if self._should_process_delta(doc)]
                
                if batch:
                    successful, failed = self._process_document_batch(batch)
                    successful_count += len(successful)
                    failed_documents.extend(failed)
                    
                    # Update status
                    self.import_status.processed_documents += len(successful)
                    self.import_status.failed_documents.extend(failed)
                    self._save_import_state()
            
            return successful_count, failed_documents
            
        except Exception as e:
            logger.error(f"File processing failed {file_path}: {str(e)}")
            return 0, []

    def _should_process_delta(self, doc: Dict[str, Any]) -> bool:
        """Determine if a document should be processed in delta import."""
        try:
            # Get document ID using flexible field detection
            doc_id = None
            if hasattr(settings, 'ID_FIELD') and settings.ID_FIELD in doc:
                doc_id = doc[settings.ID_FIELD]
            elif 'id' in doc:
                doc_id = doc['id']
            elif 'partNumber_airgas_text' in doc:
                doc_id = doc['partNumber_airgas_text']
            
            if not doc_id:
                # If we can't find an ID, process the document
                return True
            
            # Check if document exists
            try:
                existing_doc = self.get_document(doc_id)
                # Compare content hashes
                new_hash = self._get_document_hash(doc)
                existing_hash = self._get_document_hash(existing_doc)
                return new_hash != existing_hash
            except DocumentNotFoundError:
                # Document doesn't exist, should process
                return True
                
        except Exception as e:
            logger.error(f"Error checking document delta status: {str(e)}")
            # Process document if we can't determine status
            return True

    def import_full(self) -> ImportResult:
        """Optimized full import with parallel processing and error handling."""
        logger.info(f"Starting optimized full import from {settings.IMPORT_PATH_FULL}")
        
        try:
            # Reset import status
            self.import_status = ImportStatus()
            self.import_status.last_successful_import = datetime.now().isoformat()
            
            # Reset collection with optimized settings
            self.reset_collection()
            
            # Get all JSON files
            json_files = glob.glob(os.path.join(settings.IMPORT_PATH_FULL, "*.json"))
            self.import_status.total_files = len(json_files)
            
            total_documents = 0
            failed_documents = []
            
            # Process files in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_file = {
                    executor.submit(self._process_file, file_path): file_path 
                    for file_path in json_files
                }
                
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        doc_count, failed = future.result()
                        total_documents += doc_count
                        failed_documents.extend(failed)
                        self.import_status.processed_files += 1
                        self._save_import_state()
                    except Exception as e:
                        logger.error(f"File {file_path} failed: {str(e)}")
            
            self.import_status.is_complete = True
            self._save_import_state()
            
            return ImportResult(
                success=True,
                message=f"Successfully imported {total_documents} documents",
                details={"total_documents": total_documents},
                status=self.import_status,
                failed_documents=failed_documents
            )
            
        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            self.import_status.error_message = str(e)
            self._save_import_state()
            raise

    def import_delta(self) -> ImportResult:
        """Optimized delta import with change detection."""
        logger.info(f"Starting optimized delta import from {settings.IMPORT_PATH_DELTA}")
        
        try:
            # Initialize new import status
            self.import_status = ImportStatus()
            self.import_status.last_successful_import = datetime.now().isoformat()
            
            # Get all JSON files
            json_files = glob.glob(os.path.join(settings.IMPORT_PATH_DELTA, "*.json"))
            self.import_status.total_files = len(json_files)
            
            total_documents = 0
            failed_documents = []
            
            # Process files in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_file = {
                    executor.submit(self._process_file, file_path, True): file_path 
                    for file_path in json_files
                }
                
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        doc_count, failed = future.result()
                        total_documents += doc_count
                        failed_documents.extend(failed)
                        self.import_status.processed_files += 1
                        self._save_import_state()
                    except Exception as e:
                        logger.error(f"File {file_path} failed: {str(e)}")
            
            self.import_status.is_complete = True
            self._save_import_state()
            
            return ImportResult(
                success=True,
                message=f"Successfully imported {total_documents} delta documents",
                details={"total_documents": total_documents},
                status=self.import_status,
                failed_documents=failed_documents
            )
            
        except Exception as e:
            logger.error(f"Delta import failed: {str(e)}")
            self.import_status.error_message = str(e)
            self._save_import_state()
            raise

    def export_documents(self, export_path: Optional[str] = None) -> Tuple[str, ExportStatus]:
        """
        Export all documents to a JSON file with pagination to handle large collections.
        
        Args:
            export_path: Optional custom export path. If None, uses the configured path.
            
        Returns:
            Tuple of (export file path, export status)
        """
        start_time = time.time()
        export_path = export_path or settings.EXPORT_PATH
        export_dir = os.path.dirname(export_path)
        
        # Reset export status
        self.export_status = ExportStatus(
            start_time=datetime.now().isoformat(),
            total_documents=0,
            processed_documents=0,
            export_path=export_path
        )
        
        # Create export directory if it doesn't exist
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
        
        try:
            # Get document count for progress tracking
            total_count = self.get_document_count()
            self.export_status.total_documents = total_count
            logger.info(f"Starting export of {total_count} documents to {export_path}")
            
            # Check if we have a document limit
            max_docs = settings.EXPORT_MAX_DOCUMENTS
            if max_docs > 0:
                total_count = min(total_count, max_docs)
                logger.info(f"Export limited to {max_docs} documents")
            
            # Use a batch size from settings
            batch_size = settings.EXPORT_BATCH_SIZE
            
            # Define a consistent field order - based on your sample data
            key_order = [
                "partNumber_airgas_text", 
                "manufacturerPartNumber_text", 
                "shortDescription_airgas_text",
                "onlinePrice_string", 
                "img_270Wx270H_string"
                # Add any other fields you want in a specific order
            ]
            
            # Open the file in write mode
            with open(export_path, 'w', encoding='utf-8') as f:
                # Write the opening bracket for the JSON array
                f.write('[')
                
                # Process documents in batches to avoid memory issues
                first_item = True
                processed_count = 0
                
                # Use the generator to efficiently process batches
                for batch in self.get_documents_batch(batch_size):
                    # Check if we've reached the maximum documents
                    if max_docs > 0 and processed_count >= max_docs:
                        break
                    
                    # Process this batch
                    for doc in batch:
                        # Skip if we've reached the limit
                        if max_docs > 0 and processed_count >= max_docs:
                            break
                            
                        # Write comma before item (except for the first one)
                        if not first_item:
                            f.write(',')
                        else:
                            first_item = False
                        
                        # Create an ordered document with fields in the specified order
                        ordered_doc = {}
                        
                        # First add keys from our defined order
                        for key in key_order:
                            if key in doc:
                                ordered_doc[key] = doc[key]
                        
                        # Then add any remaining keys (this handles fields not in our key_order list)
                        for key, value in doc.items():
                            if key not in ordered_doc:
                                ordered_doc[key] = value
                                
                        # Write the document as JSON
                        f.write('\n  ' + json.dumps(ordered_doc))
                        
                        # Update counters
                        processed_count += 1
                        self.export_status.processed_documents = processed_count
                    
                    # Log progress periodically
                    if processed_count % (batch_size * 5) == 0:
                        elapsed = time.time() - start_time
                        docs_per_sec = processed_count / elapsed if elapsed > 0 else 0
                        logger.info(f"Exported {processed_count}/{total_count} documents ({docs_per_sec:.1f} docs/sec)")
                
                # Write the closing bracket for the JSON array
                f.write('\n]')
            
            # Update final status
            self.export_status.end_time = datetime.now().isoformat()
            self.export_status.is_complete = True
            
            elapsed = time.time() - start_time
            docs_per_sec = processed_count / elapsed if elapsed > 0 else 0
            logger.info(f"Export completed: {processed_count} documents exported to {export_path} in {elapsed:.1f} seconds ({docs_per_sec:.1f} docs/sec)")
            
            return export_path, self.export_status
            
        except IOError as e:
            error_msg = f"Failed to write export file {export_path}: {str(e)}"
            logger.error(error_msg)
            self.export_status.error_message = error_msg
            raise FileOperationError(export_path, "write", error_msg)
        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            logger.error(error_msg)
            self.export_status.error_message = error_msg
            raise DatabaseError(error_msg, details={"export_path": export_path})


# Create global document service instance
document_service = DocumentService()
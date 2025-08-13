from typing import Dict, Any, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
import numpy as np
from app.core.logging import logger
from app.config.config import settings
from app.core.errors import DatabaseError
import os
from fastembed import TextEmbedding
import time

class DatabaseClient:
    """Client/Wrapper for interacting with Qdrant vector database."""
    
    def __init__(self):
        """Initialize Qdrant client."""
        try:
            self.client = QdrantClient(
                host=settings.HOST,
                port=settings.PORT,
                api_key=settings.API_KEY,
                https=settings.USE_HTTPS
            )
            logger.info("Qdrant client initialized successfully")
            
            # Initialize embedding model
            self._init_embedding_model()
            
            # Verify collection exists
            self.get_or_create_collection(settings.COLLECTION_NAME)
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {str(e)}")
            raise DatabaseError("Failed to initialize database client")
    
    def _init_embedding_model(self):
        """Initialize the embedding model with caching."""
        try:
            # Initialize FastEmbed model (same as indexing.py)
            self.model = TextEmbedding(
                "BAAI/bge-small-en-v1.5",
                max_length=512,
                threads=2,  # Conservative for legacy usage
                cache_dir=None  # No disk caching for speed
            )
            logger.info("FastEmbed model initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {str(e)}")
            raise DatabaseError("Failed to initialize embedding model")
    
    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection from Qdrant."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            if collection_name in collection_names:
                self.client.delete_collection(collection_name=collection_name)
                logger.info(f"Deleted collection: {collection_name}")
            else:
                logger.info(f"Collection {collection_name} does not exist")
                
        except Exception as e:
            logger.error(f"Failed to delete collection: {str(e)}")
            raise DatabaseError(f"Failed to delete collection: {str(e)}")
    
    def get_or_create_collection(self, collection_name: str) -> None:
        """Get or create a collection in Qdrant."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            if collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=settings.VECTOR_SIZE,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {collection_name}")
            else:
                logger.info(f"Using existing collection: {collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to get/create collection: {str(e)}")
            raise DatabaseError(f"Failed to get/create collection: {str(e)}")
    
    def query(
        self,
        query_text: str,
        k: int = 10,
        collection_name: Optional[str] = None,
        search_type: str = "vector"
    ) -> List[Dict[str, Any]]:
        """Query the vector database."""
        try:
            collection = collection_name or settings.COLLECTION_NAME
            
            if search_type == "vector":
                # Vector search
                results = self.client.search(
                    collection_name=collection,
                    query_vector=self._get_embedding(query_text),
                    limit=k
                )
            else:
                # Keyword search using BM25
                results = self.client.search(
                    collection_name=collection,
                    query_text=query_text,
                    limit=k
                )
            
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in results
            ]
            
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            raise DatabaseError(f"Query failed: {str(e)}")
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using FastEmbed model."""
        try:
            # FastEmbed returns iterator, so we need to get first item
            embedding = list(self.model.embed([text]))[0]
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise DatabaseError(f"Failed to generate embedding: {str(e)}")
    
    def upsert_documents(
        self,
        documents: List[Dict[str, Any]],
        collection_name: Optional[str] = None,
        cleanup_old: bool = False,
        batch_size: int = 100
    ) -> None:
        """Upsert documents into the collection with optional cleanup of old records."""
        try:
            collection = collection_name or settings.COLLECTION_NAME
            
            # Get current document IDs if cleanup is requested
            current_ids = set()
            if cleanup_old:
                current_ids = {doc["id"] for doc in documents}
            
            # Process documents in batches
            total_processed = 0
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                # Prepare points for this batch
                points = []
                for doc in batch:
                    # Generate embedding for text field
                    vector = self._get_embedding(doc.get("text", ""))
                    
                    # Create point
                    point = models.PointStruct(
                        id=doc["id"],
                        vector=vector,
                        payload=doc
                    )
                    points.append(point)
                
                # Upsert this batch
                self.client.upsert(
                    collection_name=collection,
                    points=points
                )
                
                total_processed += len(points)
                logger.info(f"Processed batch of {len(points)} documents (total: {total_processed}/{len(documents)})")
            
            # Cleanup old records if requested
            if cleanup_old:
                # Get all existing points in batches
                all_ids_to_delete = []
                offset = None
                
                while True:
                    # Get batch of existing points
                    scroll_result = self.client.scroll(
                        collection_name=collection,
                        limit=batch_size,
                        offset=offset
                    )
                    
                    existing_points = scroll_result[0]
                    offset = scroll_result[1]
                    
                    if not existing_points:
                        break
                    
                    # Find IDs to delete in this batch
                    batch_ids_to_delete = [
                        point.id for point in existing_points 
                        if point.id not in current_ids
                    ]
                    
                    all_ids_to_delete.extend(batch_ids_to_delete)
                    
                    if not offset:
                        break
                
                # Delete old records in batches
                for i in range(0, len(all_ids_to_delete), batch_size):
                    batch_ids = all_ids_to_delete[i:i + batch_size]
                    if batch_ids:
                        self.client.delete(
                            collection_name=collection,
                            points_selector=models.PointIdsList(
                                points=batch_ids
                            )
                        )
                        logger.info(f"Deleted batch of {len(batch_ids)} old records")
            
            logger.info(f"Completed processing {total_processed} documents")
            
        except Exception as e:
            logger.error(f"Failed to upsert documents: {str(e)}")
            raise DatabaseError(f"Failed to upsert documents: {str(e)}")

# Create global database client instance - FIX: Use DatabaseClient instead of QdrantClient
db_client = DatabaseClient()
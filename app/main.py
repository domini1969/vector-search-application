# app/main.py
from fastapi import FastAPI, HTTPException, Query, Path, UploadFile, File
from typing import Dict, Any, List, Optional
import uvicorn
from pydantic import BaseModel
import json
import os

from app.services.search_service import search_service
from app.core.logging import logger
from app.config.config import settings
from app.core.database import db_client

# 🚀 NEW: Import the enhanced search router
from app.api.endpoints.search import router as search_router

app = FastAPI(
    title="Vector Search Service (Qdrant)",
    description="API for vector search using Qdrant with enhanced search capabilities",
    version="1.0.0"
)

# 🚀 NEW: Include the enhanced search router
app.include_router(search_router, prefix="/api", tags=["Enhanced Search"])

# Request/Response Models
class SearchRequest(BaseModel):
    query: str
    count: int = 10
    filter_field: Optional[str] = None
    filter_value: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query: str

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str

class LoadDataResponse(BaseModel):
    success: bool
    message: str
    documents_loaded: int
    collection_name: str

# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        return {
            "status": "healthy",
            "service": "qdrant",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Service unhealthy")

@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search endpoint with request body."""
    try:
        results = search_service.search_with_details(
            query_text=request.query,
            count=request.count,
            filter_field=request.filter_field,
            filter_value=request.filter_value
        )
        return {
            "results": results,
            "total": len(results),
            "query": request.query
        }
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search", response_model=SearchResponse)
async def search_get(
    query: str = Query(..., description="Search query text"),
    count: int = Query(10, description="Number of results to return"),
    filter_field: Optional[str] = Query(None, description="Field to filter on"),
    filter_value: Optional[str] = Query(None, description="Value to filter on")
):
    """Search endpoint with query parameters."""
    try:
        results = search_service.search_with_details(
            query_text=query,
            count=count,
            filter_field=filter_field,
            filter_value=filter_value
        )
        return {
            "results": results,
            "total": len(results),
            "query": query
        }
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/load-data", response_model=LoadDataResponse)
async def load_data(
    file: UploadFile = File(..., description="JSON file containing product data"),
    collection_name: str = Query(settings.COLLECTION_NAME, description="Collection name to load data into"),
    cleanup_old: bool = Query(True, description="Whether to remove records that are no longer in the new data"),
    batch_size: int = Query(100, description="Number of documents to process in each batch", ge=1, le=1000)
):
    """Load product data from JSON file into Qdrant."""
    try:
        # Read and parse JSON file
        content = await file.read()
        documents = json.loads(content)
        
        # Process documents
        processed_docs = []
        for doc in documents:
            # Add text field for embedding if not present
            if "text" not in doc:
                # Combine relevant fields for embedding
                text_parts = []
                if "shortDescription_airgas_text" in doc:
                    text_parts.append(doc["shortDescription_airgas_text"])
                if "manufacturerPartNumber_text" in doc:
                    text_parts.append(doc["manufacturerPartNumber_text"])
                doc["text"] = " ".join(text_parts)
            
            # Ensure document has an ID
            if "id" not in doc:
                # Generate a positive integer ID from the part number
                part_number = doc.get("partNumber_airgas_text", "")
                # Use a simple hash function that produces positive integers
                doc["id"] = abs(hash(part_number)) % (2**63)  # Keep within 64-bit unsigned integer range
            
            processed_docs.append(doc)
        
        # Upsert documents with optional cleanup of old records
        db_client.upsert_documents(
            documents=processed_docs,
            collection_name=collection_name,
            cleanup_old=cleanup_old,
            batch_size=batch_size
        )
        
        return {
            "success": True,
            "message": f"Successfully loaded {len(processed_docs)} documents" + (" (old records were cleaned up)" if cleanup_old else ""),
            "documents_loaded": len(processed_docs),
            "collection_name": collection_name
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        logger.error(f"Failed to load data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collections")
async def list_collections():
    """List available collections."""
    try:
        # This would need to be implemented in the database client
        return {"collections": ["products_fast"]}  # Placeholder
    except Exception as e:
        logger.error(f"Failed to list collections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collections/{collection_name}/stats")
async def collection_stats(
    collection_name: str = Path(..., description="Name of the collection")
):
    """Get statistics for a specific collection."""
    try:
        # This would need to be implemented in the database client
        return {
            "collection": collection_name,
            "vectors_count": 0,  # Placeholder
            "points_count": 0,   # Placeholder
            "segments_count": 0  # Placeholder
        }
    except Exception as e:
        logger.error(f"Failed to get collection stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 🔧 MODIFIED: Enhanced the existing /api/query endpoint
@app.get("/api/query")
async def query(
    q: str = Query(..., description="Search query text"),
    count: int = Query(10, description="Number of results to return"),
    filter_field: Optional[str] = Query(None, description="Field to filter on"),
    filter_value: Optional[str] = Query(None, description="Value to filter on"),
    use_fusion: bool = Query(False, description="Enable fusion search (exact + vector)")
):
    """Query endpoint with query parameters. Now supports fusion search!"""
    try:
        results = search_service.filtered_search(
            query_text=q,
            count=count,
            filter_field=filter_field,
            filter_value=filter_value,
            use_fusion=use_fusion
        )
        # Return just the results array without wrapping in a response object
        return results
    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
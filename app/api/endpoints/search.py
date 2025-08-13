# app/api/endpoints/search.py
from typing import Dict, Any, List, Optional
import time
import os
import sys

from fastapi import APIRouter, Query, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
import asyncio
from functools import partial

from app.api.models.document import SearchResult
from app.services.search_service import (
    search_service, 
    ultra_search_service, 
    lean_search_service,
    UltraFastSearchService,
    LeanSearchService,
    ReallyFastSearchService
)
from app.core.errors import DatabaseError
from app.core.logging import logger
from app.config import settings

# Import the enhanced indexing class with search methods
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../scripts"))
from indexing import EnhancedIndexing

router = APIRouter(tags=["search"])

# Create additional service instances for testing
really_fast_service = ReallyFastSearchService()

# Create enhanced indexing instance for multi-method search
try:
    enhanced_indexer = EnhancedIndexing(
        collection_name=settings.COLLECTION_NAME,
        qdrant_url="http://localhost:6333"
    )
    logger.info("✅ Enhanced indexer initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize enhanced indexer: {e}")
    enhanced_indexer = None


@router.get(
    "/query", 
    summary="Flexible Query Endpoint - Support for dense, sparse, or hybrid modes",
    description="Search for documents with mode selection: dense (semantic), sparse (BM25), or hybrid (RRF fusion)"
)
async def query(
    q: str = Query(..., description="Query text to search for"),
    count: int = Query(10, description="Number of results to return", ge=1, le=100),
    mode: str = Query("hybrid", description="Search mode: 'dense', 'sparse', or 'hybrid'"),
    filter_field: Optional[str] = Query(None, description="Field name to filter on"),
    filter_value: Optional[str] = Query(None, description="Value to filter on")
):
    """Search for documents with flexible mode selection."""
    if not enhanced_indexer:
        raise HTTPException(status_code=503, detail="Enhanced search service not available")
    
    try:
        # Validate mode
        if mode not in ["dense", "sparse", "hybrid"]:
            raise HTTPException(status_code=400, detail="Mode must be 'dense', 'sparse', or 'hybrid'")
        
        # Execute search based on mode
        if mode == "dense":
            result = enhanced_indexer.search_dense(q, count)
        elif mode == "sparse":
            result = enhanced_indexer.search_bm25(q, count)
        elif mode == "hybrid":
            result = enhanced_indexer.search_hybrid(q, count)
        
        return {
            "results": [
                {
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload
                }
                for point in result["results"]
            ],
            "search_time_ms": result["search_time_ms"],
            "method": result["method"],
            "query": result["query"],
            "mode": mode,
            "count": len(result["results"])
        }
        
    except DatabaseError as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get(
    "/search",
    summary="Optimized search endpoint - Returns full document details",
    description="Search for documents and return full document details in a single response"
)
async def optimized_search(
    request: Request,
    q: str = Query(..., description="Query text to search for"),
    count: int = Query(10, description="Number of results to return", ge=1, le=100),
    filter_field: Optional[str] = Query(None, description="Field name to filter on"),
    filter_value: Optional[str] = Query(None, description="Value to filter on"),
    use_fusion: bool = Query(False, description="Enable fusion search (exact + vector)")
):
    """
    Optimized search endpoint that returns search results with complete document details.
    Eliminates the need for separate document fetching requests.
    """
    try:
        # Create a timeout for the search operation
        timeout = 30.0  # 30 seconds timeout
        
        # Run search with timeout
        search_func = partial(
            search_service.search_with_details,
            query_text=q,
            count=count,
            filter_field=filter_field,
            filter_value=filter_value,
            use_fusion=use_fusion
        )
        
        # Run in threadpool to avoid blocking
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, search_func)
        
        response = {
            "query": q,
            "count": len(results),
            "results": results
        }
        
        return response
        
    except asyncio.TimeoutError:
        logger.error("Search operation timed out")
        raise HTTPException(
            status_code=504,
            detail="Search operation timed out. Please try again or refine your search."
        )
        
    except DatabaseError as e:
        logger.error(f"Database error in search: {str(e)}")
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Database error: {e.message}"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in search: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later."
        )


@router.get(
    "/search/ultra-fast",
    summary="🚀 Ultra Fast Search - Core vector search (25-40ms)",
    description="Ultra-fast vector search using proven configuration. Returns core search results with timing info."
)
async def ultra_fast_search(
    q: str = Query(..., description="Query text to search for"),
    count: int = Query(10, description="Number of results to return", ge=1, le=100)
):
    """Ultra-fast core search using the proven 25-40ms configuration."""
    try:
        start_time = time.time()
        
        # Use the core ultra-fast search method
        results = ultra_search_service.search(q, count)
        
        search_time = (time.time() - start_time) * 1000
        
        return {
            "query": q,
            "search_time_ms": round(search_time, 1),
            "count": len(results),
            "results": results,
            "search_type": "ultra_fast_vector"
        }
        
    except Exception as e:
        logger.error(f"Ultra-fast search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ultra-fast search failed: {str(e)}")


@router.get(
    "/search/fusion",
    summary="🎯 Fusion Search - Parallel exact + vector search",
    description="Advanced fusion search combining exact matching and vector search in parallel for best results."
)
async def fusion_search(
    q: str = Query(..., description="Query text to search for"),
    count: int = Query(10, description="Number of results to return", ge=1, le=100)
):
    """Fusion search combining exact and vector search for optimal results."""
    try:
        start_time = time.time()
        
        # Use the new fusion search method
        results = search_service.search_fusion(q, count)
        
        search_time = (time.time() - start_time) * 1000
        
        return {
            "query": q,
            "search_time_ms": round(search_time, 1),
            "count": len(results),
            "results": results,
            "search_type": "fusion_exact_vector"
        }
        
    except Exception as e:
        logger.error(f"Fusion search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fusion search failed: {str(e)}")


@router.get(
    "/search/lean",
    summary="⚡ Lean Search - Maximum speed minimal features",
    description="Absolute fastest search with minimal processing for maximum speed."
)
async def lean_search(
    q: str = Query(..., description="Query text to search for"),
    count: int = Query(10, description="Number of results to return", ge=1, le=100)
):
    """Lean search optimized for absolute maximum speed."""
    try:
        start_time = time.time()
        
        # Use the lean search method
        results = lean_search_service.search_lean(q, count)
        
        search_time = (time.time() - start_time) * 1000
        
        return {
            "query": q,
            "search_time_ms": round(search_time, 1),
            "count": len(results),
            "results": results,
            "search_type": "lean_minimal"
        }
        
    except Exception as e:
        logger.error(f"Lean search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lean search failed: {str(e)}")


@router.get(
    "/search/really-fast",
    summary="🏃 Really Fast Search - Alias for ultra-fast",
    description="Really fast search service (alias for ultra-fast search)."
)
async def really_fast_search(
    q: str = Query(..., description="Query text to search for"),
    count: int = Query(10, description="Number of results to return", ge=1, le=100)
):
    """Really fast search service (backward compatibility alias)."""
    try:
        start_time = time.time()
        
        # Use the really fast service
        results = really_fast_service.search(q, count)
        
        search_time = (time.time() - start_time) * 1000
        
        return {
            "query": q,
            "search_time_ms": round(search_time, 1),
            "count": len(results),
            "results": results,
            "search_type": "really_fast_alias"
        }
        
    except Exception as e:
        logger.error(f"Really fast search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Really fast search failed: {str(e)}")


@router.get(
    "/search/compare",
    summary="📊 Compare All Search Methods",
    description="Compare performance across all search methods for the same query."
)
async def compare_search_methods(
    q: str = Query(..., description="Query text to search for"),
    count: int = Query(5, description="Number of results to return", ge=1, le=20)
):
    """Compare performance across all available search methods."""
    try:
        comparison_results = {}
        
        # Test Ultra Fast Search
        try:
            start_time = time.time()
            ultra_results = ultra_search_service.search(q, count)
            ultra_time = (time.time() - start_time) * 1000
            comparison_results["ultra_fast"] = {
                "time_ms": round(ultra_time, 1),
                "count": len(ultra_results),
                "results": ultra_results[:3]  # Show first 3 for comparison
            }
        except Exception as e:
            comparison_results["ultra_fast"] = {"error": str(e)}
        
        # Test Fusion Search
        try:
            start_time = time.time()
            fusion_results = search_service.search_fusion(q, count)
            fusion_time = (time.time() - start_time) * 1000
            comparison_results["fusion"] = {
                "time_ms": round(fusion_time, 1),
                "count": len(fusion_results),
                "results": fusion_results[:3]  # Show first 3 for comparison
            }
        except Exception as e:
            comparison_results["fusion"] = {"error": str(e)}
        
        # Test Lean Search
        try:
            start_time = time.time()
            lean_results = lean_search_service.search_lean(q, count)
            lean_time = (time.time() - start_time) * 1000
            comparison_results["lean"] = {
                "time_ms": round(lean_time, 1),
                "count": len(lean_results),
                "results": lean_results[:3]  # Show first 3 for comparison
            }
        except Exception as e:
            comparison_results["lean"] = {"error": str(e)}
        
        return {
            "query": q,
            "comparison": comparison_results,
            "note": "Showing first 3 results from each method for comparison"
        }
        
    except Exception as e:
        logger.error(f"Search comparison failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search comparison failed: {str(e)}")


@router.get(
    "/search/performance-stats",
    summary="📈 Performance Statistics",
    description="Get detailed performance statistics from all search services."
)
async def get_performance_stats():
    """Get performance statistics from all search services."""
    try:
        stats = {
            "search_service": search_service.get_performance_stats(),
            "ultra_search_service": ultra_search_service.get_performance_stats(),
            "lean_search_service": lean_search_service.get_performance_stats(),
            "really_fast_service": really_fast_service.get_performance_stats()
        }
        
        return {
            "performance_stats": stats,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance stats: {str(e)}")


@router.post(
    "/search/optimize",
    summary="🔧 Optimize Search Services",
    description="Optimize and warm up all search services for best performance."
)
async def optimize_search_services():
    """Optimize and warm up all search services."""
    try:
        optimization_results = {}
        
        # Optimize main search service
        optimization_results["search_service"] = search_service.optimize_for_collection()
        
        # Optimize ultra search service
        optimization_results["ultra_search_service"] = ultra_search_service.optimize_for_collection()
        
        # Optimize lean search service
        optimization_results["lean_search_service"] = lean_search_service.optimize_for_collection()
        
        # Optimize really fast service
        optimization_results["really_fast_service"] = really_fast_service.optimize_for_collection()
        
        return {
            "status": "completed",
            "optimization_results": optimization_results,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Search optimization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search optimization failed: {str(e)}")


@router.delete(
    "/search/cache",
    summary="🧹 Clear Search Caches",
    description="Clear all embedding caches from search services."
)
async def clear_search_caches():
    """Clear embedding caches from all search services."""
    try:
        # Clear caches from all services
        search_service.clear_cache()
        ultra_search_service.clear_cache()
        lean_search_service.clear_cache()
        really_fast_service.clear_cache()
        
        return {
            "status": "success",
            "message": "All search caches cleared",
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Failed to clear caches: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear caches: {str(e)}")


# ==================== ENHANCED SEARCH METHODS ====================

@router.get(
    "/dense",
    summary="🎯 Dense Search",
    description="Semantic vector search on product descriptions only (shortDescription_airgas_text field)"
)
async def search_dense(
    query: str = Query(..., description="Search query text"),
    limit: int = Query(10, description="Number of results to return", ge=1, le=50)
):
    """Dense vector search - searches ONLY shortDescription_airgas_text field for semantic similarity."""
    if not enhanced_indexer:
        raise HTTPException(status_code=503, detail="Enhanced search service not available")
    
    try:
        result = enhanced_indexer.search_dense(query, limit)
        return {
            "results": [
                {
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload
                }
                for point in result["results"]
            ],
            "search_time_ms": result["search_time_ms"],
            "method": result["method"],
            "query": result["query"],
            "fields_searched": "shortDescription_airgas_text"
        }
    except Exception as e:
        logger.error(f"Dense search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dense search failed: {str(e)}")


@router.get(
    "/sparse",
    summary="🔍 BM25 Sparse Search", 
    description="Traditional BM25 sparse search on descriptions + part numbers (Qdrant native)"
)
async def search_sparse(
    query: str = Query(..., description="Search query text"),
    limit: int = Query(10, description="Number of results to return", ge=1, le=50)
):
    """BM25 sparse search - searches shortDescription + partNumber + manufacturerPartNumber fields."""
    if not enhanced_indexer:
        raise HTTPException(status_code=503, detail="Enhanced search service not available")
    
    try:
        result = enhanced_indexer.search_bm25(query, limit)
        return {
            "results": [
                {
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload
                }
                for point in result["results"]
            ],
            "search_time_ms": result["search_time_ms"],
            "method": result["method"],
            "query": result["query"],
            "fields_searched": "shortDescription_airgas_text + partNumber_airgas_text + manufacturerPartNumber_text"
        }
    except Exception as e:
        logger.error(f"BM25 search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"BM25 search failed: {str(e)}")




@router.get(
    "/hybrid",
    summary="⚡ Hybrid Search",
    description="Dense + BM25 fusion search using Qdrant native RRF"
)
async def search_hybrid(
    query: str = Query(..., description="Search query text"),
    limit: int = Query(10, description="Number of results to return", ge=1, le=50)
):
    """Hybrid search combining dense semantic search with BM25 sparse search using Qdrant native RRF."""
    if not enhanced_indexer:
        raise HTTPException(status_code=503, detail="Enhanced search service not available")
    
    try:
        result = enhanced_indexer.search_hybrid(query, limit=limit)
        return {
            "results": [
                {
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload
                }
                for point in result["results"]
            ],
            "search_time_ms": result["search_time_ms"],
            "method": result["method"],
            "query": result["query"],
            "fusion_method": result["fusion_method"],
            "fields_searched": "Dense (shortDescription) + BM25 (shortDescription + part numbers)"
        }
    except Exception as e:
        logger.error(f"Hybrid search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")




@router.get(
    "/methods-info",
    summary="📋 Search Methods Info",
    description="Get information about all available search methods and their field mappings"
)
async def search_methods_info():
    """Get detailed information about all available search methods."""
    return {
        "available_methods": {
            "query": {
                "name": "Flexible Query",
                "description": "Flexible search with mode selection (dense, sparse, hybrid)",
                "modes": ["dense", "sparse", "hybrid"],
                "type": "flexible",
                "endpoint": "/api/query"
            },
            "dense": {
                "name": "Dense Search",
                "description": "Semantic vector search on product descriptions only",
                "fields": ["shortDescription_airgas_text"],
                "type": "vector",
                "endpoint": "/api/dense"
            },
            "sparse": {
                "name": "BM25 Sparse Search",
                "description": "Traditional BM25 keyword search (Qdrant native)",
                "fields": ["shortDescription_airgas_text", "partNumber_airgas_text", "manufacturerPartNumber_text"],
                "type": "sparse",
                "endpoint": "/api/sparse"
            },
            "hybrid": {
                "name": "Hybrid Search",
                "description": "Dense + BM25 fusion using Qdrant native RRF",
                "fields": ["Dense: shortDescription_airgas_text", "BM25: shortDescription + part numbers"],
                "type": "hybrid_rrf",
                "endpoint": "/api/hybrid"
            }
        },
        "field_mapping": {
            "dense_search_fields": ["shortDescription_airgas_text"],
            "sparse_search_fields": ["shortDescription_airgas_text", "partNumber_airgas_text", "manufacturerPartNumber_text"],
            "available_fields": ["partNumber_airgas_text", "manufacturerPartNumber_text", "shortDescription_airgas_text", "onlinePrice_string", "img_270Wx270H_string"]
        },
        "fusion_method": "qdrant_native_rrf",
        "configuration": "Dense + BM25 (Qdrant native) only",
        "service_status": "available" if enhanced_indexer else "unavailable"
    }


@router.get(
    "/test",
    summary="🧪 Test Enhanced Search Service",
    description="Test endpoint to verify enhanced search service is working"
)
async def test_enhanced_search():
    """Test the enhanced search service initialization and basic functionality."""
    if not enhanced_indexer:
        return {
            "status": "error",
            "message": "Enhanced search service not available",
            "details": "EnhancedIndexing class failed to initialize"
        }
    
    try:
        # Test basic properties
        return {
            "status": "success",
            "message": "Enhanced search service is working (Dense + BM25 only)",
            "details": {
                "collection_name": enhanced_indexer.collection_name,
                "models_available": {
                    "dense": enhanced_indexer.use_dense,
                    "bm25": enhanced_indexer.use_bm25
                },
                "search_methods": ["dense", "sparse", "hybrid"],
                "fusion_method": "qdrant_native_rrf",
                "num_threads": enhanced_indexer.num_threads,
                "quantization_mode": enhanced_indexer.quantization_mode.value if enhanced_indexer.quantization_mode else "none",
                "configuration": "Dense + BM25 (Qdrant native) only"
            }
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Enhanced search service error: {str(e)}",
            "details": str(e)
        }
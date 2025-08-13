# app/services/search_service.py
"""
Ultra-Fast Search Service with Fusion - Enhanced with parallel exact + vector search
Uses exact same configuration that achieves 25-40ms performance + fusion capabilities
FIXED: Async event loop handling for FastAPI compatibility
"""

from typing import Dict, Any, List, Optional
import time
import asyncio
import multiprocessing as mp
from functools import lru_cache
from dataclasses import dataclass
import concurrent.futures

# Import your existing modules
try:
    from app.core.database import db_client
    from app.core.errors import DatabaseError
    from app.core.logging import logger
    from app.config.config import settings
except ImportError:
    # Fallback for development/testing
    class MockLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
    
    logger = MockLogger()
    
    class MockSettings:
        COLLECTION_NAME = "products_fast"
    
    settings = MockSettings()

# Import optimized libraries - exactly like test_speed.py
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue


@dataclass
class SearchResult:
    """Standardized search result format for fusion"""
    id: str
    score: float
    payload: Dict[str, Any]
    search_type: str
    qdrant_id: Optional[str] = None
    boost_factor: float = 1.0


class UltraFastSearchService:
    """Ultra-fast search service with fusion capabilities."""
    
    def __init__(self, 
                 collection_name: Optional[str] = None,
                 qdrant_host: str = "localhost", 
                 qdrant_port: int = 6333,
                 model_name: str = None,
                 num_threads: Optional[int] = None):
        """Initialize with exact same config as test_speed.py"""
        
        self.collection_name = collection_name or getattr(settings, 'COLLECTION_NAME', 'products_fast')
        self.num_threads = num_threads or min(mp.cpu_count(), 8)
        self.model_name = model_name or getattr(settings, 'MODEL_NAME', 'BAAI/bge-small-en-v1.5')
        
        logger.info(f"🔧 Initializing with collection: {self.collection_name}")
        logger.info(f"🤖 Using model: {self.model_name}")
        logger.info(f"🧵 Threads: {self.num_threads}")
        
        # CRITICAL: Use exact same client config as test_speed.py
        self.client = QdrantClient(
            host=qdrant_host, 
            port=qdrant_port, 
            timeout=600, 
            prefer_grpc=True  # This is KEY for performance
        )
        
        # CRITICAL: Use exact same model config as test_speed.py
        logger.info("⚡ Loading FastEmbed model (matching test_speed.py config)...")
        start_time = time.time()
        
        self.dense_model = TextEmbedding(
            self.model_name,
            max_length=512,
            threads=self.num_threads,
            cache_dir=None
        )
        
        load_time = time.time() - start_time
        logger.info(f"✅ Model loaded in {load_time:.2f}s")
        
        # Performance tracking
        self._search_count = 0
        self._total_time = 0.0
        self._fusion_stats = {
            'total_fusion_searches': 0,
            'avg_exact_time': 0,
            'avg_vector_time': 0,
            'avg_fusion_time': 0,
            'avg_total_fusion_time': 0
        }
        
        logger.info(f"🚀 Ultra-fast search service ready: {self.collection_name}")
        logger.info("🎯 Fusion search capabilities enabled")
    
    def verify_collection(self):
        """Verify collection exists - from test_speed.py"""
        try:
            collections = self.client.get_collections()
            collection_exists = any(col.name == self.collection_name for col in collections.collections)
            
            if not collection_exists:
                logger.error(f"❌ Collection '{self.collection_name}' not found!")
                available = [col.name for col in collections.collections]
                logger.error(f"Available collections: {available}")
                return False
            else:
                logger.info(f"✅ Collection '{self.collection_name}' found")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error verifying collection: {e}")
            return False
    
    @lru_cache(maxsize=1000)
    def _get_embedding_cached(self, text: str) -> tuple:
        """Get embedding with caching - using exact test_speed.py method"""
        try:
            # EXACT same method as test_speed.py
            query_vector = list(self.dense_model.query_embed([text]))[0]
            return tuple(query_vector.tolist() if hasattr(query_vector, 'tolist') else query_vector)
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return tuple([0.0] * 384)  # Default fallback
    
    def search(self, query_text: str, count: int = 10) -> List[Dict[str, Any]]:
        """Core search method - EXACT copy of test_speed.py logic"""
        total_start = time.time()
        
        try:
            self._search_count += 1
            
            # Time embedding generation separately (like test_speed.py)
            embed_start = time.time()
            query_vector = list(self._get_embedding_cached(query_text))
            embed_time = time.time() - embed_start
            
            # Time search separately (like test_speed.py)
            search_start = time.time()
            
            # EXACT same search call as test_speed.py
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                using="dense",
                with_payload=True,
                limit=count,
                timeout=30,  # Same timeout as test_speed.py
                search_params={
                    "hnsw_ef": 128,  # Same ef as test_speed.py
                    "exact": False
                }
            )
            
            search_time = time.time() - search_start
            total_time = embed_time + search_time
            
            # Update stats
            self._total_time += total_time
            
            # Same logging format as test_speed.py
            logger.info(
                f"'{query_text}': {total_time*1000:.1f}ms total "
                f"({embed_time*1000:.1f}ms embed + {search_time*1000:.1f}ms search) "
                f"- {len(results.points)} results"
            )
            
            # Performance evaluation (same as test_speed.py)
            if total_time < 0.1:
                logger.info("✅ EXCELLENT performance!")
            elif total_time < 0.2:
                logger.info("✅ GOOD performance")
            else:
                logger.warning(f"⚠️ Could be faster - {total_time*1000:.1f}ms")
                if search_time > 1.0:
                    logger.error(f"🚨 Search taking {search_time:.1f}s - check if vectors are on disk!")
            
            # Format results
            formatted_results = []
            for hit in results.points:
                formatted_results.append({
                    "id": hit.payload.get('partNumber_airgas_text', str(hit.id)),
                    "score": float(hit.score),
                    "payload": hit.payload,
                    "qdrant_id": hit.id,
                    "search_type": "ultra_fast"
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise DatabaseError(f"Search failed: {e}")
    
    def _exact_search_sync(self, query: str, count: int = 20) -> List[SearchResult]:
        """Synchronous exact matching search with normalized scores"""
        results = []
        start_time = time.time()
        
        try:
            clean_query = query.strip().upper()
            
            # Search fields with normalized scores
            search_fields = [
                ("partNumber_airgas_text", 1.0, "exact"),
                ("manufacturerPartNumber_text", 0.9, "exact_mfg")
            ]
            
            for field_name, normalized_score, search_type in search_fields:
                try:
                    qdrant_results = self.client.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=Filter(
                            must=[FieldCondition(key=field_name, match=MatchValue(value=clean_query))]
                        ),
                        limit=min(count, 10),
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    for point in qdrant_results[0]:
                        results.append(SearchResult(
                            id=point.payload.get('partNumber_airgas_text', str(point.id)),
                            score=normalized_score,
                            payload=point.payload,
                            search_type=search_type,
                            qdrant_id=str(point.id),
                            boost_factor=1.0
                        ))
                    
                    # If we found exact matches, don't search other fields
                    if results and search_type == "exact":
                        break
                        
                except Exception as field_error:
                    continue
        
        except Exception as e:
            logger.error(f"Exact search error: {e}")
        
        search_time = time.time() - start_time
        self._fusion_stats['avg_exact_time'] = (self._fusion_stats['avg_exact_time'] * 0.9 + search_time * 0.1)
        
        return results
    
    def _vector_search_sync(self, query: str, count: int = 20) -> List[SearchResult]:
        """Synchronous semantic vector search with normalized scores"""
        results = []
        start_time = time.time()
        
        try:
            # Get embedding (cached)
            query_vector = list(self._get_embedding_cached(query))
            
            # Use proven optimal parameters
            qdrant_results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                using="dense",
                with_payload=True,
                with_vectors=False,
                limit=count,
                search_params={
                    "hnsw_ef": 128,
                    "exact": False
                }
            )
            
            for point in qdrant_results.points:
                # Only include results with meaningful scores
                if point.score >= 0.4:
                    results.append(SearchResult(
                        id=point.payload.get('partNumber_airgas_text', str(point.id)),
                        score=float(point.score),
                        payload=point.payload,
                        search_type='vector',
                        qdrant_id=str(point.id),
                        boost_factor=1.0
                    ))
        
        except Exception as e:
            logger.error(f"Vector search error: {e}")
        
        search_time = time.time() - start_time
        self._fusion_stats['avg_vector_time'] = (self._fusion_stats['avg_vector_time'] * 0.9 + search_time * 0.1)
        
        return results
    
    def simple_fusion(self, exact_results: List[SearchResult], 
                      vector_results: List[SearchResult]) -> List[SearchResult]:
        """Simple fusion with normalized scores - no artificial boosting"""
        start_time = time.time()
        
        # Combine all results
        all_results = exact_results + vector_results
        
        # Simple deduplication - keep best normalized score
        seen_ids = {}
        fused_results = []
        
        for result in all_results:
            result_id = result.id
            
            if result_id not in seen_ids:
                seen_ids[result_id] = result
                fused_results.append(result)
            else:
                existing = seen_ids[result_id]
                
                # Keep the result with higher normalized score
                if result.score > existing.score:
                    # Replace with better result
                    result.search_type = f"{existing.search_type}+{result.search_type}"
                    seen_ids[result_id] = result
                    # Replace in list
                    for i, res in enumerate(fused_results):
                        if res.id == result_id:
                            fused_results[i] = result
                            break
                else:
                    # Keep existing but note additional match
                    existing.search_type = f"{existing.search_type}+{result.search_type}"
        
        # Sort by normalized score (0-1 range)
        fused_results.sort(key=lambda x: x.score, reverse=True)
        
        fusion_time = time.time() - start_time
        self._fusion_stats['avg_fusion_time'] = (self._fusion_stats['avg_fusion_time'] * 0.9 + fusion_time * 0.1)
        
        return fused_results
    
    def _parallel_fusion_search_sync(self, query: str, count: int = 10) -> List[SearchResult]:
        """Synchronous parallel fusion search using ThreadPoolExecutor"""
        total_start = time.time()
        
        logger.info(f"🔍 Fusion Search: '{query}'")
        
        # Use ThreadPoolExecutor for parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both searches
            exact_future = executor.submit(self._exact_search_sync, query, count)
            vector_future = executor.submit(self._vector_search_sync, query, count * 2)
            
            # Wait for both to complete
            exact_results = exact_future.result()
            vector_results = vector_future.result()
        
        logger.info(f"📊 Results: Exact={len(exact_results)}, Vector={len(vector_results)}")
        
        # Simple fusion
        fused_results = self.simple_fusion(exact_results, vector_results)
        
        # Update stats
        total_time = time.time() - total_start
        self._fusion_stats['total_fusion_searches'] += 1
        self._fusion_stats['avg_total_fusion_time'] = (
            self._fusion_stats['avg_total_fusion_time'] * 0.9 + total_time * 0.1
        )
        
        logger.info(f"⚡ Fusion time: {total_time*1000:.1f}ms")
        logger.info(f"🎯 Fused results: {len(fused_results[:count])}")
        
        return fused_results[:count]
    
    def search_fusion(self, query_text: str, count: int = 10) -> List[Dict[str, Any]]:
        """Synchronous fusion search - FIXED for FastAPI compatibility"""
        try:
            # Use synchronous parallel search instead of asyncio.run()
            fusion_results = self._parallel_fusion_search_sync(query_text, count)
            
            # Convert SearchResult objects to dict format
            formatted_results = []
            for result in fusion_results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload,
                    "qdrant_id": result.qdrant_id,
                    "search_type": result.search_type
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Fusion search failed: {e}")
            raise DatabaseError(f"Fusion search failed: {e}")
    
    def search_with_details(
        self,
        query_text: str,
        count: int = 10,
        filter_field: Optional[str] = None,
        filter_value: Optional[str] = None,
        enable_reranking: bool = False,
        use_fusion: bool = False  # New parameter to enable fusion
    ) -> List[Dict[str, Any]]:
        """Search with details - now supports fusion search"""
        try:
            # Choose search method
            if use_fusion:
                search_results = self.search_fusion(query_text, count * 2 if filter_field else count)
            else:
                search_count = count * 2 if filter_field else count
                search_results = self.search(query_text, search_count)
            
            # Apply simple post-filter if needed
            if filter_field and filter_value:
                search_results = [
                    r for r in search_results
                    if r.get('payload', {}).get(filter_field) == filter_value
                ]
            
            # Format results to match expected API
            return [
                {
                    "image": r['payload'].get("img_270Wx270H_string", ""),
                    "id": r['id'],
                    "text": r['payload'].get("shortDescription_airgas_text", ""),
                    "Mfr Code": r['payload'].get("manufacturerPartNumber_text", ""),
                    "Price": r['payload'].get("onlinePrice_string", ""),
                    "score": round(r['score'], 3),
                    "search_type": r['search_type']
                }
                for r in search_results[:count]
            ]
            
        except Exception as e:
            logger.error(f"Search with details failed: {e}")
            raise DatabaseError(f"Search with details failed: {e}")
    
    def filtered_search(
        self,
        query_text: str,
        count: int = 10,
        filter_field: Optional[str] = None,
        filter_value: Optional[str] = None,
        use_fusion: bool = False  # New parameter
    ) -> List[Dict[str, Any]]:
        """Filtered search with optional fusion"""
        try:
            # Choose search method
            if use_fusion:
                search_results = self.search_fusion(query_text, count * 3 if filter_field else count)
            else:
                search_count = count * 3 if filter_field else count
                search_results = self.search(query_text, search_count)
            
            # Apply filtering
            if filter_field and filter_value:
                search_results = [
                    r for r in search_results
                    if r.get('payload', {}).get(filter_field) == filter_value
                ]
            
            # Format results (removed search_type for /api/query endpoint)
            return [
                {
                    "id": r['payload'].get('partNumber_airgas_text', r["id"]),
                    "score": r["score"]
                }
                for r in search_results[:count]
            ]
            
        except Exception as e:
            logger.error(f"Filtered search failed: {e}")
            raise DatabaseError(f"Filtered search failed: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics including fusion stats"""
        avg_time = self._total_time / max(self._search_count, 1)
        
        stats = {
            'total_searches': self._search_count,
            'avg_search_time_ms': avg_time * 1000,
            'embedding_cache_size': self._get_embedding_cached.cache_info().currsize,
            'search_mode': 'ultra_fast_with_fusion',
            'model_type': 'fastembed',
            'client_type': 'grpc_optimized'
        }
        
        # Add fusion stats if any fusion searches were performed
        if self._fusion_stats['total_fusion_searches'] > 0:
            stats.update({
                'total_fusion_searches': self._fusion_stats['total_fusion_searches'],
                'avg_exact_time_ms': self._fusion_stats['avg_exact_time'] * 1000,
                'avg_vector_time_ms': self._fusion_stats['avg_vector_time'] * 1000,
                'avg_fusion_time_ms': self._fusion_stats['avg_fusion_time'] * 1000,
                'avg_total_fusion_time_ms': self._fusion_stats['avg_total_fusion_time'] * 1000,
            })
        
        return stats
    
    def clear_cache(self):
        """Clear embedding cache"""
        self._get_embedding_cached.cache_clear()
        logger.info("Embedding cache cleared")
    
    def optimize_for_collection(self):
        """Test and optimize collection"""
        try:
            if not self.verify_collection():
                return {'status': 'failed', 'error': 'Collection not found'}
            
            # Warmup both regular and fusion search
            start = time.time()
            self.search("test warmup", count=5)
            regular_time = time.time() - start
            
            start = time.time()
            self.search_fusion("test warmup fusion", count=5)
            fusion_time = time.time() - start
            
            logger.info(f"Collection optimization complete.")
            logger.info(f"Regular search: {regular_time*1000:.1f}ms")
            logger.info(f"Fusion search: {fusion_time*1000:.1f}ms")
            
            return {
                'status': 'optimized',
                'regular_search_time_ms': regular_time * 1000,
                'fusion_search_time_ms': fusion_time * 1000,
                'collection_verified': True
            }
            
        except Exception as e:
            logger.error(f"Collection optimization failed: {e}")
            return {'status': 'failed', 'error': str(e)}


# Backwards compatibility classes
class ReallyFastSearchService(UltraFastSearchService):
    """Alias for backwards compatibility."""
    pass


class LeanSearchService(UltraFastSearchService):
    """Minimal search for absolute speed."""
    
    def search_lean(self, query_text: str, count: int = 10) -> List[Dict[str, Any]]:
        """Absolute minimal search - maximum speed"""
        try:
            # Direct embedding
            query_vector = list(self._get_embedding_cached(query_text))
            
            # Direct search with fixed optimal params
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                using="dense",
                with_payload=True,
                limit=count,
                search_params={"hnsw_ef": 64, "exact": False}
            )
            
            # Minimal formatting
            return [
                {
                    "id": hit.payload.get('partNumber_airgas_text', str(hit.id)),
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in results.points
            ]
            
        except Exception as e:
            raise DatabaseError(f"Lean search failed: {e}")


# Create the service instances
search_service = UltraFastSearchService()
ultra_search_service = search_service
lean_search_service = LeanSearchService()

# Export the services
__all__ = [
    'search_service', 
    'ultra_search_service', 
    'lean_search_service',
    'UltraFastSearchService', 
    'LeanSearchService',
    'ReallyFastSearchService'
]
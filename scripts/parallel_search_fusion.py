#!/usr/bin/env python3
"""
SIMPLIFIED Parallel Search - Exact + Vector Only
Removed text search, normalized scores to 0-1 range
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from functools import lru_cache

# Your existing imports
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue


@dataclass
class SearchResult:
    """Standardized search result format"""
    id: str
    score: float
    payload: Dict[str, Any]
    search_type: str
    qdrant_id: Optional[str] = None
    boost_factor: float = 1.0


class SimplifiedParallelSearch:
    """Simplified parallel search - Exact + Vector only with normalized scores"""
    
    def __init__(self, collection_name: str = "products_fast"):
        self.collection_name = collection_name
        
        # Use your proven fast configuration
        self.client = QdrantClient(
            "http://localhost:6333", 
            timeout=30, 
            prefer_grpc=True
        )
        
        self.model = TextEmbedding(
            "BAAI/bge-small-en-v1.5",
            max_length=512,
            threads=8,
            cache_dir=None
        )
        
        # Performance tracking
        self.search_stats = {
            'total_searches': 0,
            'avg_exact_time': 0,
            'avg_vector_time': 0,
            'avg_fusion_time': 0,
            'avg_total_time': 0
        }
        
        print(f"🚀 Simplified Parallel Search initialized for: {collection_name}")
        print("📋 Search types: Exact + Vector only")
        print("📏 Scores normalized to 0-1 range")
    
    @lru_cache(maxsize=2000)
    def _get_embedding_cached(self, text: str) -> tuple:
        """Cached embedding generation"""
        try:
            query_vector = list(self.model.query_embed([text]))[0]
            return tuple(query_vector.tolist() if hasattr(query_vector, 'tolist') else query_vector)
        except Exception as e:
            print(f"Embedding error: {e}")
            return tuple([0.0] * 384)
    
    async def exact_search_async(self, query: str, count: int = 20) -> List[SearchResult]:
        """Exact matching search with normalized scores"""
        results = []
        start_time = time.time()
        
        try:
            clean_query = query.strip().upper()
            
            # Search fields with normalized scores
            search_fields = [
                ("partNumber_airgas_text", 1.0, "exact"),
                ("manufacturerPartNumber_text", 0.9, "exact_mfg")  # Slightly lower for mfg part
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
                            score=normalized_score,  # Already normalized to 0-1
                            payload=point.payload,
                            search_type=search_type,
                            qdrant_id=str(point.id),
                            boost_factor=1.0  # No artificial boosting, let normalized scores speak
                        ))
                    
                    # If we found exact matches, don't search other fields
                    if results and search_type == "exact":
                        break
                        
                except Exception as field_error:
                    continue
        
        except Exception as e:
            print(f"Exact search error: {e}")
        
        search_time = time.time() - start_time
        self.search_stats['avg_exact_time'] = (self.search_stats['avg_exact_time'] * 0.9 + search_time * 0.1)
        
        return results
    
    async def vector_search_async(self, query: str, count: int = 20) -> List[SearchResult]:
        """Semantic vector search with normalized scores"""
        results = []
        start_time = time.time()
        
        try:
            # Get embedding (cached)
            query_vector = list(self._get_embedding_cached(query))
            
            # Use your proven optimal parameters
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
                # Qdrant already returns normalized cosine scores (0-1 range)
                # Only include results with meaningful scores
                if point.score >= 0.4:
                    results.append(SearchResult(
                        id=point.payload.get('partNumber_airgas_text', str(point.id)),
                        score=float(point.score),  # Already normalized 0-1
                        payload=point.payload,
                        search_type='vector',
                        qdrant_id=str(point.id),
                        boost_factor=1.0  # No artificial boosting
                    ))
        
        except Exception as e:
            print(f"Vector search error: {e}")
        
        search_time = time.time() - start_time
        self.search_stats['avg_vector_time'] = (self.search_stats['avg_vector_time'] * 0.9 + search_time * 0.1)
        
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
        self.search_stats['avg_fusion_time'] = (self.search_stats['avg_fusion_time'] * 0.9 + fusion_time * 0.1)
        
        return fused_results
    
    async def parallel_search(self, query: str, count: int = 10) -> List[SearchResult]:
        """Main simplified parallel search - Exact + Vector only"""
        total_start = time.time()
        
        print(f"🔍 Simplified Parallel Search: '{query}'")
        print("⚡ Running Exact + Vector search in parallel...")
        
        # Run only exact and vector searches
        exact_task = self.exact_search_async(query, count)
        vector_task = self.vector_search_async(query, count * 2)
        
        # Wait for both to complete
        exact_results, vector_results = await asyncio.gather(
            exact_task, vector_task
        )
        
        print(f"📊 Results: Exact={len(exact_results)}, Vector={len(vector_results)}")
        
        # Simple fusion
        fused_results = self.simple_fusion(exact_results, vector_results)
        
        # Update stats
        total_time = time.time() - total_start
        self.search_stats['total_searches'] += 1
        self.search_stats['avg_total_time'] = (self.search_stats['avg_total_time'] * 0.9 + total_time * 0.1)
        
        print(f"⚡ Total time: {total_time*1000:.1f}ms")
        print(f"🎯 Fused results: {len(fused_results[:count])}")
        
        return fused_results[:count]
    
    def search(self, query: str, count: int = 10) -> List[SearchResult]:
        """Synchronous wrapper"""
        return asyncio.run(self.parallel_search(query, count))
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'total_searches': self.search_stats['total_searches'],
            'avg_exact_time_ms': self.search_stats['avg_exact_time'] * 1000,
            'avg_vector_time_ms': self.search_stats['avg_vector_time'] * 1000,
            'avg_fusion_time_ms': self.search_stats['avg_fusion_time'] * 1000,
            'avg_total_time_ms': self.search_stats['avg_total_time'] * 1000,
            'search_mode': 'simplified_exact_vector',
            'score_range': '0.0 - 1.0 (normalized)'
        }
    
    def clear_cache(self):
        """Clear embedding cache"""
        self._get_embedding_cached.cache_clear()
        print("🧹 Cache cleared")


def test_simplified_search():
    """Test the simplified parallel search"""
    
    print("🚀 SIMPLIFIED PARALLEL SEARCH TEST")
    print("="*60)
    print("🎯 Search Strategy: Exact + Vector only")
    print("📏 Score Range: 0.0 - 1.0 (normalized)")
    print("="*60)
    
    search_engine = SimplifiedParallelSearch()
    
    test_queries = [
        "gas torch",
        "RAD64002019",
        "Miller welding equipment", 
        "safety regulator",
        "torch ABC123",
        "welding helmet"
    ]
    
    for query in test_queries:
        print(f"\n{'='*40}")
        print(f"🔍 Testing: '{query}'")
        print(f"{'='*40}")
        
        try:
            results = search_engine.search(query, count=5)
            
            if results:
                print(f"📋 Top {len(results)} results:")
                for i, result in enumerate(results, 1):
                    print(f"   {i}. {result.search_type.upper()}: {result.id}")
                    print(f"      Score: {result.score:.3f} (normalized 0-1)")
                    print(f"      Product: {result.payload.get('shortDescription_airgas_text', 'N/A')[:60]}...")
                    print()
            else:
                print("   ❌ No results found")
        
        except Exception as e:
            print(f"   ❌ Search failed: {e}")
    
    # Show performance stats
    print(f"\n{'='*60}")
    print("📊 PERFORMANCE STATISTICS")
    print(f"{'='*60}")
    stats = search_engine.get_performance_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.1f}")
        else:
            print(f"   {key}: {value}")


if __name__ == "__main__":
    test_simplified_search()
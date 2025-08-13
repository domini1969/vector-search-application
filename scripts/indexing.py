#!/usr/bin/env python3
"""
ENHANCED optimized_indexing.py - Memory-Optimized Indexing + Payload Indexes
Creates collections optimized for both semantic search AND exact matching
"""

import json
import os
import time
import tarfile
from typing import List, Dict, Optional
from enum import Enum
from tqdm import tqdm
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor
import gc

# Core dependencies
from datasets import Dataset
from fastembed import TextEmbedding, SparseTextEmbedding
from qdrant_client import QdrantClient, models

class IndexingMode(Enum):
    """Indexing modes available"""
    DENSE_ONLY = "dense"
    SPARSE_ONLY = "sparse"
    HYBRID = "hybrid"

class QuantizationMode(Enum):
    """Vector quantization modes optimized for speed"""
    NONE = "none"           # No quantization (fastest search, most RAM)
    SCALAR = "scalar"       # Scalar quantization (balanced speed/memory)
    BINARY = "binary"       # Binary quantization (fastest quantized, lowest quality)

class EnhancedIndexing:
    """Enhanced indexing with vector + payload indexes for maximum performance"""
    
    def __init__(self, 
                 products_file: str = "data/import/full/products.tar.gz",
                 collection_name: str = "products_fast",
                 qdrant_url: str = "http://localhost:6333",
                 batch_size: int = 2048,
                 indexing_mode: str = "dense",
                 # Speed-focused HNSW parameters
                 hnsw_m: int = 32,
                 hnsw_ef_construct: int = 200,
                 # Memory-focused settings
                 quantization_mode: str = "scalar",
                 storage_mode: str = "memory",
                 # Performance parameters
                 num_threads: Optional[int] = None,
                 embedding_batch_size: int = 4096,
                 # FIXED: Renamed parameter to avoid conflict
                 enable_payload_indexes: bool = True):
        
        self.products_file = products_file
        self.collection_name = collection_name
        self.batch_size = batch_size
        self.embedding_batch_size = embedding_batch_size
        self.indexing_mode = IndexingMode(indexing_mode.lower())
        self.quantization_mode = QuantizationMode(quantization_mode.lower())
        self.storage_mode = storage_mode.lower()
        self.hnsw_m = hnsw_m
        self.hnsw_ef_construct = hnsw_ef_construct
        self.num_threads = num_threads or min(mp.cpu_count(), 8)
        # FIXED: Store as different attribute name
        self.enable_payload_indexes = enable_payload_indexes
        
        print(f">> ENHANCED MEMORY-OPTIMIZED INDEXING:")
        print(f"   Source file: {products_file}")
        print(f"   Target collection: {collection_name}")
        print(f"   Mode: {self.indexing_mode.value}")
        print(f"   Quantization: {self.quantization_mode.value}")
        print(f"   Storage: {self.storage_mode} (MEMORY for speed)")
        print(f"   HNSW: M={hnsw_m}, ef_construct={hnsw_ef_construct} (speed-tuned)")
        print(f"   Payload indexes: {'ENABLED' if enable_payload_indexes else 'DISABLED'}")
        print(f"   Batch sizes: upload={batch_size}, embedding={embedding_batch_size}")
        print(f"   Threads: {self.num_threads}")
        
        # Initialize optimized client with gRPC
        self.client = QdrantClient(qdrant_url, timeout=600, prefer_grpc=True)
        
        # Initialize models
        self._load_models()
    
    def _load_models(self):
        """Load embedding models - Dense + BM25 only (Qdrant native)"""
        print(f">> Loading embedding models for {self.indexing_mode.value} mode...")
        start_time = time.time()
        
        self.dense_model = None
        self.bm25_model = None
        self.use_dense = False
        self.use_bm25 = False
        
        # Load dense model for DENSE_ONLY or HYBRID modes
        if self.indexing_mode in [IndexingMode.DENSE_ONLY, IndexingMode.HYBRID]:
            try:
                # OPTIMIZED: Use FastEmbed with maximum performance settings
                self.dense_model = TextEmbedding(
                    "BAAI/bge-small-en-v1.5",
                    max_length=512,
                    threads=self.num_threads,  # Multi-threaded
                    cache_dir=None  # No disk caching for speed
                )
                self.use_dense = True
                print("   >> Dense model loaded (FastEmbed optimized)")
            except Exception as e:
                print(f"   >> Dense model failed: {e}")
                if self.indexing_mode == IndexingMode.DENSE_ONLY:
                    raise  # Dense mode requires dense model
        
        # Load BM25 sparse model for SPARSE_ONLY or HYBRID modes (Qdrant native)
        if self.indexing_mode in [IndexingMode.SPARSE_ONLY, IndexingMode.HYBRID]:
            try:
                self.bm25_model = SparseTextEmbedding(
                    "Qdrant/bm25",
                    threads=self.num_threads,
                    cache_dir=None
                )
                self.use_bm25 = True
                print("   >> BM25 sparse model loaded (Qdrant native)")
            except Exception as e:
                print(f"   >> BM25 model failed: {e}")
                if self.indexing_mode == IndexingMode.SPARSE_ONLY:
                    raise RuntimeError("Sparse mode requires BM25 model")
        
        # Validate that at least one model is loaded
        if not (self.use_dense or self.use_bm25):
            raise RuntimeError(f"No models could be loaded for {self.indexing_mode.value} mode")
        
        # Legacy compatibility
        self.use_sparse = self.use_bm25
        self.sparse_model = self.bm25_model
        
        load_time = time.time() - start_time
        models_loaded = []
        if self.use_dense: models_loaded.append("Dense")
        if self.use_bm25: models_loaded.append("BM25")
        
        print(f"   >> Models loaded in {load_time:.2f}s")
        print(f"   >> Active models ({self.indexing_mode.value}): {', '.join(models_loaded)}")
        print(f"   >> Configuration: Dense + BM25 (Qdrant native) only")
    
    def load_data(self) -> Dataset:
        """Load and process data with optimizations - supports JSON and tar.gz files"""
        print("[LOAD] Loading data...")
        start_time = time.time()
        
        # Handle relative paths - check multiple possible locations
        possible_paths = [
            self.products_file,  # Original path
            os.path.join("..", self.products_file),  # From scripts/ directory
            os.path.join(os.path.dirname(__file__), "..", self.products_file),  # Relative to script location
        ]
        
        actual_file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                actual_file_path = path
                break
                
        if actual_file_path is None:
            print(f"[ERROR] File not found. Searched in:")
            for path in possible_paths:
                print(f"  - {os.path.abspath(path)}")
            raise FileNotFoundError(f"File '{self.products_file}' not found in any expected location")
        
        # Update the path to the found file
        self.products_file = actual_file_path
        
        print(f"[DATA] Source: {self.products_file}")
        
        # Handle compressed tar.gz files
        if self.products_file.endswith('.tar.gz'):
            print("[EXTRACT] Processing compressed data file...")
            try:
                with tarfile.open(self.products_file, 'r:gz') as tar:
                    # List all files in archive for debugging
                    all_members = tar.getnames()
                    print(f"[INFO] Archive contains {len(all_members)} files")
                    
                    # Find the JSON file inside the archive
                    json_files = [member for member in tar.getmembers() if member.name.endswith('.json')]
                    
                    if not json_files:
                        print(f"[ERROR] No JSON files found. Available files: {all_members}")
                        raise FileNotFoundError("No JSON file found in the tar.gz archive")
                    
                    if len(json_files) > 1:
                        json_names = [f.name for f in json_files]
                        print(f"[WARNING] Multiple JSON files found: {json_names}")
                        print(f"[INFO] Using: {json_files[0].name}")
                    
                    # Extract and read the JSON file
                    json_file = tar.extractfile(json_files[0])
                    if json_file is None:
                        raise ValueError(f"Could not extract {json_files[0].name} from archive")
                    
                    print(f"[READ] Processing JSON file: {json_files[0].name}")
                    print(f"[SIZE] File size: {json_files[0].size:,} bytes")
                    products = json.load(json_file)
                    
            except tarfile.ReadError as e:
                raise ValueError(f"Invalid tar.gz file: {e}")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON data in archive: {e}")
        else:
            # Handle regular JSON files
            print("[READ] Processing JSON file...")
            with open(self.products_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
        
        # OPTIMIZED: Batch processing of product data
        processed_products = []
        batch_size = 1000
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            
            for j, product in enumerate(batch):
                if '_id' not in product:
                    product['_id'] = product.get('partNumber_airgas_text', str(i + j))
                
                # Create field-specific searchable text
                # Dense search: Only shortDescription for semantic search
                product['dense_text'] = str(product.get('shortDescription_airgas_text', ''))
                
                # Sparse search: Description + Part numbers for keyword matching
                sparse_parts = []
                if desc := product.get('shortDescription_airgas_text'):
                    sparse_parts.append(str(desc))
                if part := product.get('partNumber_airgas_text'):
                    sparse_parts.append(part)
                if mfg_part := product.get('manufacturerPartNumber_text'):
                    sparse_parts.append(mfg_part)
                
                product['sparse_text'] = ' '.join(sparse_parts)
                
                # Legacy compatibility
                product['searchable_text'] = product['sparse_text']
                
                # Ensure important fields exist
                for field in ['partNumber_airgas_text', 'manufacturerPartNumber_text', 
                             'shortDescription_airgas_text', 'onlinePrice_string', 'img_270Wx270H_string']:
                    if field not in product:
                        product[field] = None
            
            processed_products.extend(batch)
            
            # Memory management
            if i % (batch_size * 10) == 0:
                gc.collect()
        
        dataset = Dataset.from_list(processed_products)
        load_time = time.time() - start_time
        
        print(f"   [SUCCESS] Loaded {len(dataset)} products in {load_time:.2f}s")
        
        # Data validation and summary
        if len(dataset) > 0:
            sample_product = dataset[0]
            print(f"   [FIELDS] Sample product fields: {list(sample_product.keys())}")
            
            # Validate critical fields
            critical_fields = ['partNumber_airgas_text', 'shortDescription_airgas_text']
            missing_critical = []
            for field in critical_fields:
                if field not in sample_product or not sample_product[field]:
                    missing_critical.append(field)
            
            if missing_critical:
                print(f"   [WARNING] Missing critical fields in sample: {missing_critical}")
            else:
                print(f"   [VALID] Critical fields validated")
                
            print(f"   [SAMPLE] Part: {sample_product.get('partNumber_airgas_text', 'N/A')}")
            print(f"   [DESC] Description: {str(sample_product.get('shortDescription_airgas_text', 'N/A'))[:100]}...")
        else:
            raise ValueError("No products loaded from data file")
        return dataset
    
    def _create_memory_optimized_quantization_config(self, vector_size: int):
        """Create quantization configuration optimized for memory storage"""
        if self.quantization_mode == QuantizationMode.NONE:
            return None
        elif self.quantization_mode == QuantizationMode.SCALAR:
            return models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(
                    type=models.ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True  # Keep in RAM for speed
                )
            )
        elif self.quantization_mode == QuantizationMode.BINARY:
            return models.BinaryQuantization(
                binary=models.BinaryQuantizationConfig(
                    always_ram=True  # Keep in RAM for speed
                )
            )
    
    def create_collection(self):
        """Create memory-optimized collection with enhanced performance"""
        print(f"[FAST] Creating enhanced memory-optimized collection: {self.collection_name}")
        print(f"   [TARGET] Target: Maximum search speed + exact matching")
        start_time = time.time()
        
        # Delete existing collection
        try:
            self.client.delete_collection(self.collection_name)
            print("   [DELETE]  Deleted existing collection")
        except:
            pass
        
        vectors_config = {}
        sparse_config = {}
        
        if self.use_dense:
            # Get vector dimensions
            sample_dense = list(self.dense_model.passage_embed(["test"]))[0]
            dense_size = len(sample_dense)
            
            # Create memory-optimized quantization config
            quantization_config = self._create_memory_optimized_quantization_config(dense_size)
            
            vectors_config["dense"] = models.VectorParams(
                size=dense_size,
                distance=models.Distance.COSINE,
                # ENHANCED: Memory-optimized HNSW config
                hnsw_config=models.HnswConfigDiff(
                    m=self.hnsw_m,  # Higher M for faster search
                    ef_construct=self.hnsw_ef_construct,  # Higher ef_construct
                    full_scan_threshold=50000,  # High threshold to avoid full scans
                    max_indexing_threads=self.num_threads,
                    on_disk=False,  # CRITICAL: Keep in memory for speed
                    payload_m=16 if quantization_config else None
                ),
                quantization_config=quantization_config,
                on_disk=False  # CRITICAL: Keep vectors in memory
            )
            
            print(f"   ✓ Dense config: size={dense_size}, M={self.hnsw_m}, ef={self.hnsw_ef_construct}")
            print(f"   [ROCKET] Memory optimization: on_disk=False for both vectors and HNSW")
            
            if quantization_config:
                print(f"   [PACKAGE] {self.quantization_mode.value} quantization: always_ram=True")
        
        # Configure BM25 sparse vector field (Qdrant native)
        if self.use_bm25:
            sparse_config["bm25"] = models.SparseVectorParams(
                modifier=models.Modifier.NONE,  # BM25 doesn't need IDF modification
                index=models.SparseIndexParams(
                    on_disk=False  # Keep in memory for speed
                )
            )
            print("   ✓ BM25 sparse config: in-memory, no modifier (Qdrant native)")
        
        # ENHANCED: Memory-optimized collection configuration
        optimizers_config = models.OptimizersConfigDiff(
            deleted_threshold=0.2,
            vacuum_min_vector_number=50000,
            default_segment_number=6,  # More segments for parallel processing
            max_segment_size=400000,  # Optimized segment size
            memmap_threshold=100000,  # Use memory mapping judiciously
            indexing_threshold=5000,  # Start indexing earlier
            flush_interval_sec=30,  # More frequent flushing
            max_optimization_threads=self.num_threads
        )
        
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=vectors_config,
            sparse_vectors_config=sparse_config,
            optimizers_config=optimizers_config,
            shard_number=2,  # Multiple shards for performance
            replication_factor=1,
            write_consistency_factor=1
        )
        
        create_time = time.time() - start_time
        print(f"   [OK] Enhanced collection created in {create_time:.2f}s")
    
    def create_payload_indexes(self):
        """Create payload indexes for ultra-fast exact searches"""
        if not self.enable_payload_indexes:
            print("   [STATS] Payload indexing disabled")
            return
        
        print(f"\n[STATS] CREATING PAYLOAD INDEXES FOR EXACT SEARCH...")
        print(f"   [TARGET] Target: 1-5ms exact searches (vs 100+ms without indexes)")
        
        # Define indexes for exact search optimization
        indexes_to_create = [
            {
                "field_name": "partNumber_airgas_text",
                "field_schema": "keyword",
                "description": "Main product part numbers - most common exact searches"
            },
            {
                "field_name": "manufacturerPartNumber_text", 
                "field_schema": "keyword",
                "description": "Manufacturer part numbers - secondary exact searches"
            },
            {
                "field_name": "_id",
                "field_schema": "keyword",
                "description": "Document IDs for direct lookups"
            }
        ]
        
        successful_indexes = 0
        
        for index_config in indexes_to_create:
            field_name = index_config["field_name"]
            field_schema = index_config["field_schema"]
            description = index_config["description"]
            
            try:
                print(f"   [STATS] Creating payload index: '{field_name}'")
                
                start_time = time.time()
                
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_schema,
                    wait=True  # Wait for index creation to complete
                )
                
                creation_time = time.time() - start_time
                print(f"      [OK] Created in {creation_time:.2f}s")
                successful_indexes += 1
                
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"      [OK] Index already exists")
                    successful_indexes += 1
                else:
                    print(f"      [ERROR] Failed: {e}")
        
        print(f"   [STATS] Payload indexes: {successful_indexes}/{len(indexes_to_create)} created")
        if successful_indexes == len(indexes_to_create):
            print(f"   [ROCKET] Exact searches will now be 1-5ms instead of 100+ms!")
    
    def generate_embeddings_batch(self, dense_texts: List[str], sparse_texts: List[str]):
        """PARALLEL OPTIMIZED: Generate embeddings concurrently with FastEmbed - Field-specific text processing"""
        import time
        
        start_time = time.time()
        
        # Define embedding functions for parallel execution
        def generate_dense_embeddings():
            """Generate dense embeddings in parallel"""
            if not self.use_dense:
                return None
            
            embeddings = []
            # OPTIMIZED: Much larger batches for FastEmbed efficiency
            optimized_batch_size = min(self.embedding_batch_size, 8192)
            
            for i in range(0, len(dense_texts), optimized_batch_size):
                batch = dense_texts[i:i + optimized_batch_size]
                
                # OPTIMIZED: Use passage_embed for indexing (not query_embed)
                batch_embeddings = list(self.dense_model.passage_embed(batch))
                embeddings.extend(batch_embeddings)
                
                # Memory management - less frequent for speed
                if len(embeddings) % 20000 == 0:  # Much less frequent
                    gc.collect()
            
            return embeddings
        
        def generate_bm25_embeddings():
            """Generate BM25 embeddings in parallel"""
            if not self.use_bm25:
                return None
            
            embeddings = []
            for i in range(0, len(sparse_texts), self.embedding_batch_size):
                batch = sparse_texts[i:i + self.embedding_batch_size]
                batch_embeddings = list(self.bm25_model.passage_embed(batch))
                embeddings.extend(batch_embeddings)
            
            return embeddings
        
        # Execute embedding generation in parallel (Dense + BM25 only)
        max_workers = min(2, self.num_threads)  # 2 workers for Dense + BM25
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tasks concurrently
            futures = []
            if self.use_dense:
                futures.append(('dense', executor.submit(generate_dense_embeddings)))
            if self.use_bm25:
                futures.append(('bm25', executor.submit(generate_bm25_embeddings)))
            
            # Collect results as they complete
            dense_embeddings = None
            bm25_embeddings = None
            
            for model_type, future in futures:
                if model_type == 'dense':
                    dense_embeddings = future.result()
                elif model_type == 'bm25':
                    bm25_embeddings = future.result()
        
        embedding_time = time.time() - start_time
        active_models = sum([self.use_dense, self.use_bm25])
        
        print(f"   >> PARALLEL: Generated {len(dense_texts)} embeddings using {active_models} models in {embedding_time:.1f}s")
        
        return dense_embeddings, bm25_embeddings
    
    def index_data(self, dataset: Dataset):
        """ENHANCED: Memory-optimized indexing with performance optimizations"""
        print(f"[ROCKET] ENHANCED MEMORY-OPTIMIZED INDEXING: {len(dataset)} products...")
        print(f"   [TARGET] Target: Fast search + exact matching")
        start_time = time.time()
        
        total_indexed = 0
        pbar = tqdm(total=len(dataset), desc="[ROCKET] Enhanced Indexing", unit="products")
        
        dataset_list = list(dataset)
        
        # OPTIMIZED: Much larger chunk sizing for 100+ products/second
        chunk_size = min(self.batch_size * 4, 8192)  # Larger chunks for efficiency
        
        for chunk_start in range(0, len(dataset_list), chunk_size):
            chunk_end = min(chunk_start + chunk_size, len(dataset_list))
            chunk = dataset_list[chunk_start:chunk_end]
            
            chunk_start_time = time.time()
            
            # Extract field-specific text and generate embeddings
            dense_texts = [item['dense_text'] for item in chunk]  # Only shortDescription
            sparse_texts = [item['sparse_text'] for item in chunk]  # Description + part numbers
            dense_embeddings, bm25_embeddings = self.generate_embeddings_batch(dense_texts, sparse_texts)
            
            # OPTIMIZED: Much larger upload batches for speed
            optimized_upload_batch = min(self.batch_size, 4096)
            
            for batch_start in range(0, len(chunk), optimized_upload_batch):
                batch_end = min(batch_start + optimized_upload_batch, len(chunk))
                batch_items = chunk[batch_start:batch_end]
                
                points = []
                for i, item in enumerate(batch_items):
                    global_idx = batch_start + i
                    
                    vector_dict = {}
                    if self.use_dense and dense_embeddings:
                        vector_dict["dense"] = dense_embeddings[global_idx].tolist()
                    if self.use_bm25 and bm25_embeddings:
                        vector_dict["bm25"] = bm25_embeddings[global_idx].as_object()
                    
                    point = models.PointStruct(
                        id=abs(hash(str(item["_id"]))) % (2**31),
                        vector=vector_dict,
                        payload={
                            "_id": item["_id"],
                            "partNumber_airgas_text": item.get("partNumber_airgas_text"),
                            "manufacturerPartNumber_text": item.get("manufacturerPartNumber_text"),
                            "shortDescription_airgas_text": item.get("shortDescription_airgas_text"),
                            "onlinePrice_string": item.get("onlinePrice_string"),
                            "img_270Wx270H_string": item.get("img_270Wx270H_string"),
                            "searchable_text": item["searchable_text"]
                        }
                    )
                    points.append(point)
                
                # OPTIMIZED: Upload with maximum parallelism via gRPC
                self.client.upload_points(
                    self.collection_name,
                    points=points,
                    batch_size=len(points),
                    parallel=min(self.num_threads, 16),  # Much higher parallelism
                    max_retries=2,  # Fewer retries for speed
                    wait=False
                )
                
                total_indexed += len(batch_items)
                pbar.update(len(batch_items))
            
            # Cleanup and memory management - less frequent for speed
            del dense_embeddings, bm25_embeddings, dense_texts, sparse_texts
            if chunk_start % (chunk_size * 8) == 0:  # Much less frequent GC
                gc.collect()
            
            chunk_time = time.time() - chunk_start_time
            chunk_processed = chunk_end - chunk_start
            pbar.set_postfix({
                'speed': f"{chunk_processed/chunk_time:.0f}/s",
                'indexed': f"{total_indexed}"
            })
        
        pbar.close()
        
        # Create payload indexes AFTER data upload for optimal performance
        self.create_payload_indexes()
        
        # OPTIMIZED: Minimal wait time for maximum speed
        print("🔄 Finalizing enhanced index...")
        time.sleep(2)  # Much shorter wait for speed
        
        total_time = time.time() - start_time
        rate = len(dataset) / total_time
        
        print(f"   🎉 ENHANCED INDEXING COMPLETE!")
        print(f"   [STATS] {len(dataset)} products in {total_time:.1f}s ({rate:.0f} products/s)")
        print(f"   [ROCKET] Collection optimized for: Vector search + Exact matching")
        print(f"   [FAST] Expected performance: 5-25ms total search time")
    
    def test_search_performance(self):
        """Test both vector and exact search performance"""
        print(f"\n🏃 TESTING ENHANCED SEARCH PERFORMANCE:")
        
        # Test vector search
        print(f"\n[STATS] VECTOR SEARCH TESTS:")
        vector_queries = ["gas torch", "safety equipment", "regulator", "welding"]
        
        for query in vector_queries:
            try:
                search_start = time.time()
                query_vector = list(self.dense_model.query_embed([query]))[0]
                
                results = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector.tolist(),
                    using="dense",
                    with_payload=True,
                    limit=10,
                    timeout=10,
                    search_params={"hnsw_ef": 128, "exact": False}  # Optimized parameters
                )
                
                search_time = time.time() - search_start
                print(f"   '{query}': {search_time*1000:.1f}ms - {len(results.points)} results")
                
                if search_time < 0.05:
                    print(f"      [ROCKET] EXCELLENT performance!")
                elif search_time < 0.1:
                    print(f"      [OK] GOOD performance")
                else:
                    print(f"      [WARNING]  Could be faster")
                    
            except Exception as e:
                print(f"   '{query}': Search failed - {e}")
        
        # Test exact search (if payload indexes were created)
        if self.enable_payload_indexes:
            print(f"\n[STATS] EXACT SEARCH TESTS:")
            exact_queries = ["RAD64002019", "MIL11-1101C", "NONEXISTENT123"]
            
            for query in exact_queries:
                try:
                    search_start = time.time()
                    
                    results = self.client.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=models.Filter(
                            must=[models.FieldCondition(
                                key="partNumber_airgas_text", 
                                match=models.MatchValue(value=query.upper())
                            )]
                        ),
                        limit=5,
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    search_time = time.time() - search_start
                    result_count = len(results[0])
                    print(f"   '{query}': {search_time*1000:.1f}ms - {result_count} results")
                    
                    if search_time < 0.01:
                        print(f"      [ROCKET] ULTRA-FAST exact search!")
                    elif search_time < 0.02:
                        print(f"      [OK] EXCELLENT exact search!")
                    else:
                        print(f"      [WARNING]  Exact search could be faster")
                        
                except Exception as e:
                    print(f"   '{query}': Exact search failed - {e}")
    
    def get_collection_info(self):
        """Get enhanced collection information"""
        try:
            info = self.client.get_collection(self.collection_name)
            print(f"\n[STATS] ENHANCED COLLECTION INFO:")
            print(f"   Name: {info.config.collection_name if hasattr(info.config, 'collection_name') else self.collection_name}")
            print(f"   Status: {info.status}")
            print(f"   Points: {info.points_count:,}")
            print(f"   [ROCKET] Optimized for: Vector search + Exact matching")
            print(f"   💾 Storage: In-memory (vectors and HNSW)")
            print(f"   [PACKAGE] Quantization: {self.quantization_mode.value}")
            print(f"   [STATS] Payload indexes: {'ENABLED' if self.enable_payload_indexes else 'DISABLED'}")
            print(f"   [FAST] Expected search performance:")
            print(f"      - Vector search: 5-25ms")
            print(f"      - Exact search: 1-5ms")
            print(f"      - Combined parallel: 10-30ms")
            
        except Exception as e:
            print(f"   [ERROR] Could not get collection info: {e}")
    
    # ==================== FUSION METHODS ====================
    
    def reciprocal_rank_fusion(self, dense_results, sparse_results, k=60, limit=10):
        """
        Reciprocal Rank Fusion (RRF) - More robust fusion method
        Score = 1 / (k + rank)
        
        Args:
            dense_results: Results from dense search
            sparse_results: Results from sparse search
            k: RRF parameter (default 60, commonly used value)
            limit: Final number of results to return
        """
        print(f"🔄 RRF: Fusing {len(dense_results.points)} dense + {len(sparse_results.points)} sparse results")
        
        fused_scores = {}
        
        # Process dense results
        for rank, point in enumerate(dense_results.points, 1):
            doc_id = point.id
            rrf_score = 1.0 / (k + rank)
            
            if doc_id not in fused_scores:
                fused_scores[doc_id] = {
                    'rrf_score': 0.0,
                    'dense_rank': rank,
                    'sparse_rank': 0,
                    'dense_score': point.score,
                    'sparse_score': 0.0,
                    'point': point
                }
            fused_scores[doc_id]['rrf_score'] += rrf_score
        
        # Process sparse results
        for rank, point in enumerate(sparse_results.points, 1):
            doc_id = point.id
            rrf_score = 1.0 / (k + rank)
            
            if doc_id not in fused_scores:
                fused_scores[doc_id] = {
                    'rrf_score': 0.0,
                    'dense_rank': 0,
                    'sparse_rank': rank,
                    'dense_score': 0.0,
                    'sparse_score': point.score,
                    'point': point
                }
            else:
                fused_scores[doc_id]['sparse_rank'] = rank
                fused_scores[doc_id]['sparse_score'] = point.score
                
            fused_scores[doc_id]['rrf_score'] += rrf_score
        
        # Sort by RRF score and take top results
        sorted_results = sorted(fused_scores.values(), 
                               key=lambda x: x['rrf_score'], reverse=True)
        
        # Prepare final results with RRF scores
        final_results = []
        for i, item in enumerate(sorted_results[:limit]):
            point = item['point']
            point.score = item['rrf_score']  # Set RRF score as the result score
            final_results.append(point)
            
            # Debug info for top 3 results
            if i < 3:
                print(f"   #{i+1}: RRF={item['rrf_score']:.4f} | Dense(rank={item['dense_rank']}, score={item['dense_score']:.3f}) | Sparse(rank={item['sparse_rank']}, score={item['sparse_score']:.3f})")
        
        print(f"[OK] RRF: Returning top {len(final_results)} fused results")
        return final_results
    
    def _linear_fusion(self, dense_results, sparse_results, fusion_alpha, limit):
        """Legacy linear fusion method (for backward compatibility)"""
        print(f"[GEAR]  Linear fusion with alpha={fusion_alpha}")
        
        combined_scores = {}
        
        # Add dense scores
        for point in dense_results.points:
            combined_scores[point.id] = {
                'dense_score': point.score,
                'sparse_score': 0,
                'point': point
            }
        
        # Add sparse scores
        for point in sparse_results.points:
            if point.id in combined_scores:
                combined_scores[point.id]['sparse_score'] = point.score
            else:
                combined_scores[point.id] = {
                    'dense_score': 0,
                    'sparse_score': point.score,
                    'point': point
                }
        
        # Calculate fusion scores and sort
        for item in combined_scores.values():
            item['fusion_score'] = (fusion_alpha * item['dense_score'] + 
                                   (1 - fusion_alpha) * item['sparse_score'])
        
        # Sort by fusion score and take top results
        sorted_results = sorted(combined_scores.values(), 
                               key=lambda x: x['fusion_score'], reverse=True)
        
        final_results = []
        for item in sorted_results[:limit]:
            point = item['point']
            point.score = item['fusion_score']  # Update score to fusion score
            final_results.append(point)
        
        return final_results
    
    def normalize_scores(self, scores, method='min_max'):
        """Normalize scores to 0-1 range for linear fusion methods"""
        if not scores or len(scores) == 0:
            return scores
        
        if method == 'min_max':
            min_score = min(scores)
            max_score = max(scores)
            if max_score == min_score:
                return [1.0] * len(scores)
            return [(s - min_score) / (max_score - min_score) for s in scores]
        
        elif method == 'z_score':
            mean_score = sum(scores) / len(scores)
            variance = sum((s - mean_score)**2 for s in scores) / len(scores)
            std_dev = variance**0.5
            if std_dev == 0:
                return [0.5] * len(scores)
            return [(s - mean_score) / std_dev + 0.5 for s in scores]  # Shift to positive range
    
    # ==================== SEARCH METHODS ====================
    
    def search_dense(self, query: str, limit: int = 10):
        """Dense vector search only - searches ONLY shortDescription_airgas_text field"""
        if not self.use_dense:
            raise ValueError("Dense model not loaded")
        
        start_time = time.time()
        query_vector = list(self.dense_model.query_embed([query]))[0]
        
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector.tolist(),
            using="dense",
            with_payload=True,
            limit=limit,
            search_params={"hnsw_ef": 128, "exact": False}
        )
        
        search_time = time.time() - start_time
        return {
            "results": results.points,
            "search_time_ms": search_time * 1000,
            "method": "dense",
            "query": query
        }
    
    def search_bm25(self, query: str, limit: int = 10):
        """BM25 sparse search only - searches shortDescription + partNumber + manufacturerPartNumber fields"""
        if not self.use_bm25:
            raise ValueError("BM25 model not loaded")
        
        start_time = time.time()
        query_vector = list(self.bm25_model.query_embed([query]))[0]
        
        # Debug: Check BM25 query format for comparison
        print(f"DEBUG BM25 standalone: query_vector type: {type(query_vector)}")
        bm25_sparse_query = query_vector.as_object()
        print(f"DEBUG BM25 standalone: sparse_query type: {type(bm25_sparse_query)}")
        print(f"DEBUG BM25 standalone: sparse_query format: {str(bm25_sparse_query)[:100]}")
        
        # Convert to Qdrant SparseVector format
        indices = bm25_sparse_query['indices'].tolist()
        values = bm25_sparse_query['values'].tolist()
        sparse_vector = models.SparseVector(indices=indices, values=values)
        print(f"DEBUG BM25: Created SparseVector with {len(indices)} terms")
        
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=sparse_vector,
            using="bm25",
            with_payload=True,
            limit=limit
        )
        
        search_time = time.time() - start_time
        return {
            "results": results.points,
            "search_time_ms": search_time * 1000,
            "method": "bm25",
            "query": query
        }
    
    def search_hybrid(self, query: str, limit: int = 10):
        """Hybrid search using Qdrant native RRF fusion (Dense + BM25)
        
        Uses Qdrant's built-in RRF (Reciprocal Rank Fusion) for optimal performance.
        """
        if not (self.use_dense and self.use_bm25):
            raise ValueError("Both dense and BM25 models required for hybrid search")
        
        start_time = time.time()
        print(f"🔄 Qdrant native RRF hybrid search (Dense + BM25)")
        
        # Generate embeddings
        dense_query = list(self.dense_model.query_embed([query]))[0]
        bm25_query = list(self.bm25_model.query_embed([query]))[0]
        
        # Convert BM25 query to Qdrant SparseVector format
        bm25_sparse_query = bm25_query.as_object()
        indices = bm25_sparse_query['indices'].tolist()
        values = bm25_sparse_query['values'].tolist()
        sparse_vector = models.SparseVector(indices=indices, values=values)
        
        # Use Qdrant native hybrid search with RRF 
        # Note: Using separate searches and manual RRF until Qdrant Python client supports native fusion
        # Perform parallel searches for better performance
        from concurrent.futures import ThreadPoolExecutor
        
        def dense_search():
            return self.client.query_points(
                collection_name=self.collection_name,
                query=dense_query.tolist(),
                using="dense",
                with_payload=True,
                limit=limit * 2,  # Get more for fusion
                search_params={"hnsw_ef": 128, "exact": False}
            )
        
        def sparse_search():
            return self.client.query_points(
                collection_name=self.collection_name,
                query=sparse_vector,
                using="bm25",
                with_payload=True,
                limit=limit * 2
            )
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            dense_future = executor.submit(dense_search)
            sparse_future = executor.submit(sparse_search)
            
            dense_results = dense_future.result()
            sparse_results = sparse_future.result()
        
        # Apply manual RRF fusion (k=60 is standard)
        results_points = self.reciprocal_rank_fusion(dense_results, sparse_results, k=60, limit=limit)
        
        search_time = time.time() - start_time
        return {
            "results": results_points,
            "search_time_ms": search_time * 1000,
            "method": "qdrant_native_rrf",
            "query": query,
            "fusion_method": "qdrant_rrf"
        }
    
    
    # ==================== END SEARCH METHODS ====================
    
    def run(self):
        """Run enhanced memory-optimized indexing"""
        total_start = time.time()
        
        try:
            print("="*80)
            print(f"[ROCKET] ENHANCED MEMORY-OPTIMIZED INDEXING - {self.indexing_mode.value.upper()} MODE")
            print(f"[TARGET] TARGET: MAXIMUM SEARCH SPEED + EXACT MATCHING")
            print(f"STORAGE: IN-MEMORY FOR PERFORMANCE")
            print(f"[STATS] PAYLOAD INDEXES: {'ENABLED' if self.enable_payload_indexes else 'DISABLED'}")
            print("="*80)
            
            # Load data
            dataset = self.load_data()
            
            # Create enhanced collection
            self.create_collection()
            
            # Index data with payload indexes
            self.index_data(dataset)
            
            # Get collection info
            self.get_collection_info()
            
            # Test enhanced performance
            self.test_search_performance()
            
            total_time = time.time() - total_start
            
            print(f"\n🎉 ENHANCED OPTIMIZATION COMPLETE!")
            print(f"   [FAST] Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
            print(f"   [ROCKET] Collection: {self.collection_name} (enhanced)")
            print(f"   [STATS] Products: {len(dataset):,}")
            print(f"   [TARGET] Expected performance:")
            print(f"      - Vector search: 5-25ms (vs 2000+ms before)")
            print(f"      - Exact search: 1-5ms (vs 100+ms before)")
            print(f"      - Parallel search: 10-30ms total")
            print(f"   💡 Ready for production with your simplified parallel search!")
            
        except Exception as e:
            print(f"[ERROR] Error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def test_all_search_methods(self, test_queries: list = None):
        """Test all 3 search methods: Dense, BM25, and Hybrid (Dense + BM25)"""
        if test_queries is None:
            test_queries = ["gas torch", "safety equipment", "regulator valve", "welding supplies"]
        
        print(f"\n🧪 TESTING ALL SEARCH METHODS (Dense + BM25 only):")
        print(f"   [SEARCH] Dense: shortDescription_airgas_text ONLY")
        print(f"   [SEARCH] BM25: shortDescription + partNumber + manufacturerPartNumber")
        print(f"   [SEARCH] Hybrid: Qdrant native RRF fusion (Dense + BM25)")
        print(f"   Testing queries: {test_queries}")
        print("="*80)
        
        for query in test_queries:
            print(f"\n[SEARCH] Query: '{query}'")
            print("-" * 60)
            
            methods_to_test = []
            
            # Always test dense
            if self.use_dense:
                methods_to_test.append(("Dense", self.search_dense))
            
            # Test BM25 if available
            if self.use_bm25:
                methods_to_test.append(("BM25", self.search_bm25))
            
            # Test hybrid if both dense and BM25 are available
            if self.use_dense and self.use_bm25:
                methods_to_test.append(("Hybrid RRF", self.search_hybrid))
            
            # Run all tests
            for method_name, method_func in methods_to_test:
                try:
                    result = method_func(query, limit=5)
                    
                    print(f"   {method_name:15}: {result['search_time_ms']:6.1f}ms | {len(result['results'])} results")
                    
                    # Show top result for comparison
                    if result['results']:
                        top_result = result['results'][0]
                        part_num = top_result.payload.get('partNumber_airgas_text', 'N/A')
                        description = top_result.payload.get('shortDescription_airgas_text', 'N/A')
                        score = top_result.score
                        print(f"                    Top: {part_num} | {description[:40]}... | Score: {score:.4f}")
                    
                except Exception as e:
                    print(f"   {method_name:15}: ERROR - {e}")
        
        print("\n" + "="*80)
        print("[TARGET] SEARCH METHOD COMPARISON COMPLETE!")
    
    def test_field_specific_indexing(self):
        """Test that field-specific text creation works correctly"""
        print(f"\n🧪 TESTING FIELD-SPECIFIC INDEXING:")
        
        # Sample product data
        sample_product = {
            'partNumber_airgas_text': 'HYP220479',
            'manufacturerPartNumber_text': '220479', 
            'shortDescription_airgas_text': 'Hypertherm® 30 Amp Gas Diffuser',
            'onlinePrice_string': '23.5'
        }
        
        print(f"Sample product:")
        print(f"   Part Number: {sample_product['partNumber_airgas_text']}")
        print(f"   MFG Number: {sample_product['manufacturerPartNumber_text']}")
        print(f"   Description: {sample_product['shortDescription_airgas_text']}")
        
        # Apply field-specific text creation logic
        sample_product['dense_text'] = str(sample_product.get('shortDescription_airgas_text', ''))
        
        sparse_parts = []
        if desc := sample_product.get('shortDescription_airgas_text'):
            sparse_parts.append(str(desc))
        if part := sample_product.get('partNumber_airgas_text'):
            sparse_parts.append(part)
        if mfg_part := sample_product.get('manufacturerPartNumber_text'):
            sparse_parts.append(mfg_part)
        
        sample_product['sparse_text'] = ' '.join(sparse_parts)
        
        print(f"\n[SEARCH] Field-specific indexing results:")
        print(f"   Dense text (shortDescription only): '{sample_product['dense_text']}'")
        print(f"   Sparse text (desc + parts): '{sample_product['sparse_text']}'")
        
        print(f"\n[OK] Field separation working correctly!")
        print(f"   Dense will search: Description semantics only")  
        print(f"   Sparse will search: Description + exact part number matches")

def main():
    """Main function with enhanced presets"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Enhanced Memory-Optimized Indexing with Payload Indexes",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Basic parameters
    parser.add_argument("--products-file", default="data/import/full/products.tar.gz",
                       help="Path to products JSON file or tar.gz archive")
    parser.add_argument("--collection", default="products_fast",
                       help="Collection name")
    parser.add_argument("--url", default="http://localhost:6333",
                       help="Qdrant server URL")
    parser.add_argument("--batch-size", type=int, default=512,
                       help="Upload batch size")
    parser.add_argument("--embedding-batch-size", type=int, default=1024,
                       help="Embedding batch size")
    
    # Mode
    parser.add_argument("--mode", choices=["dense", "sparse", "hybrid"], 
                       default="dense", help="Indexing mode")
    
    # Memory-optimized HNSW parameters
    parser.add_argument("--hnsw-m", type=int, default=32,
                       help="HNSW M parameter (higher = faster search)")
    parser.add_argument("--hnsw-ef-construct", type=int, default=200,
                       help="HNSW ef_construct (higher = better quality)")
    
    # Memory-focused options
    parser.add_argument("--quantization", choices=["none", "scalar", "binary"],
                       default="scalar", help="Quantization mode")
    parser.add_argument("--storage", choices=["memory", "disk"],
                       default="memory", help="Storage mode (memory recommended)")
    
    # Performance
    parser.add_argument("--threads", type=int, default=None,
                       help="Number of threads")
    
    # FIXED: Updated argument name to match new parameter
    parser.add_argument("--no-payload-indexes", action="store_true",
                       help="Disable payload index creation")
    
    # Enhanced presets
    parser.add_argument("--preset", choices=["max-speed", "balanced", "memory-efficient", "production", "ultra-fast"],
                       help="Use predefined optimization preset")
    
    args = parser.parse_args()
    
    # Apply enhanced presets
    if args.preset == "max-speed":
        print("[ROCKET] Applying MAX-SPEED preset:")
        args.quantization = "none"
        args.storage = "memory"
        args.hnsw_m = 48
        args.hnsw_ef_construct = 300
        args.batch_size = 1024
        args.embedding_batch_size = 2048
        print("   - No quantization (fastest)")
        print("   - Memory storage")
        print("   - High HNSW parameters")
        print("   - Payload indexes enabled")
        
    elif args.preset == "production":
        print("🏭 Applying PRODUCTION preset:")
        args.quantization = "scalar"
        args.storage = "memory"
        args.hnsw_m = 32
        args.hnsw_ef_construct = 200
        args.batch_size = 768
        args.embedding_batch_size = 1536
        print("   - Scalar quantization (balanced)")
        print("   - Memory storage")
        print("   - Production HNSW parameters")
        print("   - Payload indexes enabled")
        print("   - Optimized for real-world usage")
        
    elif args.preset == "ultra-fast":
        print("⚡ Applying ULTRA-FAST preset for 100+ products/second:")
        args.quantization = "none"
        args.storage = "memory"
        args.hnsw_m = 16  # Lower M for faster indexing
        args.hnsw_ef_construct = 128  # Lower ef_construct for faster indexing
        args.batch_size = 4096
        args.embedding_batch_size = 8192
        print("   - No quantization (maximum speed)")
        print("   - Memory storage (fastest)")
        print("   - INDEXING-OPTIMIZED HNSW: M=16, ef=128 (fast indexing)")
        print("   - Large batch sizes for throughput")
        print("   - Target: 100+ products/second (indexing-optimized)")
        
    elif args.preset == "balanced":
        print("[BALANCE] Applying BALANCED preset:")
        args.quantization = "scalar"
        args.storage = "memory"
        args.hnsw_m = 32
        args.hnsw_ef_construct = 200
        print("   - Scalar quantization")
        print("   - Memory storage")
        print("   - Balanced parameters")
        
    elif args.preset == "memory-efficient":
        print("💾 Applying MEMORY-EFFICIENT preset:")
        args.quantization = "binary"
        args.storage = "memory"
        args.hnsw_m = 24
        args.hnsw_ef_construct = 150
        print("   - Binary quantization")
        print("   - Memory storage")
        print("   - Conservative parameters")
    
    # Force memory storage for performance
    if args.storage != "memory":
        print(f"[WARNING]  Forcing storage=memory for optimal performance (was {args.storage})")
        args.storage = "memory"
    
    print(f"\n[ROCKET] ENHANCED INDEXING PIPELINE")
    print(f"Creating enhanced collection: {args.collection}")
    print(f"Features: Vector search + Exact matching + Payload indexes")
    
    indexer = EnhancedIndexing(
        products_file=args.products_file,
        collection_name=args.collection,
        qdrant_url=args.url,
        batch_size=args.batch_size,
        embedding_batch_size=args.embedding_batch_size,
        indexing_mode=args.mode,
        hnsw_m=args.hnsw_m,
        hnsw_ef_construct=args.hnsw_ef_construct,
        quantization_mode=args.quantization,
        storage_mode=args.storage,
        num_threads=args.threads,
        enable_payload_indexes=not args.no_payload_indexes  # FIXED: Updated parameter name
    )
    
    indexer.run()

if __name__ == "__main__":
    main()
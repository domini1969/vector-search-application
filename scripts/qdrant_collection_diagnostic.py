#!/usr/bin/env python3
"""
Quick diagnostic to identify why searches are taking 2+ seconds
"""

import time
from qdrant_client import QdrantClient
from fastembed import TextEmbedding

def diagnose_slow_searches():
    """Quick diagnosis of slow search performance."""
    print("🔍 QUICK DIAGNOSTIC: Why are searches taking 2+ seconds?")
    print("="*60)
    
    # Connect to Qdrant
    client = QdrantClient("http://localhost:6333")
    
    try:
        # Get collection info
        collection_info = client.get_collection("products")
        
        print(f"📊 Collection Status: {collection_info.status}")
        print(f"📊 Points: {collection_info.points_count:,}")
        print(f"📊 Vectors: {collection_info.vectors_count:,}" if collection_info.vectors_count else "📊 Vectors: Not available")
        
        # Analyze configuration - handle different API versions
        config = collection_info.config
        
        # Try different ways to access vector configuration
        vectors_config = None
        if hasattr(config, 'vectors_config'):
            vectors_config = config.vectors_config
        elif hasattr(config, 'params') and hasattr(config.params, 'vectors'):
            vectors_config = config.params.vectors
        elif hasattr(config, 'params') and hasattr(config.params, 'vector'):
            vectors_config = {'dense': config.params.vector}
        else:
            # Try to find vector config in other attributes
            for attr_name in dir(config):
                if 'vector' in attr_name.lower() and not attr_name.startswith('_'):
                    attr_value = getattr(config, attr_name)
                    print(f"   Found vector-related attribute: {attr_name}")
                    if hasattr(attr_value, 'size'):
                        vectors_config = {'dense': attr_value}
                        break
        
        if vectors_config and ('dense' in vectors_config or hasattr(vectors_config, 'size')):
            # Handle both dict-style and object-style configurations
            if 'dense' in vectors_config:
                dense_config = vectors_config['dense']
            else:
                dense_config = vectors_config
            
            print(f"\n🔧 VECTOR CONFIGURATION:")
            print(f"   Vector size: {getattr(dense_config, 'size', 'unknown')}")
            print(f"   Distance: {getattr(dense_config, 'distance', 'unknown')}")
            
            # Safely check on_disk attribute
            vectors_on_disk = getattr(dense_config, 'on_disk', None)
            print(f"   Vectors on disk: {vectors_on_disk if vectors_on_disk is not None else 'default (False)'}")
            
            # Check HNSW configuration with safe attribute access
            hnsw_config = None
            if hasattr(dense_config, 'hnsw_config'):
                hnsw_config = dense_config.hnsw_config
            elif hasattr(dense_config, 'hnsw'):
                hnsw_config = dense_config.hnsw
            
            if hnsw_config:
                print(f"\n🏗️  HNSW CONFIGURATION:")
                
                # Safely get HNSW attributes
                m_val = getattr(hnsw_config, 'm', None)
                ef_construct_val = getattr(hnsw_config, 'ef_construct', None)
                full_scan_threshold_val = getattr(hnsw_config, 'full_scan_threshold', None)
                hnsw_on_disk = getattr(hnsw_config, 'on_disk', None)
                max_threads = getattr(hnsw_config, 'max_indexing_threads', None)
                
                print(f"   M: {m_val if m_val is not None else 'default (16)'}")
                print(f"   ef_construct: {ef_construct_val if ef_construct_val is not None else 'default (100)'}")
                print(f"   full_scan_threshold: {full_scan_threshold_val if full_scan_threshold_val is not None else 'default (20000)'}")
                print(f"   HNSW on disk: {hnsw_on_disk if hnsw_on_disk is not None else 'default (False)'}")
                print(f"   max_indexing_threads: {max_threads if max_threads is not None else 'default'}")
                
                # PROBLEM IDENTIFICATION
                print(f"\n❌ PROBLEM ANALYSIS:")
                
                # Check if HNSW index is on disk
                if hnsw_on_disk is True:
                    print("   🐌 MAJOR ISSUE: HNSW index is stored ON DISK!")
                    print("      This causes 2+ second search times because:")
                    print("      - Index graph must be read from disk for each search")
                    print("      - No RAM caching of the index structure")
                    print("      - Disk I/O bottleneck on every query")
                    print("      🚨 THIS IS LIKELY YOUR MAIN PROBLEM!")
                
                # Check if vectors are on disk
                if vectors_on_disk is True:
                    print("   🐌 MAJOR ISSUE: Vectors are stored ON DISK!")
                    print("      This causes slow searches because:")
                    print("      - Vector data must be read from disk")
                    print("      - No memory caching of vectors")
                    print("      🚨 THIS IS LIKELY YOUR MAIN PROBLEM!")
                
                # If both are in memory, look for other issues
                if hnsw_on_disk is not True and vectors_on_disk is not True:
                    print("   🤔 Vectors and HNSW appear to be in memory...")
                    print("      Looking for other performance issues:")
                
                # Check HNSW parameters
                actual_m = m_val if m_val is not None else 16
                if actual_m < 16:
                    print(f"   ⚠️  ISSUE: Low HNSW M value ({actual_m}) - should be 32+ for speed")
                elif actual_m >= 32:
                    print(f"   ✅ HNSW M value is good ({actual_m})")
                else:
                    print(f"   📈 HNSW M value is acceptable ({actual_m}) but could be higher")
                
                actual_ef = ef_construct_val if ef_construct_val is not None else 100
                if actual_ef < 100:
                    print(f"   ⚠️  ISSUE: Low ef_construct ({actual_ef}) - should be 200+ for quality")
                elif actual_ef >= 200:
                    print(f"   ✅ ef_construct value is good ({actual_ef})")
                else:
                    print(f"   📈 ef_construct value is acceptable ({actual_ef}) but could be higher")
            else:
                print(f"\n🏗️  HNSW CONFIGURATION: Could not access HNSW config")
                print("   This might indicate configuration issues")
            
            # Check quantization
            quantization_config = getattr(dense_config, 'quantization_config', None)
            if quantization_config:
                print(f"   📦 Quantization: Enabled")
                if hasattr(quantization_config, 'scalar') and quantization_config.scalar:
                    print(f"      Type: Scalar quantization")
                    scalar_config = quantization_config.scalar
                    if hasattr(scalar_config, 'always_ram'):
                        print(f"      Always in RAM: {scalar_config.always_ram}")
                elif hasattr(quantization_config, 'binary') and quantization_config.binary:
                    print(f"      Type: Binary quantization")
                elif hasattr(quantization_config, 'product') and quantization_config.product:
                    print(f"      Type: Product quantization")
            else:
                print(f"   📦 Quantization: Disabled")
        else:
            print(f"\n❌ Could not access vector configuration")
            print("   This suggests a configuration issue or API version mismatch")
            print("   Available config attributes:")
            config_attrs = [attr for attr in dir(config) if not attr.startswith('_')]
            for attr in config_attrs[:10]:  # Show first 10 attributes
                print(f"     - {attr}")
        
        # Check optimizer configuration
        print(f"\n⚙️  OPTIMIZER CONFIGURATION:")
        optimizer_config = None
        if hasattr(config, 'optimizer_config'):
            optimizer_config = config.optimizer_config
        elif hasattr(config, 'optimizers_config'):
            optimizer_config = config.optimizers_config
        elif hasattr(config, 'params') and hasattr(config.params, 'optimizer_config'):
            optimizer_config = config.params.optimizer_config
        
        if optimizer_config:
            default_segments = getattr(optimizer_config, 'default_segment_number', None)
            max_segment_size = getattr(optimizer_config, 'max_segment_size', None)
            indexing_threshold = getattr(optimizer_config, 'indexing_threshold', None)
            
            print(f"   Default segments: {default_segments if default_segments is not None else 'default'}")
            print(f"   Max segment size: {max_segment_size if max_segment_size is not None else 'default'}")
            print(f"   Indexing threshold: {indexing_threshold if indexing_threshold is not None else 'default'}")
        else:
            print("   Using default optimizer settings")
            
        # Debug: Show all config structure
        print(f"\n🔍 DEBUG: Collection Config Structure:")
        print(f"   Config type: {type(config)}")
        config_attrs = [attr for attr in dir(config) if not attr.startswith('_') and not callable(getattr(config, attr))]
        for attr in config_attrs:
            try:
                value = getattr(config, attr)
                print(f"   {attr}: {type(value).__name__}")
            except:
                print(f"   {attr}: <error accessing>")

        
        # Performance test with different ef values
        print(f"\n🏃 PERFORMANCE TEST:")
        print("Loading embedding model...")
        model = TextEmbedding("BAAI/bge-small-en-v1.5")
        
        test_query = "gas torch"
        print(f"Testing query: '{test_query}'")
        
        # Generate embedding
        embed_start = time.time()
        embedding = list(model.query_embed([test_query]))[0]
        embed_time = time.time() - embed_start
        print(f"   Embedding generation: {embed_time*1000:.1f}ms")
        
        # Test different ef values
        ef_values = [16, 32, 64, 128]
        
        for ef in ef_values:
            search_start = time.time()
            try:
                results = client.query_points(
                    collection_name="products",
                    query=embedding.tolist(),
                    using="dense",
                    with_payload=False,
                    with_vectors=False,
                    limit=10,
                    timeout=15,
                    search_params={
                        "hnsw_ef": ef,
                        "exact": False
                    }
                )
                search_time = time.time() - search_start
                print(f"   ef={ef}: {search_time*1000:.1f}ms - {len(results.points)} results")
                
                if search_time > 1.0:  # > 1 second
                    print(f"      🐌 VERY SLOW! This confirms disk I/O bottleneck")
                elif search_time > 0.5:  # > 500ms
                    print(f"      ⚠️  SLOW - likely reading from disk")
                elif search_time > 0.1:  # > 100ms
                    print(f"      📈 ACCEPTABLE - could be better")
                else:
                    print(f"      ✅ GOOD - reading from memory")
                    
            except Exception as e:
                print(f"   ef={ef}: FAILED - {e}")
        
        # SOLUTIONS
        print(f"\n💡 SOLUTIONS TO FIX 2+ SECOND SEARCHES:")
        print("="*60)
        
        print("🚨 Based on your 2+ second search times, here are the solutions:")
        print()
        print("🚀 IMMEDIATE SOLUTIONS (choose one):")
        print()
        print("   1. 🆕 CREATE NEW OPTIMIZED COLLECTION (RECOMMENDED):")
        print("      python optimized_indexing.py \\")
        print("        --collection products_fast \\")
        print("        --storage memory \\")
        print("        --quantization scalar \\")
        print("        --hnsw-m 32 \\")
        print("        --hnsw-ef-construct 200")
        print()
        print("   2. 📋 USE THE SPEED-OPTIMIZED INDEXER:")
        print("      # First, backup your data")
        print("      cp products.json products_backup.json")
        print("      # Then create fast collection")
        print("      python speed_optimized_indexing.py \\")
        print("        --preset max-speed \\")
        print("        --collection products_fast")
        print()
        print("   3. 🔧 MANUAL OPTIMIZATION (if you understand Qdrant):")
        print("      - Delete current collection")
        print("      - Recreate with on_disk=False for both vectors and HNSW")
        print("      - Use higher HNSW parameters (M=32, ef_construct=200)")
        print("      - Enable scalar quantization with always_ram=True")
        
        print(f"\n🎯 EXPECTED PERFORMANCE AFTER FIX:")
        print("   Current performance:")
        print("     ❌ Search time: 2000+ ms (unacceptable)")
        print("     ❌ Memory usage: Low (disk-based)")
        print("   After optimization:")
        print("     ✅ First search: ~100-200ms (index loading)")
        print("     ✅ Subsequent searches: ~20-50ms (memory access)")
        print("     ✅ With caching: ~5-20ms (cache hits)")
        print("     ⚠️  Memory usage: Higher (RAM-based, but worth it)")
        
        print(f"\n📋 STEP-BY-STEP RECOMMENDATION:")
        print("1. 💾 Backup your current data:")
        print("   cp products.json products_backup.json")
        print()
        print("2. 🚀 Create fast collection using the speed-optimized indexer:")
        print("   python speed_optimized_indexing.py --preset balanced --collection products_fast")
        print()
        print("3. 🔄 Update your application configuration:")
        print("   Change COLLECTION_NAME from 'products' to 'products_fast'")
        print()
        print("4. 🧪 Test the performance:")
        print("   python -c \"")
        print("   from app.services.search_service import search_service")
        print("   import time")
        print("   start = time.time()")
        print("   results = search_service.search('gas torch', 10)")
        print("   print(f'Search took: {(time.time()-start)*1000:.1f}ms')")
        print("   \"")
        print()
        print("5. 📊 Compare performance:")
        print("   - Old collection: 2000+ ms")
        print("   - New collection: Should be 50-150 ms")
        
        print(f"\n⚠️  IMPORTANT NOTES:")
        print("- The new collection will use more RAM but be 20x faster")
        print("- Keep your backup until you're satisfied with performance")
        print("- You can run both collections simultaneously for comparison")
        print("- The speed improvement is dramatic and worth the memory trade-off")
        
        print(f"\n🆘 IF YOU NEED IMMEDIATE HELP:")
        print("1. Run: python speed_optimized_indexing.py --preset balanced --collection products_fast")
        print("2. Update your app to use 'products_fast' collection")
        print("3. Test search performance")
        print("4. Report back with timing results")

        
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_slow_searches()
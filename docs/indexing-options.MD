Indexing Options
  --mode {dense,sparse,hybrid}     # Indexing mode (default: dense)
  - dense: Only Dense model (semantic search)
  - sparse: Only BM25 + MiniCOIL (keyword search)
  - hybrid: All models (complete search capabilities)

  📦 Performance Parameters

  --batch-size BATCH_SIZE          # Upload batch size (default: 512)
  --embedding-batch-size EMBEDDING_BATCH_SIZE  # Embedding batch size (default: 1024)
  --threads THREADS                # Number of threads (default: auto-detect, max 8)

  🏗️ HNSW Index Parameters

  --hnsw-m HNSW_M                 # HNSW M parameter - higher = faster search (default: 32)
  --hnsw-ef-construct HNSW_EF_CONSTRUCT  # HNSW ef_construct - higher = better quality (default: 200)

  💾 Storage & Memory Parameters

  --quantization {none,scalar,binary}  # Vector quantization (default: scalar)
  --storage {memory,disk}             # Storage mode - memory recommended (default: memory)

  📊 Index Configuration

  --no-payload-indexes            # Disable payload index creation (default: enabled)

  🚀 Optimization Presets

  --preset {max-speed,balanced,memory-efficient,production}  # Predefined optimization preset

  📋 Preset Configurations

  --preset max-speed (🚀 Maximum Performance)

  # Automatically sets:
  --quantization none             # No compression (fastest search)
  --storage memory               # Memory storage
  --hnsw-m 48                   # High connections (faster search)
  --hnsw-ef-construct 300       # High quality index
  --batch-size 1024             # Large upload batches
  --embedding-batch-size 2048   # Large embedding batches
  # Payload indexes: ENABLED

  --preset balanced (⚖️ Balanced Performance)

  # Automatically sets:
  --quantization scalar          # Some compression (balanced)
  --storage memory              # Memory storage
  --hnsw-m 32                  # Moderate connections
  --hnsw-ef-construct 200      # Good quality
  --batch-size 768             # Medium batches
  --embedding-batch-size 1536  # Medium embedding batches
  # Payload indexes: ENABLED

  --preset memory-efficient (💾 Low Memory Usage)

  # Automatically sets:
  --quantization binary         # High compression (saves memory)
  --storage memory             # Memory storage
  --hnsw-m 24                 # Fewer connections (less memory)
  --hnsw-ef-construct 150     # Lower quality (faster indexing)
  --batch-size 512            # Smaller batches
  --embedding-batch-size 1024 # Smaller embedding batches
  # Payload indexes: ENABLED

  --preset production (🏭 Production Ready)

  # Automatically sets:
  --quantization scalar         # Balanced compression
  --storage memory             # Memory storage
  --hnsw-m 32                 # Good connections
  --hnsw-ef-construct 200     # Good quality
  --batch-size 768            # Medium batches
  --embedding-batch-size 1536 # Medium embedding batches
  # Payload indexes: ENABLED

  🎛️ Complete Command Examples

  Quick Start Commands:

  # Default (Dense only, balanced settings)
  python indexing.py

  # Maximum speed, dense only
  python indexing.py --preset max-speed --mode dense

  # Maximum speed, all models
  python indexing.py --preset max-speed --mode hybrid

  # Memory efficient, sparse only
  python indexing.py --preset memory-efficient --mode sparse

  Custom Configuration Examples:

  # Custom high-performance setup
  python indexing.py --mode hybrid --hnsw-m 64 --hnsw-ef-construct 400 --quantization none --batch-size 2048

  # Custom memory-optimized setup
  python indexing.py --mode dense --hnsw-m 16 --hnsw-ef-construct 100 --quantization binary --batch-size 256

  # Custom balanced setup
  python indexing.py --mode hybrid --hnsw-m 40 --hnsw-ef-construct 250 --quantization scalar --threads 12

  # Different collection and data file
  python indexing.py --products-file custom_products.json --collection my_products --mode hybrid

  # Disable payload indexes (faster indexing, slower exact search)
  python indexing.py --no-payload-indexes --preset max-speed --mode hybrid

  # Different Qdrant server
  python indexing.py --url http://remote-qdrant:6333 --mode hybrid

  Performance Testing Commands:

  # Test dense performance with parallel embeddings
  python indexing.py --preset max-speed --mode dense --batch-size 2048 --embedding-batch-size 4096

  # Test sparse performance
  python indexing.py --preset max-speed --mode sparse --batch-size 2048

  # Test full hybrid performance
  python indexing.py --preset max-speed --mode hybrid --batch-size 1024 --threads 16

  # Memory-constrained environment
  python indexing.py --preset memory-efficient --mode dense --batch-size 256 --embedding-batch-size 512

  Production Deployment Commands:

  # Standard production (all capabilities)
  python indexing.py --preset production --mode hybrid --collection products_v2

  # High-performance production (if you have resources)
  python indexing.py --preset max-speed --mode hybrid --collection products_fast --threads 16

  # Memory-limited production server
  python indexing.py --preset memory-efficient --mode hybrid --collection products_efficient

  ⚡ Performance Impact Guide

  | Parameter              | Low Value          | High Value         | Impact              |
  |------------------------|--------------------|--------------------|---------------------|
  | --hnsw-m               | 16 (less memory)   | 64 (more memory)   | Search speed        |
  | --hnsw-ef-construct    | 100 (faster index) | 400 (slower index) | Search quality      |
  | --batch-size           | 256 (less memory)  | 2048 (more memory) | Indexing speed      |
  | --embedding-batch-size | 512 (less memory)  | 4096 (more memory) | Embedding speed     |
  | --threads              | 4 (less CPU)       | 16 (more CPU)      | Parallel processing |

  🎯 Mode Selection Guide

  | Use Case                    | Recommended Mode | Models Loaded   | Speed                |
  |-----------------------------|------------------|-----------------|----------------------|
  | Semantic search only        | --mode dense     | Dense           | ⚡⚡⚡ Fastest          |
  | Keyword search only         | --mode sparse    | BM25 + MiniCOIL | ⚡⚡ Fast              |
  | Complete search system      | --mode hybrid    | All 3 models    | ⚡ Complete           |
  | Testing parallel embeddings | --mode dense     | Dense           | ⚡⚡⚡ Best for testing |

  Now you have complete control over every aspect of the indexing process with proper parallel embedding 
  generation and mode-specific optimization! 🚀

> python indexing.py --preset memory-efficient --mode desnse - what this does in terms of paramters?

● I notice you typed --mode desnse (typo) - it should be --mode dense. Let me show you what this command would
  do:

  python indexing.py --preset memory-efficient --mode dense

  📋 What This Command Does:

  This command combines the memory-efficient preset with dense-only mode, giving you the most memory-friendly
  semantic search setup.

  🔧 Actual Parameters Applied:

  From --preset memory-efficient:

  --quantization binary          # High compression (saves ~75% memory)
  --storage memory              # Keep in memory (not disk)
  --hnsw-m 24                  # Fewer connections (saves memory)
  --hnsw-ef-construct 150      # Lower construction quality (faster indexing)
  --batch-size 512             # Smaller upload batches (less RAM usage)
  --embedding-batch-size 1024  # Smaller embedding batches (less RAM usage)
  # Payload indexes: ENABLED (default)

  From --mode dense:

  # Models loaded:
  Dense model: ✅ LOADED (BAAI/bge-small-en-v1.5)
  BM25 model: ❌ NOT LOADED (saves ~2GB RAM)
  MiniCOIL model: ❌ NOT LOADED (saves ~2GB RAM)

  # Embeddings generated:
  Dense embeddings: ✅ GENERATED (384-dim vectors with binary quantization)
  BM25 embeddings: ❌ NOT GENERATED
  MiniCOIL embeddings: ❌ NOT GENERATED

  💾 Memory Usage Comparison:

  | Component          | Normal Setup            | This Command             | Memory Saved |
  |--------------------|-------------------------|--------------------------|--------------|
  | Models in RAM      | ~6GB (all 3 models)     | ~2GB (dense only)        | ~4GB saved   |
  | Vector Storage     | Full precision          | Binary quantized         | ~75% saved   |
  | HNSW Index         | M=32 (more connections) | M=24 (fewer connections) | ~25% saved   |
  | Processing Batches | Large batches           | Small batches            | ~50% saved   |

  ⚡ Performance Characteristics:

  | Aspect         | Performance           | Details                                  |
  |----------------|-----------------------|------------------------------------------|
  | Model Loading  | ⚡⚡⚡ Very Fast (~0.7s) | Only dense model loads                   |
  | Indexing Speed | ⚡⚡ Good               | Smaller batches, binary quantization     |
  | Search Speed   | ⚡⚡ Good               | Binary quantization slightly slower      |
  | Search Quality | 🟡 Reduced            | Binary quantization loses some precision |
  | Memory Usage   | 🟢 Minimal            | Perfect for limited RAM environments     |

  🎯 What You Get:

  ✅ Capabilities:

  - Semantic search on product descriptions
  - Very low memory footprint
  - Fast model loading (only dense model)
  - Reasonable indexing speed
  - Exact payload matching (part numbers, etc.)

  ❌ Limitations:

  - No keyword search (no BM25/MiniCOIL)
  - No hybrid search capabilities
  - Slightly reduced search quality (binary quantization)
  - Cannot search part numbers semantically

  💡 Perfect For:

  # Scenarios where this command is ideal:
  - Limited RAM environments (< 8GB available)
  - Docker containers with memory limits
  - Cloud instances with small memory
  - Development/testing environments
  - When you only need semantic search
  - Embedded systems or edge devices

  🔄 Alternative Commands:

  If you want to adjust this setup:

  # Same memory efficiency but better search quality
  python indexing.py --preset memory-efficient --mode dense --quantization scalar

  # Add keyword search capability (uses more memory)
  python indexing.py --preset memory-efficient --mode sparse

  # Full capabilities but still memory-conscious
  python indexing.py --preset memory-efficient --mode hybrid

  # Even more memory efficient (but lower quality)
  python indexing.py --preset memory-efficient --mode dense --hnsw-m 16 --batch-size 256

  This command gives you the most memory-efficient semantic search setup possible while still maintaining 
  reasonable performance! 💾⚡

> What does this means? Come up with an ecommerce search example from amazon --   --hnsw-m 24                  # 
  Fewer connections (saves memory)
    --hnsw-ef-construct 150      # Lower construction quality (faster indexing)

● Great question! Let me explain HNSW parameters with a concrete Amazon ecommerce search example:

  🛍️ Amazon Search Example: HNSW Parameters

  What is HNSW?

  HNSW (Hierarchical Navigable Small World) is like a multi-level highway system for finding similar products
  quickly.

  ---
  🛣️ HNSW-M Parameter: "Highway Connections"

  --hnsw-m 24 (Memory-Efficient)

  Think of it as: Each product has 24 direct connections to similar products

  Amazon Example:

  🎧 Sony WH-1000XM4 Headphones connects to:
  ├─ Bose QuietComfort 45 (noise-canceling competitor)
  ├─ Apple AirPods Max (premium headphones)
  ├─ Sennheiser HD 660S (audiophile choice)
  ├─ Audio-Technica ATH-M50x (studio headphones)
  ├─ JBL Live 650BTNC (budget alternative)
  ... 19 more similar products

  vs

  --hnsw-m 48 (High-Performance)

  Think of it as: Each product has 48 direct connections to similar products

  🎧 Sony WH-1000XM4 Headphones connects to:
  ├─ All 24 connections from above, PLUS:
  ├─ Beats Studio3 (brand alternative)
  ├─ Plantronics BackBeat Pro 2 (business use)
  ├─ Skullcandy Crusher (bass-heavy)
  ├─ Bang & Olufsen Beoplay H9 (luxury)
  ├─ Microsoft Surface Headphones (tech ecosystem)
  ... 19 more additional connections

  🚀 Search Impact:

  - M=24: When someone searches "wireless noise canceling headphones", the system follows 24 pathways to find
  matches
  - M=48: Same search follows 48 pathways, finding more diverse and potentially better matches

  ---
  🏗️ EF-Construct Parameter: "Highway Construction Quality"

  --hnsw-ef-construct 150 (Memory-Efficient)

  Think of it as: During indexing, we explore 150 candidate connections before deciding the best ones

  Amazon Indexing Example:

  When adding "Apple AirPods Pro" to the search index:

  🔍 Construction Process (ef-construct=150):
  1. Look at 150 existing products as potential connections
  2. Find best matches among those 150:
     ✓ AirPods Max (same brand)
     ✓ Sony WF-1000XM4 (competitor)
     ✓ Bose QuietComfort Earbuds (similar category)
     ✓ Samsung Galaxy Buds Pro (Android alternative)
     ... up to M=24 final connections

  ⏱️ Time: Faster (less exploration)
  🎯 Quality: Good (but might miss some great connections)

  --hnsw-ef-construct 300 (High-Performance)

  Think of it as: During indexing, we explore 300 candidate connections before deciding

  🔍 Construction Process (ef-construct=300):
  1. Look at 300 existing products as potential connections
  2. Find best matches among those 300:
     ✓ All the connections from ef=150, PLUS:
     ✓ Jabra Elite 85t (professional audio)
     ✓ Master & Dynamic MW08 (premium audiophile)
     ✓ Nothing Ear (1) (design-focused)
     ✓ Anker Soundcore Liberty Air 2 (budget-conscious)
     ... up to M=48 final connections

  ⏱️ Time: Slower (more exploration)
  🎯 Quality: Better (finds more optimal connections)

  ---
  🛍️ Real Search Scenario Impact

  Customer searches: "bluetooth earbuds for running"

  With Memory-Efficient Settings (M=24, ef=150):

  Search Path:
  🏃‍♂️ Query → AirPods Pro → 24 connections → Results:
  1. Powerbeats Pro (sports-focused)
  2. Jabra Elite Active 75t (fitness)
  3. Sony WF-SP800N (sports)
  4. Bose SoundSport Free (running)
  5. JayBird Vista (athletic)

  ⚡ Speed: 15ms
  💾 Memory: 2GB RAM
  🎯 Results: Good matches

  With High-Performance Settings (M=48, ef=300):

  Search Path:
  🏃‍♂️ Query → AirPods Pro → 48 connections → Results:
  1. Powerbeats Pro (sports-focused)
  2. Jabra Elite Active 75t (fitness)
  3. Sony WF-SP800N (sports)
  4. Bose SoundSport Free (running)
  5. JayBird Vista (athletic)
  6. Beats Flex (workout-friendly) ← Additional find
  7. Sennheiser CX Sport (running-specific) ← Additional find
  8. Under Armour True Wireless Flash (athletic brand) ← Additional find

  ⚡ Speed: 8ms (faster due to better connections!)
  💾 Memory: 4GB RAM
  🎯 Results: More comprehensive matches

  ---
  💰 Business Impact on Amazon

  Memory-Efficient (M=24, ef=150)

  ✅ Pros:
  - Handles millions of products with less server cost
  - Good enough results for most searches
  - Faster indexing of new products
  - Lower cloud infrastructure costs

  ❌ Cons:
  - Might miss some perfect product matches
  - Less diverse search results
  - Fewer "discovery" opportunities

  High-Performance (M=48, ef=300)

  ✅ Pros:
  - Better product discovery → higher sales
  - More comprehensive search results
  - Better customer satisfaction
  - Finds niche products customers love

  ❌ Cons:
  - 2x memory costs for server infrastructure
  - Slower when adding new products to catalog
  - Higher cloud computing bills

  ---
  🎯 Summary for Your Amazon-Style Search

  | Setting                         | Amazon's Choice                     | Why                          |
  |---------------------------------|-------------------------------------|------------------------------|
  | Small Store (< 100K products)   | --hnsw-m 48 --hnsw-ef-construct 300 | Better discovery, affordable |
  | Medium Store (100K-1M products) | --hnsw-m 32 --hnsw-ef-construct 200 | Balanced performance         |
  | Large Store (> 1M products)     | --hnsw-m 24 --hnsw-ef-construct 150 | Cost-effective, scalable     |

  Your --preset memory-efficient settings are perfect for a cost-conscious ecommerce platform that still wants        
  good search results! 💡
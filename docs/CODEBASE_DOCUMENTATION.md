# Qdrant Vector Search Service - Codebase Documentation

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Hierarchy](#architecture-hierarchy)
3. [Core Components](#core-components)
4. [Service Layer](#service-layer)
5. [API Layer](#api-layer)
6. [Data Layer](#data-layer)
7. [Utility Scripts](#utility-scripts)
8. [Program Flow](#program-flow)
9. [Dependencies](#dependencies)

---

## 🏗️ System Overview

This is a **hybrid vector search service** built for Airgas product search, combining semantic similarity and exact matching for high-performance product discovery.

**Key Technologies:**
- **FastAPI** - REST API framework
- **Qdrant** - Vector database for embeddings
- **Sentence Transformers** - Text embedding generation
- **Docker** - Containerized deployment

---

## 🏛️ Architecture Hierarchy

```
📁 qdrant/
├── 🚀 Entry Points
│   ├── app/main.py                    # FastAPI application entry point
│   └── scripts/indexing.py            # Data indexing script
│
├── 🏢 Core Application (app/)
│   ├── 📋 Configuration
│   │   └── app/config/config.py       # Application settings & environment
│   │
│   ├── 🔧 Core Infrastructure
│   │   ├── app/core/database.py       # Qdrant database client
│   │   ├── app/core/errors.py         # Custom exception classes
│   │   └── app/core/logging.py        # Logging configuration
│   │
│   ├── 🎯 Services Layer
│   │   ├── app/services/search_service.py      # Main search engine
│   │   ├── app/services/document_service.py    # Document management
│   │   ├── app/services/partno_classifier.py  # Part number detection
│   │   └── app/services/version_service.py    # Document versioning
│   │
│   ├── 🌐 API Layer
│   │   ├── app/api/endpoints/
│   │   │   ├── search.py              # Search endpoints
│   │   │   ├── document.py            # Document CRUD endpoints
│   │   │   ├── admin.py               # Administrative endpoints
│   │   │   └── health.py              # Health check endpoints
│   │   └── app/api/models/
│   │       └── document.py            # Pydantic data models
│   │
│   └── 🛠️ Utilities
│       └── search_ui/search.py        # Search interface
│
├── 📊 Data & Scripts
│   ├── scripts/
│   │   ├── indexing.py                # Main indexing script
│   │   ├── test_speed.py              # Performance testing
│   │   ├── parallel_search_fusion.py  # Fusion search implementation
│   │   ├── qdrant_collection_diagnostic.py # Collection diagnostics
│   │   └── list_qdrant_fields.py     # Field inspection
│   │
│   ├── data/
│   │   ├── import/full/               # Full data imports
│   │   ├── import/delta/              # Incremental updates
│   │   └── exports/                   # Data exports
│   │
│   └── logs/                          # Application logs
│
└── 🐳 Deployment
    ├── docker-compose.yml             # Container orchestration
    └── requirements.txt               # Python dependencies
```

---

## 🔧 Core Components

### 1. **Entry Points**

#### `app/main.py` - FastAPI Application
**Purpose:** Main application entry point and API server
**Dependencies:** 
- `app/services/search_service.py`
- `app/core/logging.py`
- `app/config/config.py`
- `app/core/database.py`

**Key Functions:**
- Initializes FastAPI application
- Registers API routers
- Defines core endpoints (`/health`, `/api/search`, `/api/load-data`)
- Handles file uploads and data loading
- Manages search requests with filtering

**Program Flow:**
```
Request → FastAPI Router → Search Service → Database Client → Qdrant
Response ← Database Client ← Search Service ← FastAPI Router ← Client
```

#### `scripts/indexing.py` - Data Indexing Script
**Purpose:** Bulk data processing and vector creation
**Dependencies:**
- `fastembed` for embeddings
- `qdrant_client` for database operations
- `datasets` for data processing

**Key Functions:**
- Loads product data from JSON
- Generates embeddings using sentence transformers
- Creates optimized Qdrant collections
- Implements memory-optimized processing
- Supports multiple indexing modes (dense, sparse, hybrid)

---

### 2. **Configuration Layer**

#### `app/config/config.py` - Application Settings
**Purpose:** Centralized configuration management
**Dependencies:** `pydantic_settings`, `python-dotenv`

**Key Features:**
- Environment variable loading
- Qdrant connection settings
- Search performance parameters
- Model configuration
- Threading optimization settings
- UI configuration options

**Configuration Categories:**
- **Database Settings:** Host, port, API keys, HTTPS
- **Search Settings:** Limits, thresholds, spell check
- **Performance Settings:** Thread counts, caching, optimization
- **Model Settings:** Embedding models, cross-encoders
- **UI Settings:** Search endpoints, feature toggles

---

### 3. **Core Infrastructure**

#### `app/core/database.py` - Database Client
**Purpose:** Qdrant database operations wrapper
**Dependencies:** `qdrant_client`, `sentence_transformers`

**Key Functions:**
- **Collection Management:** Create, delete, verify collections
- **Document Operations:** Upsert, query, delete documents
- **Embedding Generation:** Text-to-vector conversion
- **Batch Processing:** Efficient bulk operations
- **Error Handling:** Database-specific exception management

**Program Flow:**
```
Text Input → Embedding Model → Vector → Qdrant Storage
Query → Vector Search → Results → Formatted Response
```

#### `app/core/errors.py` - Custom Exceptions
**Purpose:** Application-specific error handling
**Dependencies:** None (base exception classes)

**Exception Types:**
- `BaseAppException` - Base application exception
- `DatabaseError` - Database operation failures
- `DocumentNotFoundError` - Missing document errors
- `DocumentConflictError` - Document conflicts
- `FileOperationError` - File I/O failures
- `ValidationError` - Data validation errors
- `ConfigurationError` - Configuration issues

#### `app/core/logging.py` - Logging Configuration
**Purpose:** Centralized logging setup
**Dependencies:** `logging`, `app/config/config.py`

**Features:**
- File and console logging
- Log rotation (10MB files, 10 backups)
- Configurable log levels
- Structured logging format
- Application-specific logger

---

## 🎯 Service Layer

### 1. **Search Services**

#### `app/services/search_service.py` - Main Search Engine
**Purpose:** High-performance search with multiple strategies
**Dependencies:** `fastembed`, `qdrant_client`, `app/core/database.py`

**Service Classes:**
- `UltraFastSearchService` - Core 25-40ms performance
- `LeanSearchService` - Maximum speed minimal features
- `ReallyFastSearchService` - Alias for ultra-fast

**Key Functions:**
- **Vector Search:** Semantic similarity search
- **Exact Search:** Keyword matching
- **Fusion Search:** Parallel exact + vector search
- **Filtered Search:** Field-based filtering
- **Performance Tracking:** Search timing and statistics

**Search Flow:**
```
Query → Embedding → Vector Search → Results
Query → Exact Match → Keyword Search → Results
Query → Fusion → Parallel Search → Combined Results
```

#### `app/services/partno_classifier.py` - Part Number Detection
**Purpose:** Intelligent query classification
**Dependencies:** `re` (regex), no external dependencies

**Key Functions:**
- **Query Classification:** Determines if query is a part number
- **Pattern Recognition:** Identifies part number patterns
- **Scoring System:** Multi-factor classification scoring
- **Explanation:** Provides classification reasoning

**Classification Factors:**
- Alphanumeric patterns
- Length validation
- Common prefixes
- Search term detection
- Document reference filtering

### 2. **Document Services**

#### `app/services/document_service.py` - Document Management
**Purpose:** Document CRUD operations and bulk processing
**Dependencies:** `app/core/database.py`, `app/core/errors.py`

**Key Functions:**
- **Document CRUD:** Create, read, update, delete
- **Bulk Operations:** Batch processing for efficiency
- **Import/Export:** Data loading and export
- **Validation:** Document structure validation
- **State Management:** Import progress tracking

**Processing Flow:**
```
JSON File → Validation → Batch Processing → Database Upsert
Query → Document Retrieval → Formatted Response
```

#### `app/services/version_service.py` - Document Versioning
**Purpose:** Document version control and history
**Dependencies:** `app/core/database.py`, `datetime`

**Key Functions:**
- **Version Creation:** New document versions
- **Version Updates:** Incremental versioning
- **History Management:** Version history tracking
- **Archive Operations:** Version archiving
- **Rollback Support:** Version restoration

**Versioning Flow:**
```
Document Update → Archive Current → Create New Version → Update Metadata
Version Query → History Lookup → Version Retrieval
```

---

## 🌐 API Layer

### 1. **API Endpoints**

#### `app/api/endpoints/search.py` - Search Endpoints
**Purpose:** REST API for search operations
**Dependencies:** `app/services/search_service.py`, `fastapi`

**Endpoints:**
- `GET /api/query` - Simple search with minimal response
- `GET /api/search` - Full search with complete details
- `GET /api/search/ultra-fast` - Ultra-fast vector search
- `GET /api/search/fusion` - Fusion search (exact + vector)
- `GET /api/search/lean` - Maximum speed search
- `GET /api/search/compare` - Performance comparison
- `GET /api/search/performance-stats` - Performance metrics

**Request Flow:**
```
HTTP Request → FastAPI Router → Search Service → Database → Response
```

#### `app/api/endpoints/document.py` - Document Endpoints
**Purpose:** Document CRUD operations
**Dependencies:** `app/services/document_service.py`

**Endpoints:**
- `POST /api/documents` - Create document
- `GET /api/documents/{id}` - Get document
- `PUT /api/documents/{id}` - Update document
- `DELETE /api/documents/{id}` - Delete document
- `GET /api/documents` - List documents

#### `app/api/endpoints/admin.py` - Administrative Endpoints
**Purpose:** System administration and monitoring
**Dependencies:** `app/core/database.py`

**Endpoints:**
- `GET /api/admin/collections` - List collections
- `GET /api/admin/stats` - System statistics
- `POST /api/admin/optimize` - Optimize collections

#### `app/api/endpoints/health.py` - Health Check Endpoints
**Purpose:** System health monitoring
**Dependencies:** `app/core/database.py`

**Endpoints:**
- `GET /health` - Basic health check
- `GET /api/health/detailed` - Detailed health status

### 2. **Data Models**

#### `app/api/models/document.py` - Pydantic Models
**Purpose:** Request/response data validation
**Dependencies:** `pydantic`, `typing`

**Model Classes:**
- `SearchResult` - Search result structure
- `DocumentBase` - Base document model
- `DocumentResponse` - Document response format
- `ImportStatus` - Import progress tracking
- `ExportStatus` - Export progress tracking
- `DocumentHistoryResponse` - Version history
- `DocumentVersionResponse` - Version details

---

## 📊 Data Layer

### 1. **Data Storage**

**Qdrant Collections:**
- `products_fast` - Main product collection
- `products_fast_history` - Version history collection

**Data Structure:**
```json
{
  "id": "partNumber_airgas_text",
  "vector": [0.1, 0.2, ...], // 384-dimensional embedding
  "payload": {
    "partNumber_airgas_text": "ABC123",
    "manufacturerPartNumber_text": "MFG456",
    "shortDescription_airgas_text": "Product description",
    "onlinePrice_string": "99.99",
    "img_270Wx270H_string": "image_url",
    "searchable_text": "Combined searchable text"
  }
}
```

### 2. **Data Processing**

**Indexing Process:**
```
JSON Products → Text Processing → Embedding Generation → Qdrant Storage
```

**Search Process:**
```
Query Text → Embedding → Vector Search → Result Ranking → Response
```

---

## 🛠️ Utility Scripts

### 1. **Performance Scripts**

#### `scripts/test_speed.py` - Performance Testing
**Purpose:** Search performance benchmarking
**Dependencies:** `fastembed`, `qdrant_client`

**Key Functions:**
- Search timing measurement
- Performance evaluation
- Collection diagnostics
- Configuration verification

#### `scripts/parallel_search_fusion.py` - Fusion Search
**Purpose:** Advanced search combining multiple strategies
**Dependencies:** `concurrent.futures`, `app/services/search_service.py`

**Key Functions:**
- Parallel exact and vector search
- Result fusion algorithms
- Performance optimization
- Search strategy comparison

### 2. **Diagnostic Scripts**

#### `scripts/qdrant_collection_diagnostic.py` - Collection Analysis
**Purpose:** Collection health and performance analysis
**Dependencies:** `qdrant_client`

**Key Functions:**
- Collection statistics
- Performance metrics
- Configuration analysis
- Optimization recommendations

#### `scripts/list_qdrant_fields.py` - Field Inspection
**Purpose:** Document field analysis
**Dependencies:** `qdrant_client`

**Key Functions:**
- Field discovery
- Data type analysis
- Schema documentation
- Field statistics

---

## 🔄 Program Flow

### 1. **Application Startup Flow**

```
1. app/main.py (Entry Point)
   ├── Load configuration (app/config/config.py)
   ├── Initialize logging (app/core/logging.py)
   ├── Setup database client (app/core/database.py)
   ├── Initialize search services (app/services/search_service.py)
   ├── Register API routers (app/api/endpoints/*)
   └── Start FastAPI server
```

### 2. **Search Request Flow**

```
HTTP Request → FastAPI Router → Search Endpoint
    ↓
Search Service (app/services/search_service.py)
    ↓
Part Number Classifier (app/services/partno_classifier.py)
    ↓
Database Client (app/core/database.py)
    ↓
Qdrant Vector Database
    ↓
Formatted Response → HTTP Response
```

### 3. **Data Indexing Flow**

```
scripts/indexing.py (Entry Point)
    ↓
Load Product Data (JSON)
    ↓
Text Processing & Validation
    ↓
Embedding Generation (FastEmbed)
    ↓
Qdrant Collection Creation
    ↓
Batch Upsert Operations
    ↓
Performance Testing
    ↓
Collection Optimization
```

### 4. **Document Management Flow**

```
Document Service (app/services/document_service.py)
    ↓
Validation (app/core/errors.py)
    ↓
Version Service (app/services/version_service.py)
    ↓
Database Client (app/core/database.py)
    ↓
Qdrant Storage
```

---

## 🔗 Dependencies

### 1. **Core Dependencies**

**FastAPI Stack:**
- `fastapi>=0.115.0` - Web framework
- `uvicorn[standard]>=0.34.0` - ASGI server
- `pydantic>=2.11.0` - Data validation
- `pydantic-settings>=2.9.0` - Settings management

**Vector Database:**
- `qdrant-client>=1.14.2` - Qdrant client library

**Embedding Models:**
- `sentence-transformers>=4.1.0` - Text embeddings
- `fastembed>=0.0.1` - Fast embedding generation

**Utilities:**
- `python-dotenv>=1.1.0` - Environment management
- `rapidfuzz>=3.13.0` - Fuzzy string matching
- `numpy>=1.21.0` - Numerical operations
- `python-multipart>=0.0.5` - File uploads

### 2. **Development Dependencies**

**Indexing & Processing:**
- `aiohttp>=3.8.5` - Async HTTP client
- `psutil>=6.0.0` - System monitoring
- `datasets>=2.14.5` - Data processing
- `tqdm` - Progress bars

**Logging:**
- `loguru>=0.5.3` - Advanced logging

### 3. **Dependency Hierarchy**

```
app/main.py
├── app/services/search_service.py
│   ├── fastembed
│   ├── qdrant_client
│   └── app/core/database.py
│       ├── sentence_transformers
│       └── qdrant_client
├── app/core/logging.py
├── app/config/config.py
└── app/api/endpoints/search.py
    └── app/services/search_service.py

scripts/indexing.py
├── fastembed
├── qdrant_client
├── datasets
└── tqdm
```

---

## 🎯 Key Features

### 1. **Performance Optimizations**
- **Ultra-fast search** (25-40ms response times)
- **Parallel processing** with thread pools
- **Memory optimization** with quantization
- **Caching** for embeddings and results
- **gRPC communication** with Qdrant

### 2. **Search Capabilities**
- **Hybrid search** (exact + semantic)
- **Fusion search** with parallel execution
- **Part number detection** for intelligent routing
- **Filtering** by product attributes
- **Multiple search strategies** for different use cases

### 3. **Data Management**
- **Bulk indexing** with memory optimization
- **Version control** for document history
- **Import/export** functionality
- **Delta updates** for incremental processing
- **Data validation** and error handling

### 4. **Monitoring & Diagnostics**
- **Performance tracking** and statistics
- **Health monitoring** endpoints
- **Collection diagnostics** and optimization
- **Comprehensive logging** with rotation
- **Error handling** with custom exceptions

---

## 🚀 Deployment

### 1. **Docker Deployment**
```yaml
# docker-compose.yml
services:
  vector-search-server:
    build: .
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - COLLECTION_NAME=products_vector
      - MODEL_NAME=BAAI/bge-small-en-v1.5
```

### 2. **Environment Configuration**
```bash
# .env file
HOST=localhost
PORT=6333
COLLECTION_NAME=products_fast
VECTOR_SIZE=384
SEARCH_LIMIT=100
SCORE_THRESHOLD=0.7
```

### 3. **Service Startup**
```bash
# Start the service
python -m app.main

# Run indexing
python scripts/indexing.py

# Test performance
python scripts/test_speed.py
```

---

This documentation provides a comprehensive overview of the Qdrant vector search service architecture, showing how each component interacts and contributes to the overall system functionality. 
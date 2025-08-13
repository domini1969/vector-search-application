from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(".env")

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Qdrant server settings
    HOST: str = os.getenv("HOST", "localhost")
    PORT: int = int(os.getenv("PORT", "6333"))
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "6334"))
    API_KEY: Optional[str] = os.getenv("API_KEY")
    USE_HTTPS: bool = os.getenv("USE_HTTPS", "false").lower() == "true"
    
    # Collection settings
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "products")
    VECTOR_SIZE: int = int(os.getenv("VECTOR_SIZE", "384"))  # Default for bge-small-en-v1.5
    
    # Search settings
    SEARCH_LIMIT: int = int(os.getenv("SEARCH_LIMIT", "100"))
    SCORE_THRESHOLD: float = float(os.getenv("SCORE_THRESHOLD", "0.7"))
    
    # Spell check settings
    SPELLCHECK: bool = os.getenv("SPELLCHECK", "true").lower() == "true"
    SPELLCHECK_THRESHOLD: int = int(os.getenv("SPELLCHECK_THRESHOLD", "80"))
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_PATH: str = os.getenv("LOG_PATH", "logs/service.log")
    ENABLE_DETAILED_SEARCH_LOGS: bool = os.getenv("ENABLE_DETAILED_SEARCH_LOGS", "true").lower() == "true"
    DEBUG_UI: bool = os.getenv("DEBUG_UI", "false").lower() == "true"  # UI/Frontend debugging
    
    # Schema settings
    ID_FIELD: str = os.getenv("ID_FIELD", "partNumber_airgas_text")  # Default to "partNumber_airgas_text" if not set
    TEXT_FIELD: str = os.getenv("TEXT_FIELD", "shortDescription_airgas_text")  # Default to "shortDescription_airgas_text" if not set
    
    # Model settings
    MODEL_NAME: str = os.getenv("MODEL_NAME", "BAAI/bge-small-en-v1.5")
    CROSS_ENCODER_MODEL: str = os.getenv("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    # Reranking weights
    VECTOR_SCORE_WEIGHT: float = float(os.getenv("VECTOR_SCORE_WEIGHT", "0.2"))
    CROSS_ENCODER_WEIGHT: float = float(os.getenv("CROSS_ENCODER_WEIGHT", "0.8"))
    
    # ====== NEW: SEARCH UI CONFIGURATION ======
    # Search API Configuration
    SEARCH_API_HOST: str = os.getenv("SEARCH_API_HOST", "localhost")
    SEARCH_API_PORT: str = os.getenv("SEARCH_API_PORT", "8000")
    
    # Default search endpoint type
    # Options: ultra-fast, fusion, lean, really-fast, basic, query
    SEARCH_ENDPOINT_TYPE: str = os.getenv("SEARCH_ENDPOINT_TYPE", "fusion")
    
    # UI Feature Toggles
    SHOW_SEARCH_TYPE_SELECTOR: bool = os.getenv("SHOW_SEARCH_TYPE_SELECTOR", "true").lower() == "true"
    SHOW_PERFORMANCE_STATS: bool = os.getenv("SHOW_PERFORMANCE_STATS", "true").lower() == "true"
    
    # ====== PERFORMANCE OPTIMIZATION SETTINGS ======
    # System-level thread limiting for better performance
    MAX_SEARCH_THREADS: int = int(os.getenv("MAX_SEARCH_THREADS", "2"))
    OMP_NUM_THREADS: int = int(os.getenv("OMP_NUM_THREADS", "2"))
    MKL_NUM_THREADS: int = int(os.getenv("MKL_NUM_THREADS", "2"))
    TOKENIZERS_PARALLELISM: bool = os.getenv("TOKENIZERS_PARALLELISM", "false").lower() == "true"
    
    # Vector search optimization
    VECTOR_SEARCH_LIMIT: int = int(os.getenv("VECTOR_SEARCH_LIMIT", "35"))
    CROSS_ENCODER_LIMIT: int = int(os.getenv("CROSS_ENCODER_LIMIT", "25"))
    HNSW_EF: int = int(os.getenv("HNSW_EF", "48"))
    
    # Caching settings
    SEARCH_CACHE_TTL: int = int(os.getenv("SEARCH_CACHE_TTL", "300"))
    SEARCH_CACHE_MAX_SIZE: int = int(os.getenv("SEARCH_CACHE_MAX_SIZE", "1000"))
    
    # Threading optimization
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "3"))
    THREAD_POOL_SIZE: int = int(os.getenv("THREAD_POOL_SIZE", "3"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set system environment variables for threading optimization
        os.environ['OMP_NUM_THREADS'] = str(self.OMP_NUM_THREADS)
        os.environ['MKL_NUM_THREADS'] = str(self.MKL_NUM_THREADS)
        os.environ['TOKENIZERS_PARALLELISM'] = str(self.TOKENIZERS_PARALLELISM).lower()
        os.environ['MAX_SEARCH_THREADS'] = str(self.MAX_SEARCH_THREADS)

# Create settings instance
settings = Settings()
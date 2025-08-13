# app/config/__init__.py
# Configuration package initialization

from app.config.config import settings

# For backward compatibility
try:
    from app.config.config import settings, ensure_directories
except ImportError:
    # Create a dummy ensure_directories function if not available
    def ensure_directories():
        pass

# Export everything that should be available when importing from app.config
__all__ = ["settings", "ensure_directories"]
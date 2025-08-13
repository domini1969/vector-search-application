FROM python:3.12.5-slim

# Install system dependencies in a single layer
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    libatlas-base-dev \
    liblapack-dev \
    libblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Streamlit for UI
RUN pip install --no-cache-dir streamlit

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data

# Expose ports
EXPOSE 8000 8501

# Health check with curl available
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 
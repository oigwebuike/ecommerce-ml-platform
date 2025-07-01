# Multi-stage build for production deployment
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config/ ./config/
COPY run_demo.py .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "src/4_ml_inference_api.py"]

# Build variants for different services
FROM base as data-generator
CMD ["python", "src/1_data_generator.py"]

FROM base as stream-processor  
CMD ["python", "src/2_stream_processor.py"]

FROM base as batch-processor
CMD ["python", "src/3_batch_processor.py"]

FROM base as ml-api
EXPOSE 8000
CMD ["uvicorn", "src.4_ml_inference_api:app", "--host", "0.0.0.0", "--port", "8000"]
# Multi-stage Dockerfile for Ingestion API
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies with cache mount
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r app && useradd -r -g app app

# Set work directory
WORKDIR /app

# Development stage
FROM base as development

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Change ownership
RUN chown -R app:app /app

USER app

EXPOSE 8000

CMD ["python", "main.py"]

# Production stage
FROM base as production

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install gunicorn==21.2.0

# Copy application code
COPY . .

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Create necessary directories
RUN mkdir -p /app/logs \
    && chown -R app:app /app

USER app

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "main:app"]

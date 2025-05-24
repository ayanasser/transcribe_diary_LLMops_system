# Multi-stage Dockerfile for Job Status API
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
    curl \
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

# Copy application code
COPY . .

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Create necessary directories
RUN mkdir -p /app/storage \
    && chown -R app:app /app

USER app

EXPOSE 8001

CMD ["python", "main.py"]

# Production stage
FROM base as production

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt \
    && pip install gunicorn==21.2.0

# Copy application code
COPY . .

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Create necessary directories
RUN mkdir -p /app/storage /app/logs \
    && chown -R app:app /app

USER app

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8001", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "main:app"]

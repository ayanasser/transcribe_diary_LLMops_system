import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps

import structlog
from prometheus_client import Counter, Histogram, Gauge
import redis
from shared.config.settings import settings


# Prometheus metrics
REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')
JOB_COUNT = Counter('jobs_total', 'Total jobs processed', ['status'])
JOB_DURATION = Histogram('job_duration_seconds', 'Job processing time', ['service'])
ACTIVE_JOBS = Gauge('active_jobs', 'Currently active jobs', ['service'])


def setup_logging():
    """Configure structured logging"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.monitoring.log_level.upper()),
    )


def get_logger(name: str):
    """Get a structured logger instance"""
    return structlog.get_logger(name)


class RedisClient:
    """Redis client wrapper with connection pooling"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            db=settings.redis.db,
            password=settings.redis.password,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=60,  # Increased for blocking operations
            retry_on_timeout=True,
            health_check_interval=30
        )
    
    def publish(self, channel: str, message: Dict[str, Any]):
        """Publish message to Redis channel"""
        return self.redis_client.publish(channel, json.dumps(message))
    
    def subscribe(self, channel: str):
        """Subscribe to Redis channel"""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(channel)
        return pubsub
    
    def set_job_status(self, job_id: str, status: str, data: Optional[Dict] = None):
        """Set job status in Redis"""
        job_data = {"status": status, "updated_at": datetime.utcnow().isoformat()}
        if data:
            job_data.update(data)
        
        return self.redis_client.hset(f"job:{job_id}", mapping=job_data)
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get job status from Redis"""
        data = self.redis_client.hgetall(f"job:{job_id}")
        return data if data else None
    
    def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False


def track_job_metrics(service_name: str):
    """Decorator to track job processing metrics"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            ACTIVE_JOBS.labels(service=service_name).inc()
            
            try:
                result = func(*args, **kwargs)
                JOB_COUNT.labels(status='completed').inc()
                return result
            except Exception as e:
                JOB_COUNT.labels(status='failed').inc()
                raise
            finally:
                duration = time.time() - start_time
                JOB_DURATION.labels(service=service_name).observe(duration)
                ACTIVE_JOBS.labels(service=service_name).dec()
        
        return wrapper
    return decorator


def validate_audio_url(url: str) -> bool:
    """Validate audio URL format and accessibility"""
    import requests
    from urllib.parse import urlparse
    
    try:
        # Parse URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Check if URL is accessible (HEAD request)
        response = requests.head(url, timeout=10)
        if response.status_code not in [200, 206]:
            return False
        
        # Check content type if available
        content_type = response.headers.get('content-type', '').lower()
        if content_type and content_type not in settings.allowed_audio_formats:
            return False
        
        # Check content length if available
        content_length = response.headers.get('content-length')
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > settings.max_file_size_mb:
                return False
        
        return True
    except Exception:
        return False


def download_file(url: str, output_path: str, chunk_size: int = 8192) -> bool:
    """Download file from URL with progress tracking"""
    import requests
    
    try:
        with requests.get(url, stream=True, timeout=30) as response:
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
        
        return True
    except Exception as e:
        get_logger(__name__).error("Failed to download file", url=url, error=str(e))
        return False


def ensure_directory(path: str):
    """Ensure directory exists"""
    import os
    os.makedirs(path, exist_ok=True)


# Global Redis client instance
redis_client = RedisClient()

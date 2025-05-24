# MIT License
# Copyright (c) 2025 Aya Nasser
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.



from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from datetime import datetime, timedelta
from typing import Dict, List
import uvicorn

from shared.models.schemas import JobRequest, JobResponse, HealthCheck, ErrorResponse, generate_job_id, JobStatus
from shared.config.settings import settings
from shared.utils.helpers import (
    setup_logging, get_logger, redis_client, REQUEST_COUNT, REQUEST_DURATION,
    validate_audio_url, track_job_metrics
)
from shared.utils.telemetry import setup_telemetry, create_span, inject_context_into_headers


# Setup
setup_logging()
logger = get_logger(__name__)
tracer = setup_telemetry("ingestion-api")

app = FastAPI(
    title="Audio Transcription Ingestion API",
    description="API for submitting audio transcription jobs",
    version="1.0.0"
)

# Add OpenTelemetry instrumentation if enabled
if settings.observability.enable_traces:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer)
    RedisInstrumentor.instrument(tracer_provider=tracer)
    
    logger.info("OpenTelemetry instrumentation enabled for FastAPI and Redis")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting storage
rate_limit_store: Dict[str, List[float]] = {}


def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def rate_limit_check(request: Request) -> bool:
    """Check rate limiting for client IP"""
    client_ip = get_client_ip(request)
    current_time = time.time()
    
    # Clean old entries (older than 1 hour)
    if client_ip in rate_limit_store:
        rate_limit_store[client_ip] = [
            timestamp for timestamp in rate_limit_store[client_ip]
            if current_time - timestamp < 3600
        ]
    else:
        rate_limit_store[client_ip] = []
    
    # Check hourly limit
    if len(rate_limit_store[client_ip]) >= settings.rate_limit.requests_per_hour:
        return False
    
    # Check per-minute limit
    minute_ago = current_time - 60
    recent_requests = [
        timestamp for timestamp in rate_limit_store[client_ip]
        if timestamp > minute_ago
    ]
    
    if len(recent_requests) >= settings.rate_limit.requests_per_minute:
        return False
    
    # Add current request
    rate_limit_store[client_ip].append(current_time)
    return True


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time and metrics"""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    REQUEST_DURATION.observe(process_time)
    
    return response


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    dependencies = {
        "redis": "healthy" if redis_client.health_check() else "unhealthy"
    }
    
    return HealthCheck(dependencies=dependencies)


@app.post("/jobs", response_model=JobResponse)
async def submit_job(job_request: JobRequest, request: Request):
    """Submit a new transcription job"""
    
    # Rate limiting check
    if not rate_limit_check(request):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    
    # Validate audio URL
    if not validate_audio_url(str(job_request.audio_url)):
        raise HTTPException(
            status_code=400,
            detail="Invalid or inaccessible audio URL"
        )
    
    # Generate job ID
    job_id = generate_job_id()
    
    try:
        # Create a span for job processing
        with create_span(
            "submit_transcription_job",
            attributes={
                "job.id": job_id,
                "job.priority": job_request.priority,
                "job.model": job_request.whisper_model,
                "client.ip": get_client_ip(request)
            }
        ):
            # Create job record
            job_data = {
                "job_id": job_id,
                "status": JobStatus.PENDING,
                "audio_url": str(job_request.audio_url),
                "priority": job_request.priority,
                "whisper_model": job_request.whisper_model,
                "user_id": job_request.user_id,
                "metadata": job_request.metadata,
                "created_at": datetime.utcnow().isoformat(),
                "client_ip": get_client_ip(request),
                "trace_id": tracer.get_current_span().get_span_context().trace_id if settings.observability.enable_traces else None
            }
            
            # Store job in Redis
            with create_span("redis_set_job_status"):
                redis_client.set_job_status(job_id, JobStatus.PENDING, job_data)
            
            # Publish to transcription queue
            transcription_task = {
                "job_id": job_id,
                "audio_url": str(job_request.audio_url),
                "whisper_model": job_request.whisper_model,
                "priority": job_request.priority,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Publish to Redis queue with span tracking
            with create_span("redis_publish_task"):
                redis_client.publish("transcription_queue", transcription_task)
            
            logger.info("Job submitted successfully", job_id=job_id, priority=job_request.priority)
        
        # Estimate completion time based on priority
        priority_delays = {
            "urgent": 5,
            "high": 15,
            "medium": 30,
            "low": 60
        }
        estimated_completion = datetime.utcnow() + timedelta(
            minutes=priority_delays.get(job_request.priority, 30)
        )
        
        return JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
            estimated_completion=estimated_completion
        )
        
    except Exception as e:
        logger.error("Failed to submit job", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to submit job. Please try again."
        )
        
    except Exception as e:
        logger.error("Failed to submit job", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to submit job. Please try again."
        )


@app.get("/jobs/{job_id}", response_model=Dict)
async def get_job_status(job_id: str):
    """Get job status and details"""
    job_data = redis_client.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    
    return job_data


@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a pending job"""
    job_data = redis_client.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    
    if job_data.get("status") not in [JobStatus.PENDING, JobStatus.DOWNLOADING]:
        raise HTTPException(
            status_code=400,
            detail="Job cannot be cancelled in current status"
        )
    
    # Update job status to cancelled
    redis_client.set_job_status(job_id, "cancelled")
    
    logger.info("Job cancelled", job_id=job_id)
    
    return {"message": "Job cancelled successfully"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=f"HTTP {exc.status_code}",
            message=exc.detail
        ).dict()
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.monitoring.log_level.lower()
    )

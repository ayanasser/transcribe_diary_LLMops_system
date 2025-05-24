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



from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Dict, List, Optional
import uvicorn
from pathlib import Path

from shared.models.schemas import JobDetails, HealthCheck, JobStatus
from shared.config.settings import settings
from shared.utils.helpers import setup_logging, get_logger, redis_client


setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Audio Transcription Job Status API",
    description="API for tracking job progress and retrieving results",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    dependencies = {
        "redis": "healthy" if redis_client.health_check() else "unhealthy"
    }
    
    return HealthCheck(dependencies=dependencies)


@app.get("/jobs/{job_id}", response_model=Dict)
async def get_job_details(job_id: str):
    """Get detailed job information"""
    job_data = redis_client.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    
    return job_data


@app.get("/jobs/{job_id}/transcription")
async def get_transcription(job_id: str):
    """Get the transcription text for a job"""
    job_data = redis_client.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    
    if job_data.get("status") not in [JobStatus.GENERATING_NOTES, JobStatus.COMPLETED]:
        raise HTTPException(
            status_code=400,
            detail="Transcription not yet available"
        )
    
    transcription = job_data.get("transcription")
    if not transcription:
        # Try to read from file
        transcription_path = job_data.get("transcription_path")
        if transcription_path and Path(transcription_path).exists():
            with open(transcription_path, 'r', encoding='utf-8') as f:
                transcription = f.read()
    
    if not transcription:
        raise HTTPException(
            status_code=404,
            detail="Transcription not available"
        )
    
    return {"transcription": transcription}


@app.get("/jobs/{job_id}/diary-note")
async def get_diary_note(job_id: str):
    """Get the generated diary note for a job"""
    job_data = redis_client.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    
    if job_data.get("status") != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Diary note not yet available"
        )
    
    diary_note = job_data.get("diary_note")
    if not diary_note:
        # Try to read from file
        diary_note_path = job_data.get("diary_note_path")
        if diary_note_path and Path(diary_note_path).exists():
            with open(diary_note_path, 'r', encoding='utf-8') as f:
                diary_note = f.read()
    
    if not diary_note:
        raise HTTPException(
            status_code=404,
            detail="Diary note not available"
        )
    
    return {"diary_note": diary_note}


@app.get("/jobs/{job_id}/download/transcription")
async def download_transcription(job_id: str):
    """Download transcription as a text file"""
    job_data = redis_client.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    
    transcription_path = job_data.get("transcription_path")
    if not transcription_path or not Path(transcription_path).exists():
        raise HTTPException(
            status_code=404,
            detail="Transcription file not found"
        )
    
    return FileResponse(
        path=transcription_path,
        filename=f"transcription_{job_id}.txt",
        media_type="text/plain"
    )


@app.get("/jobs/{job_id}/download/diary-note")
async def download_diary_note(job_id: str):
    """Download diary note as a markdown file"""
    job_data = redis_client.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    
    diary_note_path = job_data.get("diary_note_path")
    if not diary_note_path or not Path(diary_note_path).exists():
        raise HTTPException(
            status_code=404,
            detail="Diary note file not found"
        )
    
    return FileResponse(
        path=diary_note_path,
        filename=f"diary_note_{job_id}.md",
        media_type="text/markdown"
    )


@app.get("/jobs", response_model=List[Dict])
async def list_jobs(
    status: Optional[JobStatus] = None,
    user_id: Optional[str] = None,
    limit: int = 100
):
    """List jobs with optional filtering"""
    # This is a simple implementation using Redis SCAN
    # In production, you'd use a proper database with indexing
    
    job_keys = []
    cursor = 0
    
    while True:
        cursor, keys = redis_client.redis_client.scan(
            cursor=cursor,
            match="job:*",
            count=100
        )
        job_keys.extend(keys)
        
        if cursor == 0:
            break
    
    jobs = []
    for key in job_keys[:limit]:
        job_data = redis_client.redis_client.hgetall(key)
        if job_data:
            # Filter by status if specified
            if status and job_data.get("status") != status:
                continue
            
            # Filter by user_id if specified
            if user_id and job_data.get("user_id") != user_id:
                continue
            
            jobs.append(job_data)
    
    return jobs


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its associated files"""
    job_data = redis_client.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    
    # Delete files
    storage_path = Path(settings.storage.local_path)
    
    transcription_path = job_data.get("transcription_path")
    if transcription_path and Path(transcription_path).exists():
        Path(transcription_path).unlink()
    
    diary_note_path = job_data.get("diary_note_path")
    if diary_note_path and Path(diary_note_path).exists():
        Path(diary_note_path).unlink()
    
    # Delete from Redis
    redis_client.redis_client.delete(f"job:{job_id}")
    
    logger.info("Job deleted", job_id=job_id)
    
    return {"message": "Job deleted successfully"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.debug,
        log_level=settings.monitoring.log_level.lower()
    )

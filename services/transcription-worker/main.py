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



import os
import json
import time
import hashlib
import tempfile
from datetime import datetime
from pathlib import Path

import whisper
import torch
import redis
import redis
from shared.models.schemas import JobStatus, TranscriptionTask
from shared.config.settings import settings
from shared.utils.helpers import (
    setup_logging, get_logger, redis_client, track_job_metrics,
    download_file, ensure_directory
)


setup_logging()
logger = get_logger(__name__)


class TranscriptionWorker:
    """Whisper-based transcription worker"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() and settings.whisper.device == "cuda" else "cpu"
        self.loaded_models = {}
        self.storage_path = Path(settings.storage.local_path)
        ensure_directory(str(self.storage_path))
        
        logger.info("Transcription worker initialized", device=self.device)
    
    def get_model(self, model_name: str):
        """Load and cache Whisper model"""
        if model_name not in self.loaded_models:
            logger.info("Loading Whisper model", model=model_name)
            
            model = whisper.load_model(
                model_name,
                device=self.device,
                download_root=settings.whisper.cache_dir
            )
            self.loaded_models[model_name] = model
            
            logger.info("Model loaded successfully", model=model_name)
        
        return self.loaded_models[model_name]
    
    def get_audio_hash(self, file_path: str) -> str:
        """Generate hash of audio file for deduplication"""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def profile_audio(self, file_path: str) -> dict:
        """Profile audio file to get metadata"""
        try:
            import librosa
            
            # Load audio to get duration and sample rate
            y, sr = librosa.load(file_path, sr=None)
            duration = len(y) / sr
            
            return {
                "duration_seconds": duration,
                "sample_rate": sr,
                "channels": 1 if len(y.shape) == 1 else y.shape[0],
                "file_size_bytes": os.path.getsize(file_path)
            }
        except Exception as e:
            logger.warning("Failed to profile audio", error=str(e))
            return {
                "file_size_bytes": os.path.getsize(file_path)
            }
    
    @track_job_metrics("transcription")
    def process_job(self, task_data: dict):
        """Process a transcription job"""
        job_id = task_data["job_id"]
        audio_url = task_data["audio_url"]
        model_name = task_data["whisper_model"]
        
        logger.info("Starting transcription job", job_id=job_id, model=model_name)
        
        try:
            # Update job status
            redis_client.set_job_status(job_id, JobStatus.DOWNLOADING)
            
            # Download audio file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".audio") as temp_file:
                temp_path = temp_file.name
            
            if not download_file(audio_url, temp_path):
                raise Exception("Failed to download audio file")
            
            # Profile audio
            audio_profile = self.profile_audio(temp_path)
            logger.info("Audio profiled", job_id=job_id, **audio_profile)
            
            # Check for duplicate processing
            audio_hash = self.get_audio_hash(temp_path)
            existing_result = self.check_existing_transcription(audio_hash)
            
            if existing_result:
                logger.info("Using cached transcription", job_id=job_id, hash=audio_hash)
                transcription = existing_result
            else:
                # Update job status
                redis_client.set_job_status(job_id, JobStatus.TRANSCRIBING)
                
                # Load model and transcribe
                model = self.get_model(model_name)
                
                logger.info("Starting transcription", job_id=job_id)
                start_time = time.time()
                
                result = model.transcribe(temp_path)
                transcription = result["text"]
                
                transcription_time = time.time() - start_time
                logger.info(
                    "Transcription completed",
                    job_id=job_id,
                    duration=transcription_time,
                    text_length=len(transcription)
                )
                
                # Cache result
                self.cache_transcription(audio_hash, transcription)
            
            # Save transcription to storage
            transcription_path = self.save_transcription(job_id, transcription)
            
            # Update job with transcription
            update_data = {
                "transcription": transcription,
                "transcription_path": transcription_path,
                "audio_profile": audio_profile,
                "audio_hash": audio_hash
            }
            redis_client.set_job_status(job_id, JobStatus.TRANSCRIBING, update_data)
            
            # Publish to LLM queue
            llm_task = {
                "job_id": job_id,
                "transcription": transcription,
                "transcription_path": transcription_path,
                "priority": task_data.get("priority", "medium"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            redis_client.publish("llm_queue", llm_task)
            
            logger.info("Job forwarded to LLM processing", job_id=job_id)
            
        except Exception as e:
            logger.error("Transcription job failed", job_id=job_id, error=str(e))
            redis_client.set_job_status(
                job_id,
                JobStatus.FAILED,
                {"error_message": str(e)}
            )
        finally:
            # Cleanup
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def check_existing_transcription(self, audio_hash: str) -> str:
        """Check if transcription already exists for this audio hash"""
        cache_key = f"transcription_cache:{audio_hash}"
        return redis_client.redis_client.get(cache_key)
    
    def cache_transcription(self, audio_hash: str, transcription: str):
        """Cache transcription result"""
        cache_key = f"transcription_cache:{audio_hash}"
        # Cache for 30 days
        redis_client.redis_client.setex(cache_key, 30 * 24 * 3600, transcription)
    
    def save_transcription(self, job_id: str, transcription: str) -> str:
        """Save transcription to persistent storage"""
        output_path = self.storage_path / "transcriptions" / f"{job_id}.txt"
        ensure_directory(str(output_path.parent))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(transcription)
        
        return str(output_path)
    
    def run(self):
        """Run the worker to process transcription jobs"""
        logger.info("Starting transcription worker")
        
        # Subscribe to transcription queue
        pubsub = redis_client.subscribe("transcription_queue")
        
        while True:
            try:
                # Use get_message with timeout instead of listen()
                message = pubsub.get_message(timeout=30)
                
                if message is None:
                    # No message received within timeout, continue
                    logger.debug("No message received, continuing...")
                    continue
                    
                if message['type'] == 'message':
                    try:
                        task_data = json.loads(message['data'])
                        self.process_job(task_data)
                    except Exception as e:
                        logger.error("Failed to process message", error=str(e))
                        
            except redis.ConnectionError as e:
                logger.error("Redis connection error, retrying in 5 seconds...", error=str(e))
                time.sleep(5)
                # Reconnect
                pubsub = redis_client.subscribe("transcription_queue")
            except Exception as e:
                logger.error("Unexpected error in worker loop", error=str(e))
                time.sleep(1)


if __name__ == "__main__":
    worker = TranscriptionWorker()
    worker.run()

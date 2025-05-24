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
from datetime import datetime
from pathlib import Path

import redis
import openai
from shared.models.schemas import JobStatus
from shared.config.settings import settings
from shared.utils.helpers import (
    setup_logging, get_logger, redis_client, track_job_metrics,
    ensure_directory
)
from shared.utils.llm_router import llm_router


setup_logging()
logger = get_logger(__name__)


class LLMWorker:
    """LLM-powered note generation worker with fallback capabilities"""
    
    def __init__(self):
        # Initialize storage
        self.storage_path = Path(settings.storage.local_path)
        ensure_directory(str(self.storage_path))
        
        logger.info("LLM worker initialized")
    
    def generate_diary_prompt(self, transcription: str) -> str:
        """Generate a comprehensive prompt for diary note creation"""
        return f"""Convert the following transcription into a well-structured personal diary entry. 

Create a thoughtful, reflective diary note with the following sections:

📅 **Date & Time**: Today's date and approximate time
😊 **Mood/Feelings**: Emotional state and general feelings expressed
🌟 **Key Events**: Main activities, experiences, or topics discussed
💭 **Thoughts & Reflections**: Personal insights, learnings, or deeper thoughts
🎯 **Takeaways**: Important points or actions to remember

Guidelines:
- Write in first person as if the person is writing their own diary
- Maintain a personal, authentic tone
- Focus on the emotional and experiential aspects
- Keep it concise but meaningful
- If multiple topics are discussed, organize them logically

Transcription:
{transcription}

Please create a personal diary entry based on this content:"""
    
    @track_job_metrics("llm")
    def process_job(self, task_data: dict):
        """Process an LLM job to generate diary notes"""
        job_id = task_data["job_id"]
        transcription = task_data.get("transcription", "")
        
        logger.info("Starting LLM job", job_id=job_id, text_length=len(transcription))
        
        try:
            # Update job status
            redis_client.set_job_status(job_id, JobStatus.GENERATING_NOTES)
            
            # Read transcription from file if path provided
            if not transcription and "transcription_path" in task_data:
                with open(task_data["transcription_path"], 'r', encoding='utf-8') as f:
                    transcription = f.read()
            
            if not transcription:
                raise Exception("No transcription content available")
            
            # Generate diary note
            diary_note = self.generate_diary_note(transcription)
            
            # Save diary note to storage
            note_path = self.save_diary_note(job_id, diary_note)
            
            # Update job with completion
            completion_data = {
                "diary_note": diary_note,
                "diary_note_path": note_path,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            redis_client.set_job_status(job_id, JobStatus.COMPLETED, completion_data)
            
            logger.info(
                "LLM job completed successfully",
                job_id=job_id,
                note_length=len(diary_note)
            )
            
        except Exception as e:
            logger.error("LLM job failed", job_id=job_id, error=str(e))
            redis_client.set_job_status(
                job_id,
                JobStatus.FAILED,
                {"error_message": str(e)}
            )
    
    def generate_diary_note(self, transcription: str) -> str:
        """Generate diary note using LLM router with fallback capabilities"""
        prompt = self.generate_diary_prompt(transcription)
        system_prompt = "You are a thoughtful assistant that helps people create meaningful personal diary entries from their spoken thoughts or experiences. Focus on emotional depth, personal reflection, and authentic expression."
        
        try:
            logger.info("Calling LLM router")
            start_time = time.time()
            
            # Generate diary note with intelligent provider selection and fallback
            diary_note, provider_info = llm_router.generate_text(prompt, system_prompt)
            
            api_time = time.time() - start_time
            
            logger.info(
                "LLM generation completed",
                duration=api_time,
                provider=provider_info,
                response_length=len(diary_note)
            )
            
            return diary_note
            
        except Exception as e:
            logger.error("All LLM generation attempts failed", error=str(e))
            # Last resort fallback
            return self.generate_fallback_note(transcription)
    
    def generate_fallback_note(self, transcription: str) -> str:
        """Generate a simple fallback diary note when API fails"""
        return f"""📅 **Date & Time**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

😊 **Mood/Feelings**: [Unable to analyze due to service limitation]

🌟 **Key Events**: 
{transcription[:500]}{'...' if len(transcription) > 500 else ''}

💭 **Thoughts & Reflections**: 
This is a transcribed recording that needs further personal reflection.

🎯 **Takeaways**: 
Review the full transcription for important points and personal insights.

---
*Note: This entry was automatically generated as a fallback when the full AI processing was unavailable.*"""
    
    def save_diary_note(self, job_id: str, diary_note: str) -> str:
        """Save diary note to persistent storage"""
        output_path = self.storage_path / "diary_notes" / f"{job_id}.md"
        ensure_directory(str(output_path.parent))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(diary_note)
        
        return str(output_path)
    
    def run(self):
        """Run the worker to process LLM jobs"""
        logger.info("Starting LLM worker")
        
        # Subscribe to LLM queue
        pubsub = redis_client.subscribe("llm_queue")
        
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
                pubsub = redis_client.subscribe("llm_queue")
            except Exception as e:
                logger.error("Unexpected error in worker loop", error=str(e))
                time.sleep(1)


if __name__ == "__main__":
    worker = LLMWorker()
    worker.run()

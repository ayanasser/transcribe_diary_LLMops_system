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



"""
Integration test for the full audio transcription and note generation pipeline.

This test verifies the end-to-end flow from job submission to final diary note generation.
It uses Docker Compose to spin up the required services and tests the whole system together.
"""
import os
import time
import unittest
import uuid
import json
import requests
from pathlib import Path

import pytest


@pytest.mark.integration
class TestFullPipeline(unittest.TestCase):
    """Integration test for the full transcription pipeline"""
    
    INGESTION_API_URL = os.environ.get("INGESTION_API_URL", "http://localhost:8000")
    JOB_STATUS_API_URL = os.environ.get("JOB_STATUS_API_URL", "http://localhost:8001")
    TEST_AUDIO_URL = os.environ.get(
        "TEST_AUDIO_URL",
        "https://github.com/openai/whisper/raw/main/tests/jfk.flac"  # Public audio file from Whisper repo
    )
    TIMEOUT_SECONDS = int(os.environ.get("TEST_TIMEOUT_SECONDS", "300"))  # 5 minutes
    
    def test_full_pipeline(self):
        """Test the complete audio processing pipeline"""
        # 1. Submit a new job
        job_id = self._submit_job()
        self.assertIsNotNone(job_id)
        
        # 2. Wait for job to complete
        final_status, job_details = self._wait_for_job_completion(job_id)
        
        # 3. Verify successful completion
        self.assertEqual(final_status, "completed")
        self.assertIsNotNone(job_details)
        self.assertIn("diary_note", job_details)
        self.assertIsNotNone(job_details.get("diary_note"))
        self.assertTrue(len(job_details.get("diary_note", "")) > 0)
        self.assertTrue(len(job_details.get("transcription", "")) > 0)
        
        # 4. Check transcription and diary note content
        self._validate_content(job_details)
        
        print(f"✅ Full pipeline test passed! Job ID: {job_id}")
        print(f"Transcription length: {len(job_details.get('transcription', ''))} chars")
        print(f"Diary note length: {len(job_details.get('diary_note', ''))} chars")
    
    def _submit_job(self):
        """Submit a new job to the ingestion API"""
        payload = {
            "audio_url": self.TEST_AUDIO_URL,
            "priority": "high",
            "whisper_model": "base",
            "metadata": {"test_id": str(uuid.uuid4())}
        }
        
        try:
            response = requests.post(
                f"{self.INGESTION_API_URL}/jobs",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("job_id")
        except requests.RequestException as e:
            self.fail(f"Failed to submit job: {str(e)}")
    
    def _wait_for_job_completion(self, job_id):
        """Wait for the job to complete or fail"""
        start_time = time.time()
        terminal_states = ["completed", "failed"]
        
        while time.time() - start_time < self.TIMEOUT_SECONDS:
            try:
                response = requests.get(
                    f"{self.JOB_STATUS_API_URL}/jobs/{job_id}",
                    timeout=30
                )
                
                if response.status_code == 200:
                    job_data = response.json()
                    status = job_data.get("status")
                    
                    # Print progress
                    print(f"Job status: {status} ({int(time.time() - start_time)}s elapsed)")
                    
                    if status in terminal_states:
                        return status, job_data
                
                # Wait before next check
                time.sleep(5)
                
            except requests.RequestException as e:
                print(f"Error checking job status: {str(e)}")
                time.sleep(5)
        
        self.fail(f"Job did not complete within timeout ({self.TIMEOUT_SECONDS}s)")
    
    def _validate_content(self, job_details):
        """Validate the content of transcription and diary note"""
        transcription = job_details.get("transcription", "")
        diary_note = job_details.get("diary_note", "")
        
        # Basic validation
        self.assertTrue(len(transcription) > 50)
        self.assertTrue(len(diary_note) > 100)
        
        # Check diary note structure
        self.assertIn("Date & Time", diary_note)
        self.assertIn("Mood/Feelings", diary_note)
        self.assertIn("Key Events", diary_note)
        self.assertIn("Thoughts & Reflections", diary_note)
        
        # Ensure some content from transcription is reflected in note
        # Extract some keywords from transcription (basic check)
        words = transcription.split()
        keywords = [w for w in words if len(w) > 5][:3]  # Get 3 long words
        
        # At least one keyword should be in the diary note
        keyword_found = any(keyword.lower() in diary_note.lower() for keyword in keywords)
        self.assertTrue(keyword_found, f"None of the keywords {keywords} found in diary note")


if __name__ == "__main__":
    unittest.main()

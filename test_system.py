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



#!/usr/bin/env python3
"""
Test script for the Audio Transcription & Note Generation System
"""

import requests
import time
import json
from datetime import datetime


class TranscriptionSystemTester:
    def __init__(self, base_url="http://localhost:8000", status_url="http://localhost:8001"):
        self.base_url = base_url
        self.status_url = status_url
    
    def test_health_checks(self):
        """Test health endpoints"""
        print("🔍 Testing health checks...")
        
        # Test ingestion API health
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Ingestion API health check passed")
            else:
                print(f"❌ Ingestion API health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Ingestion API health check failed: {e}")
        
        # Test status API health
        try:
            response = requests.get(f"{self.status_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Status API health check passed")
            else:
                print(f"❌ Status API health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Status API health check failed: {e}")
    
    def submit_test_job(self, audio_url=None, priority="medium"):
        """Submit a test transcription job"""
        if not audio_url:
            # Use a sample audio file
            audio_url = "https://www2.cs.uic.edu/~i101/SoundFiles/BabyElephantWalk60.wav"
        
        print(f"📤 Submitting test job with audio URL: {audio_url}")
        
        job_data = {
            "audio_url": audio_url,
            "priority": priority,
            "whisper_model": "base",
            "metadata": {
                "test": True,
                "submitted_at": datetime.now().isoformat()
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/jobs",
                json=job_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                job_info = response.json()
                job_id = job_info["job_id"]
                print(f"✅ Job submitted successfully! Job ID: {job_id}")
                return job_id
            else:
                print(f"❌ Job submission failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Job submission failed: {e}")
            return None
    
    def check_job_status(self, job_id):
        """Check the status of a job"""
        try:
            response = requests.get(f"{self.status_url}/jobs/{job_id}", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get job status: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Failed to get job status: {e}")
            return None
    
    def wait_for_completion(self, job_id, max_wait_time=600):
        """Wait for job completion"""
        print(f"⏳ Waiting for job {job_id} to complete...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status = self.check_job_status(job_id)
            if status:
                current_status = status.get("status")
                print(f"📊 Job status: {current_status}")
                
                if current_status == "completed":
                    print("🎉 Job completed successfully!")
                    return status
                elif current_status == "failed":
                    error_msg = status.get("error_message", "Unknown error")
                    print(f"❌ Job failed: {error_msg}")
                    return status
            
            time.sleep(10)
        
        print("⏰ Timeout waiting for job completion")
        return None
    
    def get_results(self, job_id):
        """Get job results"""
        print(f"📄 Retrieving results for job {job_id}...")
        
        # Get transcription
        try:
            response = requests.get(f"{self.status_url}/jobs/{job_id}/transcription", timeout=10)
            if response.status_code == 200:
                transcription = response.json().get("transcription")
                print(f"📝 Transcription: {transcription[:200]}..." if len(transcription) > 200 else f"📝 Transcription: {transcription}")
            else:
                print(f"❌ Failed to get transcription: {response.status_code}")
        except Exception as e:
            print(f"❌ Failed to get transcription: {e}")
        
        # Get diary note
        try:
            response = requests.get(f"{self.status_url}/jobs/{job_id}/diary-note", timeout=10)
            if response.status_code == 200:
                diary_note = response.json().get("diary_note")
                print(f"📖 Diary Note: {diary_note[:200]}..." if len(diary_note) > 200 else f"📖 Diary Note: {diary_note}")
            else:
                print(f"❌ Failed to get diary note: {response.status_code}")
        except Exception as e:
            print(f"❌ Failed to get diary note: {e}")
    
    def run_full_test(self, audio_url=None):
        """Run a complete test of the system"""
        print("🚀 Starting full system test...")
        print("="*50)
        
        # Step 1: Health checks
        self.test_health_checks()
        print()
        
        # Step 2: Submit job
        job_id = self.submit_test_job(audio_url)
        if not job_id:
            print("❌ Test failed: Could not submit job")
            return False
        print()
        
        # Step 3: Wait for completion
        final_status = self.wait_for_completion(job_id)
        if not final_status:
            print("❌ Test failed: Job did not complete in time")
            return False
        print()
        
        # Step 4: Get results
        if final_status.get("status") == "completed":
            self.get_results(job_id)
            print("\n🎉 Full system test completed successfully!")
            return True
        else:
            print(f"❌ Test failed: Job ended with status {final_status.get('status')}")
            return False
    
    def stress_test(self, num_jobs=5):
        """Submit multiple jobs to test system under load"""
        print(f"🔥 Starting stress test with {num_jobs} jobs...")
        
        job_ids = []
        for i in range(num_jobs):
            print(f"Submitting job {i+1}/{num_jobs}...")
            job_id = self.submit_test_job(priority="low")
            if job_id:
                job_ids.append(job_id)
                time.sleep(1)  # Small delay between submissions
        
        print(f"📊 Submitted {len(job_ids)} jobs successfully")
        
        # Monitor progress
        completed = 0
        failed = 0
        
        while completed + failed < len(job_ids):
            time.sleep(30)
            for job_id in job_ids:
                status = self.check_job_status(job_id)
                if status:
                    job_status = status.get("status")
                    if job_status == "completed":
                        completed += 1
                        job_ids.remove(job_id)
                    elif job_status == "failed":
                        failed += 1
                        job_ids.remove(job_id)
            
            print(f"📊 Progress: {completed} completed, {failed} failed, {len(job_ids)} pending")
        
        print(f"🏁 Stress test completed: {completed} successful, {failed} failed")


def main():
    tester = TranscriptionSystemTester()
    
    print("Audio Transcription & Note Generation System Test")
    print("=" * 60)
    
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "health":
            tester.test_health_checks()
        elif command == "submit":
            audio_url = sys.argv[2] if len(sys.argv) > 2 else None
            job_id = tester.submit_test_job(audio_url)
            if job_id:
                print(f"Job ID: {job_id}")
        elif command == "status":
            if len(sys.argv) < 3:
                print("Usage: python test_system.py status <job_id>")
                return
            job_id = sys.argv[2]
            status = tester.check_job_status(job_id)
            if status:
                print(json.dumps(status, indent=2))
        elif command == "stress":
            num_jobs = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            tester.stress_test(num_jobs)
        elif command == "full":
            audio_url = sys.argv[2] if len(sys.argv) > 2 else None
            success = tester.run_full_test(audio_url)
            sys.exit(0 if success else 1)
        else:
            print("Unknown command. Available commands: health, submit, status, stress, full")
    else:
        # Run interactive mode
        print("\nAvailable commands:")
        print("1. Health check")
        print("2. Submit test job")
        print("3. Full system test")
        print("4. Stress test")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            tester.test_health_checks()
        elif choice == "2":
            audio_url = input("Enter audio URL (or press Enter for default): ").strip()
            job_id = tester.submit_test_job(audio_url if audio_url else None)
            if job_id:
                print(f"Job ID: {job_id}")
        elif choice == "3":
            audio_url = input("Enter audio URL (or press Enter for default): ").strip()
            tester.run_full_test(audio_url if audio_url else None)
        elif choice == "4":
            num_jobs = input("Enter number of jobs (default 5): ").strip()
            num_jobs = int(num_jobs) if num_jobs.isdigit() else 5
            tester.stress_test(num_jobs)
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()

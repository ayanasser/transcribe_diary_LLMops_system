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
Pytest configuration file with fixtures and plugins
"""
import os
import pytest
import tempfile
from pathlib import Path

# Add project root to path for imports
import sys
sys.path.append(str(Path(__file__).parent))

# Create fixtures for testing
@pytest.fixture(scope="session")
def temp_storage_dir():
    """Create a temporary directory for file storage during tests"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.environ["STORAGE_LOCAL_PATH"] = tmpdirname
        yield tmpdirname

@pytest.fixture(scope="session")
def mock_audio_file():
    """Create a mock audio file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp:
        # Create 1-second dummy audio file
        with open(temp.name, 'wb') as f:
            # Write a minimal WAV header (44 bytes) followed by 1 second of silence
            f.write(b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x00\x04\x00\x00\x00\x04\x00\x00\x10\x00data\x00\x00\x00\x00')
            f.write(b'\x00' * 4000)  # 1 second of silence
        
        yield temp.name
    
    # Clean up
    if os.path.exists(temp.name):
        os.unlink(temp.name)

@pytest.fixture(scope="session")
def mock_redis():
    """Mock Redis client for testing"""
    from unittest.mock import MagicMock
    
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.hgetall.return_value = {"status": "completed"}
    mock_redis.publish.return_value = 1
    
    return mock_redis

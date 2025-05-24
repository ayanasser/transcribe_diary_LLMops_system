from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class RedisSettings(BaseSettings):
    host: str = "redis"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    
    class Config:
        env_prefix = "REDIS_"


class DatabaseSettings(BaseSettings):
    url: str = "postgresql://user:password@postgres:5432/transcription_db"
    
    class Config:
        env_prefix = "DATABASE_"


class StorageSettings(BaseSettings):
    type: str = "local"  # "local" or "gcs"
    local_path: str = "/app/storage"
    gcs_bucket: Optional[str] = None
    gcs_credentials_path: Optional[str] = None
    
    class Config:
        env_prefix = "STORAGE_"


class OpenAISettings(BaseSettings):
    api_key: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.2
    
    class Config:
        env_prefix = "OPENAI_"


class AnthropicSettings(BaseSettings):
    api_key: Optional[str] = None
    model: str = "claude-3-haiku-20240307"
    max_tokens: int = 1024
    temperature: float = 0.2
    
    class Config:
        env_prefix = "ANTHROPIC_"


class MistralSettings(BaseSettings):
    api_key: Optional[str] = None
    model: str = "mistral-large-latest"
    max_tokens: int = 1000
    temperature: float = 0.2
    
    class Config:
        env_prefix = "MISTRAL_"


class LocalLLMSettings(BaseSettings):
    enabled: bool = False
    model: str = "llama-3-8b-instruct"
    endpoint: str = "http://localhost:8080/v1"
    max_tokens: int = 512
    temperature: float = 0.0
    
    class Config:
        env_prefix = "LOCAL_LLM_"


class WhisperSettings(BaseSettings):
    cache_dir: str = "/app/whisper_cache"
    device: str = "cpu"  # "cpu" or "cuda"
    
    class Config:
        env_prefix = "WHISPER_"


class RateLimitSettings(BaseSettings):
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    
    class Config:
        env_prefix = "RATE_LIMIT_"


class MonitoringSettings(BaseSettings):
    prometheus_port: int = 8080
    log_level: str = "INFO"
    
    class Config:
        env_prefix = "MONITORING_"


class ObservabilitySettings(BaseSettings):
    otlp_endpoint: Optional[str] = None  # Disabled by default to avoid startup issues
    otlp_insecure: bool = True
    enable_traces: bool = False  # Disabled by default
    enable_metrics: bool = False  # Disabled by default
    sample_rate: float = 1.0
    
    class Config:
        env_prefix = "OBSERVABILITY_"


class Settings(BaseSettings):
    # Application
    app_name: str = "Transcription Pipeline"
    debug: bool = False
    environment: str = "development"
    
    # Service-specific settings
    redis: RedisSettings = RedisSettings()
    database: DatabaseSettings = DatabaseSettings()
    storage: StorageSettings = StorageSettings()
    openai: OpenAISettings = OpenAISettings()
    anthropic: AnthropicSettings = AnthropicSettings()
    mistral: MistralSettings = MistralSettings()
    local_llm: LocalLLMSettings = LocalLLMSettings()
    whisper: WhisperSettings = WhisperSettings()
    rate_limit: RateLimitSettings = RateLimitSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    observability: ObservabilitySettings = ObservabilitySettings()
    
    # Worker settings
    max_concurrent_jobs: int = 4
    job_timeout_seconds: int = 3600  # 1 hour
    
    # File validation
    max_file_size_mb: int = 500
    allowed_audio_formats: List[str] = [
        "audio/mpeg", "audio/wav", "audio/mp4", "audio/webm", 
        "audio/ogg", "audio/flac", "audio/aac"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

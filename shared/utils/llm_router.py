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



#!/usr/bin/env python
# filepath: /home/aya/mlops_assessment/shared/utils/llm_router.py
import time
import enum
from typing import Dict, Any, List, Optional, Tuple

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import openai
import anthropic

from shared.config.settings import settings
from shared.utils.helpers import get_logger

logger = get_logger(__name__)

class ModelProvider(str, enum.Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"
    LOCAL = "local"


class ModelPriority(int, enum.Enum):
    """Model routing priority - lower number is higher priority"""
    PRIMARY = 1
    SECONDARY = 2
    FALLBACK = 3
    LAST_RESORT = 4


class LLMRouter:
    """
    A router that handles LLM provider selection, fallback, and retry logic
    
    Features:
    - Multi-provider support (OpenAI, Anthropic, Mistral)
    - Automatic fallback to backup providers
    - Rate limit handling with exponential backoff
    - Configurable model preferences and routing
    - Local fallback option when all cloud providers fail
    """
    
    def __init__(self):
        """Initialize LLM router with configured providers"""
        # Initialize clients for each provider
        self.openai_client = openai.OpenAI(api_key=settings.openai.api_key)
        
        # Set up anthropic client if API key is available
        self.anthropic_client = None
        if hasattr(settings, "anthropic") and settings.anthropic.api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=settings.anthropic.api_key)
        
        # Configure provider routing
        self.model_config = self._get_model_configuration()
        self.available_providers = self._check_available_providers()
        
        logger.info(
            "LLM router initialized", 
            available_providers=self.available_providers
        )
    
    def _get_model_configuration(self) -> Dict[str, Dict]:
        """Get model configuration with fallback preferences"""
        # Default models configuration
        default_config = {
            ModelProvider.OPENAI: {
                "priority": ModelPriority.PRIMARY,
                "models": {
                    "primary": "gpt-4o",
                    "fallback": "gpt-3.5-turbo" 
                },
                "max_tokens": settings.openai.max_tokens,
                "temperature": settings.openai.temperature
            }
        }
        
        # Add Anthropic config if available
        if self.anthropic_client:
            default_config[ModelProvider.ANTHROPIC] = {
                "priority": ModelPriority.SECONDARY,
                "models": {
                    "primary": "claude-3-opus-20240229",
                    "fallback": "claude-3-haiku-20240307"
                },
                "max_tokens": 1024,
                "temperature": 0.2
            }
        
        # Add local fallback if configured
        if hasattr(settings, "local_llm") and settings.local_llm.enabled:
            default_config[ModelProvider.LOCAL] = {
                "priority": ModelPriority.LAST_RESORT,
                "models": {
                    "primary": settings.local_llm.model
                },
                "max_tokens": 512,
                "temperature": 0.0
            }
            
        return default_config
    
    def _check_available_providers(self) -> List[ModelProvider]:
        """Check which providers are available and configured"""
        available = []
        
        # Check OpenAI
        if settings.openai.api_key:
            available.append(ModelProvider.OPENAI)
            
        # Check Anthropic
        if self.anthropic_client:
            available.append(ModelProvider.ANTHROPIC)
            
        # Check for local model
        if hasattr(settings, "local_llm") and settings.local_llm.enabled:
            available.append(ModelProvider.LOCAL)
        
        return available
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.RateLimitError, anthropic.RateLimitError))
    )
    def _call_openai(self, prompt: str, system_prompt: str, model: str) -> str:
        """Call OpenAI API with retry logic"""
        try:
            start_time = time.time()
            
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.model_config[ModelProvider.OPENAI]["temperature"],
                max_tokens=self.model_config[ModelProvider.OPENAI]["max_tokens"],
            )
            
            api_time = time.time() - start_time
            result = response.choices[0].message.content.strip()
            
            logger.info(
                "OpenAI API call completed",
                model=model,
                duration=api_time,
                tokens_used=response.usage.total_tokens
            )
            
            return result
            
        except Exception as e:
            logger.error("OpenAI API call failed", error=str(e), model=model)
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(anthropic.RateLimitError)
    )
    def _call_anthropic(self, prompt: str, system_prompt: str, model: str) -> str:
        """Call Anthropic API with retry logic"""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not configured")
            
        try:
            start_time = time.time()
            
            response = self.anthropic_client.messages.create(
                model=model,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.model_config[ModelProvider.ANTHROPIC]["temperature"],
                max_tokens=self.model_config[ModelProvider.ANTHROPIC]["max_tokens"]
            )
            
            api_time = time.time() - start_time
            result = response.content[0].text
            
            logger.info(
                "Anthropic API call completed",
                model=model,
                duration=api_time
            )
            
            return result
            
        except Exception as e:
            logger.error("Anthropic API call failed", error=str(e), model=model)
            raise
    
    def _call_local_model(self, prompt: str, system_prompt: str, model: str) -> str:
        """Call local model if available"""
        # This would integrate with a local inference server
        # For now, just returning a simple template
        logger.warning("Using local fallback model")
        
        # Simple templated response with current date
        from datetime import datetime
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        return f"""📅 **Date & Time**: {current_date}

😊 **Mood/Feelings**: [Generated with local fallback model]

🌟 **Key Events**: 
The audio contained a personal recording that was processed through our transcription system.

💭 **Thoughts & Reflections**: 
This diary entry was generated using a local fallback model due to cloud LLM service unavailability.

🎯 **Takeaways**: 
Please review the transcription directly for the most accurate representation of the content.

---
*Note: This entry was generated by a simplified local model.*"""
    
    def _get_providers_by_priority(self) -> List[Tuple[ModelProvider, Dict]]:
        """Get providers sorted by priority"""
        available_providers = [
            (provider, self.model_config[provider]) 
            for provider in self.available_providers
        ]
        
        # Sort by priority (lower number is higher priority)
        return sorted(
            available_providers, 
            key=lambda x: x[1]["priority"]
        )
    
    def generate_text(self, prompt: str, system_prompt: str) -> Tuple[str, str]:
        """
        Generate text using the best available provider with fallback logic
        
        Returns:
            Tuple of (generated_text, provider_name)
        """
        providers_by_priority = self._get_providers_by_priority()
        last_error = None
        
        for provider, config in providers_by_priority:
            # Try primary model first
            primary_model = config["models"]["primary"]
            
            try:
                if provider == ModelProvider.OPENAI:
                    return self._call_openai(prompt, system_prompt, primary_model), f"{provider}:{primary_model}"
                elif provider == ModelProvider.ANTHROPIC:
                    return self._call_anthropic(prompt, system_prompt, primary_model), f"{provider}:{primary_model}"
                elif provider == ModelProvider.LOCAL:
                    return self._call_local_model(prompt, system_prompt, primary_model), f"{provider}:{primary_model}"
            except Exception as e:
                logger.warning(
                    f"Primary model failed, trying fallback", 
                    provider=provider, 
                    model=primary_model,
                    error=str(e)
                )
                last_error = e
                
                # Try fallback model if available
                if "fallback" in config["models"]:
                    fallback_model = config["models"]["fallback"]
                    try:
                        if provider == ModelProvider.OPENAI:
                            return self._call_openai(prompt, system_prompt, fallback_model), f"{provider}:{fallback_model}"
                        elif provider == ModelProvider.ANTHROPIC:
                            return self._call_anthropic(prompt, system_prompt, fallback_model), f"{provider}:{fallback_model}" 
                    except Exception as e:
                        logger.error(
                            f"Fallback model failed", 
                            provider=provider, 
                            model=fallback_model,
                            error=str(e)
                        )
                        last_error = e
        
        # If all models failed, return a simple fallback response
        logger.error(
            "All LLM providers failed", 
            last_error=str(last_error)
        )
        
        # Final fallback response
        from datetime import datetime
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        fallback_response = f"""📅 **Date & Time**: {current_date}

😊 **Mood/Feelings**: [Unable to analyze]

🌟 **Key Events**: 
This audio was transcribed but note generation failed.

💭 **Thoughts & Reflections**: 
Please refer to the transcription directly.

🎯 **Takeaways**: 
System encountered an error when attempting to generate diary notes.

---
*Note: This is an emergency fallback response due to service unavailability.*"""
        
        return fallback_response, "emergency_fallback"

# Global router instance
llm_router = LLMRouter()

"""
Tests for the LLM router module
"""
import unittest
from unittest.mock import patch, MagicMock

from shared.utils.llm_router import LLMRouter, ModelProvider, ModelPriority


class TestLLMRouter(unittest.TestCase):
    """Test cases for the LLM router"""
    
    @patch('shared.utils.llm_router.openai')
    @patch('shared.utils.llm_router.anthropic')
    def setUp(self, mock_anthropic, mock_openai):
        """Set up the test case"""
        self.mock_openai = mock_openai
        self.mock_anthropic = mock_anthropic
        self.router = LLMRouter()
    
    def test_init(self):
        """Test router initialization"""
        self.assertIsNotNone(self.router.openai_client)
        self.assertIn(ModelProvider.OPENAI, self.router.available_providers)
    
    @patch('shared.utils.llm_router.LLMRouter._call_openai')
    def test_generate_text_primary_success(self, mock_call_openai):
        """Test successful text generation with primary provider"""
        mock_call_openai.return_value = "Generated text"
        
        result, provider = self.router.generate_text("Test prompt", "Test system prompt")
        
        self.assertEqual(result, "Generated text")
        self.assertTrue(provider.startswith(ModelProvider.OPENAI))
        mock_call_openai.assert_called_once()
    
    @patch('shared.utils.llm_router.LLMRouter._call_openai')
    def test_generate_text_primary_failure_fallback(self, mock_call_openai):
        """Test fallback when primary model fails"""
        # Primary model fails, fallback succeeds
        mock_call_openai.side_effect = [Exception("API error"), "Fallback text"]
        
        result, provider = self.router.generate_text("Test prompt", "Test system prompt")
        
        self.assertEqual(result, "Fallback text")
        self.assertTrue("fallback" in provider)
        self.assertEqual(mock_call_openai.call_count, 2)
    
    @patch('shared.utils.llm_router.LLMRouter._call_openai')
    @patch('shared.utils.llm_router.LLMRouter._call_anthropic')
    def test_generate_text_provider_fallback(self, mock_call_anthropic, mock_call_openai):
        """Test fallback to secondary provider when primary provider fails completely"""
        # Override available providers for this test
        self.router.available_providers = [ModelProvider.OPENAI, ModelProvider.ANTHROPIC]
        self.router.anthropic_client = MagicMock()
        
        # OpenAI fails entirely
        mock_call_openai.side_effect = Exception("API error")
        mock_call_anthropic.return_value = "Secondary provider text"
        
        result, provider = self.router.generate_text("Test prompt", "Test system prompt")
        
        self.assertEqual(result, "Secondary provider text")
        self.assertTrue(provider.startswith(ModelProvider.ANTHROPIC))
        mock_call_openai.assert_called_once()
        mock_call_anthropic.assert_called_once()
    
    @patch('shared.utils.llm_router.LLMRouter._call_openai')
    @patch('shared.utils.llm_router.LLMRouter._call_anthropic')
    def test_generate_text_all_providers_fail(self, mock_call_anthropic, mock_call_openai):
        """Test emergency fallback when all providers fail"""
        # Override available providers for this test
        self.router.available_providers = [ModelProvider.OPENAI, ModelProvider.ANTHROPIC]
        self.router.anthropic_client = MagicMock()
        
        # All providers fail
        mock_call_openai.side_effect = Exception("OpenAI error")
        mock_call_anthropic.side_effect = Exception("Anthropic error")
        
        result, provider = self.router.generate_text("Test prompt", "Test system prompt")
        
        self.assertIn("emergency fallback", provider)
        self.assertIn("Note: This is an emergency fallback", result)
        mock_call_openai.assert_called_once()
        mock_call_anthropic.assert_called_once()


if __name__ == '__main__':
    unittest.main()

"""
Integration tests for ChatbotApp error handling with APIRetryHandler.

Tests verify that API calls are properly wrapped with retry logic and
that user-friendly error messages are displayed.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from error_handler import APIRetryHandler, RetryExhaustedError


class TestChatbotErrorIntegration:
    """Test error handling integration in ChatbotApp."""
    
    def test_error_handler_initialization(self):
        """Test that ChatbotApp initializes APIRetryHandler correctly."""
        # Import here to avoid GUI initialization issues
        with patch('chatbot_app.tk.Tk'):
            from chatbot_app import ChatbotApp
            
            # Mock config to avoid needing actual API keys
            with patch('chatbot_app.load_config') as mock_config:
                mock_config.return_value = {
                    "openai_api_key": "test-key",
                    "elevenlabs_api_key": "test-key",
                    "voice_id": "test-voice",
                    "position": "post-human"
                }
                
                app = ChatbotApp()
                
                # Verify error_handler is initialized
                assert hasattr(app, 'error_handler')
                assert isinstance(app.error_handler, APIRetryHandler)
                assert app.error_handler.max_retries == 4
                assert app.error_handler.base_delay == 1.0
    
    def test_api_retry_handler_wraps_whisper_call(self):
        """Test that Whisper API calls are wrapped with retry logic."""
        handler = APIRetryHandler(max_retries=2, base_delay=0.1)
        
        # Mock Whisper transcribe that fails twice then succeeds
        mock_transcribe = Mock(side_effect=[
            requests.exceptions.ConnectionError("Network error"),
            requests.exceptions.Timeout("Timeout"),
            "Hello world"
        ])
        
        # Call with retry
        result = handler.call_with_retry(mock_transcribe, b"audio_data")
        
        # Verify it retried and eventually succeeded
        assert result == "Hello world"
        assert mock_transcribe.call_count == 3
    
    def test_api_retry_handler_wraps_llm_call(self):
        """Test that LLM API calls are wrapped with retry logic."""
        handler = APIRetryHandler(max_retries=2, base_delay=0.1)
        
        # Mock LLM generate that fails once then succeeds
        mock_generate = Mock(side_effect=[
            requests.exceptions.HTTPError(response=Mock(status_code=503)),
            "AI response"
        ])
        
        # Call with retry
        result = handler.call_with_retry(mock_generate, "user input")
        
        # Verify it retried and eventually succeeded
        assert result == "AI response"
        assert mock_generate.call_count == 2
    
    def test_api_retry_handler_wraps_tts_call(self):
        """Test that TTS API calls are wrapped with retry logic."""
        handler = APIRetryHandler(max_retries=2, base_delay=0.1)
        
        # Mock TTS synthesize that fails once then succeeds
        mock_synthesize = Mock(side_effect=[
            requests.exceptions.ConnectionError("Network error"),
            b"mp3_audio_data"
        ])
        
        # Call with retry
        result = handler.call_with_retry(mock_synthesize, "text to speak")
        
        # Verify it retried and eventually succeeded
        assert result == b"mp3_audio_data"
        assert mock_synthesize.call_count == 2
    
    def test_retry_exhausted_raises_error(self):
        """Test that RetryExhaustedError is raised after max retries."""
        handler = APIRetryHandler(max_retries=2, base_delay=0.1)
        
        # Mock API call that always fails
        mock_api = Mock(side_effect=requests.exceptions.ConnectionError("Network error"))
        
        # Verify RetryExhaustedError is raised
        with pytest.raises(RetryExhaustedError):
            handler.call_with_retry(mock_api)
        
        # Verify it tried max_retries + 1 times (initial + 2 retries)
        assert mock_api.call_count == 3
    
    def test_error_translation_for_network_errors(self):
        """Test that network errors are translated to user-friendly messages."""
        handler = APIRetryHandler()
        
        # Test various network errors
        conn_error = requests.exceptions.ConnectionError("Connection failed")
        assert "check your internet connection" in handler.translate_error(conn_error).lower()
        
        timeout_error = requests.exceptions.Timeout("Request timeout")
        assert "took too long" in handler.translate_error(timeout_error).lower()
    
    def test_error_translation_for_api_errors(self):
        """Test that API errors are translated to user-friendly messages."""
        handler = APIRetryHandler()
        
        # Test 401 error
        response_401 = Mock(status_code=401)
        http_error_401 = requests.exceptions.HTTPError(response=response_401)
        assert "api keys" in handler.translate_error(http_error_401).lower()
        
        # Test 429 error
        response_429 = Mock(status_code=429)
        http_error_429 = requests.exceptions.HTTPError(response=response_429)
        assert "too many requests" in handler.translate_error(http_error_429).lower()
        
        # Test 503 error
        response_503 = Mock(status_code=503)
        http_error_503 = requests.exceptions.HTTPError(response=response_503)
        assert "temporarily unavailable" in handler.translate_error(http_error_503).lower()
    
    def test_error_translation_for_retry_exhausted(self):
        """Test that RetryExhaustedError is translated to user-friendly message."""
        handler = APIRetryHandler()
        
        retry_error = RetryExhaustedError("Failed after 4 retries")
        message = handler.translate_error(retry_error)
        
        assert "multiple attempts" in message.lower()
        assert "check your connection" in message.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

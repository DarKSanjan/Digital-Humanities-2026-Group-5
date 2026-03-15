"""
Unit tests for error_handler module.

Tests the APIRetryHandler and NetworkMonitor classes including exponential 
backoff retry logic, error message translation, and network connectivity monitoring.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
import requests
from backend.src.error_handler import (
    APIRetryHandler,
    NetworkMonitor,
    ProcessMonitor,
    RetryExhaustedError,
    ErrorContext
)


class TestAPIRetryHandler:
    """Test suite for APIRetryHandler class."""
    
    def test_successful_call_no_retry(self):
        """Test that successful API calls don't trigger retries."""
        handler = APIRetryHandler()
        mock_func = Mock(return_value="success")
        
        result = handler.call_with_retry(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        assert mock_func.call_count == 1
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
    
    def test_retry_with_exponential_backoff(self):
        """Test exponential backoff delays: 1s, 2s, 4s, 8s."""
        handler = APIRetryHandler(max_retries=4, base_delay=0.1)  # Use shorter delays for testing
        
        # Mock function that fails 3 times then succeeds
        mock_func = Mock(side_effect=[
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.ConnectionError("Connection failed"),
            "success"
        ])
        
        start_time = time.time()
        result = handler.call_with_retry(mock_func)
        elapsed_time = time.time() - start_time
        
        assert result == "success"
        assert mock_func.call_count == 4
        
        # Verify exponential backoff: 0.1 + 0.2 + 0.4 = 0.7s minimum
        # Allow some tolerance for execution time
        assert elapsed_time >= 0.6
    
    def test_retry_exhausted_raises_error(self):
        """Test that RetryExhaustedError is raised after max retries."""
        handler = APIRetryHandler(max_retries=2, base_delay=0.01)
        
        # Mock function that always fails
        mock_func = Mock(side_effect=requests.exceptions.ConnectionError("Connection failed"))
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            handler.call_with_retry(mock_func)
        
        assert "failed after 3 attempts" in str(exc_info.value)
        assert mock_func.call_count == 3  # Initial attempt + 2 retries
    
    def test_translate_connection_error(self):
        """Test translation of connection errors."""
        handler = APIRetryHandler()
        error = requests.exceptions.ConnectionError("Connection refused")
        
        message = handler.translate_error(error)
        
        assert "Unable to connect" in message
        assert "internet connection" in message
    
    def test_translate_timeout_error(self):
        """Test translation of timeout errors."""
        handler = APIRetryHandler()
        error = requests.exceptions.Timeout("Request timed out")
        
        message = handler.translate_error(error)
        
        assert "took too long" in message
    
    def test_translate_http_401_error(self):
        """Test translation of 401 authentication errors."""
        handler = APIRetryHandler()
        
        # Create mock response with 401 status
        mock_response = Mock()
        mock_response.status_code = 401
        error = requests.exceptions.HTTPError(response=mock_response)
        
        message = handler.translate_error(error)
        
        assert "Authentication failed" in message
        assert "API keys" in message
    
    def test_translate_http_429_error(self):
        """Test translation of 429 rate limit errors."""
        handler = APIRetryHandler()
        
        mock_response = Mock()
        mock_response.status_code = 429
        error = requests.exceptions.HTTPError(response=mock_response)
        
        message = handler.translate_error(error)
        
        assert "Too many requests" in message
    
    def test_translate_http_503_error(self):
        """Test translation of 503 service unavailable errors."""
        handler = APIRetryHandler()
        
        mock_response = Mock()
        mock_response.status_code = 503
        error = requests.exceptions.HTTPError(response=mock_response)
        
        message = handler.translate_error(error)
        
        assert "temporarily unavailable" in message
    
    def test_translate_memory_error(self):
        """Test translation of memory errors."""
        handler = APIRetryHandler()
        error = MemoryError("Out of memory")
        
        message = handler.translate_error(error)
        
        assert "memory is low" in message
        assert "close other applications" in message
    
    def test_translate_cuda_error(self):
        """Test translation of CUDA/GPU errors."""
        handler = APIRetryHandler()
        error = RuntimeError("CUDA out of memory")
        
        message = handler.translate_error(error)
        
        assert "GPU rendering" in message
        assert "CPU mode" in message
    
    def test_translate_retry_exhausted_error(self):
        """Test translation of RetryExhaustedError."""
        handler = APIRetryHandler()
        error = RetryExhaustedError("Failed after retries")
        
        message = handler.translate_error(error)
        
        assert "multiple attempts" in message
        assert "check your connection" in message
    
    def test_translate_generic_error(self):
        """Test translation of unknown error types."""
        handler = APIRetryHandler()
        error = ValueError("Some unexpected error")
        
        message = handler.translate_error(error)
        
        assert "unexpected error" in message
    
    def test_create_error_context_network_error(self):
        """Test ErrorContext creation for network errors."""
        handler = APIRetryHandler()
        error = requests.exceptions.ConnectionError("Connection failed")
        
        context = handler.create_error_context(error, retry_count=2)
        
        assert context.error_type == "network"
        assert context.original_error == error
        assert context.retry_count == 2
        assert context.is_recoverable is True
        assert "Unable to connect" in context.user_message
        assert "ConnectionError" in context.technical_details
    
    def test_create_error_context_api_error_recoverable(self):
        """Test ErrorContext creation for recoverable API errors (429, 503)."""
        handler = APIRetryHandler()
        
        mock_response = Mock()
        mock_response.status_code = 429
        error = requests.exceptions.HTTPError(response=mock_response)
        
        context = handler.create_error_context(error, retry_count=1)
        
        assert context.error_type == "api"
        assert context.is_recoverable is True
        assert "Too many requests" in context.user_message
    
    def test_create_error_context_api_error_not_recoverable(self):
        """Test ErrorContext creation for non-recoverable API errors (401)."""
        handler = APIRetryHandler()
        
        mock_response = Mock()
        mock_response.status_code = 401
        error = requests.exceptions.HTTPError(response=mock_response)
        
        context = handler.create_error_context(error, retry_count=0)
        
        assert context.error_type == "api"
        assert context.is_recoverable is False
        assert "Authentication failed" in context.user_message
    
    def test_create_error_context_system_error(self):
        """Test ErrorContext creation for system errors."""
        handler = APIRetryHandler()
        error = MemoryError("Out of memory")
        
        context = handler.create_error_context(error, retry_count=0)
        
        assert context.error_type == "system"
        assert context.is_recoverable is False
        assert "memory is low" in context.user_message
    
    def test_retry_preserves_function_arguments(self):
        """Test that retries preserve original function arguments."""
        handler = APIRetryHandler(max_retries=2, base_delay=0.01)
        
        # Mock function that fails once then succeeds
        mock_func = Mock(side_effect=[
            requests.exceptions.ConnectionError("Connection failed"),
            "success"
        ])
        
        result = handler.call_with_retry(mock_func, "arg1", "arg2", kwarg1="value1")
        
        assert result == "success"
        assert mock_func.call_count == 2
        
        # Verify both calls had the same arguments
        for call in mock_func.call_args_list:
            assert call[0] == ("arg1", "arg2")
            assert call[1] == {"kwarg1": "value1"}
    
    def test_exponential_backoff_timing(self):
        """Test that exponential backoff follows 1s, 2s, 4s, 8s pattern."""
        handler = APIRetryHandler(max_retries=4, base_delay=0.1)
        
        mock_func = Mock(side_effect=[
            requests.exceptions.ConnectionError("Failed"),
            requests.exceptions.ConnectionError("Failed"),
            requests.exceptions.ConnectionError("Failed"),
            requests.exceptions.ConnectionError("Failed"),
            "success"
        ])
        
        start_time = time.time()
        result = handler.call_with_retry(mock_func)
        elapsed_time = time.time() - start_time
        
        # Expected delays: 0.1 + 0.2 + 0.4 + 0.8 = 1.5s
        # Allow some tolerance
        assert elapsed_time >= 1.4
        assert elapsed_time < 2.0
        assert result == "success"


class TestNetworkMonitor:
    """Test suite for NetworkMonitor class."""
    
    def test_initialization(self):
        """Test NetworkMonitor initialization with default values."""
        monitor = NetworkMonitor()
        
        assert monitor.check_interval == 10.0
        assert monitor.is_connected is True
        assert monitor.callbacks == []
        assert monitor._monitoring is False
        assert monitor._monitor_thread is None
    
    def test_initialization_custom_interval(self):
        """Test NetworkMonitor initialization with custom check interval."""
        monitor = NetworkMonitor(check_interval=5.0)
        
        assert monitor.check_interval == 5.0
    
    def test_register_callback(self):
        """Test registering a callback function."""
        monitor = NetworkMonitor()
        
        def test_callback(is_connected: bool):
            pass
        
        monitor.register_callback(test_callback)
        
        assert test_callback in monitor.callbacks
        assert len(monitor.callbacks) == 1
    
    def test_register_multiple_callbacks(self):
        """Test registering multiple callback functions."""
        monitor = NetworkMonitor()
        
        def callback1(is_connected: bool):
            pass
        
        def callback2(is_connected: bool):
            pass
        
        monitor.register_callback(callback1)
        monitor.register_callback(callback2)
        
        assert len(monitor.callbacks) == 2
        assert callback1 in monitor.callbacks
        assert callback2 in monitor.callbacks
    
    def test_register_duplicate_callback(self):
        """Test that registering the same callback twice doesn't duplicate it."""
        monitor = NetworkMonitor()
        
        def test_callback(is_connected: bool):
            pass
        
        monitor.register_callback(test_callback)
        monitor.register_callback(test_callback)
        
        assert len(monitor.callbacks) == 1
    
    def test_unregister_callback(self):
        """Test unregistering a callback function."""
        monitor = NetworkMonitor()
        
        def test_callback(is_connected: bool):
            pass
        
        monitor.register_callback(test_callback)
        assert test_callback in monitor.callbacks
        
        monitor.unregister_callback(test_callback)
        assert test_callback not in monitor.callbacks
        assert len(monitor.callbacks) == 0
    
    def test_unregister_nonexistent_callback(self):
        """Test unregistering a callback that was never registered."""
        monitor = NetworkMonitor()
        
        def test_callback(is_connected: bool):
            pass
        
        # Should not raise an error
        monitor.unregister_callback(test_callback)
        assert len(monitor.callbacks) == 0
    
    @patch('backend.src.error_handler.requests.get')
    def test_check_connectivity_success(self, mock_get):
        """Test connectivity check when connection is successful."""
        monitor = NetworkMonitor()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = monitor.check_connectivity()
        
        assert result is True
        mock_get.assert_called_once_with("https://www.google.com", timeout=5)
    
    @patch('backend.src.error_handler.requests.get')
    def test_check_connectivity_failure(self, mock_get):
        """Test connectivity check when connection fails."""
        monitor = NetworkMonitor()
        
        # Mock connection error
        mock_get.side_effect = requests.exceptions.ConnectionError("No connection")
        
        result = monitor.check_connectivity()
        
        assert result is False
    
    @patch('backend.src.error_handler.requests.get')
    def test_check_connectivity_timeout(self, mock_get):
        """Test connectivity check when request times out."""
        monitor = NetworkMonitor()
        
        # Mock timeout error
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")
        
        result = monitor.check_connectivity()
        
        assert result is False
    
    @patch('backend.src.error_handler.requests.get')
    def test_check_connectivity_non_200_status(self, mock_get):
        """Test connectivity check when response is not 200."""
        monitor = NetworkMonitor()
        
        # Mock non-200 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = monitor.check_connectivity()
        
        assert result is False
    
    @patch('backend.src.error_handler.requests.get')
    def test_start_monitoring(self, mock_get):
        """Test starting network monitoring."""
        monitor = NetworkMonitor(check_interval=0.1)
        
        # Mock successful connectivity
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        monitor.start_monitoring()
        
        assert monitor._monitoring is True
        assert monitor._monitor_thread is not None
        assert monitor._monitor_thread.is_alive()
        
        # Clean up
        monitor.stop_monitoring()
    
    @patch('backend.src.error_handler.requests.get')
    def test_stop_monitoring(self, mock_get):
        """Test stopping network monitoring."""
        monitor = NetworkMonitor(check_interval=0.1)
        
        # Mock successful connectivity
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        monitor.start_monitoring()
        assert monitor._monitoring is True
        
        monitor.stop_monitoring()
        
        assert monitor._monitoring is False
        # Give thread time to finish
        time.sleep(0.2)
        assert not monitor._monitor_thread.is_alive()
    
    @patch('backend.src.error_handler.requests.get')
    def test_start_monitoring_twice(self, mock_get):
        """Test that starting monitoring twice doesn't create multiple threads."""
        monitor = NetworkMonitor(check_interval=0.1)
        
        # Mock successful connectivity
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        monitor.start_monitoring()
        first_thread = monitor._monitor_thread
        
        monitor.start_monitoring()
        second_thread = monitor._monitor_thread
        
        assert first_thread is second_thread
        
        # Clean up
        monitor.stop_monitoring()
    
    @patch('backend.src.error_handler.requests.get')
    def test_connectivity_change_triggers_callback(self, mock_get):
        """Test that connectivity changes trigger registered callbacks."""
        monitor = NetworkMonitor(check_interval=0.1)
        
        # Track callback invocations
        callback_calls = []
        
        def test_callback(is_connected: bool):
            callback_calls.append(is_connected)
        
        monitor.register_callback(test_callback)
        
        # Start with connected state
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        monitor.start_monitoring()
        time.sleep(0.15)  # Wait for first check
        
        # Simulate disconnection
        mock_get.side_effect = requests.exceptions.ConnectionError("No connection")
        time.sleep(0.15)  # Wait for next check
        
        # Simulate reconnection
        mock_get.side_effect = None
        mock_get.return_value = mock_response
        time.sleep(0.15)  # Wait for next check
        
        monitor.stop_monitoring()
        
        # Should have been called twice: once for disconnect, once for reconnect
        assert len(callback_calls) >= 2
        assert False in callback_calls  # Disconnection
        assert True in callback_calls   # Reconnection
    
    @patch('backend.src.error_handler.requests.get')
    def test_multiple_callbacks_all_triggered(self, mock_get):
        """Test that all registered callbacks are triggered on connectivity change."""
        monitor = NetworkMonitor(check_interval=0.1)
        
        # Track callback invocations
        callback1_calls = []
        callback2_calls = []
        
        def callback1(is_connected: bool):
            callback1_calls.append(is_connected)
        
        def callback2(is_connected: bool):
            callback2_calls.append(is_connected)
        
        monitor.register_callback(callback1)
        monitor.register_callback(callback2)
        
        # Start with connected state
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        monitor.start_monitoring()
        time.sleep(0.15)
        
        # Simulate disconnection
        mock_get.side_effect = requests.exceptions.ConnectionError("No connection")
        time.sleep(0.15)
        
        monitor.stop_monitoring()
        
        # Both callbacks should have been called
        assert len(callback1_calls) >= 1
        assert len(callback2_calls) >= 1
        assert False in callback1_calls
        assert False in callback2_calls
    
    @patch('backend.src.error_handler.requests.get')
    def test_callback_exception_doesnt_break_monitoring(self, mock_get):
        """Test that exceptions in callbacks don't break the monitoring loop."""
        monitor = NetworkMonitor(check_interval=0.1)
        
        # Track callback invocations
        good_callback_calls = []
        
        def bad_callback(is_connected: bool):
            raise ValueError("Callback error")
        
        def good_callback(is_connected: bool):
            good_callback_calls.append(is_connected)
        
        monitor.register_callback(bad_callback)
        monitor.register_callback(good_callback)
        
        # Start with connected state
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        monitor.start_monitoring()
        time.sleep(0.15)
        
        # Simulate disconnection
        mock_get.side_effect = requests.exceptions.ConnectionError("No connection")
        time.sleep(0.15)
        
        monitor.stop_monitoring()
        
        # Good callback should still have been called despite bad callback error
        assert len(good_callback_calls) >= 1
        assert False in good_callback_calls
    
    @patch('backend.src.error_handler.requests.get')
    def test_no_callback_on_unchanged_connectivity(self, mock_get):
        """Test that callbacks are not triggered when connectivity doesn't change."""
        monitor = NetworkMonitor(check_interval=0.1)
        
        # Track callback invocations
        callback_calls = []
        
        def test_callback(is_connected: bool):
            callback_calls.append(is_connected)
        
        monitor.register_callback(test_callback)
        
        # Keep connected state throughout
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        monitor.start_monitoring()
        time.sleep(0.35)  # Wait for multiple checks
        
        monitor.stop_monitoring()
        
        # Callback should not have been called since connectivity never changed
        assert len(callback_calls) == 0



class TestProcessMonitor:
    """Test suite for ProcessMonitor class."""
    
    def test_initialization(self):
        """Test ProcessMonitor initialization with default values."""
        monitor = ProcessMonitor()
        
        assert monitor.health_check_timeout == 2.0
        assert monitor.is_healthy is True
        assert monitor.last_heartbeat > 0
    
    def test_initialization_custom_timeout(self):
        """Test ProcessMonitor initialization with custom timeout."""
        monitor = ProcessMonitor(health_check_timeout=5.0)
        
        assert monitor.health_check_timeout == 5.0
    
    def test_heartbeat_updates_timestamp(self):
        """Test that heartbeat updates the last_heartbeat timestamp."""
        monitor = ProcessMonitor()
        
        initial_heartbeat = monitor.last_heartbeat
        time.sleep(0.1)
        monitor.heartbeat()
        
        assert monitor.last_heartbeat > initial_heartbeat
    
    def test_check_health_returns_true_when_healthy(self):
        """Test that check_health returns True when heartbeat is recent."""
        monitor = ProcessMonitor(health_check_timeout=2.0)
        
        monitor.heartbeat()
        result = monitor.check_health()
        
        assert result is True
        assert monitor.is_healthy is True
    
    def test_check_health_returns_false_after_timeout(self):
        """Test that check_health returns False when heartbeat times out."""
        monitor = ProcessMonitor(health_check_timeout=0.1)
        
        monitor.heartbeat()
        time.sleep(0.15)  # Wait longer than timeout
        result = monitor.check_health()
        
        assert result is False
        assert monitor.is_healthy is False
    
    def test_check_health_detects_crash_within_2_seconds(self):
        """Test crash detection within 2 seconds (Requirement 4.1)."""
        monitor = ProcessMonitor(health_check_timeout=2.0)
        
        monitor.heartbeat()
        
        # Check immediately - should be healthy
        assert monitor.check_health() is True
        
        # Wait 1.5 seconds - should still be healthy
        time.sleep(1.5)
        assert monitor.check_health() is True
        
        # Wait another 0.6 seconds (total 2.1s) - should detect crash
        time.sleep(0.6)
        assert monitor.check_health() is False
    
    def test_heartbeat_restores_health(self):
        """Test that calling heartbeat restores health after timeout."""
        monitor = ProcessMonitor(health_check_timeout=0.1)
        
        monitor.heartbeat()
        time.sleep(0.15)  # Timeout
        
        assert monitor.check_health() is False
        
        # Send heartbeat to restore health
        monitor.heartbeat()
        assert monitor.check_health() is True
    
    def test_get_time_since_heartbeat(self):
        """Test getting time elapsed since last heartbeat."""
        monitor = ProcessMonitor()
        
        monitor.heartbeat()
        time.sleep(0.1)
        
        elapsed = monitor.get_time_since_heartbeat()
        
        assert elapsed >= 0.1
        assert elapsed < 0.2  # Should be close to 0.1s
    
    def test_reset_restores_healthy_state(self):
        """Test that reset restores monitor to healthy state."""
        monitor = ProcessMonitor(health_check_timeout=0.1)
        
        monitor.heartbeat()
        time.sleep(0.15)  # Timeout
        assert monitor.check_health() is False
        
        # Reset should restore health
        monitor.reset()
        
        assert monitor.is_healthy is True
        assert monitor.check_health() is True
    
    def test_reset_updates_heartbeat_timestamp(self):
        """Test that reset updates the heartbeat timestamp."""
        monitor = ProcessMonitor()
        
        initial_heartbeat = monitor.last_heartbeat
        time.sleep(0.1)
        monitor.reset()
        
        assert monitor.last_heartbeat > initial_heartbeat
    
    def test_multiple_heartbeats_maintain_health(self):
        """Test that regular heartbeats maintain healthy status."""
        monitor = ProcessMonitor(health_check_timeout=0.2)
        
        # Send heartbeats every 0.1s for 0.5s
        for _ in range(5):
            monitor.heartbeat()
            assert monitor.check_health() is True
            time.sleep(0.1)
    
    def test_health_status_change_logged(self):
        """Test that health status changes are logged."""
        monitor = ProcessMonitor(health_check_timeout=0.1)
        
        monitor.heartbeat()
        
        # First check - healthy
        assert monitor.check_health() is True
        
        # Wait for timeout
        time.sleep(0.15)
        
        # Second check - should detect unhealthy and log
        with patch.object(monitor.logger, 'error') as mock_error:
            result = monitor.check_health()
            assert result is False
            assert mock_error.called
            
            # Verify error message contains relevant info
            call_args = mock_error.call_args[0][0]
            assert "health check failed" in call_args.lower()
            assert "timeout" in call_args.lower()
    
    def test_health_restoration_logged(self):
        """Test that health restoration is logged."""
        monitor = ProcessMonitor(health_check_timeout=0.1)
        
        monitor.heartbeat()
        time.sleep(0.15)  # Timeout
        assert monitor.check_health() is False
        
        # Restore health
        monitor.heartbeat()
        
        with patch.object(monitor.logger, 'info') as mock_info:
            result = monitor.check_health()
            assert result is True
            assert mock_info.called
            
            # Verify info message about restoration
            call_args = mock_info.call_args[0][0]
            assert "health restored" in call_args.lower()
    
    def test_concurrent_heartbeats_thread_safe(self):
        """Test that heartbeat is thread-safe with concurrent calls."""
        monitor = ProcessMonitor()
        
        def send_heartbeats():
            for _ in range(10):
                monitor.heartbeat()
                time.sleep(0.01)
        
        # Start multiple threads sending heartbeats
        threads = [threading.Thread(target=send_heartbeats) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should still be healthy
        assert monitor.check_health() is True
    
    def test_check_health_boundary_condition(self):
        """Test check_health at exact timeout boundary."""
        monitor = ProcessMonitor(health_check_timeout=0.2)
        
        monitor.heartbeat()
        time.sleep(0.15)  # Just before timeout
        
        # Just before timeout, should still be healthy
        result = monitor.check_health()
        assert result is True
        
        # Wait past timeout
        time.sleep(0.1)  # Total 0.25s, past 0.2s timeout
        result = monitor.check_health()
        assert result is False

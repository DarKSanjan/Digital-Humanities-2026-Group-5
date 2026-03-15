"""
Error handling module for API retry logic and user-friendly error messages.

This module provides robust error handling with exponential backoff retry logic
and translation of technical errors into user-friendly messages.
"""

import logging
import time
import threading
from typing import Any, Callable, Optional, List
from dataclasses import dataclass
import requests


logger = logging.getLogger(__name__)


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""
    pass


@dataclass
class ErrorContext:
    """Context information for error handling."""
    error_type: str  # "network", "api", "system"
    original_error: Exception
    timestamp: float
    retry_count: int
    user_message: str
    technical_details: str
    is_recoverable: bool


class APIRetryHandler:
    """Handles API calls with exponential backoff retry logic."""
    
    def __init__(self, max_retries: int = 4, base_delay: float = 1.0):
        """
        Initialize the retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts (default: 4)
            base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.logger = logging.getLogger(__name__)
    
    def call_with_retry(
        self,
        api_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute API call with exponential backoff retry logic.
        
        Retry delays: 1s, 2s, 4s, 8s (for max_retries=4)
        
        Args:
            api_func: The API function to call
            *args: Positional arguments to pass to api_func
            **kwargs: Keyword arguments to pass to api_func
            
        Returns:
            The result from the API call
            
        Raises:
            RetryExhaustedError: If all retry attempts fail
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.info(f"API call attempt {attempt + 1}/{self.max_retries + 1}")
                result = api_func(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(f"API call succeeded after {attempt} retries")
                
                return result
                
            except Exception as e:
                last_error = e
                
                # Log the error with details
                self.logger.warning(
                    f"API call attempt {attempt + 1} failed: {type(e).__name__}: {str(e)}"
                )
                
                # If this was the last attempt, raise RetryExhaustedError
                if attempt == self.max_retries:
                    error_msg = f"API call failed after {self.max_retries + 1} attempts"
                    self.logger.error(error_msg)
                    raise RetryExhaustedError(error_msg) from e
                
                # Calculate exponential backoff delay: 1s, 2s, 4s, 8s
                delay = self.base_delay * (2 ** attempt)
                self.logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)
        
        # This should never be reached, but just in case
        raise RetryExhaustedError(
            f"API call failed after {self.max_retries + 1} attempts"
        ) from last_error
    
    def translate_error(self, error: Exception) -> str:
        """
        Convert technical error to user-friendly message.
        
        Args:
            error: The exception to translate
            
        Returns:
            A user-friendly error message string
        """
        # API errors (HTTP errors) - check first before general RequestException
        if isinstance(error, requests.exceptions.HTTPError):
            if hasattr(error, 'response') and error.response is not None:
                status_code = error.response.status_code
                
                if status_code == 401:
                    return "Authentication failed. Please check your API keys in settings."
                elif status_code == 429:
                    return "Too many requests. Please wait a moment before trying again."
                elif status_code == 503:
                    return "The service is temporarily unavailable. Please try again later."
                elif status_code >= 500:
                    return "The service is experiencing issues. Please try again later."
                elif status_code >= 400:
                    return "There was a problem with the request. Please try again."
            
            return "An error occurred while communicating with the service."
        
        # Network errors
        elif isinstance(error, requests.exceptions.ConnectionError):
            return "Unable to connect to the service. Please check your internet connection."
        
        elif isinstance(error, requests.exceptions.Timeout):
            return "The request took too long. Please try again."
        
        elif isinstance(error, requests.exceptions.RequestException):
            return "A network error occurred. Please check your connection and try again."
        
        # System errors
        elif isinstance(error, MemoryError):
            return "System memory is low. Please close other applications and try again."
        
        elif isinstance(error, RuntimeError):
            error_str = str(error).lower()
            if "cuda" in error_str or "gpu" in error_str:
                return "GPU rendering encountered an issue. Switching to CPU mode..."
            return "A system error occurred. Please try again."
        
        # Retry exhausted
        elif isinstance(error, RetryExhaustedError):
            return "Unable to complete the request after multiple attempts. Please check your connection and try again."
        
        # Generic fallback
        else:
            return "An unexpected error occurred. Please try again."
    
    def create_error_context(
        self,
        error: Exception,
        retry_count: int = 0
    ) -> ErrorContext:
        """
        Create an ErrorContext object with full error information.
        
        Args:
            error: The exception that occurred
            retry_count: Number of retries attempted
            
        Returns:
            ErrorContext object with error details
        """
        # Determine error type
        if isinstance(error, requests.exceptions.HTTPError):
            error_type = "api"
            # 401 is not recoverable (auth issue), 429 and 503 are recoverable
            if hasattr(error, 'response') and error.response is not None:
                status_code = error.response.status_code
                is_recoverable = status_code in [429, 503] or status_code >= 500
            else:
                is_recoverable = True
        elif isinstance(error, (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException
        )):
            error_type = "network"
            is_recoverable = True
        elif isinstance(error, (MemoryError, RuntimeError)):
            error_type = "system"
            is_recoverable = False
        else:
            error_type = "unknown"
            is_recoverable = False
        
        return ErrorContext(
            error_type=error_type,
            original_error=error,
            timestamp=time.time(),
            retry_count=retry_count,
            user_message=self.translate_error(error),
            technical_details=f"{type(error).__name__}: {str(error)}",
            is_recoverable=is_recoverable
        )


class NetworkMonitor:
    """Monitors network connectivity status."""
    
    def __init__(self, check_interval: float = 10.0):
        """
        Initialize the network monitor.
        
        Args:
            check_interval: Time in seconds between connectivity checks (default: 10.0)
        """
        self.check_interval = check_interval
        self.is_connected = True
        self.callbacks: List[Callable[[bool], None]] = []
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self.logger = logging.getLogger(__name__)
    
    def start_monitoring(self):
        """Start background connectivity checks."""
        if self._monitoring:
            self.logger.warning("Network monitoring already started")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.logger.info("Network monitoring started")
    
    def stop_monitoring(self):
        """Stop background connectivity checks."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=self.check_interval + 1)
        self.logger.info("Network monitoring stopped")
    
    def register_callback(self, callback: Callable[[bool], None]):
        """
        Register callback for connectivity changes.
        
        Args:
            callback: Function to call when connectivity changes.
                     Receives bool parameter (True=connected, False=disconnected)
        """
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            self.logger.debug(f"Registered connectivity callback: {callback.__name__}")
    
    def unregister_callback(self, callback: Callable[[bool], None]):
        """
        Unregister a previously registered callback.
        
        Args:
            callback: The callback function to remove
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            self.logger.debug(f"Unregistered connectivity callback: {callback.__name__}")
    
    def check_connectivity(self) -> bool:
        """
        Check if internet is available.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            # Try to connect to a reliable endpoint
            # Using Google's DNS as a lightweight connectivity check
            response = requests.get(
                "https://www.google.com",
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def _monitor_loop(self):
        """Background monitoring loop that checks connectivity periodically."""
        while self._monitoring:
            try:
                current_status = self.check_connectivity()
                
                # If connectivity status changed, notify callbacks
                if current_status != self.is_connected:
                    self.logger.info(
                        f"Network connectivity changed: "
                        f"{'connected' if current_status else 'disconnected'}"
                    )
                    self.is_connected = current_status
                    self._notify_callbacks(current_status)
                
                # Wait for next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in network monitoring loop: {e}")
                time.sleep(self.check_interval)
    
    def _notify_callbacks(self, is_connected: bool):
        """
        Notify all registered callbacks of connectivity change.
        
        Args:
            is_connected: Current connectivity status
        """
        for callback in self.callbacks:
            try:
                callback(is_connected)
            except Exception as e:
                self.logger.error(
                    f"Error calling connectivity callback {callback.__name__}: {e}"
                )


class ProcessMonitor:
    """Monitors Python process health."""
    
    def __init__(self, health_check_timeout: float = 2.0):
        """
        Initialize the process monitor.
        
        Args:
            health_check_timeout: Maximum time in seconds since last heartbeat
                                 before process is considered unhealthy (default: 2.0)
        """
        self.health_check_timeout = health_check_timeout
        self.is_healthy = True
        self.last_heartbeat = time.time()
        self.logger = logging.getLogger(__name__)
    
    def heartbeat(self):
        """
        Update heartbeat timestamp to indicate process is alive.
        
        This should be called regularly by the main process to signal
        that it is still responsive.
        """
        self.last_heartbeat = time.time()
        self.logger.debug(f"Heartbeat updated at {self.last_heartbeat}")
    
    def check_health(self) -> bool:
        """
        Check if process is responsive based on heartbeat timing.
        
        Returns:
            True if process is healthy (heartbeat within timeout),
            False if process appears to have crashed (no heartbeat for > timeout)
        """
        current_time = time.time()
        time_since_heartbeat = current_time - self.last_heartbeat
        
        was_healthy = self.is_healthy
        self.is_healthy = time_since_heartbeat <= self.health_check_timeout
        
        # Log health status changes
        if was_healthy and not self.is_healthy:
            self.logger.error(
                f"Process health check failed: no heartbeat for {time_since_heartbeat:.2f}s "
                f"(timeout: {self.health_check_timeout}s)"
            )
        elif not was_healthy and self.is_healthy:
            self.logger.info("Process health restored")
        
        return self.is_healthy
    
    def get_time_since_heartbeat(self) -> float:
        """
        Get time elapsed since last heartbeat.
        
        Returns:
            Time in seconds since last heartbeat
        """
        return time.time() - self.last_heartbeat
    
    def reset(self):
        """
        Reset the process monitor to healthy state.
        
        This should be called after process recovery or restart.
        """
        self.is_healthy = True
        self.last_heartbeat = time.time()
        self.logger.info("Process monitor reset")

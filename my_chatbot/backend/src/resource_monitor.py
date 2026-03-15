"""Resource monitoring module for tracking memory and VRAM usage."""

import logging
import time
import gc
import os
import glob
from dataclasses import dataclass
from typing import Optional, Dict, Callable, List
import threading

logger = logging.getLogger(__name__)


@dataclass
class ResourceMetrics:
    """System resource usage metrics."""
    timestamp: float
    memory_usage_gb: float
    memory_percent: float
    vram_usage_gb: Optional[float]
    vram_percent: Optional[float]
    session_duration: float
    frame_rate: float
    response_latency: float


class ResourceMonitor:
    """Monitors system resource usage."""
    
    def __init__(
        self,
        memory_warning_threshold: float = 0.8,
        memory_critical_threshold: float = 0.9,
        vram_warning_threshold: float = 5.0,  # GB
        vram_critical_threshold: float = 6.0,  # GB
        check_interval: float = 5.0,
        gc_interval: float = 600.0,  # 10 minutes
        temp_file_patterns: Optional[List[str]] = None
    ):
        """
        Initialize the resource monitor.
        
        Args:
            memory_warning_threshold: Memory usage percentage to trigger warning (0.0-1.0)
            memory_critical_threshold: Memory usage percentage to trigger critical action (0.0-1.0)
            vram_warning_threshold: VRAM usage in GB to trigger warning
            vram_critical_threshold: VRAM usage in GB to trigger critical action
            check_interval: Interval in seconds between resource checks
            gc_interval: Interval in seconds between automatic garbage collection (default: 600s = 10 minutes)
            temp_file_patterns: List of glob patterns for temporary files to clean up
        """
        self.memory_warning_threshold = memory_warning_threshold
        self.memory_critical_threshold = memory_critical_threshold
        self.vram_warning_threshold = vram_warning_threshold
        self.vram_critical_threshold = vram_critical_threshold
        self.check_interval = check_interval
        self.gc_interval = gc_interval
        self.temp_file_patterns = temp_file_patterns or []
        
        self.metrics: Dict[str, float] = {}
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._gc_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[ResourceMetrics], None]] = []
        self._last_gc_time: float = time.time()
        
        # Try to import psutil for memory monitoring
        try:
            import psutil
            self.psutil = psutil
            self._process = psutil.Process()
        except ImportError:
            logger.warning("psutil not available - memory monitoring will be limited")
            self.psutil = None
            self._process = None
        
        # Try to import torch for VRAM monitoring
        try:
            import torch
            self.torch = torch
            self._gpu_available = torch.cuda.is_available()
            if self._gpu_available:
                # Get total VRAM for percentage calculations
                self._total_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            else:
                self._total_vram_gb = None
        except ImportError:
            logger.warning("torch not available - VRAM monitoring will be disabled")
            self.torch = None
            self._gpu_available = False
            self._total_vram_gb = None
    
    def start_monitoring(self):
        """Start background resource monitoring."""
        if self._monitoring:
            logger.warning("Resource monitoring already started")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        # Start periodic garbage collection thread
        self._gc_thread = threading.Thread(target=self._gc_loop, daemon=True)
        self._gc_thread.start()
        
        logger.info(
            f"Resource monitoring started (check interval: {self.check_interval}s, "
            f"GC interval: {self.gc_interval}s)"
        )
    
    def stop_monitoring(self):
        """Stop background resource monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=self.check_interval + 1)
        if self._gc_thread:
            self._gc_thread.join(timeout=self.gc_interval + 1)
        logger.info("Resource monitoring stopped")
    
    def register_callback(self, callback: Callable[[ResourceMetrics], None]):
        """
        Register a callback to be called when metrics are updated.
        
        Args:
            callback: Function that takes ResourceMetrics as argument
        """
        self._callbacks.append(callback)
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._monitoring:
            try:
                # Get current metrics
                memory_usage = self.get_memory_usage()
                memory_percent = self.get_memory_percent()
                vram_usage = self.get_vram_usage()
                vram_percent = self.get_vram_percent()
                
                # Update metrics dictionary
                self.metrics['memory_usage_gb'] = memory_usage
                self.metrics['memory_percent'] = memory_percent
                if vram_usage is not None:
                    self.metrics['vram_usage_gb'] = vram_usage
                if vram_percent is not None:
                    self.metrics['vram_percent'] = vram_percent
                
                # Log current usage
                logger.debug(
                    f"Resource usage - Memory: {memory_usage:.2f}GB ({memory_percent:.1f}%), "
                    f"VRAM: {vram_usage:.2f}GB ({vram_percent:.1f}%)" if vram_usage else
                    f"Resource usage - Memory: {memory_usage:.2f}GB ({memory_percent:.1f}%)"
                )
                
                # Check thresholds
                self._check_memory_thresholds(memory_percent)
                if vram_usage is not None:
                    self._check_vram_thresholds(vram_usage)
                
                # Notify callbacks
                metrics = ResourceMetrics(
                    timestamp=time.time(),
                    memory_usage_gb=memory_usage,
                    memory_percent=memory_percent,
                    vram_usage_gb=vram_usage,
                    vram_percent=vram_percent,
                    session_duration=0.0,  # To be set by caller
                    frame_rate=0.0,  # To be set by caller
                    response_latency=0.0  # To be set by caller
                )
                for callback in self._callbacks:
                    try:
                        callback(metrics)
                    except Exception as e:
                        logger.error(f"Error in resource monitor callback: {e}")
                
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
            
            # Wait for next check
            time.sleep(self.check_interval)
    
    def _gc_loop(self):
        """Background garbage collection loop."""
        while self._monitoring:
            try:
                # Wait for the GC interval
                time.sleep(self.gc_interval)
                
                if not self._monitoring:
                    break
                
                # Trigger periodic garbage collection
                logger.info("Periodic garbage collection triggered (10-minute interval)")
                self.trigger_garbage_collection()
                
                # Clean up temporary files
                self.cleanup_temporary_files()
                
            except Exception as e:
                logger.error(f"Error in garbage collection loop: {e}")
    
    def get_memory_usage(self) -> float:
        """
        Get current memory usage in GB.
        
        Returns:
            Memory usage in GB
        """
        if self._process and self.psutil:
            try:
                memory_info = self._process.memory_info()
                return memory_info.rss / (1024 ** 3)
            except Exception as e:
                logger.error(f"Failed to get memory usage: {e}")
        
        return 0.0
    
    def get_memory_percent(self) -> float:
        """
        Get current memory usage as percentage of total system memory.
        
        Returns:
            Memory usage percentage (0.0-1.0)
        """
        if self.psutil:
            try:
                memory = self.psutil.virtual_memory()
                return memory.percent / 100.0
            except Exception as e:
                logger.error(f"Failed to get memory percentage: {e}")
        
        return 0.0
    
    def get_vram_usage(self) -> Optional[float]:
        """
        Get current VRAM usage in GB (if GPU available).
        
        Returns:
            VRAM usage in GB, or None if GPU not available
        """
        if not self._gpu_available or not self.torch:
            return None
        
        try:
            if self.torch.cuda.is_available():
                allocated = self.torch.cuda.memory_allocated(0)
                return allocated / (1024 ** 3)
        except Exception as e:
            logger.error(f"Failed to get VRAM usage: {e}")
        
        return None
    
    def get_vram_percent(self) -> Optional[float]:
        """
        Get current VRAM usage as percentage of total VRAM.
        
        Returns:
            VRAM usage percentage (0.0-1.0), or None if GPU not available
        """
        if not self._gpu_available or self._total_vram_gb is None:
            return None
        
        vram_usage = self.get_vram_usage()
        if vram_usage is None:
            return None
        
        return vram_usage / self._total_vram_gb
    
    def _check_memory_thresholds(self, memory_percent: float):
        """Check memory usage against thresholds and take action."""
        if memory_percent >= self.memory_critical_threshold:
            logger.critical(
                f"Memory usage critical: {memory_percent:.1%} "
                f"(threshold: {self.memory_critical_threshold:.1%})"
            )
            self.trigger_garbage_collection()
        elif memory_percent >= self.memory_warning_threshold:
            logger.warning(
                f"Memory usage high: {memory_percent:.1%} "
                f"(threshold: {self.memory_warning_threshold:.1%})"
            )
    
    def _check_vram_thresholds(self, vram_usage: float):
        """Check VRAM usage against thresholds and log warnings."""
        if vram_usage >= self.vram_critical_threshold:
            logger.critical(
                f"VRAM usage critical: {vram_usage:.2f}GB "
                f"(threshold: {self.vram_critical_threshold:.2f}GB)"
            )
        elif vram_usage >= self.vram_warning_threshold:
            logger.warning(
                f"VRAM usage high: {vram_usage:.2f}GB "
                f"(threshold: {self.vram_warning_threshold:.2f}GB)"
            )
    
    def trigger_garbage_collection(self):
        """Force garbage collection and log results."""
        logger.info("Triggering garbage collection...")
        
        # Get memory before GC
        memory_before = self.get_memory_usage()
        
        # Run garbage collection
        collected = gc.collect()
        
        # Get memory after GC
        memory_after = self.get_memory_usage()
        memory_freed = memory_before - memory_after
        
        # Update last GC time
        self._last_gc_time = time.time()
        
        logger.info(
            f"Garbage collection completed: {collected} objects collected, "
            f"{memory_freed:.2f}GB freed"
        )
    
    def cleanup_temporary_files(self):
        """Clean up temporary files based on configured patterns."""
        if not self.temp_file_patterns:
            logger.debug("No temporary file patterns configured, skipping cleanup")
            return
        
        total_files_removed = 0
        total_size_freed = 0
        
        for pattern in self.temp_file_patterns:
            try:
                files = glob.glob(pattern, recursive=True)
                for file_path in files:
                    try:
                        if os.path.isfile(file_path):
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            total_files_removed += 1
                            total_size_freed += file_size
                            logger.debug(f"Removed temporary file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove temporary file {file_path}: {e}")
            except Exception as e:
                logger.warning(f"Failed to process pattern {pattern}: {e}")
        
        if total_files_removed > 0:
            size_mb = total_size_freed / (1024 * 1024)
            logger.info(
                f"Temporary file cleanup completed: {total_files_removed} files removed, "
                f"{size_mb:.2f}MB freed"
            )
        else:
            logger.debug("No temporary files found to clean up")
    
    def release_gpu_resources(self):
        """Release GPU resources when switching to CPU mode."""
        if not self._gpu_available or not self.torch:
            logger.debug("GPU not available, no resources to release")
            return
        
        try:
            # Get VRAM usage before cleanup
            vram_before = self.get_vram_usage()
            
            # Clear CUDA cache
            if self.torch.cuda.is_available():
                self.torch.cuda.empty_cache()
                logger.info("CUDA cache cleared")
            
            # Force garbage collection to clean up GPU tensors
            gc.collect()
            
            # Get VRAM usage after cleanup
            vram_after = self.get_vram_usage()
            
            if vram_before is not None and vram_after is not None:
                vram_freed = vram_before - vram_after
                logger.info(
                    f"GPU resources released: {vram_freed:.2f}GB VRAM freed "
                    f"(before: {vram_before:.2f}GB, after: {vram_after:.2f}GB)"
                )
            else:
                logger.info("GPU resources released")
                
        except Exception as e:
            logger.error(f"Failed to release GPU resources: {e}")
    
    def add_temp_file_pattern(self, pattern: str):
        """
        Add a temporary file pattern for cleanup.
        
        Args:
            pattern: Glob pattern for temporary files (e.g., "temp/*.wav")
        """
        if pattern not in self.temp_file_patterns:
            self.temp_file_patterns.append(pattern)
            logger.debug(f"Added temporary file pattern: {pattern}")
    
    def check_session_stability(self, session_duration: float) -> bool:
        """
        Verify performance metrics for extended sessions.
        
        Args:
            session_duration: Duration of current session in seconds
        
        Returns:
            True if session is stable, False otherwise
        """
        if session_duration < 1800:  # Less than 30 minutes
            return True
        
        # Check if memory usage is within acceptable limits
        memory_percent = self.get_memory_percent()
        if memory_percent >= self.memory_critical_threshold:
            logger.warning(
                f"Session stability check failed: memory usage {memory_percent:.1%} "
                f"exceeds critical threshold"
            )
            return False
        
        # Check if VRAM usage is within acceptable limits (if GPU available)
        vram_usage = self.get_vram_usage()
        if vram_usage is not None and vram_usage >= self.vram_critical_threshold:
            logger.warning(
                f"Session stability check failed: VRAM usage {vram_usage:.2f}GB "
                f"exceeds critical threshold"
            )
            return False
        
        logger.info(f"Session stability check passed (duration: {session_duration:.0f}s)")
        return True

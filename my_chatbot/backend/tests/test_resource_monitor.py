"""Unit tests for ResourceMonitor class."""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from backend.src.resource_monitor import ResourceMonitor, ResourceMetrics


class TestResourceMonitorInitialization:
    """Test ResourceMonitor initialization."""
    
    def test_default_initialization(self):
        """Test ResourceMonitor initializes with default values."""
        monitor = ResourceMonitor()
        
        assert monitor.memory_warning_threshold == 0.8
        assert monitor.memory_critical_threshold == 0.9
        assert monitor.vram_warning_threshold == 5.0
        assert monitor.vram_critical_threshold == 6.0
        assert monitor.check_interval == 5.0
        assert not monitor._monitoring
    
    def test_custom_thresholds(self):
        """Test ResourceMonitor initializes with custom thresholds."""
        monitor = ResourceMonitor(
            memory_warning_threshold=0.7,
            memory_critical_threshold=0.85,
            vram_warning_threshold=4.0,
            vram_critical_threshold=5.5,
            check_interval=3.0
        )
        
        assert monitor.memory_warning_threshold == 0.7
        assert monitor.memory_critical_threshold == 0.85
        assert monitor.vram_warning_threshold == 4.0
        assert monitor.vram_critical_threshold == 5.5
        assert monitor.check_interval == 3.0


class TestMemoryMonitoring:
    """Test memory usage monitoring."""
    
    def test_get_memory_usage(self):
        """Test getting memory usage in GB."""
        # Mock process memory info
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 2 * 1024 ** 3  # 2GB in bytes
        mock_process.memory_info.return_value = mock_memory_info
        
        mock_psutil = Mock()
        
        monitor = ResourceMonitor()
        monitor._process = mock_process
        monitor.psutil = mock_psutil
        
        memory_usage = monitor.get_memory_usage()
        
        assert memory_usage == 2.0
    
    def test_get_memory_percent(self):
        """Test getting memory usage percentage."""
        # Mock virtual memory
        mock_memory = Mock()
        mock_memory.percent = 75.0
        
        mock_psutil = Mock()
        mock_psutil.virtual_memory.return_value = mock_memory
        
        monitor = ResourceMonitor()
        monitor.psutil = mock_psutil
        
        memory_percent = monitor.get_memory_percent()
        
        assert memory_percent == 0.75
    
    def test_memory_usage_without_psutil(self):
        """Test memory usage returns 0 when psutil not available."""
        monitor = ResourceMonitor()
        monitor.psutil = None
        monitor._process = None
        
        memory_usage = monitor.get_memory_usage()
        
        assert memory_usage == 0.0


class TestVRAMMonitoring:
    """Test VRAM usage monitoring."""
    
    def test_get_vram_usage_with_gpu(self):
        """Test getting VRAM usage when GPU is available."""
        # Mock CUDA availability and memory
        mock_torch = Mock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.memory_allocated.return_value = 3 * 1024 ** 3  # 3GB in bytes
        
        monitor = ResourceMonitor()
        monitor.torch = mock_torch
        monitor._gpu_available = True
        monitor._total_vram_gb = 8.0
        
        vram_usage = monitor.get_vram_usage()
        
        assert vram_usage == 3.0
    
    def test_get_vram_usage_without_gpu(self):
        """Test VRAM usage returns None when GPU not available."""
        monitor = ResourceMonitor()
        monitor._gpu_available = False
        monitor.torch = None
        
        vram_usage = monitor.get_vram_usage()
        
        assert vram_usage is None
    
    def test_get_vram_percent(self):
        """Test getting VRAM usage percentage."""
        # Mock CUDA availability and memory
        mock_torch = Mock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.memory_allocated.return_value = 4 * 1024 ** 3  # 4GB
        
        monitor = ResourceMonitor()
        monitor.torch = mock_torch
        monitor._gpu_available = True
        monitor._total_vram_gb = 8.0
        
        vram_percent = monitor.get_vram_percent()
        
        assert vram_percent == 0.5


class TestThresholdChecking:
    """Test threshold checking and warnings."""
    
    def test_memory_warning_threshold(self, caplog):
        """Test warning logged when memory exceeds warning threshold."""
        monitor = ResourceMonitor(memory_warning_threshold=0.8)
        
        # Simulate memory at 85% (above 80% warning)
        monitor._check_memory_thresholds(0.85)
        
        assert "Memory usage high" in caplog.text
    
    def test_memory_critical_threshold(self, caplog):
        """Test critical action when memory exceeds critical threshold."""
        # Mock process for GC
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 2 * 1024 ** 3
        mock_process.memory_info.return_value = mock_memory_info
        
        mock_psutil = Mock()
        
        monitor = ResourceMonitor(memory_critical_threshold=0.9)
        monitor.psutil = mock_psutil
        monitor._process = mock_process
        
        # Simulate memory at 95% (above 90% critical)
        monitor._check_memory_thresholds(0.95)
        
        assert "Memory usage critical" in caplog.text
    
    def test_vram_warning_threshold(self, caplog):
        """Test warning logged when VRAM exceeds warning threshold."""
        monitor = ResourceMonitor(vram_warning_threshold=5.0)
        
        # Simulate VRAM at 5.5GB (above 5GB warning)
        monitor._check_vram_thresholds(5.5)
        
        assert "VRAM usage high" in caplog.text
    
    def test_vram_critical_threshold(self, caplog):
        """Test critical logged when VRAM exceeds critical threshold."""
        monitor = ResourceMonitor(vram_critical_threshold=6.0)
        
        # Simulate VRAM at 6.5GB (above 6GB critical)
        monitor._check_vram_thresholds(6.5)
        
        assert "VRAM usage critical" in caplog.text


class TestGarbageCollection:
    """Test garbage collection functionality."""
    
    @patch('backend.src.resource_monitor.gc')
    def test_trigger_garbage_collection(self, mock_gc, caplog):
        """Test garbage collection is triggered and logged."""
        import logging
        caplog.set_level(logging.INFO)
        
        # Mock memory before and after GC
        mock_process = Mock()
        mock_memory_info_before = Mock()
        mock_memory_info_before.rss = 2 * 1024 ** 3  # 2GB
        mock_memory_info_after = Mock()
        mock_memory_info_after.rss = 1.5 * 1024 ** 3  # 1.5GB
        
        mock_process.memory_info.side_effect = [
            mock_memory_info_before,
            mock_memory_info_after
        ]
        
        mock_psutil = Mock()
        mock_gc.collect.return_value = 42  # Number of objects collected
        
        monitor = ResourceMonitor()
        monitor.psutil = mock_psutil
        monitor._process = mock_process
        
        monitor.trigger_garbage_collection()
        
        assert "Triggering garbage collection" in caplog.text
        assert "42 objects collected" in caplog.text
        mock_gc.collect.assert_called_once()


class TestSessionStability:
    """Test session stability checking."""
    
    def test_session_stability_short_session(self):
        """Test session stability returns True for sessions under 30 minutes."""
        monitor = ResourceMonitor()
        
        # Session duration: 15 minutes (900 seconds)
        is_stable = monitor.check_session_stability(900.0)
        
        assert is_stable is True
    
    def test_session_stability_long_session_stable(self):
        """Test session stability returns True for stable long sessions."""
        # Mock memory at 70% (below critical)
        mock_memory = Mock()
        mock_memory.percent = 70.0
        
        mock_psutil = Mock()
        mock_psutil.virtual_memory.return_value = mock_memory
        
        monitor = ResourceMonitor()
        monitor.psutil = mock_psutil
        monitor._gpu_available = False
        
        # Session duration: 35 minutes (2100 seconds)
        is_stable = monitor.check_session_stability(2100.0)
        
        assert is_stable is True
    
    def test_session_stability_long_session_memory_critical(self):
        """Test session stability returns False when memory is critical."""
        # Mock memory at 95% (above 90% critical)
        mock_memory = Mock()
        mock_memory.percent = 95.0
        
        mock_psutil = Mock()
        mock_psutil.virtual_memory.return_value = mock_memory
        
        monitor = ResourceMonitor(memory_critical_threshold=0.9)
        monitor.psutil = mock_psutil
        monitor._gpu_available = False
        
        # Session duration: 35 minutes (2100 seconds)
        is_stable = monitor.check_session_stability(2100.0)
        
        assert is_stable is False
    
    def test_session_stability_long_session_vram_critical(self):
        """Test session stability returns False when VRAM is critical."""
        # Mock memory at 70% (OK)
        mock_memory = Mock()
        mock_memory.percent = 70.0
        
        mock_psutil = Mock()
        mock_psutil.virtual_memory.return_value = mock_memory
        
        # Mock VRAM at 6.5GB (above 6GB critical)
        mock_torch = Mock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.memory_allocated.return_value = 6.5 * 1024 ** 3
        
        monitor = ResourceMonitor(vram_critical_threshold=6.0)
        monitor.psutil = mock_psutil
        monitor.torch = mock_torch
        monitor._gpu_available = True
        monitor._total_vram_gb = 8.0
        
        # Session duration: 35 minutes (2100 seconds)
        is_stable = monitor.check_session_stability(2100.0)
        
        assert is_stable is False


class TestMonitoringLoop:
    """Test background monitoring loop."""
    
    def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        monitor = ResourceMonitor(check_interval=0.1)
        
        assert not monitor._monitoring
        
        monitor.start_monitoring()
        assert monitor._monitoring
        assert monitor._monitor_thread is not None
        
        time.sleep(0.2)  # Let it run briefly
        
        monitor.stop_monitoring()
        assert not monitor._monitoring
    
    def test_monitoring_updates_metrics(self):
        """Test monitoring loop updates metrics dictionary."""
        # Mock memory
        mock_memory = Mock()
        mock_memory.percent = 50.0
        
        mock_psutil = Mock()
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 1 * 1024 ** 3  # 1GB
        mock_process.memory_info.return_value = mock_memory_info
        
        monitor = ResourceMonitor(check_interval=0.1)
        monitor.psutil = mock_psutil
        monitor._process = mock_process
        monitor._gpu_available = False
        
        monitor.start_monitoring()
        time.sleep(0.3)  # Wait for at least 2 checks
        monitor.stop_monitoring()
        
        assert 'memory_usage_gb' in monitor.metrics
        assert 'memory_percent' in monitor.metrics
    
    def test_monitoring_callbacks(self):
        """Test monitoring loop calls registered callbacks."""
        # Mock memory
        mock_memory = Mock()
        mock_memory.percent = 50.0
        
        mock_psutil = Mock()
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 1 * 1024 ** 3
        mock_process.memory_info.return_value = mock_memory_info
        
        monitor = ResourceMonitor(check_interval=0.1)
        monitor.psutil = mock_psutil
        monitor._process = mock_process
        monitor._gpu_available = False
        
        # Register callback
        callback_called = threading.Event()
        received_metrics = []
        
        def callback(metrics: ResourceMetrics):
            received_metrics.append(metrics)
            callback_called.set()
        
        monitor.register_callback(callback)
        
        monitor.start_monitoring()
        callback_called.wait(timeout=1.0)
        monitor.stop_monitoring()
        
        assert len(received_metrics) > 0
        assert isinstance(received_metrics[0], ResourceMetrics)


class TestResourceMetrics:
    """Test ResourceMetrics dataclass."""
    
    def test_resource_metrics_creation(self):
        """Test creating ResourceMetrics instance."""
        metrics = ResourceMetrics(
            timestamp=time.time(),
            memory_usage_gb=1.5,
            memory_percent=0.75,
            vram_usage_gb=3.0,
            vram_percent=0.5,
            session_duration=1800.0,
            frame_rate=30.0,
            response_latency=2.5
        )
        
        assert metrics.memory_usage_gb == 1.5
        assert metrics.memory_percent == 0.75
        assert metrics.vram_usage_gb == 3.0
        assert metrics.vram_percent == 0.5
        assert metrics.session_duration == 1800.0
        assert metrics.frame_rate == 30.0
        assert metrics.response_latency == 2.5
    
    def test_resource_metrics_with_none_vram(self):
        """Test ResourceMetrics with None VRAM values (CPU mode)."""
        metrics = ResourceMetrics(
            timestamp=time.time(),
            memory_usage_gb=1.5,
            memory_percent=0.75,
            vram_usage_gb=None,
            vram_percent=None,
            session_duration=1800.0,
            frame_rate=30.0,
            response_latency=2.5
        )
        
        assert metrics.vram_usage_gb is None
        assert metrics.vram_percent is None



class TestGarbageCollectionEnhancements:
    """Test enhanced garbage collection functionality."""
    
    def test_gc_interval_initialization(self):
        """Test ResourceMonitor initializes with GC interval."""
        monitor = ResourceMonitor(gc_interval=300.0)
        
        assert monitor.gc_interval == 300.0
        assert monitor._last_gc_time > 0
    
    def test_temp_file_patterns_initialization(self):
        """Test ResourceMonitor initializes with temp file patterns."""
        patterns = ["temp/*.wav", "temp/*.mp3"]
        monitor = ResourceMonitor(temp_file_patterns=patterns)
        
        assert monitor.temp_file_patterns == patterns
    
    def test_add_temp_file_pattern(self):
        """Test adding temporary file pattern."""
        monitor = ResourceMonitor()
        
        monitor.add_temp_file_pattern("temp/*.wav")
        assert "temp/*.wav" in monitor.temp_file_patterns
        
        # Adding same pattern again should not duplicate
        monitor.add_temp_file_pattern("temp/*.wav")
        assert monitor.temp_file_patterns.count("temp/*.wav") == 1
    
    @patch('backend.src.resource_monitor.glob.glob')
    @patch('backend.src.resource_monitor.os.path.isfile')
    @patch('backend.src.resource_monitor.os.path.getsize')
    @patch('backend.src.resource_monitor.os.remove')
    def test_cleanup_temporary_files(self, mock_remove, mock_getsize, mock_isfile, mock_glob, caplog):
        """Test temporary file cleanup."""
        import logging
        caplog.set_level(logging.INFO)
        
        # Mock glob to return some files
        mock_glob.return_value = ["temp/audio1.wav", "temp/audio2.wav"]
        mock_isfile.return_value = True
        mock_getsize.return_value = 1024 * 1024  # 1MB each
        
        monitor = ResourceMonitor(temp_file_patterns=["temp/*.wav"])
        monitor.cleanup_temporary_files()
        
        # Verify files were removed
        assert mock_remove.call_count == 2
        assert "2 files removed" in caplog.text
        assert "2.00MB freed" in caplog.text
    
    @patch('backend.src.resource_monitor.glob.glob')
    def test_cleanup_temporary_files_no_patterns(self, mock_glob, caplog):
        """Test cleanup with no patterns configured."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        monitor = ResourceMonitor()
        monitor.cleanup_temporary_files()
        
        # Should not call glob
        mock_glob.assert_not_called()
        assert "No temporary file patterns configured" in caplog.text
    
    @patch('backend.src.resource_monitor.glob.glob')
    def test_cleanup_temporary_files_no_files_found(self, mock_glob, caplog):
        """Test cleanup when no files match patterns."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        mock_glob.return_value = []
        
        monitor = ResourceMonitor(temp_file_patterns=["temp/*.wav"])
        monitor.cleanup_temporary_files()
        
        assert "No temporary files found" in caplog.text
    
    def test_release_gpu_resources_no_gpu(self, caplog):
        """Test GPU resource release when GPU not available."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        monitor = ResourceMonitor()
        monitor._gpu_available = False
        monitor.torch = None
        
        monitor.release_gpu_resources()
        
        assert "GPU not available" in caplog.text
    
    def test_release_gpu_resources_with_gpu(self, caplog):
        """Test GPU resource release when GPU is available."""
        import logging
        caplog.set_level(logging.INFO)
        
        # Mock CUDA
        mock_torch = Mock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.empty_cache = Mock()
        mock_torch.cuda.memory_allocated.side_effect = [
            4 * 1024 ** 3,  # 4GB before
            2 * 1024 ** 3   # 2GB after
        ]
        
        monitor = ResourceMonitor()
        monitor.torch = mock_torch
        monitor._gpu_available = True
        monitor._total_vram_gb = 8.0
        
        monitor.release_gpu_resources()
        
        # Verify CUDA cache was cleared
        mock_torch.cuda.empty_cache.assert_called_once()
        assert "CUDA cache cleared" in caplog.text
        assert "2.00GB VRAM freed" in caplog.text
    
    def test_gc_thread_starts_with_monitoring(self):
        """Test GC thread starts when monitoring starts."""
        monitor = ResourceMonitor(check_interval=0.1, gc_interval=0.5)
        
        monitor.start_monitoring()
        
        assert monitor._gc_thread is not None
        assert monitor._gc_thread.is_alive()
        
        monitor.stop_monitoring()
    
    @patch('backend.src.resource_monitor.gc')
    def test_periodic_gc_triggers(self, mock_gc, caplog):
        """Test periodic garbage collection triggers after interval."""
        import logging
        caplog.set_level(logging.INFO)
        
        # Mock memory
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 2 * 1024 ** 3
        mock_process.memory_info.return_value = mock_memory_info
        
        mock_psutil = Mock()
        mock_gc.collect.return_value = 10
        
        monitor = ResourceMonitor(check_interval=0.1, gc_interval=0.3)
        monitor.psutil = mock_psutil
        monitor._process = mock_process
        
        monitor.start_monitoring()
        time.sleep(0.5)  # Wait for GC to trigger
        monitor.stop_monitoring()
        
        # Verify periodic GC was triggered
        assert "Periodic garbage collection triggered" in caplog.text
        assert mock_gc.collect.called
    
    @patch('backend.src.resource_monitor.gc')
    def test_trigger_gc_updates_last_gc_time(self, mock_gc):
        """Test that triggering GC updates the last GC time."""
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 2 * 1024 ** 3
        mock_process.memory_info.return_value = mock_memory_info
        
        mock_psutil = Mock()
        mock_gc.collect.return_value = 5
        
        monitor = ResourceMonitor()
        monitor.psutil = mock_psutil
        monitor._process = mock_process
        
        initial_time = monitor._last_gc_time
        time.sleep(0.1)
        
        monitor.trigger_garbage_collection()
        
        assert monitor._last_gc_time > initial_time


class TestThresholdBasedGC:
    """Test threshold-based garbage collection triggering."""
    
    @patch('backend.src.resource_monitor.gc')
    def test_memory_threshold_triggers_gc(self, mock_gc, caplog):
        """Test that exceeding memory threshold triggers GC."""
        import logging
        caplog.set_level(logging.INFO)
        
        # Mock memory
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 2 * 1024 ** 3
        mock_process.memory_info.return_value = mock_memory_info
        
        mock_psutil = Mock()
        mock_gc.collect.return_value = 15
        
        monitor = ResourceMonitor(memory_critical_threshold=0.8)
        monitor.psutil = mock_psutil
        monitor._process = mock_process
        
        # Trigger threshold check with 85% memory (above 80% critical)
        monitor._check_memory_thresholds(0.85)
        
        # Verify GC was triggered
        assert "Memory usage critical" in caplog.text
        assert "Triggering garbage collection" in caplog.text
        mock_gc.collect.assert_called()

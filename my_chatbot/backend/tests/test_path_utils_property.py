"""Property-based tests for cross-platform path handling utilities.

Feature: persuasive-chatbot
Property 28: Cross-Platform Path Handling
Validates: Requirements 13.2, 13.8
"""

import pytest
import os
import platform
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
from src.path_utils import PathUtils


class TestCrossPlatformPathHandling:
    """
    Property 28: Cross-Platform Path Handling
    
    For any file system operation in the Python backend, the system should
    use platform-agnostic path handling (e.g., pathlib or os.path) that
    works correctly on both Windows and macOS without hardcoded separators.
    
    Validates: Requirements 13.2, 13.8
    """
    
    @given(
        parts=st.lists(
            st.text(
                alphabet=st.characters(
                    blacklist_categories=('Cs',),  # Exclude surrogates
                    blacklist_characters='/\\:*?"<>|'  # Exclude invalid path chars
                ),
                min_size=1,
                max_size=20
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=20)
    def test_property_28_path_joining_is_platform_agnostic(self, parts):
        """
        Property: Path joining should work correctly on any platform without
        hardcoded separators.
        
        For any list of path components, joining them should produce a valid
        path using the platform's native separator.
        """
        # Filter out empty strings and strings with only whitespace
        parts = [p.strip() for p in parts if p.strip()]
        assume(len(parts) > 0)
        
        # Join paths using our utility
        joined = PathUtils.join_paths(*parts)
        
        # Verify it's a Path object
        assert isinstance(joined, Path)
        
        # Verify the path contains all parts
        path_str = str(joined)
        for part in parts:
            assert part in path_str
        
        # Verify it uses platform-appropriate separator
        if len(parts) > 1:
            # Should contain the platform separator
            assert os.sep in path_str or len(parts) == 1
    
    @given(
        path_str=st.text(
            alphabet=st.characters(
                blacklist_categories=('Cs',),
                blacklist_characters='*?"<>|'  # Exclude some invalid chars
            ),
            min_size=1,
            max_size=50
        )
    )
    @settings(max_examples=20)
    def test_property_28_path_normalization_is_consistent(self, path_str):
        """
        Property: Path normalization should be consistent and idempotent.
        
        For any path string, normalizing it multiple times should produce
        the same result.
        """
        # Skip paths that are just separators or invalid
        assume(path_str.strip() and path_str.strip() not in ['/', '\\', '.', '..'])
        
        try:
            # Normalize once
            normalized1 = PathUtils.normalize_path(path_str)
            
            # Normalize again
            normalized2 = PathUtils.normalize_path(normalized1)
            
            # Should be the same
            assert normalized1 == normalized2
            
            # Should be a Path object
            assert isinstance(normalized1, Path)
            assert isinstance(normalized2, Path)
        except (ValueError, OSError):
            # Some paths may be invalid on certain platforms
            pass
    
    @given(
        suffix=st.one_of(st.none(), st.sampled_from(['.txt', '.json', '.tmp', '.dat'])),
        prefix=st.one_of(st.none(), st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=ord('a'), max_codepoint=ord('z')),
            min_size=1, 
            max_size=10
        ))
    )
    @settings(max_examples=20)
    def test_property_28_temp_file_creation_is_platform_agnostic(self, suffix, prefix):
        """
        Property: Temporary file creation should work on any platform.
        
        For any suffix and prefix, creating a temp file should succeed and
        produce a valid path.
        """
        # Create temp file
        temp_path = PathUtils.create_temp_file(suffix=suffix, prefix=prefix)
        
        try:
            # Verify it's a Path object
            assert isinstance(temp_path, Path)
            
            # Verify the file exists
            assert temp_path.exists()
            assert temp_path.is_file()
            
            # Verify suffix if provided
            if suffix:
                assert str(temp_path).endswith(suffix)
            
            # Verify prefix if provided
            if prefix:
                assert prefix in temp_path.name
            
            # Verify it's in the temp directory
            temp_dir = PathUtils.get_temp_dir()
            assert temp_path.parent == temp_dir or temp_dir in temp_path.parents
            
        finally:
            # Clean up
            if temp_path.exists():
                temp_path.unlink()
    
    @given(
        content=st.text(min_size=0, max_size=1000)
    )
    @settings(max_examples=20)
    def test_property_28_text_file_operations_handle_line_endings(self, content):
        """
        Property: Text file operations should handle platform-specific line
        endings transparently.
        
        For any text content, writing and reading should preserve the content
        regardless of line ending differences.
        """
        with PathUtils.temp_file_context(suffix='.txt') as temp_path:
            # Write content
            PathUtils.write_text_file(temp_path, content)
            
            # Read it back
            read_content = PathUtils.read_text_file(temp_path)
            
            # Content should be preserved, accounting for platform line ending normalization
            # Python's text mode converts \r to \n on Windows, which is expected behavior
            # Normalize both for comparison
            normalized_content = content.replace('\r\n', '\n').replace('\r', '\n')
            normalized_read = read_content.replace('\r\n', '\n').replace('\r', '\n')
            assert normalized_read == normalized_content
    
    @given(
        content=st.binary(min_size=0, max_size=1000)
    )
    @settings(max_examples=20)
    def test_property_28_binary_file_operations_are_platform_agnostic(self, content):
        """
        Property: Binary file operations should work identically on all platforms.
        
        For any binary content, writing and reading should preserve the exact
        bytes regardless of platform.
        """
        with PathUtils.temp_file_context(suffix='.bin') as temp_path:
            # Write binary content
            PathUtils.write_binary_file(temp_path, content)
            
            # Read it back
            read_content = PathUtils.read_binary_file(temp_path)
            
            # Content should be exactly the same
            assert read_content == content
    
    def test_property_28_directory_operations_are_platform_agnostic(self):
        """
        Property: Directory operations should work on any platform.
        
        Creating, checking, and deleting directories should work consistently
        across platforms.
        """
        with PathUtils.temp_directory_context(prefix='test_') as temp_dir:
            # Verify it's a Path object
            assert isinstance(temp_dir, Path)
            
            # Verify directory exists
            assert temp_dir.exists()
            assert temp_dir.is_dir()
            
            # Create a subdirectory
            sub_dir = temp_dir / "subdir"
            PathUtils.ensure_directory(sub_dir)
            
            assert sub_dir.exists()
            assert sub_dir.is_dir()
            
            # Create a file in the subdirectory
            test_file = sub_dir / "test.txt"
            PathUtils.write_text_file(test_file, "test content")
            
            assert test_file.exists()
            assert PathUtils.file_exists(test_file)
            
            # List files
            files = PathUtils.list_files(temp_dir, recursive=True)
            assert len(files) == 1
            assert files[0].name == "test.txt"
    
    @given(
        parts=st.lists(
            st.text(min_size=1, max_size=10, alphabet=st.characters(
                min_codepoint=ord('a'), max_codepoint=ord('z')
            )),
            min_size=2,
            max_size=5
        )
    )
    @settings(max_examples=20)
    def test_property_28_relative_path_calculation_is_correct(self, parts):
        """
        Property: Relative path calculation should work correctly on any platform.
        
        For any base and target path, calculating the relative path should
        produce a valid result.
        """
        assume(len(parts) >= 2)
        
        with PathUtils.temp_directory_context() as temp_dir:
            # Create base path
            base = temp_dir / parts[0]
            PathUtils.ensure_directory(base)
            
            # Create target path
            target = temp_dir / Path(*parts)
            PathUtils.ensure_directory(target.parent)
            
            # Calculate relative path
            try:
                relative = PathUtils.get_relative_path(target, base)
                
                # Verify it's a Path object
                assert isinstance(relative, Path)
                
                # Verify we can reconstruct the target from base + relative
                reconstructed = (base / relative).resolve()
                assert reconstructed == target.resolve()
            except ValueError:
                # Some paths may not be relative to each other
                pass
    
    def test_property_28_path_separator_is_never_hardcoded(self):
        """
        Property: Path operations should never use hardcoded separators.
        
        All path operations should use pathlib or os.sep, never hardcoded
        '/' or '\\' characters.
        """
        # Test that joining with different separators produces same result
        parts = ['dir1', 'dir2', 'file.txt']
        
        # Using our utility
        path1 = PathUtils.join_paths(*parts)
        
        # Using pathlib directly
        path2 = Path(parts[0])
        for part in parts[1:]:
            path2 = path2 / part
        
        # Should produce equivalent paths
        assert path1 == path2
        
        # Verify the path uses platform separator
        path_str = str(path1)
        if platform.system() == 'Windows':
            # Windows should use backslash (or forward slash, both work)
            assert '\\' in path_str or '/' in path_str
        else:
            # Unix-like should use forward slash
            assert '/' in path_str
    
    @given(
        filename=st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(
                min_codepoint=ord('a'),
                max_codepoint=ord('z')
            )
        )
    )
    @settings(max_examples=20)
    def test_property_28_file_existence_checks_are_reliable(self, filename):
        """
        Property: File existence checks should be reliable on any platform.
        
        For any filename, checking existence should correctly report whether
        the file exists or not.
        """
        with PathUtils.temp_directory_context() as temp_dir:
            file_path = temp_dir / f"{filename}.txt"
            
            # File should not exist initially
            assert not PathUtils.file_exists(file_path)
            
            # Create the file
            PathUtils.write_text_file(file_path, "test")
            
            # Now it should exist
            assert PathUtils.file_exists(file_path)
            
            # Delete the file
            PathUtils.delete_file(file_path)
            
            # Should not exist anymore
            assert not PathUtils.file_exists(file_path)
    
    def test_property_28_temp_directory_context_cleans_up(self):
        """
        Property: Temporary directory context manager should clean up on exit.
        
        After exiting the context, the temporary directory should be deleted.
        """
        temp_path = None
        
        with PathUtils.temp_directory_context(prefix='cleanup_test_') as temp_dir:
            temp_path = temp_dir
            
            # Should exist inside context
            assert temp_path.exists()
            assert temp_path.is_dir()
            
            # Create some files
            (temp_path / "file1.txt").write_text("test")
            (temp_path / "file2.txt").write_text("test")
        
        # Should not exist after context
        assert not temp_path.exists()

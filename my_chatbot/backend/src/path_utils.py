"""Cross-platform path handling utilities using pathlib.

This module provides platform-agnostic file system operations that work
correctly on both Windows and macOS without hardcoded separators.
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional, Union
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PathUtils:
    """
    Cross-platform path handling utilities.
    
    Uses pathlib for all file system operations to ensure platform-agnostic
    behavior. Handles platform-specific differences (file separators, line
    endings, system paths) transparently.
    """
    
    @staticmethod
    def normalize_path(path: Union[str, Path]) -> Path:
        """
        Normalize a path to use platform-appropriate separators.
        
        Args:
            path: Path string or Path object to normalize
            
        Returns:
            Normalized Path object
        """
        if isinstance(path, str):
            path = Path(path)
        
        # Resolve to absolute path and normalize
        return path.resolve()
    
    @staticmethod
    def join_paths(*parts: Union[str, Path]) -> Path:
        """
        Join path components using platform-appropriate separators.
        
        Args:
            *parts: Path components to join
            
        Returns:
            Joined Path object
        """
        if not parts:
            return Path()
        
        # Convert first part to Path, then join the rest
        result = Path(parts[0])
        for part in parts[1:]:
            result = result / part
        
        return result
    
    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            path: Directory path to ensure exists
            
        Returns:
            Path object for the directory
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {path}")
        return path
    
    @staticmethod
    def get_temp_dir() -> Path:
        """
        Get the system temporary directory.
        
        Returns:
            Path to system temp directory
        """
        return Path(tempfile.gettempdir())
    
    @staticmethod
    def create_temp_file(
        suffix: Optional[str] = None,
        prefix: Optional[str] = None,
        dir: Optional[Union[str, Path]] = None,
        delete: bool = False
    ) -> Path:
        """
        Create a temporary file.
        
        Args:
            suffix: Optional file suffix (e.g., '.txt')
            prefix: Optional file prefix
            dir: Optional directory for temp file
            delete: Whether to delete file on close (default: False)
            
        Returns:
            Path to the temporary file
        """
        if dir is not None:
            dir = str(Path(dir))
        
        fd, path = tempfile.mkstemp(
            suffix=suffix,
            prefix=prefix,
            dir=dir
        )
        
        # Close the file descriptor
        os.close(fd)
        
        temp_path = Path(path)
        logger.debug(f"Created temp file: {temp_path}")
        
        return temp_path
    
    @staticmethod
    def create_temp_directory(
        suffix: Optional[str] = None,
        prefix: Optional[str] = None,
        dir: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        Create a temporary directory.
        
        Args:
            suffix: Optional directory suffix
            prefix: Optional directory prefix
            dir: Optional parent directory for temp dir
            
        Returns:
            Path to the temporary directory
        """
        if dir is not None:
            dir = str(Path(dir))
        
        path = tempfile.mkdtemp(
            suffix=suffix,
            prefix=prefix,
            dir=dir
        )
        
        temp_path = Path(path)
        logger.debug(f"Created temp directory: {temp_path}")
        
        return temp_path
    
    @staticmethod
    @contextmanager
    def temp_file_context(
        suffix: Optional[str] = None,
        prefix: Optional[str] = None,
        dir: Optional[Union[str, Path]] = None
    ):
        """
        Context manager for temporary file that auto-deletes on exit.
        
        Args:
            suffix: Optional file suffix
            prefix: Optional file prefix
            dir: Optional directory for temp file
            
        Yields:
            Path to the temporary file
        """
        temp_path = PathUtils.create_temp_file(suffix, prefix, dir)
        try:
            yield temp_path
        finally:
            if temp_path.exists():
                temp_path.unlink()
                logger.debug(f"Deleted temp file: {temp_path}")
    
    @staticmethod
    @contextmanager
    def temp_directory_context(
        suffix: Optional[str] = None,
        prefix: Optional[str] = None,
        dir: Optional[Union[str, Path]] = None
    ):
        """
        Context manager for temporary directory that auto-deletes on exit.
        
        Args:
            suffix: Optional directory suffix
            prefix: Optional directory prefix
            dir: Optional parent directory
            
        Yields:
            Path to the temporary directory
        """
        temp_path = PathUtils.create_temp_directory(suffix, prefix, dir)
        try:
            yield temp_path
        finally:
            if temp_path.exists():
                import shutil
                shutil.rmtree(temp_path)
                logger.debug(f"Deleted temp directory: {temp_path}")
    
    @staticmethod
    def get_file_size(path: Union[str, Path]) -> int:
        """
        Get file size in bytes.
        
        Args:
            path: Path to file
            
        Returns:
            File size in bytes
        """
        return Path(path).stat().st_size
    
    @staticmethod
    def file_exists(path: Union[str, Path]) -> bool:
        """
        Check if a file exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        return Path(path).is_file()
    
    @staticmethod
    def directory_exists(path: Union[str, Path]) -> bool:
        """
        Check if a directory exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if directory exists, False otherwise
        """
        return Path(path).is_dir()
    
    @staticmethod
    def delete_file(path: Union[str, Path]) -> None:
        """
        Delete a file if it exists.
        
        Args:
            path: Path to file to delete
        """
        path = Path(path)
        if path.is_file():
            path.unlink()
            logger.debug(f"Deleted file: {path}")
    
    @staticmethod
    def delete_directory(path: Union[str, Path], recursive: bool = False) -> None:
        """
        Delete a directory.
        
        Args:
            path: Path to directory to delete
            recursive: Whether to delete recursively (default: False)
        """
        path = Path(path)
        if not path.is_dir():
            return
        
        if recursive:
            import shutil
            shutil.rmtree(path)
            logger.debug(f"Deleted directory recursively: {path}")
        else:
            path.rmdir()
            logger.debug(f"Deleted empty directory: {path}")
    
    @staticmethod
    def list_files(
        directory: Union[str, Path],
        pattern: str = "*",
        recursive: bool = False
    ) -> list[Path]:
        """
        List files in a directory.
        
        Args:
            directory: Directory to list
            pattern: Glob pattern to match (default: "*")
            recursive: Whether to search recursively (default: False)
            
        Returns:
            List of Path objects for matching files
        """
        directory = Path(directory)
        
        if recursive:
            files = list(directory.rglob(pattern))
        else:
            files = list(directory.glob(pattern))
        
        # Filter to only files (not directories)
        return [f for f in files if f.is_file()]
    
    @staticmethod
    def get_relative_path(path: Union[str, Path], base: Union[str, Path]) -> Path:
        """
        Get relative path from base to path.
        
        Args:
            path: Target path
            base: Base path
            
        Returns:
            Relative path from base to path
        """
        path = Path(path).resolve()
        base = Path(base).resolve()
        
        return path.relative_to(base)
    
    @staticmethod
    def read_text_file(path: Union[str, Path], encoding: str = 'utf-8') -> str:
        """
        Read text file with platform-appropriate line ending handling.
        
        Args:
            path: Path to file
            encoding: Text encoding (default: 'utf-8')
            
        Returns:
            File contents as string
        """
        return Path(path).read_text(encoding=encoding)
    
    @staticmethod
    def write_text_file(
        path: Union[str, Path],
        content: str,
        encoding: str = 'utf-8'
    ) -> None:
        """
        Write text file with platform-appropriate line endings.
        
        Args:
            path: Path to file
            content: Content to write
            encoding: Text encoding (default: 'utf-8')
        """
        Path(path).write_text(content, encoding=encoding)
        logger.debug(f"Wrote text file: {path}")
    
    @staticmethod
    def read_binary_file(path: Union[str, Path]) -> bytes:
        """
        Read binary file.
        
        Args:
            path: Path to file
            
        Returns:
            File contents as bytes
        """
        return Path(path).read_bytes()
    
    @staticmethod
    def write_binary_file(path: Union[str, Path], content: bytes) -> None:
        """
        Write binary file.
        
        Args:
            path: Path to file
            content: Content to write as bytes
        """
        Path(path).write_bytes(content)
        logger.debug(f"Wrote binary file: {path}")


# Convenience functions
def normalize_path(path: Union[str, Path]) -> Path:
    """Normalize a path to use platform-appropriate separators."""
    return PathUtils.normalize_path(path)


def join_paths(*parts: Union[str, Path]) -> Path:
    """Join path components using platform-appropriate separators."""
    return PathUtils.join_paths(*parts)


def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    return PathUtils.ensure_directory(path)


def get_temp_dir() -> Path:
    """Get the system temporary directory."""
    return PathUtils.get_temp_dir()

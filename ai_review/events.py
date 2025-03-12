"""File system event classes for code review monitoring."""

from pathlib import Path
from typing import Optional

class FileSystemEvent:
    """Base class for file system events."""
    
    def __init__(self, src_path: str):
        """Initialize the event.
        
        Args:
            src_path: Path to the file that triggered the event
        """
        self.src_path = str(Path(src_path).resolve())
        self.is_directory = False

class FileCreatedEvent(FileSystemEvent):
    """Event class for file creation."""
    
    def __init__(self, src_path: str):
        """Initialize the event.
        
        Args:
            src_path: Path to the created file
        """
        super().__init__(src_path)

class FileModifiedEvent(FileSystemEvent):
    """Event class for file modification."""
    
    def __init__(self, src_path: str):
        """Initialize the event.
        
        Args:
            src_path: Path to the modified file
        """
        super().__init__(src_path)

class FileDeletedEvent(FileSystemEvent):
    """Event class for file deletion."""
    
    def __init__(self, src_path: str):
        """Initialize the event.
        
        Args:
            src_path: Path to the deleted file
        """
        super().__init__(src_path)

class FileMovedEvent(FileSystemEvent):
    """Event class for file move/rename operations."""
    
    def __init__(self, src_path: str, dest_path: str):
        """Initialize the event.
        
        Args:
            src_path: Original path of the file
            dest_path: New path of the file
        """
        super().__init__(src_path)
        self.dest_path = str(Path(dest_path).resolve()) 
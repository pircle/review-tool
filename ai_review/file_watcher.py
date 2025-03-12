"""File watcher module for tracking local code changes."""

import os
import json
import time
import logging
from typing import Dict, List, Set
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

from .config_manager import ConfigManager

logger = logging.getLogger(__name__)

class ChangeTracker(FileSystemEventHandler):
    """Tracks file changes and logs them for review."""
    
    def __init__(self, config_manager: ConfigManager, watch_dirs: List[str]):
        """Initialize the change tracker.
        
        Args:
            config_manager: Configuration manager instance
            watch_dirs: List of directories to watch
        """
        super().__init__()
        self.config_manager = config_manager
        self.watch_dirs = [Path(d).resolve() for d in watch_dirs]
        self.log_file = Path("logs/review_log.json")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_existing_log()
        
    def _load_existing_log(self) -> None:
        """Load existing review log if it exists."""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    self.changes = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Could not parse existing review log, starting fresh")
                self.changes = {"file_changes": []}
        else:
            self.changes = {"file_changes": []}
    
    def _should_track_file(self, path: str) -> bool:
        """Check if the file should be tracked based on config filters."""
        path = Path(path)
        
        # Get file filters from config
        filters = self.config_manager.get_file_filters()
        
        # Check if file is in included directories
        in_included_dirs = any(
            any(parent.match(pattern) for parent in path.parents)
            for pattern in filters["include_dirs"]
        )
        if not in_included_dirs:
            return False
            
        # Check if file is in excluded directories
        if any(
            any(parent.match(pattern) for parent in path.parents)
            for pattern in filters["exclude_dirs"]
        ):
            return False
            
        # Check file patterns
        if not any(path.match(pattern) for pattern in filters["include_files"]):
            return False
            
        if any(path.match(pattern) for pattern in filters["exclude_files"]):
            return False
            
        return True
    
    def _log_change(self, event_type: str, file_path: str) -> None:
        """Log a file change event."""
        if not self._should_track_file(file_path):
            return
            
        change = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "file_path": str(Path(file_path).resolve()),
            "reviewed": False
        }
        
        self.changes["file_changes"].append(change)
        
        # Write changes to log file
        with open(self.log_file, 'w') as f:
            json.dump(self.changes, f, indent=2)
        
        logger.info(f"Logged {event_type} event for {file_path}")
    
    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events."""
        if not event.is_directory:
            self._log_change("modified", event.src_path)
    
    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation events."""
        if not event.is_directory:
            self._log_change("created", event.src_path)
    
    def on_deleted(self, event: FileDeletedEvent) -> None:
        """Handle file deletion events."""
        if not event.is_directory:
            self._log_change("deleted", event.src_path)

class FileWatcher:
    """Watches directories for file changes."""
    
    def __init__(self, config_manager: ConfigManager, watch_dirs: List[str]):
        """Initialize the file watcher.
        
        Args:
            config_manager: Configuration manager instance
            watch_dirs: List of directories to watch
        """
        self.observer = Observer()
        self.tracker = ChangeTracker(config_manager, watch_dirs)
        self.watch_dirs = watch_dirs
        
    def start(self) -> None:
        """Start watching for file changes."""
        for directory in self.watch_dirs:
            self.observer.schedule(self.tracker, directory, recursive=True)
        self.observer.start()
        logger.info(f"Started watching directories: {', '.join(self.watch_dirs)}")
        
    def stop(self) -> None:
        """Stop watching for file changes."""
        self.observer.stop()
        self.observer.join()
        logger.info("Stopped file watching") 
"""Coordinates the automated code review and correction process."""

import os
import json
import time
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

from .config_manager import ConfigManager
from .validator import ChangeValidator
from .correction_manager import CorrectionManager
from .apply_corrections import CorrectionApplier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/review_coordinator.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class CodeChangeHandler(FileSystemEventHandler):
    """Handles file system events for code changes."""
    
    def __init__(self, coordinator):
        """Initialize the handler.
        
        Args:
            coordinator: ReviewCoordinator instance
        """
        self.coordinator = coordinator
        self.monitored_extensions = {'.py', '.json', '.md', '.yml', '.yaml'}
        self.ignored_dirs = {'.git', '__pycache__', 'venv', 'env', '.env'}
        logger.info("Initialized CodeChangeHandler with monitored extensions: %s", self.monitored_extensions)
    
    def should_process_file(self, path: str) -> bool:
        """Check if a file should be processed.
        
        Args:
            path: Path to the file
            
        Returns:
            True if the file should be processed
        """
        path_parts = Path(path).parts
        should_process = (
            Path(path).suffix in self.monitored_extensions
            and not any(part.startswith('.') for part in path_parts)
            and not any(part in self.ignored_dirs for part in path_parts)
        )
        logger.debug("Should process file %s: %s", path, should_process)
        return should_process
    
    def on_created(self, event):
        """Handle file creation events."""
        logger.debug("File creation event: %s", event.src_path)
        if not event.is_directory and self.should_process_file(event.src_path):
            logger.info("Processing file creation: %s", event.src_path)
            self.coordinator.handle_change({
                "file_path": str(Path(event.src_path).resolve()),
                "event_type": "created",
                "timestamp": datetime.now().isoformat()
            })
    
    def on_modified(self, event):
        """Handle file modification events."""
        logger.debug("File modification event: %s", event.src_path)
        if not event.is_directory and self.should_process_file(event.src_path):
            logger.info("Processing file modification: %s", event.src_path)
            self.coordinator.handle_change({
                "file_path": str(Path(event.src_path).resolve()),
                "event_type": "modified",
                "timestamp": datetime.now().isoformat()
            })
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        logger.debug("File deletion event: %s", event.src_path)
        if not event.is_directory and self.should_process_file(event.src_path):
            logger.info("Processing file deletion: %s", event.src_path)
            self.coordinator.handle_change({
                "file_path": str(Path(event.src_path).resolve()),
                "event_type": "deleted",
                "timestamp": datetime.now().isoformat()
            })

class ReviewCoordinator:
    """Coordinates the automated code review and correction process."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize the coordinator.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.validator = ChangeValidator(config_manager)
        self.correction_manager = CorrectionManager(config_manager)
        self.correction_applier = CorrectionApplier(config_manager)
        self.event_handler = CodeChangeHandler(self)
        self.observer = None
        self.monitored_dirs = set()
        self.review_log_file = Path("logs/review_log.json")
        self._init_review_log()
        
        # Add cooldown and activity tracking
        current_time = time.time()
        self.cooldown_seconds = 5  # 5 seconds between checks
        self.last_modified = {}  # Track last modification time per file
        self.file_locks = set()  # Track files being processed
        self.running = True  # Flag to control the coordinator's running state
        self.last_activity_time = current_time
        self.idle_timeout = 300  # 5 minutes without activity
        self.consecutive_no_corrections = 0
        self.max_no_corrections = 5  # Stop after 5 consecutive checks with no corrections
        self.shutdown_event = None
    
    def _init_review_log(self) -> None:
        """Initialize or load the review log."""
        if not self.review_log_file.exists():
            self.review_log_file.parent.mkdir(parents=True, exist_ok=True)
            self.review_log = {"changes": []}
            self._save_review_log()
        else:
            try:
                with open(self.review_log_file, 'r') as f:
                    self.review_log = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Could not parse existing review log, starting fresh")
                self.review_log = {"changes": []}
                self._save_review_log()
    
    def _save_review_log(self) -> None:
        """Save the review log to file."""
        try:
            with open(self.review_log_file, 'w') as f:
                json.dump(self.review_log, f, indent=2)
        except Exception as e:
            logger.error("Failed to save review log: %s", str(e))

    def _is_in_cooldown(self, file_path: str) -> bool:
        """Check if a file is in cooldown period.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file is in cooldown
        """
        if file_path not in self.last_modified:
            return False
        return time.time() - self.last_modified[file_path] < self.cooldown_seconds

    def _acquire_file_lock(self, file_path: str) -> bool:
        """Try to acquire a lock for processing a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if lock was acquired
        """
        if file_path in self.file_locks:
            return False
        self.file_locks.add(file_path)
        return True

    def _release_file_lock(self, file_path: str) -> None:
        """Release the lock for a file.
        
        Args:
            file_path: Path to the file
        """
        self.file_locks.discard(file_path)

    def set_shutdown_event(self, event: threading.Event) -> None:
        """Set the shutdown event for graceful shutdown.
        
        Args:
            event: Threading event to signal shutdown
        """
        self.shutdown_event = event

    def _should_stop(self) -> bool:
        """Check if the coordinator should stop.
        
        Returns:
            bool: True if the coordinator should stop, False otherwise
        """
        return (self.shutdown_event and self.shutdown_event.is_set()) or self._is_idle()

    def _is_idle(self) -> bool:
        """Check if the coordinator is idle."""
        is_idle = (time.time() - self.last_activity_time > self.idle_timeout or 
                self.consecutive_no_corrections >= self.max_no_corrections)
        if is_idle:
            self.running = False
        return is_idle

    def _update_activity_time(self) -> None:
        """Update the last activity time."""
        self.last_activity_time = time.time()
        self.consecutive_no_corrections = 0
        self.running = True

    def handle_change(self, change: Dict) -> None:
        """Handle a file change event.
        
        Args:
            change: Dictionary containing change details
        """
        if not self.running:
            logger.debug("Coordinator is not running")
            return
            
        # Check for idle timeout
        current_time = time.time()
        time_since_activity = current_time - self.last_activity_time
        logger.debug("Time since last activity in handle_change: %f seconds (timeout: %d)", time_since_activity, self.idle_timeout)
        
        if time_since_activity > self.idle_timeout:
            logger.info("No activity detected for %f seconds (timeout: %d), stopping...", time_since_activity, self.idle_timeout)
            self.running = False
            return
            
        logger.info("Handling change: %s", change)
        self._update_activity_time()
        logger.debug("Updated activity time to %f after detecting change", self.last_activity_time)
        self.review_log["changes"].append(change)
        self._save_review_log()
        
        file_path = change["file_path"]
        if not self._acquire_file_lock(file_path):
            logger.debug("File %s is already being processed", file_path)
            return
        
        try:
            if self._is_in_cooldown(file_path):
                logger.debug("File %s is in cooldown period", file_path)
                return
            
            self.last_modified[file_path] = time.time()
            
            if change["event_type"] == "deleted":
                return
            
            # Process the change
            self.validator.validate_change(change)
            if self.correction_applier.apply_pending_corrections():
                self._update_activity_time()
                logger.debug("Updated activity time to %f after applying corrections", self.last_activity_time)
            else:
                self.consecutive_no_corrections += 1
                if self._is_idle():
                    logger.info("No activity detected for an extended period, stopping coordinator...")
                    self.running = False
            
        finally:
            self._release_file_lock(file_path)

    def start_monitoring(self, directory: str) -> None:
        """Start monitoring a directory for changes.
        
        Args:
            directory: Directory to monitor
        """
        logger.info("Setting up monitoring for directory: %s", directory)
        
        if not os.path.exists(directory):
            logger.error("Directory does not exist: %s", directory)
            return
        
        if directory in self.monitored_dirs:
            logger.warning("Directory is already being monitored: %s", directory)
            return
        
        try:
            if self.observer is None:
                self.observer = Observer()
            
            self.observer.schedule(self.event_handler, directory, recursive=True)
            self.monitored_dirs.add(directory)
            logger.info("Successfully scheduled monitoring for directory: %s", directory)
            
            if not self.observer.is_alive():
                logger.info("Starting observer...")
                self.observer.start()
                logger.info("Observer started successfully")
            
            # Reset state when starting monitoring
            self.running = True
            self.consecutive_no_corrections = 0
            self.last_activity_time = time.time()
            logger.info("Initial activity time: %f", self.last_activity_time)
            
            while self.running:
                time.sleep(0.1)  # Check more frequently
                
                # Check for shutdown or idle timeout
                current_time = time.time()
                time_since_activity = current_time - self.last_activity_time
                logger.debug("Time since last activity: %f seconds (timeout: %d)", time_since_activity, self.idle_timeout)
                
                if time_since_activity > self.idle_timeout:
                    logger.info("No activity detected for %f seconds (timeout: %d), stopping...", time_since_activity, self.idle_timeout)
                    self.running = False
                    break
                
                # Process any pending corrections
                if self.correction_applier.apply_pending_corrections():
                    self._update_activity_time()
                    logger.debug("Updated activity time to %f after applying corrections", self.last_activity_time)
                
        except Exception as e:
            logger.error("Error setting up file monitoring: %s", str(e))
            raise
        finally:
            self.stop_monitoring()

    def stop_monitoring(self) -> None:
        """Stop monitoring and clean up resources."""
        logger.info("Stopping observer...")
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        self.monitored_dirs.clear()
        self.running = False
        logger.info("Observer stopped and cleanup completed")

def main():
    """Main entry point for the review coordinator."""
    try:
        config_manager = ConfigManager()
        coordinator = ReviewCoordinator(config_manager)
        coordinator.start_monitoring()
    except Exception as e:
        logger.error(f"Error in review coordinator: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
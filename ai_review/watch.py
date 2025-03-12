"""Script to start the file watcher."""

import os
import sys
import time
import logging
import signal
from pathlib import Path
from typing import List

from .config_manager import ConfigManager
from .file_watcher import FileWatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/file_watcher.log')
    ]
)

logger = logging.getLogger(__name__)

def get_watch_directories() -> List[str]:
    """Get the directories to watch."""
    # Get the project root directory
    root_dir = Path(__file__).parent.parent.parent
    
    # Directories to watch
    watch_dirs = [
        root_dir / "ai_code_review",
        root_dir / "tests"
    ]
    
    # Ensure directories exist
    for directory in watch_dirs:
        if not directory.exists():
            logger.warning(f"Directory does not exist: {directory}")
            watch_dirs.remove(directory)
    
    return [str(d) for d in watch_dirs]

def handle_shutdown(signum, frame) -> None:
    """Handle shutdown signals."""
    logger.info("Received shutdown signal")
    if hasattr(handle_shutdown, 'watcher'):
        handle_shutdown.watcher.stop()
    sys.exit(0)

def main() -> None:
    """Main function to start the file watcher."""
    try:
        # Set up signal handlers
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
        
        # Initialize config manager
        config_manager = ConfigManager()
        
        # Get directories to watch
        watch_dirs = get_watch_directories()
        if not watch_dirs:
            logger.error("No valid directories to watch")
            sys.exit(1)
        
        # Create and start the file watcher
        watcher = FileWatcher(config_manager, watch_dirs)
        handle_shutdown.watcher = watcher  # Store for signal handler
        
        logger.info("Starting file watcher...")
        watcher.start()
        
        # Keep the script running
        while True:
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Error in file watcher: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 
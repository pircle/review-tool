"""Script for applying corrections through Cursor's API."""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import threading

from .config_manager import ConfigManager
from .validator import ChangeValidator
from .correction_manager import CorrectionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/correction_applier.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class CorrectionApplier:
    """Applies corrections using Cursor's API."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize the correction applier.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.correction_manager = CorrectionManager(config_manager)
        self.validator = ChangeValidator(config_manager)
        self.corrections_file = Path("logs/cursor_corrections.json")
        self.status_file = Path("logs/correction_status.json")
        self.corrections_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_corrections()
        self._init_status_log()
        
        # Add cooldown and activity tracking
        current_time = time.time()
        self.check_cooldown = 5  # 5 seconds between checks
        self.log_cooldown = 15  # 15 seconds between log messages
        self.last_correction_time = current_time
        self.last_log_time = current_time
        self.running = True
        self.consecutive_no_corrections = 0
        self.max_no_corrections = 5  # Stop after 5 consecutive checks
        self.idle_timeout = 300  # 5 minutes without activity
        self.shutdown_event = None
    
    def set_shutdown_event(self, event: threading.Event) -> None:
        """Set the shutdown event for graceful shutdown.
        
        Args:
            event: Threading event to signal shutdown
        """
        self.shutdown_event = event
    
    def _load_corrections(self) -> None:
        """Load existing corrections if they exist."""
        if not self.corrections_file.exists():
            with open(self.corrections_file, 'w') as f:
                json.dump({"corrections": []}, f, indent=2)
        try:
            with open(self.corrections_file, 'r') as f:
                self.corrections = json.load(f)
        except json.JSONDecodeError:
            logger.warning("Could not parse existing corrections, starting fresh")
            self.corrections = {"corrections": []}
    
    def _init_status_log(self) -> None:
        """Initialize or load the correction status log."""
        if not self.status_file.exists():
            with open(self.status_file, 'w') as f:
                json.dump({"corrections": []}, f, indent=2)
    
    def _log_failed_correction(self, correction: Dict, attempts: int) -> None:
        """Log a failed correction attempt.
        
        Args:
            correction: The correction that failed to apply
            attempts: Number of attempts made
        """
        status_entry = {
            "file": correction["file_path"],
            "issue": correction.get("fixes", [{}])[0].get("description", "Unknown issue"),
            "fix_attempts": attempts,
            "status": "❌ needs review",
            "last_attempt": datetime.now().isoformat()
        }
        
        # Load existing status log
        with open(self.status_file, 'r') as f:
            status_log = json.load(f)
        
        # Add new entry
        status_log["corrections"].append(status_entry)
        
        # Save updated log
        with open(self.status_file, 'w') as f:
            json.dump(status_log, f, indent=2)
        
        logger.warning(f"""
Manual review required for {correction['file_path']}:
- Issue: {status_entry['issue']}
- Failed after {attempts} attempts
- Please check logs/correction_status.json for details
- Manual fix may be needed for this file
""")
    
    def _update_log_time(self) -> None:
        """Update the last log time."""
        self.last_log_time = time.time()

    def _update_check_time(self) -> None:
        """Update the last check time."""
        self.last_check_time = time.time()

    def _update_correction_time(self) -> None:
        """Update the last correction time."""
        self.last_correction_time = time.time()
        self.consecutive_no_corrections = 0
        self.running = True

    def _check_cooldown(self) -> bool:
        """Check if the applier is in cooldown period."""
        return time.time() - self.last_correction_time < self.check_cooldown

    def _check_log_cooldown(self) -> bool:
        """Check if logging is throttled.
        
        Returns:
            bool: True if logging is throttled
        """
        return time.time() - self.last_log_time < self.log_cooldown

    def _is_idle(self) -> bool:
        """Check if the applier is idle."""
        return (time.time() - self.last_correction_time > self.idle_timeout or 
                self.consecutive_no_corrections >= self.max_no_corrections)

    def _should_stop(self) -> bool:
        """Check if the applier should stop.
        
        Returns:
            bool: True if the applier should stop, False otherwise
        """
        return (self.shutdown_event and self.shutdown_event.is_set()) or self._is_idle()

    def apply_pending_corrections(self) -> bool:
        """Apply any pending corrections from the correction manager.
        
        Returns:
            bool: True if corrections were found (regardless of whether they were applied),
                 False if no corrections were found.
        """
        if not self.running:
            return False
            
        # Check if we should stop due to idle timeout
        if self._is_idle():
            self.running = False
            return False
            
        # Get pending corrections first
        corrections = self.correction_manager.corrections.get("corrections", [])
        if not corrections:
            self.consecutive_no_corrections += 1
            if self.consecutive_no_corrections >= self.max_no_corrections:
                self.running = False
            if not self._check_log_cooldown():
                logging.info("No corrections found")
                self.last_log_time = time.time()
            return False
            
        # Reset consecutive no corrections since we found some
        self.consecutive_no_corrections = 0
        
        # Check if we're in cooldown
        in_cooldown = self._check_cooldown()
        
        # If in cooldown, log but don't apply
        if in_cooldown:
            if not self._check_log_cooldown():
                logging.info("Found corrections but skipping due to cooldown")
                self.last_log_time = time.time()
            return True  # Return True since we found corrections
            
        # Apply corrections
        applied = False
        for correction in corrections:
            try:
                if self.retry_correction(correction):
                    applied = True
                    if not self._check_log_cooldown():
                        logging.info("Successfully applied corrections")
                        self.last_log_time = time.time()
            except Exception as e:
                logging.error(f"Error applying correction: {e}")
                self.correction_manager.mark_correction_failed(correction["file_path"], str(e))
                
        # Only update last_correction_time if we actually applied corrections
        if applied:
            self.last_correction_time = time.time()
            
        return True  # Return True since we found corrections
    
    def _is_duplicate_correction(self, correction: Dict) -> bool:
        """Check if a correction is a duplicate of a recently applied one.
        
        Args:
            correction: The correction to check
            
        Returns:
            True if the correction is a duplicate
        """
        if not correction or "file_path" not in correction:
            return False
            
        file_path = correction["file_path"]
        current_time = datetime.now()
        
        # Check recent corrections in the status log
        try:
            with open(self.status_file, 'r') as f:
                status_log = json.load(f)
                
            for entry in status_log["corrections"]:
                if entry["file"] == file_path:
                    # Check if it was applied recently (within last 2 seconds)
                    try:
                        last_attempt = datetime.fromisoformat(entry["last_attempt"])
                        if (current_time - last_attempt).total_seconds() < 2:
                            logger.info(f"Skipping duplicate correction for {file_path} - recently applied")
                            return True
                    except (ValueError, TypeError):
                        pass
        except (json.JSONDecodeError, FileNotFoundError):
            pass
            
        return False
    
    def retry_correction(self, correction: Dict, max_retries: int = 3) -> bool:
        """Retry applying a correction multiple times.
        
        Args:
            correction: The correction to retry
            max_retries: Maximum number of retries
            
        Returns:
            bool: True if the correction was eventually applied successfully
        """
        for attempt in range(max_retries):
            try:
                if self.apply_correction(correction):
                    return True
                time.sleep(1)  # Wait before retrying
            except Exception as e:
                logging.error(f"Error applying correction: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait before retrying
                    
        logging.error(f"Failed to apply correction after {max_retries} attempts")
        self.correction_manager.mark_correction_failed(correction)
        return False

    def _fix_indentation(self, content: str, style: str = 'spaces', size: int = 4) -> str:
        """Fix indentation in content.
        
        Args:
            content: Content to fix
            style: Indentation style ('spaces' or 'tabs')
            size: Number of spaces for indentation
            
        Returns:
            Content with fixed indentation
        """
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            if not line.strip():  # Empty line
                fixed_lines.append(line)
                continue
            
            # Count leading whitespace
            indent_level = len(line) - len(line.lstrip())
            if indent_level == 0:
                fixed_lines.append(line)
                continue
            
            # Calculate number of 4-space indentation levels
            indent_steps = (indent_level + 3) // 4  # Round up to nearest 4-space level
            
            # Create new indentation string
            new_indent = ' ' * (indent_steps * 4) if style == 'spaces' else '\t' * indent_steps
            
            # Replace old indentation with new
            fixed_lines.append(new_indent + line.lstrip())
        
        return '\n'.join(fixed_lines)
    
    def apply_correction(self, correction: Dict) -> bool:
        """Apply a single correction.
        
        Args:
            correction: The correction to apply
            
        Returns:
            bool: True if the correction was applied successfully
        """
        try:
            # Check if this is a duplicate correction
            if self._is_duplicate_correction(correction):
                logging.info("Skipping duplicate correction")
                return False
                
            # Apply the correction
            self.correction_manager.apply_correction(correction)
            logging.info("Applied fix: " + correction["fixes"][0]["description"])
            
            # Update correction status
            self.correction_manager.update_correction_status(correction["file_path"], "✅ applied")
            
            return True
            
        except Exception as e:
            logging.error(f"Error applying correction: {e}")
            self.correction_manager.mark_correction_failed(correction)
            return False

def main():
    """Main entry point for applying corrections."""
    try:
        config_manager = ConfigManager()
        applier = CorrectionApplier(config_manager)
        
        # Run the correction loop with cooldown and idle detection
        while True:
            try:
                if not applier.apply_pending_corrections():
                    # If no corrections were applied, wait longer
                    time.sleep(applier.check_cooldown * 2)
                    continue
                
                # Wait for cooldown period if corrections were applied
                time.sleep(applier.check_cooldown)
                
            except KeyboardInterrupt:
                logger.info("Correction applier stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in correction loop: {str(e)}")
                time.sleep(applier.check_cooldown)  # Wait before retrying
        
    except Exception as e:
        logger.error(f"Error in correction applier: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
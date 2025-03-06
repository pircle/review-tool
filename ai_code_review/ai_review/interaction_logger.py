"""
Module for logging human interactions with the AI Code Review Tool.
"""

import os
import json
import logging
import datetime
from pathlib import Path

from .config_manager import config_manager

logger = logging.getLogger(__name__)

class InteractionLogger:
    """
    Logs human interactions with the AI Code Review Tool.
    Records approvals, rejections, and commands sent to the AI.
    """
    
    def __init__(self, log_file=None):
        """
        Initialize the interaction logger.
        
        Args:
            log_file (str, optional): Path to the log file. Defaults to validation_log.md in the logs directory.
        """
        self.log_file = log_file
        self.update_log_file()
    
    def update_log_file(self):
        """Update the log file path based on the current project."""
        # If a project is set, use project-specific logs directory
        if config_manager.current_project:
            logs_dir = config_manager.get_project_logs_dir()
            if logs_dir:
                self.log_file = os.path.join(logs_dir, "validation_log.md")
                logger.debug(f"Using project-specific log file: {self.log_file}")
            else:
                self.log_file = self.log_file or os.path.join("logs", "validation_log.md")
                logger.debug(f"Using default log file: {self.log_file}")
        else:
            self.log_file = self.log_file or os.path.join("logs", "validation_log.md")
            logger.debug(f"Using default log file: {self.log_file}")
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Create log file if it doesn't exist
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                f.write("# AI Code Review Tool - Human Interaction Log\n\n")
    
    def log_interaction(self, interaction_type, details, timestamp=None):
        """
        Log a human interaction.
        
        Args:
            interaction_type (str): Type of interaction (e.g., "approval", "rejection", "command")
            details (dict): Details of the interaction
            timestamp (datetime, optional): Timestamp of the interaction. Defaults to current time.
        """
        # Update log file path in case project has changed
        self.update_log_file()
        
        timestamp = timestamp or datetime.datetime.now()
        
        # Format the log entry
        log_entry = f"## {timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {interaction_type.capitalize()}\n\n"
        
        if interaction_type == "command":
            log_entry += f"**Command:** `{details.get('command', 'N/A')}`\n\n"
            if "description" in details:
                log_entry += f"**Description:** {details['description']}\n\n"
        
        elif interaction_type == "approval":
            log_entry += f"**Approved:** {details.get('item', 'N/A')}\n\n"
            if "file" in details:
                log_entry += f"**File:** `{details['file']}`\n\n"
            if "description" in details:
                log_entry += f"**Description:** {details['description']}\n\n"
        
        elif interaction_type == "rejection":
            log_entry += f"**Rejected:** {details.get('item', 'N/A')}\n\n"
            if "file" in details:
                log_entry += f"**File:** `{details['file']}`\n\n"
            if "reason" in details:
                log_entry += f"**Reason:** {details['reason']}\n\n"
            if "description" in details:
                log_entry += f"**Description:** {details['description']}\n\n"
        
        elif interaction_type == "modification":
            log_entry += f"**Modified:** {details.get('item', 'N/A')}\n\n"
            if "file" in details:
                log_entry += f"**File:** `{details['file']}`\n\n"
            if "original" in details:
                log_entry += f"**Original:** `{details['original']}`\n\n"
            if "modified" in details:
                log_entry += f"**Modified:** `{details['modified']}`\n\n"
            if "description" in details:
                log_entry += f"**Description:** {details['description']}\n\n"
        
        # Add any additional details
        if "additional_details" in details:
            if isinstance(details["additional_details"], dict):
                log_entry += "**Additional Details:**\n\n```json\n"
                log_entry += json.dumps(details["additional_details"], indent=2)
                log_entry += "\n```\n\n"
            else:
                log_entry += f"**Additional Details:** {details['additional_details']}\n\n"
        
        # Add separator
        log_entry += "---\n\n"
        
        # Write to log file
        try:
            with open(self.log_file, "a") as f:
                f.write(log_entry)
            logger.debug(f"Logged {interaction_type} interaction to {self.log_file}")
        except Exception as e:
            logger.error(f"Error logging interaction to {self.log_file}: {str(e)}")
    
    def log_command(self, command, description=None, additional_details=None):
        """
        Log a command sent to the AI.
        
        Args:
            command (str): The command sent to the AI
            description (str, optional): Description of the command
            additional_details (dict, optional): Additional details about the command
        """
        details = {
            "command": command,
        }
        
        if description:
            details["description"] = description
        
        if additional_details:
            details["additional_details"] = additional_details
        
        self.log_interaction("command", details)
    
    def log_approval(self, item, file=None, description=None, additional_details=None):
        """
        Log an approval of an AI suggestion.
        
        Args:
            item (str): The item that was approved
            file (str, optional): The file that was affected
            description (str, optional): Description of the approval
            additional_details (dict, optional): Additional details about the approval
        """
        details = {
            "item": item,
        }
        
        if file:
            details["file"] = file
        
        if description:
            details["description"] = description
        
        if additional_details:
            details["additional_details"] = additional_details
        
        self.log_interaction("approval", details)
    
    def log_rejection(self, item, reason=None, file=None, description=None, additional_details=None):
        """
        Log a rejection of an AI suggestion.
        
        Args:
            item (str): The item that was rejected
            reason (str, optional): The reason for rejection
            file (str, optional): The file that was affected
            description (str, optional): Description of the rejection
            additional_details (dict, optional): Additional details about the rejection
        """
        details = {
            "item": item,
        }
        
        if reason:
            details["reason"] = reason
        
        if file:
            details["file"] = file
        
        if description:
            details["description"] = description
        
        if additional_details:
            details["additional_details"] = additional_details
        
        self.log_interaction("rejection", details)
    
    def log_modification(self, file: str = None, original_suggestion: str = None, 
                        modified_suggestion: str = None, description: str = None, 
                        details: dict = None) -> None:
        """
        Log when a user modifies an AI suggestion before applying it.
        
        Args:
            file (str, optional): The file that was modified.
            original_suggestion (str, optional): The original AI suggestion.
            modified_suggestion (str, optional): The modified suggestion that was applied.
            description (str, optional): A description of the modification.
            details (dict, optional): Additional details about the modification.
        """
        log_entry = {
            "type": "MODIFICATION",
            "timestamp": self._get_timestamp(),
            "file": file,
            "description": description or "Modified AI suggestion",
        }
        
        if original_suggestion:
            log_entry["original_suggestion"] = original_suggestion
        
        if modified_suggestion:
            log_entry["modified_suggestion"] = modified_suggestion
        
        if details:
            log_entry["details"] = details
        
        self._write_log_entry(f"MODIFICATION: {description or 'Modified AI suggestion'}" + 
                             (f" for {file}" if file else ""))

# Create a singleton instance
interaction_logger = InteractionLogger() 
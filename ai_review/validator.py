"""Validator module for checking changes against requirements."""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime

from .config_manager import ConfigManager

logger = logging.getLogger(__name__)

class ChangeValidator:
    """Validates code changes against project requirements."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize the change validator.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.requirements_file = "docs/Kalkal_Requirements.md"
        self.validation_log = Path("logs/validation_log.json")
        self.validation_log.parent.mkdir(parents=True, exist_ok=True)
        self.validations = {"validations": []}
        self._load_validation_log()
    
    def _load_validation_log(self) -> None:
        """Load existing validation log if it exists."""
        if self.validation_log.exists():
            try:
                with open(self.validation_log, 'r') as f:
                    loaded_validations = json.load(f)
                    if "validations" in loaded_validations:
                        self.validations = loaded_validations
            except json.JSONDecodeError:
                logger.warning("Could not parse existing validation log, starting fresh")
    
    def _load_requirements(self) -> List[Dict[str, str]]:
        """Load project requirements from the requirements file."""
        if not os.path.exists(self.requirements_file):
            logger.warning(f"Requirements file not found: {self.requirements_file}")
            return []
            
        try:
            with open(self.requirements_file, 'r') as f:
                content = f.read()
                
            # Parse requirements from markdown
            requirements = []
            current_section = None
            
            for line in content.split('\n'):
                if line.startswith('##'):
                    current_section = line[2:].strip()
                elif line.startswith('- '):
                    if current_section:
                        requirements.append({
                            "section": current_section,
                            "requirement": line[2:].strip()
                        })
            
            return requirements
        except Exception as e:
            logger.error(f"Error loading requirements: {str(e)}")
            return []
    
    def _check_requirement(self, requirement: Dict[str, str], content: str) -> bool:
        """Check if a requirement is met in the content.
        
        Args:
            requirement: Requirement dictionary with section and requirement text
            content: File content to check against
            
        Returns:
            True if requirement is met, False otherwise
        """
        section = requirement["section"]
        req_text = requirement["requirement"].lower()
        
        if section == "Code Style":
            if "docstrings" in req_text:
                return '"""' in content or "'''" in content
            elif "indentation" in req_text:
                # Check for consistent indentation
                lines = [line for line in content.split('\n') if line.strip()]
                if not lines:
                    return True
                
                # Track indentation patterns
                indentation_patterns = set()
                
                for line in lines:
                    # Skip empty lines and lines without indentation
                    if not line or not line[0].isspace():
                        continue
                        
                    # Get indentation prefix
                    indent = line[:len(line) - len(line.lstrip())]
                    
                    # Check for mixed spaces and tabs
                    if '\t' in indent and ' ' in indent:
                        logger.warning(f"Mixed spaces and tabs found in indentation")
                        return False
                    
                    # Store the indentation pattern
                    indentation_patterns.add(indent)
                    
                    # If we have multiple patterns, check if they're consistent
                    if len(indentation_patterns) > 1:
                        # Get the base indentation unit (4 spaces or 1 tab)
                        base_indent = min(indentation_patterns, key=len)
                        base_type = '\t' if '\t' in base_indent else ' '
                        base_size = len(base_indent)
                        
                        # All other indentations should be multiples of the base
                        for pattern in indentation_patterns:
                            if (pattern[0] != base_type or 
                                len(pattern) % base_size != 0 or 
                                not all(c == base_type for c in pattern)):
                                logger.warning(f"Inconsistent indentation found: mixing different types or sizes")
                                return False
                
                return True
            elif "pep 8" in req_text:
                # Basic PEP 8 checks
                return (
                    not any(line.rstrip().endswith(' ') for line in content.split('\n'))  # No trailing whitespace
                    and not any(line.strip().startswith('import') and ',' in line for line in content.split('\n'))  # One import per line
                    and not any(len(line.rstrip()) > 100 for line in content.split('\n'))  # Line length
                )
        elif section == "Features":
            if "file watching" in req_text:
                return (
                    "watchdog" in content.lower()
                    or "observer" in content.lower()
                    or "file_watcher" in content.lower()
                )
            elif "multiple projects" in req_text:
                return (
                    "project" in content.lower()
                    and ("list" in content.lower() or "[]" in content)
                )
            elif "local validation" in req_text:
                return (
                    "validate" in content.lower()
                    or "check" in content.lower()
                    or "verify" in content.lower()
                )
        
        # Default to keyword matching
        keywords = req_text.split()
        return any(keyword in content.lower() for keyword in keywords)
    
    def validate_change(self, change: Dict[str, str]) -> Dict[str, Union[str, bool, List[str]]]:
        """Validate a single change against requirements.
        
        Args:
            change: Change event dictionary with file_path and event_type
            
        Returns:
            Dictionary containing validation results
        """
        requirements = self._load_requirements()
        if not requirements:
            return {
                "file_path": change["file_path"],
                "event_type": change["event_type"],
                "timestamp": datetime.now().isoformat(),
                "valid": True,
                "missing_requirements": [],
                "notes": "No requirements found to validate against"
            }
        
        # Read file content if it exists
        file_path = change["file_path"]
        if os.path.exists(file_path) and change["event_type"] != "deleted":
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")
                content = ""
        else:
            content = ""
        
        # Check requirements
        missing_requirements = []
        for req in requirements:
            if not self._check_requirement(req, content):
                missing_requirements.append(req["requirement"])
        
        validation = {
            "file_path": file_path,
            "event_type": change["event_type"],
            "timestamp": datetime.now().isoformat(),
            "valid": len(missing_requirements) == 0,
            "missing_requirements": missing_requirements,
            "notes": "All requirements met" if len(missing_requirements) == 0 else "Missing requirements found"
        }
        
        # Log validation result
        self.validations["validations"].append(validation)
        with open(self.validation_log, 'w') as f:
            json.dump(self.validations, f, indent=2)
        
        return validation
    
    def validate_changes(self, changes: List[Dict[str, str]]) -> List[Dict[str, Union[str, bool, List[str]]]]:
        """Validate multiple changes against requirements.
        
        Args:
            changes: List of change event dictionaries
            
        Returns:
            List of validation results
        """
        return [self.validate_change(change) for change in changes] 
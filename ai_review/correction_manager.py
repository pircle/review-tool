"""Manages automated code corrections and their application through Cursor."""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime

from .validator import ChangeValidator
from .config_manager import ConfigManager

logger = logging.getLogger(__name__)

class CorrectionManager:
    """Manages the generation and application of code corrections."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize the correction manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.corrections_file = Path("logs/cursor_corrections.json")
        self.corrections_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_corrections()
        
    def _load_corrections(self) -> None:
        """Load existing corrections if they exist."""
        if self.corrections_file.exists():
            try:
                with open(self.corrections_file, 'r') as f:
                    self.corrections = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Could not parse existing corrections, starting fresh")
                self.corrections = {"corrections": []}
        else:
            self.corrections = {"corrections": []}
            self._save_corrections()
    
    def _save_corrections(self) -> None:
        """Save corrections to file."""
        try:
            with open(self.corrections_file, 'w') as f:
                json.dump(self.corrections, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving corrections: {str(e)}")
    
    def generate_correction(self, validation_result: Dict[str, Union[str, bool, List[str]]]) -> Dict[str, any]:
        """Generate a correction for a failed validation.
        
        Args:
            validation_result: Result from the validator
            
        Returns:
            Dictionary containing the correction details
        """
        if validation_result.get("valid", True):
            return {}
        
        file_path = validation_result["file_path"]
        missing_requirements = validation_result.get("missing_requirements", [])
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return {}
        
        correction = {
            "file_path": file_path,
            "timestamp": datetime.now().isoformat(),
            "requirements": missing_requirements,
            "fixes": []
        }
        
        # Generate fixes for each missing requirement
        for requirement in missing_requirements:
            fix = self._generate_fix(requirement, content, file_path)
            if fix:
                correction["fixes"].append(fix)
        
        # Add correction to history
        self.corrections["corrections"].append(correction)
        self._save_corrections()
        
        return correction
    
    def _generate_fix(self, requirement: str, content: str, file_path: str) -> Dict[str, any]:
        """Generate a fix for a specific requirement.
        
        Args:
            requirement: The requirement that needs fixing
            content: Current file content
            file_path: Path to the file
            
        Returns:
            Dictionary containing the fix details
        """
        requirement_lower = requirement.lower()
        
        fix = {
            "requirement": requirement,
            "type": "edit",
            "description": f"Fix for: {requirement}",
            "cursor_instructions": {
                "action": "edit",
                "file": file_path,
                "changes": []
            }
        }
        
        if "indentation" in requirement_lower:
            fix["cursor_instructions"]["changes"].append({
                "type": "format",
                "description": "Fix inconsistent indentation",
                "style": "spaces",
                "size": 4
            })
        
        elif "docstrings" in requirement_lower:
            # Find functions without docstrings
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith('def ') and i > 0:
                    # Check if previous line is a docstring
                    prev_line = lines[i-1].strip()
                    if not (prev_line.startswith('"""') or prev_line.startswith("'''")):
                        func_name = line.strip().split('def ')[1].split('(')[0]
                        fix["cursor_instructions"]["changes"].append({
                            "type": "insert",
                            "line": i + 1,
                            "content": f'    """Add docstring for {func_name}."""\n'
                        })
        
        elif "pep 8" in requirement_lower:
            fix["cursor_instructions"]["changes"].append({
                "type": "format",
                "description": "Apply PEP 8 formatting",
                "style": "pep8"
            })
        
        return fix
    
    def apply_correction(self, correction: Dict[str, any]) -> bool:
        """Apply a correction using Cursor.
        
        Args:
            correction: The correction to apply
            
        Returns:
            True if the correction was applied successfully
        """
        if not correction or "fixes" not in correction:
            return False
        
        # Add correction to history if not already present
        file_path = correction.get("file_path")
        existing_correction = None
        for i, c in enumerate(self.corrections["corrections"]):
            if c.get("file_path") == file_path:
                existing_correction = i
                break
        
        if existing_correction is not None:
            # Update existing correction
            self.corrections["corrections"][existing_correction].update(correction)
        else:
            # Add new correction
            self.corrections["corrections"].append(correction)
        
        # Save the corrections to the log file before applying them
        self._save_corrections()
        
        success = True
        for fix in correction.get("fixes", []):
            try:
                # Apply the fix using Cursor's API
                instructions = fix.get("cursor_instructions", {})
                if not instructions:
                    continue
                
                file_path = instructions.get("file")
                if not file_path or not os.path.exists(file_path):
                    logger.error(f"Invalid file path: {file_path}")
                    success = False
                    continue
                
                # Read the current file content
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Apply changes
                modified_content = content
                for change in instructions.get("changes", []):
                    change_type = change.get("type")
                    
                    if change_type == "format":
                        # Apply formatting changes
                        if "indentation" in change.get("description", "").lower():
                            # Fix indentation
                            lines = modified_content.split('\n')
                            fixed_lines = []
                            base_indent = " " * change.get("size", 4)
                            
                            for line in lines:
                                if line.strip():
                                    # Count leading spaces
                                    indent_level = (len(line) - len(line.lstrip())) // change.get("size", 4)
                                    fixed_lines.append(base_indent * indent_level + line.lstrip())
                                else:
                                    fixed_lines.append(line)
                            
                            modified_content = '\n'.join(fixed_lines)
                            
                    elif change_type == "insert":
                        # Insert new content at specified line
                        line_num = change.get("line", 1) - 1  # Convert to 0-based index
                        new_content = change.get("content", "")
                        
                        lines = modified_content.split('\n')
                        if 0 <= line_num <= len(lines):
                            lines.insert(line_num, new_content.rstrip())
                            modified_content = '\n'.join(lines)
                
                # Write the modified content back to the file
                with open(file_path, 'w') as f:
                    f.write(modified_content)
                
                # Mark the fix as applied
                fix["applied"] = True
                fix["applied_at"] = datetime.now().isoformat()
                logger.info(f"Applied fix: {fix['description']}")
                
            except Exception as e:
                logger.error(f"Error applying fix: {str(e)}")
                success = False
                fix["applied"] = False
                fix["error"] = str(e)
        
        # If all fixes were applied successfully, remove the correction from our internal list
        # but keep it in the log file for history
        if success:
            if existing_correction is not None:
                del self.corrections["corrections"][existing_correction]
            else:
                # Find and remove the correction by file path
                self.corrections["corrections"] = [
                    c for c in self.corrections["corrections"]
                    if c.get("file_path") != file_path
                ]
        
        return success
    
    def _was_recently_applied(self, correction: Dict[str, any], cooldown_seconds: int = 2) -> bool:
        """Check if a correction was recently applied.
        
        Args:
            correction: The correction to check
            cooldown_seconds: Number of seconds to consider as "recent"
            
        Returns:
            True if the correction was applied recently
        """
        if not correction or "file_path" not in correction:
            return False
            
        file_path = correction["file_path"]
        
        # Check existing corrections
        for c in self.corrections["corrections"]:
            if c.get("file_path") == file_path:
                # Check if it was recently applied
                applied_at = c.get("applied_at")
                if applied_at:
                    try:
                        applied_time = datetime.fromisoformat(applied_at)
                        time_diff = (datetime.now() - applied_time).total_seconds()
                        return time_diff < cooldown_seconds
                    except (ValueError, TypeError):
                        pass
        
        return False

    def verify_correction(self, correction: Dict[str, any], validator: ChangeValidator) -> bool:
        """Verify that a correction fixed the issues.
        
        Args:
            correction: The correction that was applied
            validator: Validator instance to check the results
            
        Returns:
            True if all issues were fixed
        """
        if not correction or "file_path" not in correction:
            return False
            
        # Skip verification if the correction was recently applied
        if self._was_recently_applied(correction):
            logger.info("Skipping verification - correction was recently applied")
            return True
        
        # Create a change event for validation
        change = {
            "file_path": correction["file_path"],
            "event_type": "modified"
        }
        
        # Validate the changes
        result = validator.validate_change(change)
        
        # Check if the specific requirements in this correction are now met
        original_requirements = set(correction.get("requirements", []))
        remaining_requirements = set(result.get("missing_requirements", []))
        
        # Only check the requirements that were part of this correction
        relevant_remaining = original_requirements.intersection(remaining_requirements)
        
        fixed_requirements = original_requirements - remaining_requirements
        if fixed_requirements:
            logger.info(f"Fixed requirements: {fixed_requirements}")
        
        if relevant_remaining:
            logger.warning(f"Remaining issues: {relevant_remaining}")
        
        # Add or update the correction in the log
        file_path = correction.get("file_path")
        existing_correction = None
        for i, c in enumerate(self.corrections["corrections"]):
            if c.get("file_path") == file_path:
                existing_correction = i
                break
        
        verification_data = {
            "verified_at": datetime.now().isoformat(),
            "fixed_requirements": list(fixed_requirements),
            "remaining_requirements": list(relevant_remaining),
            "verification_success": len(relevant_remaining) == 0
        }
        
        if existing_correction is not None:
            # Update existing correction
            self.corrections["corrections"][existing_correction].update(verification_data)
        else:
            # Add new correction
            correction.update(verification_data)
            self.corrections["corrections"].append(correction)
        
        # Save the updated correction status
        self._save_corrections()
        
        return len(relevant_remaining) == 0

    def get_pending_corrections(self) -> List[Dict[str, any]]:
        """Get all pending corrections that haven't been applied yet.
        
        Returns:
            List of pending corrections
        """
        pending = []
        for correction in self.corrections.get("corrections", []):
            if not all(fix.get("applied", False) for fix in correction.get("fixes", [])):
                pending.append(correction)
        return pending

    def update_correction_status(self, file_path: str, status: str) -> None:
        """Update the status of a correction.
        
        Args:
            file_path: Path to the file
            status: New status to set
        """
        for correction in self.corrections["corrections"]:
            if correction.get("file_path") == file_path:
                correction["status"] = status
                self._save_corrections()
                break
                
    def mark_correction_failed(self, correction: Dict[str, any]) -> None:
        """Mark a correction as failed.
        
        Args:
            correction: The correction that failed
        """
        file_path = correction.get("file_path")
        if file_path:
            self.update_correction_status(file_path, "❌ needs review")
            
            # Log the failure details
            logger.warning(f"""
Manual review required for {file_path}:
- Issue: {correction.get("fixes", [{}])[0].get("description", "Unknown issue")}
- Failed after 3 attempts
- Please check logs/correction_status.json for details
- Manual fix may be needed for this file
""") 
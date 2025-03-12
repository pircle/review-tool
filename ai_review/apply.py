"""
Module for applying AI-suggested fixes to code.
"""

import os
import re
import json
import shutil
import traceback
from typing import Dict, List, Any, Optional
from openai import OpenAI
from pathlib import Path
from datetime import datetime

from .logger import logger
from .constants import LOGS_DIR, FIX_LOG_PATH, get_project_logs_dir
from .interaction_logger import interaction_logger
from .config_manager import config_manager
from .models import AppliedFix


class FixSeverity:
    """Severity levels for code fixes."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class FixCategory:
    """Categories of code fixes."""
    FORMATTING = "formatting"
    IMPORTS = "imports"
    OPTIMIZATION = "optimization"
    LOGIC = "logic"
    SECURITY = "security"
    PERFORMANCE = "performance"
    OTHER = "other"

class Fix:
    """Class representing a code fix."""
    
    def __init__(self, file: str, description: str, changes: List[Dict[str, Any]], 
                 severity: str = FixSeverity.LOW, category: str = FixCategory.OTHER,
                 auto_applicable: bool = False):
        """
        Initialize a code fix.
        
        Args:
            file: Path to the file to fix
            description: Description of the fix
            changes: List of changes to apply
            severity: Severity level of the fix
            category: Category of the fix
            auto_applicable: Whether the fix can be applied automatically
        """
        self.file = file
        self.description = description
        self.changes = changes
        self.severity = severity
        self.category = category
        self.auto_applicable = auto_applicable
        
        # Determine if fix is auto-applicable based on severity and category
        if not auto_applicable:
            self.auto_applicable = (
                severity in [FixSeverity.LOW, FixSeverity.MEDIUM] and
                category in [FixCategory.FORMATTING, FixCategory.IMPORTS, FixCategory.OPTIMIZATION]
            )

class CodeFixer:
    """Class for applying code fixes."""
    
    def __init__(self, project_name: str):
        """
        Initialize the code fixer.
        
        Args:
            project_name: Project name
        """
        self.project_name = project_name
        self.log_dir = Path(LOGS_DIR) / project_name
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.fix_log_path = self.log_dir / "fix_log.json"
        self.fixes: List[AppliedFix] = []
        self._load_existing_fixes()
    
    def _load_existing_fixes(self):
        """Load existing fixes from the log file."""
        if self.fix_log_path.exists():
            with open(self.fix_log_path) as f:
                fixes_data = json.load(f)
                for fix_data in fixes_data:
                    fix_data['timestamp'] = datetime.fromisoformat(fix_data['timestamp'])
                    self.fixes.append(AppliedFix(**fix_data))
    
    def add_fix(self, file: str, description: str, category: str, before: str, after: str):
        """Add a new fix to the log."""
        fix = AppliedFix(
            file=file,
            description=description,
            category=category,
            before=before,
            after=after,
            timestamp=datetime.now()
        )
        self.fixes.append(fix)
        self._save_fixes()
    
    def _save_fixes(self):
        """Save all fixes to the log file."""
        fixes_data = [fix.dict() for fix in self.fixes]
        for fix_data in fixes_data:
            fix_data['timestamp'] = fix_data['timestamp'].isoformat()
        
        with open(self.fix_log_path, 'w') as f:
            json.dump(fixes_data, f, indent=2)
    
    def get_fixes(self) -> List[AppliedFix]:
        """Get all applied fixes."""
        return self.fixes
    
    def apply_fixes(self, auto_fix: bool = False) -> Dict[str, Any]:
        """
        Apply fixes to the code.
        
        Args:
            auto_fix: Whether to automatically apply safe fixes
            
        Returns:
            Dictionary containing results of fix application
        """
        results = {
            "applied": [],
            "skipped": [],
            "failed": []
        }
        
        for fix in self.fixes:
            try:
                # Check if fix should be applied automatically
                should_apply = auto_fix and fix.auto_applicable
                
                if should_apply:
                    logger.info(f"Automatically applying fix: {fix.description}")
                    self._apply_fix(fix)
                    results["applied"].append({
                        "file": fix.file,
                        "description": fix.description,
                        "severity": fix.severity,
                        "category": fix.category
                    })
                else:
                    logger.info(f"Skipping fix (requires user approval): {fix.description}")
                    results["skipped"].append({
                        "file": fix.file,
                        "description": fix.description,
                        "severity": fix.severity,
                        "category": fix.category,
                        "reason": "Requires user approval"
                    })
            except Exception as e:
                logger.error(f"Failed to apply fix: {str(e)}")
                results["failed"].append({
                    "file": fix.file,
                    "description": fix.description,
                    "error": str(e)
                })
        
        # Log results
        self._log_fixes(results)
        
        return results
    
    def _apply_fix(self, fix: AppliedFix) -> None:
        """
        Apply a single fix to the code.
        
        Args:
            fix: Fix to apply
        """
        try:
            # Read the file
            with open(fix.file, "r") as f:
                content = f.read()
            
            # Apply each change
            for change in fix.changes:
                if "line" in change:
                    # Line-based change
                    lines = content.split("\n")
                    lines[change["line"]] = change["content"]
                    content = "\n".join(lines)
                elif "start" in change and "end" in change:
                    # Range-based change
                    before = content[:change["start"]]
                    after = content[change["end"]:]
                    content = before + change["content"] + after
                elif "pattern" in change:
                    # Pattern-based change
                    import re
                    content = re.sub(change["pattern"], change["replacement"], content)
            
            # Write back to file
            with open(fix.file, "w") as f:
                f.write(content)
            
            logger.info(f"Successfully applied fix to {fix.file}")
            
        except Exception as e:
            logger.error(f"Error applying fix to {fix.file}: {str(e)}")
            raise
    
    def _log_fixes(self, results: Dict[str, Any]) -> None:
        """
        Log fix results to file.
        
        Args:
            results: Results of fix application
        """
        try:
            # Create log directory if needed
            os.makedirs(os.path.dirname(self.fix_log_path), exist_ok=True)
            
            # Load existing log if it exists
            existing_log = []
            if os.path.exists(self.fix_log_path):
                with open(self.fix_log_path, "r") as f:
                    existing_log = json.load(f)
            
            # Add new results
            log_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "project": self.project_name,
                "results": results
            }
            existing_log.append(log_entry)
            
            # Write updated log
            with open(self.fix_log_path, "w") as f:
                json.dump(existing_log, f, indent=2)
            
            logger.info(f"Fix results logged to {self.fix_log_path}")
            
        except Exception as e:
            logger.error(f"Error logging fixes: {str(e)}")
            raise

class FixApplier:
    """Class for applying fixes to code."""
    
    def __init__(self, project_name: str):
        """
        Initialize the fix applier.
        
        Args:
            project_name: Project name
        """
        self.project_name = project_name
        self.fixer = CodeFixer(project_name)
    
    def apply_fixes(self, fixes: List[Dict[str, Any]], auto_fix: bool = False) -> Dict[str, Any]:
        """
        Apply fixes to code.
        
        Args:
            fixes: List of fixes to apply
            auto_fix: Whether to automatically apply safe fixes
            
        Returns:
            Dictionary containing results of fix application
        """
        # Convert fixes to Fix objects
        for fix_data in fixes:
            self.fixer.add_fix(
                fix_data["file"],
                fix_data["description"],
                fix_data["category"],
                fix_data["before"],
                fix_data["after"]
            )
        
        # Apply fixes
        return self.fixer.apply_fixes(auto_fix)

def log_fix_entry(fix_entry):
    """Log a fix entry to the fix log file."""
    os.makedirs(os.path.dirname(FIX_LOG_PATH), exist_ok=True)
    
    # Load existing log entries if they exist
    existing_entries = []
    if os.path.exists(FIX_LOG_PATH):
        try:
            with open(FIX_LOG_PATH, 'r') as f:
                existing_entries = json.load(f)
        except json.JSONDecodeError:
            logger.warning("Failed to parse existing fix log file. Starting fresh.")
    
    # Append new entry
    existing_entries.append(fix_entry)
    
    # Write back to file
    with open(FIX_LOG_PATH, 'w') as f:
        json.dump(existing_entries, f, indent=2) 
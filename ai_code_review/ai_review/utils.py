"""
Utility functions for the AI code review system.
"""

import os
import json
import logging
import pathlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from .constants import LOGS_DIR


def setup_logging(log_dir: str = None) -> logging.Logger:
    """
    Set up logging for the AI code review system.
    
    Args:
        log_dir: Directory to store log files (optional)
        
    Returns:
        Configured logger
    """
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"ai_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Configure logging
    logger = logging.getLogger("ai_code_review")
    logger.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def is_source_code_file(file_path: str) -> bool:
    """
    Check if a file is a source code file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file is a source code file, False otherwise
    """
    source_code_extensions = [
        # JavaScript/TypeScript
        '.js', '.jsx', '.ts', '.tsx',
        # Python
        '.py',
        # HTML/CSS
        '.html', '.css',
        # Configuration files
        '.json', '.yaml', '.yml'
    ]
    
    file_extension = pathlib.Path(file_path).suffix.lower()
    return file_extension in source_code_extensions


def is_supported_file(file_path: str, supported_extensions: List[str]) -> bool:
    """
    Check if a file is a supported file type.
    
    Args:
        file_path: Path to the file
        supported_extensions: List of supported file extensions
        
    Returns:
        True if the file is a supported file type, False otherwise
    """
    # First check if it's a source code file
    if not is_source_code_file(file_path):
        return False
        
    file_extension = pathlib.Path(file_path).suffix.lower()
    return file_extension in supported_extensions


def find_files_by_extension(directory: str, extensions: List[str]) -> List[str]:
    """
    Find all files with the specified extensions in a directory.
    
    Args:
        directory: Directory to search
        extensions: List of file extensions to find
        
    Returns:
        List of file paths
    """
    files = []
    
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            if is_supported_file(file_path, extensions):
                files.append(file_path)
                
    return files


def save_json(data: Any, file_path: str) -> bool:
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save
        file_path: Path to the output file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2)
        return True
    except Exception as e:
        print(f"Error saving JSON file: {e}")
        return False


def load_json(file_path: str) -> Optional[Any]:
    """
    Load data from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Loaded data or None if an error occurred
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return None


def get_file_extension(file_path: str) -> str:
    """
    Get the extension of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension (without the dot)
    """
    _, ext = os.path.splitext(file_path)
    return ext[1:] if ext.startswith('.') else ext


def is_python_file(file_path: str) -> bool:
    """
    Check if a file is a Python file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if it's a Python file, False otherwise
    """
    return get_file_extension(file_path).lower() == "py"


def find_python_files(directory: str) -> List[str]:
    """
    Find all Python files in a directory (recursively).
    
    Args:
        directory: Directory to search
        
    Returns:
        List of Python file paths
    """
    python_files = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
                
    return python_files


def create_backup(file_path: str) -> Optional[str]:
    """
    Create a backup of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Path to the backup file or None if error
    """
    try:
        backup_path = f"{file_path}.bak"
        with open(file_path, 'r', encoding='utf-8') as src:
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        return backup_path
    except Exception as e:
        print(f"Error creating backup: {e}")
        return None


def restore_backup(backup_path: str) -> bool:
    """
    Restore a file from its backup.
    
    Args:
        backup_path: Path to the backup file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        original_path = backup_path[:-4]  # Remove .bak extension
        with open(backup_path, 'r', encoding='utf-8') as src:
            with open(original_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        return True
    except Exception as e:
        print(f"Error restoring backup: {e}")
        return False


def format_suggestion(suggestion: Dict[str, Any]) -> str:
    """
    Format a suggestion for display.
    
    Args:
        suggestion: Suggestion to format
        
    Returns:
        Formatted suggestion as a string
    """
    suggestion_type = suggestion.get("type", "unknown")
    
    if suggestion_type == "complex_function":
        function_name = suggestion.get("function_name", "unknown")
        line_number = suggestion.get("line_number", 0)
        suggestion_text = suggestion.get("suggestion", "")
        
        return f"Function '{function_name}' (line {line_number}):\n{suggestion_text}"
    elif suggestion_type == "general":
        suggestion_text = suggestion.get("suggestion", "")
        return f"General suggestion:\n{suggestion_text}"
    else:
        return f"Unknown suggestion type: {suggestion_type}"


def ensure_log_dir():
    """Ensure the logs directory exists."""
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    return LOGS_DIR 
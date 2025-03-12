"""Tests for the review coordinator."""

import os
import json
import time
import pytest
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Generator
from unittest.mock import Mock

from ai_review.config_manager import ConfigManager
from ai_review.validator import ChangeValidator
from ai_review.correction_manager import CorrectionManager
from ai_review.apply_corrections import CorrectionApplier
from ai_review.review_coordinator import ReviewCoordinator, CodeChangeHandler
from ai_review.events import FileCreatedEvent, FileModifiedEvent, FileDeletedEvent

# Configure logging for tests
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create handlers
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create formatters and add it to handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)

@pytest.fixture(autouse=True)
def clear_logs():
    """Clear the log files before each test."""
    log_files = [
        Path("logs/review_log.json"),
        Path("logs/cursor_corrections.json"),
        Path("logs/validation_log.json"),
        Path("logs/correction_applier.log"),
        Path("logs/review_coordinator.log")
    ]
    
    for log_file in log_files:
        if log_file.exists():
            log_file.unlink()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        if log_file.suffix == '.json':
            data = {"changes": []} if "review_log" in log_file.name else {"corrections": []}
            with open(log_file, "w") as f:
                json.dump(data, f)
    yield

@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def config_manager(temp_dir: str) -> ConfigManager:
    """Create a config manager for testing."""
    config = {
        "openai_api_key": "test-key",
        "model": "gpt-4",
        "complexity_threshold": 5,
        "log_level": "INFO"
    }
    
    # Create config directory
    config_dir = os.path.join(temp_dir, ".ai-code-review")
    os.makedirs(config_dir, exist_ok=True)
    
    # Write config file
    config_file = os.path.join(config_dir, "config.json")
    with open(config_file, "w") as f:
        json.dump(config, f)
    
    # Set environment variable for config directory
    os.environ["AI_CODE_REVIEW_CONFIG_DIR"] = config_dir
    
    # Create instance
    config_manager = ConfigManager()
    
    yield config_manager
    
    # Clean up
    if "AI_CODE_REVIEW_CONFIG_DIR" in os.environ:
        del os.environ["AI_CODE_REVIEW_CONFIG_DIR"]

@pytest.fixture
def requirements_file(temp_dir: str):
    """Create a temporary requirements file."""
    content = """# Project Requirements

## Code Style
- Use consistent indentation
- Follow PEP 8 guidelines
- Add docstrings to all functions

## Features
- Implement file watching
- Support multiple projects
- Enable local validation
"""
    
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    req_file = docs_dir / "Kalkal_Requirements.md"
    
    with open(req_file, "w") as f:
        f.write(content)
    
    yield req_file
    
    # Clean up
    if req_file.exists():
        req_file.unlink()
    if docs_dir.exists():
        docs_dir.rmdir()

def test_code_change_handler(config_manager, temp_dir):
    """Test the CodeChangeHandler class."""
    coordinator = ReviewCoordinator(config_manager)
    handler = CodeChangeHandler(coordinator)
    
    # Create test file paths
    test_py = os.path.join(temp_dir, "test.py")
    test_json = os.path.join(temp_dir, "test.json")
    
    # Create mock events
    created_event = Mock()
    created_event.is_directory = False
    created_event.src_path = test_py
    
    # Test file creation
    handler.on_created(created_event)
    
    # Verify that the change was logged
    assert len(coordinator.review_log["changes"]) > 0
    assert coordinator.review_log["changes"][0]["event_type"] == "created"
    assert coordinator.review_log["changes"][0]["file_path"] == str(Path(test_py).resolve())
    
    # Test file modification
    modified_event = Mock()
    modified_event.is_directory = False
    modified_event.src_path = test_json
    
    handler.on_modified(modified_event)
    
    # Verify that the change was logged
    assert len(coordinator.review_log["changes"]) > 1
    assert coordinator.review_log["changes"][1]["event_type"] == "modified"
    assert coordinator.review_log["changes"][1]["file_path"] == str(Path(test_json).resolve())
    
    # Test file deletion
    deleted_event = Mock()
    deleted_event.is_directory = False
    deleted_event.src_path = test_py
    
    handler.on_deleted(deleted_event)
    
    # Verify that the change was logged
    assert len(coordinator.review_log["changes"]) > 2
    assert coordinator.review_log["changes"][2]["event_type"] == "deleted"
    assert coordinator.review_log["changes"][2]["file_path"] == str(Path(test_py).resolve())

def test_review_coordinator(config_manager: ConfigManager, temp_dir: str, requirements_file: Path):
    """Test that the review coordinator processes changes and generates corrections."""
    coordinator = ReviewCoordinator(config_manager)
    
    # Create a test file with indentation issues
    test_py = os.path.join(temp_dir, "test.py")
    with open(test_py, "w") as f:
        f.write("def test():\n  print('test')\n    print('bad indent')\n")
    
    # Create a change event
    change = {
        "file_path": str(Path(test_py).resolve()),
        "event_type": "created",
        "timestamp": datetime.now().isoformat()
    }
    
    # Process the change
    coordinator.handle_change(change)
    
    # Verify that the change was logged
    assert len(coordinator.review_log["changes"]) > 0
    assert coordinator.review_log["changes"][0]["event_type"] == "created"
    assert coordinator.review_log["changes"][0]["file_path"] == str(Path(test_py).resolve())
    
    # Verify that corrections were generated
    corrections = coordinator.correction_manager.corrections
    assert len(corrections["corrections"]) > 0
    assert any("indentation" in fix.get("description", "").lower() 
              for correction in corrections["corrections"] 
              for fix in correction.get("fixes", []))

def test_review_coordinator_monitoring(config_manager: ConfigManager, temp_dir: str):
    """Test that the review coordinator properly monitors directories."""
    coordinator = ReviewCoordinator(config_manager)
    
    # Start monitoring the temp directory
    coordinator.start_monitoring(temp_dir)
    
    # Create a test file
    test_py = os.path.join(temp_dir, "test.py")
    with open(test_py, "w") as f:
        f.write("def test():\n  print('test')\n    print('bad indent')\n")
    
    # Give the observer time to process the event
    time.sleep(1)
    
    # Verify that the file creation was logged
    assert len(coordinator.review_log["changes"]) > 0
    assert any(
        change["event_type"] == "created" and 
        change["file_path"] == str(Path(test_py).resolve())
        for change in coordinator.review_log["changes"]
    ), "File creation not logged"
    
    # Modify the file
    with open(test_py, "a") as f:
        f.write("def another():\n  pass\n")
    
    # Give the observer time to process the event
    time.sleep(1)
    
    # Verify that the file modification was logged
    assert any(
        change["event_type"] == "modified" and 
        change["file_path"] == str(Path(test_py).resolve())
        for change in coordinator.review_log["changes"]
    ), "File modification not logged"
    
    # Delete the file
    os.remove(test_py)
    
    # Give the observer time to process the event
    time.sleep(1)
    
    # Verify that the file deletion was logged
    assert any(
        change["event_type"] == "deleted" and 
        change["file_path"] == str(Path(test_py).resolve())
        for change in coordinator.review_log["changes"]
    ), "File deletion not logged"
    
    # Stop monitoring
    coordinator.stop_monitoring()
    assert not coordinator.running, "Coordinator should be stopped" 
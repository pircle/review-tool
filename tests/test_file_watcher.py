"""Tests for the file watcher module."""

import os
import json
import time
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator

from ai_review.config_manager import ConfigManager
from ai_review.file_watcher import FileWatcher, ChangeTracker

@pytest.fixture(autouse=True)
def clear_logs():
    """Clear the log file before each test."""
    log_file = Path("logs/review_log.json")
    if log_file.exists():
        log_file.unlink()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "w") as f:
        json.dump({"file_changes": []}, f)
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
        "log_level": "INFO",
        "file_filters": {
            "include_dirs": ["src/", "tests/"],
            "exclude_dirs": ["__pycache__/", "venv/"],
            "include_files": ["*.py", "*.js"],
            "exclude_files": ["*.pyc", "*.tmp"]
        }
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

def test_file_watcher_initialization(temp_dir: str, config_manager: ConfigManager):
    """Test FileWatcher initialization."""
    watcher = FileWatcher(config_manager, [temp_dir])
    assert watcher.watch_dirs == [temp_dir]
    assert isinstance(watcher.tracker, ChangeTracker)

def test_change_tracker_file_filtering(temp_dir: str, config_manager: ConfigManager):
    """Test ChangeTracker file filtering."""
    tracker = ChangeTracker(config_manager, [temp_dir])
    
    # Create test directory structure
    src_dir = Path(temp_dir) / "src"
    src_dir.mkdir()
    
    # Test included file
    test_py = src_dir / "test.py"
    assert tracker._should_track_file(str(test_py)) is True
    
    # Test excluded file
    test_pyc = src_dir / "test.pyc"
    assert tracker._should_track_file(str(test_pyc)) is False
    
    # Test excluded directory
    pycache_dir = src_dir / "__pycache__" / "test.py"
    assert tracker._should_track_file(str(pycache_dir)) is False

def test_change_tracker_logging(temp_dir: str, config_manager: ConfigManager):
    """Test ChangeTracker event logging."""
    tracker = ChangeTracker(config_manager, [temp_dir])
    
    # Create test file
    test_file = Path(temp_dir) / "src" / "test.py"
    test_file.parent.mkdir(exist_ok=True)
    test_file.touch()
    
    # Log a change
    tracker._log_change("created", str(test_file))
    
    # Check log file
    log_file = Path("logs/review_log.json")
    assert log_file.exists()
    
    with open(log_file) as f:
        log_data = json.load(f)
    
    assert len(log_data["file_changes"]) == 1
    change = log_data["file_changes"][0]
    assert change["event_type"] == "created"
    assert Path(change["file_path"]).name == "test.py"
    assert change["reviewed"] is False

def test_change_tracker_multiple_events(temp_dir: str, config_manager: ConfigManager):
    """Test ChangeTracker handling multiple events."""
    tracker = ChangeTracker(config_manager, [temp_dir])
    
    # Create test files
    src_dir = Path(temp_dir) / "src"
    src_dir.mkdir()
    
    file1 = src_dir / "test1.py"
    file2 = src_dir / "test2.py"
    
    # Log multiple changes
    tracker._log_change("created", str(file1))
    tracker._log_change("modified", str(file1))
    tracker._log_change("created", str(file2))
    
    # Check log file
    with open("logs/review_log.json") as f:
        log_data = json.load(f)
    
    assert len(log_data["file_changes"]) == 3
    events = [change["event_type"] for change in log_data["file_changes"]]
    assert events == ["created", "modified", "created"] 
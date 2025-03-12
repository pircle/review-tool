"""Tests for the correction system."""

import os
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Generator
import time
import logging

from ai_review.config_manager import ConfigManager
from ai_review.validator import ChangeValidator
from ai_review.correction_manager import CorrectionManager
from ai_review.apply_corrections import CorrectionApplier
from ai_review.review_coordinator import ReviewCoordinator

@pytest.fixture(autouse=True)
def clear_logs():
    """Clear the log files before each test."""
    log_files = [
        Path("logs/cursor_corrections.json"),
        Path("logs/validation_log.json"),
        Path("logs/correction_applier.log")
    ]
    
    for log_file in log_files:
        if log_file.exists():
            log_file.unlink()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        if log_file.suffix == '.json':
            with open(log_file, "w") as f:
                data = {"corrections": []} if "corrections" in log_file.name else {"validations": []}
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

def test_correction_manager_initialization(config_manager: ConfigManager):
    """Test CorrectionManager initialization."""
    manager = CorrectionManager(config_manager)
    assert manager.config_manager == config_manager
    assert isinstance(manager.corrections, dict)
    assert "corrections" in manager.corrections

def test_generate_correction_for_indentation(config_manager: ConfigManager, temp_dir: str, requirements_file: Path):
    """Test generating a correction for indentation issues."""
    validator = ChangeValidator(config_manager)
    manager = CorrectionManager(config_manager)
    
    # Create test file with inconsistent indentation
    test_file = Path(temp_dir) / "test.py"
    with open(test_file, "w") as f:
        f.write("""def test():
  pass  # 2 spaces
    def inner():  # 4 spaces
   return True  # 3 spaces
""")
    
    # Validate the file
    result = validator.validate_change({
        "file_path": str(test_file),
        "event_type": "created"
    })
    
    # Generate correction
    correction = manager.generate_correction(result)
    
    assert correction["file_path"] == str(test_file)
    assert len(correction["fixes"]) > 0
    
    # Check that we have an indentation fix
    indentation_fixes = [
        fix for fix in correction["fixes"]
        if any("indentation" in change.get("description", "").lower() 
              for change in fix["cursor_instructions"]["changes"])
    ]
    assert len(indentation_fixes) > 0

def test_generate_correction_for_docstrings(config_manager: ConfigManager, temp_dir: str, requirements_file: Path):
    """Test generating a correction for missing docstrings."""
    validator = ChangeValidator(config_manager)
    manager = CorrectionManager(config_manager)
    
    # Create test file without docstrings
    test_file = Path(temp_dir) / "test.py"
    with open(test_file, "w") as f:
        f.write("""def test1():
    pass

def test2():
    return True
""")
    
    # Validate the file
    result = validator.validate_change({
        "file_path": str(test_file),
        "event_type": "created"
    })
    
    # Generate correction
    correction = manager.generate_correction(result)
    
    assert correction["file_path"] == str(test_file)
    assert len(correction["fixes"]) > 0
    
    # Check that we have docstring fixes
    docstring_fixes = [
        fix for fix in correction["fixes"]
        if any("docstring" in change.get("content", "").lower() 
              for change in fix["cursor_instructions"]["changes"])
    ]
    assert len(docstring_fixes) > 0

def test_correction_applier(config_manager: ConfigManager, temp_dir: str, requirements_file: Path):
    """Test the correction applier."""
    applier = CorrectionApplier(config_manager)
    
    # Create test file with issues
    test_file = Path(temp_dir) / "test.py"
    with open(test_file, "w") as f:
        f.write("""def test():
  pass  # 2 spaces
    def inner():  # 4 spaces
   return True  # 3 spaces
""")
    
    # Validate and generate correction
    result = applier.validator.validate_change({
        "file_path": str(test_file),
        "event_type": "created"
    })
    
    # Create a focused correction for just the indentation issue
    correction = {
        "file_path": str(test_file),
        "requirements": ["Use consistent indentation"],
        "fixes": [{
            "requirement": "Use consistent indentation",
            "type": "edit",
            "description": "Fix inconsistent indentation",
            "cursor_instructions": {
                "action": "edit",
                "file": str(test_file),
                "changes": [{
                    "type": "format",
                    "description": "Fix inconsistent indentation",
                    "style": "spaces",
                    "size": 4
                }]
            }
        }]
    }
    
    # Apply correction
    success = applier.retry_correction(correction)
    assert success
    
    # Verify that the correction was logged
    with open("logs/cursor_corrections.json") as f:
        corrections = json.load(f)
        assert len(corrections["corrections"]) > 0
        assert any(c["file_path"] == str(test_file) for c in corrections["corrections"])
    
    # Verify file content was updated
    with open(test_file) as f:
        content = f.read()
        lines = content.split('\n')
        # Check that all non-empty lines use 4-space indentation
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                assert indent == 0 or indent == 4, f"Line has incorrect indentation: {line!r}"

def test_correction_verification(config_manager: ConfigManager, temp_dir: str, requirements_file: Path):
    """Test correction verification."""
    manager = CorrectionManager(config_manager)
    validator = ChangeValidator(config_manager)
    
    # Create test file with consistent indentation but no docstrings
    test_file = Path(temp_dir) / "test.py"
    with open(test_file, "w") as f:
        f.write("""def test():
    pass

def another_test():
    return True
""")
    
    # Create a correction for just the indentation requirement
    correction = {
        "file_path": str(test_file),
        "requirements": ["Use consistent indentation"],
        "fixes": [{
            "requirement": "Use consistent indentation",
            "type": "edit",
            "cursor_instructions": {
                "action": "edit",
                "file": str(test_file),
                "changes": [{
                    "type": "format",
                    "style": "spaces",
                    "size": 4
                }]
            }
        }]
    }
    
    # Verify the correction
    result = manager.verify_correction(correction, validator)
    assert result, "Verification should pass since indentation is consistent"
    
    # Create a correction with multiple requirements
    correction = {
        "file_path": str(test_file),
        "requirements": ["Use consistent indentation", "Add docstrings to all functions"],
        "fixes": [{
            "requirement": "Use consistent indentation",
            "type": "edit",
            "cursor_instructions": {
                "action": "edit",
                "file": str(test_file),
                "changes": [{
                    "type": "format",
                    "style": "spaces",
                    "size": 4
                }]
            }
        }]
    }
    
    # Verify the correction - should fail because docstring requirement isn't met
    result = manager.verify_correction(correction, validator)
    assert not result, "Verification should fail due to missing docstring requirement"
    
    # Check that the correction was logged
    with open("logs/cursor_corrections.json") as f:
        corrections = json.load(f)
        assert len(corrections["corrections"]) > 0
        
        # Find our correction
        found = False
        for c in corrections["corrections"]:
            if c["file_path"] == str(test_file):
                found = True
                assert not c["verification_success"], "Verification should be marked as failed"
                assert "Add docstrings to all functions" in c["remaining_requirements"]
                break
        
        assert found, "Correction should be in the log file"

def test_correction_applier_cooldown(config_manager: ConfigManager, temp_dir: str, requirements_file: Path):
    """Test that the correction applier respects cooldown periods."""
    applier = CorrectionApplier(config_manager)
    
    # Create test file with issues
    test_file = Path(temp_dir) / "test.py"
    with open(test_file, "w") as f:
        f.write("""def test():
  pass  # 2 spaces
""")
    
    # Create a correction for the indentation issue
    correction = {
        "file_path": str(test_file),
        "requirements": ["Use consistent indentation"],
        "fixes": [{
            "requirement": "Use consistent indentation",
            "type": "edit",
            "description": "Fix inconsistent indentation",
            "cursor_instructions": {
                "action": "edit",
                "file": str(test_file),
                "changes": [{
                    "type": "format",
                    "description": "Fix inconsistent indentation",
                    "style": "spaces",
                    "size": 4
                }]
            }
        }]
    }
    
    # Add the correction to the manager
    applier.correction_manager.corrections["corrections"].append(correction)
    applier.correction_manager._save_corrections()
    
    # First call should process
    applier.apply_pending_corrections()
    first_correction_time = applier.last_correction_time
    
    # Immediate second call should return due to cooldown
    applier.apply_pending_corrections()
    assert applier.last_correction_time == first_correction_time, "Second call should not update last_correction_time due to cooldown"
    
    # Wait for cooldown
    time.sleep(applier.check_cooldown + 0.1)  # Add 0.1s buffer
    
    # Create a new correction to ensure something is applied
    with open(test_file, "w") as f:
        f.write("""def another():
  pass  # 2 spaces again
""")
    
    correction = {
        "file_path": str(test_file),
        "requirements": ["Use consistent indentation"],
        "fixes": [{
            "requirement": "Use consistent indentation",
            "type": "edit",
            "description": "Fix inconsistent indentation",
            "cursor_instructions": {
                "action": "edit",
                "file": str(test_file),
                "changes": [{
                    "type": "format",
                    "description": "Fix inconsistent indentation",
                    "style": "spaces",
                    "size": 4
                }]
            }
        }]
    }
    
    # Add the new correction to the manager
    applier.correction_manager.corrections["corrections"] = [correction]
    applier.correction_manager._save_corrections()
    
    # Third call should process
    applier.apply_pending_corrections()
    assert applier.last_correction_time > first_correction_time, "Third call should update last_correction_time after cooldown"
    
    # Test log cooldown
    first_log_time = applier.last_log_time
    
    # Immediate call should not log
    applier.apply_pending_corrections()
    assert applier.last_log_time == first_log_time, "Should not update last_log_time during cooldown"
    
    # Wait for log cooldown
    time.sleep(applier.log_cooldown + 0.1)  # Add 0.1s buffer
    
    # Create another correction to ensure something is applied
    with open(test_file, "w") as f:
        f.write("""def third():
  pass  # 2 spaces yet again
""")
    
    correction = {
        "file_path": str(test_file),
        "requirements": ["Use consistent indentation"],
        "fixes": [{
            "requirement": "Use consistent indentation",
            "type": "edit",
            "description": "Fix inconsistent indentation",
            "cursor_instructions": {
                "action": "edit",
                "file": str(test_file),
                "changes": [{
                    "type": "format",
                    "description": "Fix inconsistent indentation",
                    "style": "spaces",
                    "size": 4
                }]
            }
        }]
    }
    
    # Add the new correction to the manager
    applier.correction_manager.corrections["corrections"] = [correction]
    applier.correction_manager._save_corrections()
    
    # Should log now
    applier.apply_pending_corrections()
    
    # Check that the error was logged
    with open("logs/correction_status.json") as f:
        status = json.load(f)
        assert any(entry["status"] == "❌ needs review" for entry in status["corrections"])

def test_correction_applier_shutdown(config_manager: ConfigManager, temp_dir: str, requirements_file: Path):
    """Test graceful shutdown of the correction applier."""
    applier = CorrectionApplier(config_manager)
    
    # Create a test file that will trigger corrections
    test_file = Path(temp_dir) / "test.py"
    with open(test_file, "w") as f:
        f.write("""def test():
  pass  # Bad indentation
""")
    
    # Start the applier in a separate thread
    import threading
    import queue
    
    shutdown_event = threading.Event()
    error_queue = queue.Queue()
    
    # Set the shutdown event in the applier
    applier.set_shutdown_event(shutdown_event)
    
    def run_applier():
        try:
            while not shutdown_event.is_set():
                applier.apply_pending_corrections()
                time.sleep(applier.check_cooldown)
        except Exception as e:
            error_queue.put(e)
    
    thread = threading.Thread(target=run_applier)
    thread.start()
    
    # Let it run for a bit
    time.sleep(2 * applier.check_cooldown)
    
    # Signal shutdown
    shutdown_event.set()
    thread.join(timeout=5)
    
    # Check for any errors
    assert thread.is_alive() is False, "Thread should have stopped"
    assert error_queue.empty(), "No errors should have occurred"

def test_correction_applier_idle_detection(config_manager: ConfigManager, temp_dir: str, requirements_file: Path):
    """Test that the correction applier detects idle state correctly."""
    applier = CorrectionApplier(config_manager)
    
    # Create test file with issues
    test_file = Path(temp_dir) / "test.py"
    with open(test_file, "w") as f:
        f.write("""def test():
  pass  # 2 spaces
""")
    
    # First call should process
    result = applier.apply_pending_corrections()
    assert result is False, "Should return False when no corrections are found"
    assert applier.running is True, "Should still be running"
    
    # Create and add a correction
    correction = {
        "file_path": str(test_file),
        "requirements": ["Use consistent indentation"],
        "fixes": [{
            "requirement": "Use consistent indentation",
            "type": "edit",
            "description": "Fix inconsistent indentation",
            "cursor_instructions": {
                "action": "edit",
                "file": str(test_file),
                "changes": [{
                    "type": "format",
                    "description": "Fix inconsistent indentation",
                    "style": "spaces",
                    "size": 4
                }]
            }
        }]
    }
    applier.correction_manager.corrections["corrections"] = [correction]
    applier.correction_manager._save_corrections()
    
    # Wait for cooldown
    time.sleep(applier.check_cooldown + 0.1)
    
    # Second call should find no corrections
    result = applier.apply_pending_corrections()
    assert result is True, "Second call should find corrections"
    assert applier.consecutive_no_corrections == 0, "Should reset no-corrections counter"
    
    # Multiple calls with no corrections should increase counter
    for _ in range(applier.max_no_corrections):
        time.sleep(applier.check_cooldown + 0.1)
        result = applier.apply_pending_corrections()
        assert result is False, "Should return False when no corrections found"
    
    assert applier.consecutive_no_corrections >= applier.max_no_corrections, "Should reach max no-corrections limit"
    assert applier.running is False, "Should stop running after max no-corrections"
    
    # Reset running state for testing
    applier.running = True
    applier.consecutive_no_corrections = 0
    applier.last_correction_time = time.time()
    
    # Create a new issue to verify counter reset
    with open(test_file, "w") as f:
        f.write("""def test():
   pass  # 3 spaces
""")
    
    # Create and add a new correction
    correction = {
        "file_path": str(test_file),
        "requirements": ["Use consistent indentation"],
        "fixes": [{
            "requirement": "Use consistent indentation",
            "type": "edit",
            "description": "Fix inconsistent indentation",
            "cursor_instructions": {
                "action": "edit",
                "file": str(test_file),
                "changes": [{
                    "type": "format",
                    "description": "Fix inconsistent indentation",
                    "style": "spaces",
                    "size": 4
                }]
            }
        }]
    }
    applier.correction_manager.corrections["corrections"] = [correction]
    applier.correction_manager._save_corrections()
    
    # Wait for cooldown
    time.sleep(applier.check_cooldown + 0.1)
    
    # Should process new correction and reset counter
    result = applier.apply_pending_corrections()
    assert result is True, "Should return True when corrections are found"
    assert applier.consecutive_no_corrections == 0, "Should reset no-corrections counter"
    assert applier.running is True, "Should still be running after activity"

def test_correction_applier_idle_timeout(config_manager: ConfigManager, temp_dir: str, requirements_file: Path):
    """Test that the correction applier handles idle timeout correctly."""
    applier = CorrectionApplier(config_manager)
    
    # Temporarily reduce idle timeout for testing
    original_timeout = applier.idle_timeout
    applier.idle_timeout = 2  # 2 seconds for testing
    
    try:
        # Create test file with issues
        test_file = Path(temp_dir) / "test.py"
        with open(test_file, "w") as f:
            f.write("""def test():
  pass  # 2 spaces
""")
        
        # First call should process
        result = applier.apply_pending_corrections()
        assert result is False, "Should return False when no corrections are found"
        assert applier.running is True, "Should still be running"
        
        # Wait for idle timeout
        time.sleep(applier.idle_timeout + 0.1)
        
        # Should return False and stop running due to idle timeout
        result = applier.apply_pending_corrections()
        assert result is False, "Should return False after idle timeout"
        assert applier.running is False, "Should stop running after idle timeout"
        
        # Create new issue
        with open(test_file, "w") as f:
            f.write("""def test():
   pass  # 3 spaces
""")
        
        # Reset running state for testing
        applier.running = True
        applier.consecutive_no_corrections = 0
        applier.last_correction_time = time.time()
        
        # Should process new correction
        result = applier.apply_pending_corrections()
        assert result is False, "Should return False when no corrections are found"
        assert applier.running is True, "Should still be running after activity"
        
    finally:
        # Restore original timeout
        applier.idle_timeout = original_timeout

def test_correction_applier_log_throttling(config_manager: ConfigManager, temp_dir: str, requirements_file: Path):
    """Test that the correction applier properly throttles logging."""
    applier = CorrectionApplier(config_manager)
    
    # Create test file with issues
    test_file = Path(temp_dir) / "test.py"
    with open(test_file, "w") as f:
        f.write("""def test():
  pass  # 2 spaces
""")
    
    # First call should process and log
    first_log_time = time.time() - 1  # Ensure it's before the call
    result = applier.apply_pending_corrections()
    assert result is False, "Should return False when no corrections are found"
    assert applier.last_log_time > first_log_time, "Should update log time on first call"
    
    # Immediate second call should not log
    second_log_time = applier.last_log_time
    result = applier.apply_pending_corrections()
    assert result is False, "Should return False when in cooldown"
    assert applier.last_log_time == second_log_time, "Should not update log time during cooldown"
    
    # Wait for log cooldown
    time.sleep(applier.log_cooldown + 0.1)
    
    # Should log again after cooldown
    result = applier.apply_pending_corrections()
    assert result is False, "Should return False when no corrections are found"
    assert applier.last_log_time > second_log_time, "Should update log time after cooldown"

def test_review_coordinator_idle_shutdown(config_manager: ConfigManager, temp_dir: str):
    """Test that the review coordinator shuts down when idle."""
    coordinator = ReviewCoordinator(config_manager)
    
    # Temporarily reduce idle timeout for testing
    original_timeout = coordinator.idle_timeout
    coordinator.idle_timeout = 2  # 2 seconds for testing
    
    try:
        # Clear any existing monitored directories
        coordinator.monitored_dirs.clear()
        
        # Start monitoring in a separate thread
        import threading
        import queue
        
        shutdown_event = threading.Event()
        error_queue = queue.Queue()
        
        # Set the shutdown event in the coordinator
        coordinator.set_shutdown_event(shutdown_event)
        
        def run_coordinator():
            try:
                coordinator.start_monitoring(temp_dir)
            except Exception as e:
                error_queue.put(e)
        
        thread = threading.Thread(target=run_coordinator)
        thread.start()
        
        try:
            # Let it run for a bit
            time.sleep(1)
            
            # Create a file to trigger activity
            test_file = Path(temp_dir) / "test.py"
            with open(test_file, "w") as f:
                f.write("""def test():
  pass  # Bad indentation
""")
            
            # Wait for activity to be processed
            time.sleep(1)
            
            # Verify that the coordinator is still running
            assert coordinator.running is True, "Coordinator should still be running"
            
            # Wait for idle timeout
            time.sleep(coordinator.idle_timeout + 1)
            
            # Verify that the coordinator has stopped
            assert coordinator.running is False, "Coordinator should have stopped due to idle timeout"
            
            # Check for any errors
            assert error_queue.empty(), "No errors should have occurred"
            
        finally:
            # Ensure cleanup
            coordinator.stop_monitoring()
            thread.join(timeout=5)
            assert not thread.is_alive(), "Thread should have stopped"
            
    finally:
        # Restore original timeout
        coordinator.idle_timeout = original_timeout 
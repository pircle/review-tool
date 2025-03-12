"""Tests for the validator module."""

import os
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Generator

from ai_review.config_manager import ConfigManager
from ai_review.validator import ChangeValidator

@pytest.fixture(autouse=True)
def clear_logs():
    """Clear the validation log before each test."""
    log_file = Path("logs/validation_log.json")
    if log_file.exists():
        log_file.unlink()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "w") as f:
        json.dump({"validations": []}, f)
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

def test_validator_initialization(config_manager: ConfigManager):
    """Test ChangeValidator initialization."""
    validator = ChangeValidator(config_manager)
    assert validator.config_manager == config_manager
    assert validator.requirements_file == "docs/Kalkal_Requirements.md"
    assert isinstance(validator.validations, dict)
    assert "validations" in validator.validations

def test_load_requirements(config_manager: ConfigManager, requirements_file: Path):
    """Test loading requirements from file."""
    validator = ChangeValidator(config_manager)
    requirements = validator._load_requirements()
    
    assert len(requirements) == 6
    assert all(isinstance(req, dict) for req in requirements)
    assert all("section" in req and "requirement" in req for req in requirements)
    
    # Check sections
    sections = {req["section"] for req in requirements}
    assert sections == {"Code Style", "Features"}

def test_validate_change_no_requirements(config_manager: ConfigManager, temp_dir: str):
    """Test validating a change when no requirements file exists."""
    validator = ChangeValidator(config_manager)
    
    # Create test file
    test_file = Path(temp_dir) / "test.py"
    with open(test_file, "w") as f:
        f.write("def test():\n    pass\n")
    
    change = {
        "file_path": str(test_file),
        "event_type": "created"
    }
    
    result = validator.validate_change(change)
    assert result["valid"] is True
    assert len(result["missing_requirements"]) == 0
    assert "No requirements found" in result["notes"]

def test_validate_change_with_requirements(config_manager: ConfigManager, requirements_file: Path, temp_dir: str):
    """Test validating a change against requirements."""
    validator = ChangeValidator(config_manager)
    
    # Create test file with inconsistent indentation and no docstrings
    test_file = Path(temp_dir) / "test.py"
    with open(test_file, "w") as f:
        f.write("""def test():
  pass  # 2 spaces
    def inner():  # 4 spaces
   return True  # 3 spaces
""")
    
    change = {
        "file_path": str(test_file),
        "event_type": "created"
    }
    
    result = validator.validate_change(change)
    missing = [r.lower() for r in result["missing_requirements"]]
    
    # Print debug information
    print("\nMissing requirements:", missing)
    
    assert any("docstring" in r for r in missing), "Should detect missing docstrings"
    assert any("indentation" in r for r in missing), "Should detect inconsistent indentation"
    assert not result["valid"], "Should be invalid due to missing requirements"

def test_validate_multiple_changes(config_manager: ConfigManager, requirements_file: Path, temp_dir: str):
    """Test validating multiple changes."""
    validator = ChangeValidator(config_manager)
    
    # Create test files
    file1 = Path(temp_dir) / "test1.py"
    with open(file1, "w") as f:
        f.write("def test1(): pass\n")
    
    file2 = Path(temp_dir) / "test2.py"
    with open(file2, "w") as f:
        f.write('''"""Test module with docstring."""

def test2():
    """Test function."""
    pass
''')
    
    changes = [
        {"file_path": str(file1), "event_type": "created"},
        {"file_path": str(file2), "event_type": "created"}
    ]
    
    results = validator.validate_changes(changes)
    assert len(results) == 2
    assert not results[0]["valid"]  # No docstring
    assert any("docstring" in r.lower() for r in results[0]["missing_requirements"])
    assert len(results[1]["missing_requirements"]) < len(results[0]["missing_requirements"]) 
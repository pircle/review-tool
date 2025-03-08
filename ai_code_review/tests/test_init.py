import os
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
from ai_review.cli import init
from ai_review.config_manager import ConfigManager

@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def config_manager():
    """Get a fresh instance of ConfigManager."""
    return ConfigManager()

def test_init_command_basic(temp_project_dir):
    """Test basic project initialization."""
    runner = CliRunner()
    result = runner.invoke(init, [temp_project_dir, '--non-interactive'])
    
    assert result.exit_code == 0
    
    # Check if config file was created
    config_file = os.path.join(temp_project_dir, "config.json")
    assert os.path.exists(config_file)
    
    # Check if required directories were created
    assert os.path.exists(os.path.join(temp_project_dir, "logs"))
    assert os.path.exists(os.path.join(temp_project_dir, "reports"))
    
    # Verify config content
    with open(config_file) as f:
        config = json.load(f)
        assert "project" in config
        assert config["project"]["name"] == os.path.basename(temp_project_dir)
        assert config["project"]["path"] == temp_project_dir

def test_init_command_with_options(temp_project_dir):
    """Test project initialization with custom options."""
    runner = CliRunner()
    result = runner.invoke(init, [
        temp_project_dir,
        '--name', 'test-project',
        '--languages', 'python,java',
        '--exclude-dirs', 'temp/,cache/',
        '--standards', 'pep8,checkstyle',
        '--non-interactive'
    ])
    
    assert result.exit_code == 0
    
    # Verify config content
    config_file = os.path.join(temp_project_dir, "config.json")
    with open(config_file) as f:
        config = json.load(f)
        assert config["project"]["name"] == "test-project"
        assert "python" in config["project"]["languages"]
        assert "java" in config["project"]["languages"]
        assert "temp/" in config["file_filters"]["exclude_dirs"]
        assert "cache/" in config["file_filters"]["exclude_dirs"]
        assert "pep8" in config["project"]["standards"]
        assert "checkstyle" in config["project"]["standards"]

def test_init_command_interactive(temp_project_dir):
    """Test interactive project initialization."""
    runner = CliRunner()
    result = runner.invoke(init, [temp_project_dir], input="test-project\npython\ntemp/\n*.tmp\n\npep8\n")
    
    assert result.exit_code == 0
    
    # Verify config content
    config_file = os.path.join(temp_project_dir, "config.json")
    with open(config_file) as f:
        config = json.load(f)
        assert config["project"]["name"] == "test-project"
        assert "python" in config["project"]["languages"]
        assert "temp/" in config["file_filters"]["exclude_dirs"]
        assert "*.tmp" in config["file_filters"]["exclude_files"]
        assert "pep8" in config["project"]["standards"]

def test_init_command_existing_project(temp_project_dir, config_manager):
    """Test initialization of an existing project."""
    # First initialization
    runner = CliRunner()
    result = runner.invoke(init, [temp_project_dir, '--name', 'test-project', '--non-interactive'])
    assert result.exit_code == 0
    
    # Second initialization with confirmation
    result = runner.invoke(init, [temp_project_dir, '--name', 'test-project'], input="y\ntest-project-updated\npython\n\n\n\npep8\n")
    assert result.exit_code == 0
    
    # Verify updated config
    config_file = os.path.join(temp_project_dir, "config.json")
    with open(config_file) as f:
        config = json.load(f)
        assert config["project"]["name"] == "test-project-updated"

def test_init_command_validation(temp_project_dir):
    """Test input validation during initialization."""
    # Test with invalid path
    runner = CliRunner()
    result = runner.invoke(init, ["/nonexistent/path"])
    assert result.exit_code != 0
    
    # Test with invalid languages
    result = runner.invoke(init, [
        temp_project_dir,
        '--languages', '',
        '--non-interactive'
    ])
    assert result.exit_code == 0  # Should succeed with empty languages
    
    # Test with invalid exclude patterns
    result = runner.invoke(init, [
        temp_project_dir,
        '--exclude-dirs', '   ,,,   ',
        '--non-interactive'
    ])
    assert result.exit_code == 0  # Should succeed and ignore empty patterns
    
    # Verify config was created with defaults
    config_file = os.path.join(temp_project_dir, "config.json")
    with open(config_file) as f:
        config = json.load(f)
        assert isinstance(config["project"]["languages"], list)
        assert isinstance(config["file_filters"]["exclude_dirs"], list) 
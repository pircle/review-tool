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

class TestInitCommand:
    """Test suite for the init command."""
    
    def test_basic_initialization(self, temp_project_dir):
        """Test basic project initialization with default values."""
        runner = CliRunner()
        result = runner.invoke(init, [temp_project_dir, '--non-interactive'])
        
        assert result.exit_code == 0
        assert "Created and configured project" in result.output
        
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
            assert isinstance(config["project"]["languages"], list)
            assert isinstance(config["project"]["standards"], list)
    
    def test_custom_options(self, temp_project_dir):
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
        assert "Created and configured project 'test-project'" in result.output
        
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
    
    def test_interactive_mode(self, temp_project_dir):
        """Test interactive project initialization."""
        runner = CliRunner()
        result = runner.invoke(init, [temp_project_dir], input="\n".join([
            "test-project",  # project name
            "python,typescript",  # languages
            "temp/,logs/",  # exclude dirs
            "*.tmp,*.log",  # exclude files
            "src/,app/",  # include dirs
            "pep8,eslint"  # standards
        ]))
        
        assert result.exit_code == 0
        assert "Created and configured project 'test-project'" in result.output
        
        # Verify config content
        config_file = os.path.join(temp_project_dir, "config.json")
        with open(config_file) as f:
            config = json.load(f)
            assert config["project"]["name"] == "test-project"
            assert set(config["project"]["languages"]) == {"python", "typescript"}
            assert "temp/" in config["file_filters"]["exclude_dirs"]
            assert "logs/" in config["file_filters"]["exclude_dirs"]
            assert "*.tmp" in config["file_filters"]["exclude_files"]
            assert "*.log" in config["file_filters"]["exclude_files"]
            assert set(config["file_filters"]["include_dirs"]) == {"src/", "app/"}
            assert set(config["project"]["standards"]) == {"pep8", "eslint"}
    
    def test_project_update(self, temp_project_dir, config_manager):
        """Test updating an existing project configuration."""
        # First initialization
        runner = CliRunner()
        result = runner.invoke(init, [
            temp_project_dir,
            '--name', 'test-project',
            '--languages', 'python',
            '--non-interactive'
        ])
        assert result.exit_code == 0
        
        # Update configuration
        result = runner.invoke(init, [temp_project_dir], input="\n".join([
            "y",  # confirm update
            "test-project",  # keep same name
            "python,java",  # add java
            "",  # no new exclude dirs
            "",  # no new exclude files
            "",  # keep default include dirs
            "pep8,checkstyle"  # add checkstyle
        ]))
        
        assert result.exit_code == 0
        assert "Updated configuration for project 'test-project'" in result.output
        
        # Verify updated config
        config_file = os.path.join(temp_project_dir, "config.json")
        with open(config_file) as f:
            config = json.load(f)
            assert config["project"]["name"] == "test-project"
            assert set(config["project"]["languages"]) == {"python", "java"}
            assert set(config["project"]["standards"]) == {"pep8", "checkstyle"}
    
    def test_input_validation(self, temp_project_dir):
        """Test input validation during initialization."""
        # Test with invalid path
        runner = CliRunner()
        result = runner.invoke(init, ["/nonexistent/path"])
        assert result.exit_code != 0
        assert "Error" in result.output
        
        # Test with empty values in non-interactive mode
        result = runner.invoke(init, [
            temp_project_dir,
            '--languages', '',
            '--exclude-dirs', '   ,,,   ',
            '--non-interactive'
        ])
        assert result.exit_code == 0  # Should succeed with defaults
        
        # Verify config was created with defaults
        config_file = os.path.join(temp_project_dir, "config.json")
        with open(config_file) as f:
            config = json.load(f)
            assert isinstance(config["project"]["languages"], list)
            assert isinstance(config["file_filters"]["exclude_dirs"], list)
            assert len(config["file_filters"]["exclude_dirs"]) >= len(ConfigManager.DEFAULT_CONFIG["file_filters"]["exclude_dirs"])
    
    def test_multiple_projects(self, temp_project_dir):
        """Test handling multiple projects."""
        # Create first project
        runner = CliRunner()
        result = runner.invoke(init, [
            temp_project_dir,
            '--name', 'project1',
            '--languages', 'python',
            '--non-interactive'
        ])
        assert result.exit_code == 0
        
        # Create second project in a subdirectory
        project2_dir = os.path.join(temp_project_dir, "project2")
        os.makedirs(project2_dir)
        result = runner.invoke(init, [
            project2_dir,
            '--name', 'project2',
            '--languages', 'javascript',
            '--non-interactive'
        ])
        assert result.exit_code == 0
        
        # Verify both projects have their own configs
        for project_name, project_dir in [('project1', temp_project_dir), ('project2', project2_dir)]:
            config_file = os.path.join(project_dir, "config.json")
            assert os.path.exists(config_file)
            with open(config_file) as f:
                config = json.load(f)
                assert config["project"]["name"] == project_name
                assert config["project"]["path"] == project_dir 
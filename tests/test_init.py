import os
import json
import pytest
import sys
from click.testing import CliRunner
from ai_review.cli import cli
from ai_review.config_manager import ConfigManager
from pathlib import Path
import logging

@pytest.fixture
def fs(tmp_path):
    """Create a temporary filesystem for testing."""
    return str(tmp_path)

@pytest.fixture
def fs_abs(tmp_path):
    """Create a temporary filesystem for testing with absolute path."""
    return os.path.abspath(str(tmp_path))

@pytest.fixture
def config_manager(fs):
    """Create a ConfigManager instance for testing."""
    from ai_review.config_manager import config_manager
    # Set config directory to temporary path
    config_manager.config_dir = Path(fs) / ".ai-code-review"
    # Reset state
    config_manager.current_project = None
    config_manager.project_config_file = None
    config_manager.projects = {"projects": []}
    # Reset config file on disk
    with open(config_manager.projects_file, 'w') as f:
        json.dump({"projects": []}, f, indent=2)
    # Ensure stdout is flushed after config operations
    sys.stdout.flush()
    return config_manager

@pytest.fixture
def cli_runner(tmp_path):
    """Create a CLI runner with an isolated filesystem.
    
    Args:
        tmp_path: Temporary directory path provided by pytest
        
    Yields:
        CliRunner: Click CLI test runner
    """
    runner = CliRunner(mix_stderr=False)
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs:
        # Create necessary log files
        logs_dir = Path(fs) / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize log files with empty data
        (logs_dir / "correction_status.json").write_text('{"corrections": []}')
        (logs_dir / "cursor_corrections.json").write_text('{"corrections": []}')
        (logs_dir / "review_log.json").write_text('{"changes": []}')
        (logs_dir / "review_coordinator.log").touch()
        (logs_dir / "correction_applier.log").touch()
        
        # Create default config directory
        config_dir = Path(fs) / ".ai-code-review"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure all file handles are closed before yielding
        sys.stdout.flush()
        sys.stderr.flush()
        
        try:
            yield runner
        finally:
            # Close any open file handles
            for handler in logging.getLogger().handlers:
                handler.close()
            # Flush stdout and stderr again
            sys.stdout.flush()
            sys.stderr.flush()
            # Close any open file descriptors
            for fd in range(3, 100):  # Skip stdin, stdout, stderr
                try:
                    os.close(fd)
                except OSError:
                    pass

def test_basic_initialization(fs_abs, config_manager, cli_runner):
    """Test basic project initialization."""
    result = cli_runner.invoke(cli, ['init', fs_abs, '--non-interactive'])  # Non-interactive mode
    
    # Debug output
    print(f"Exit code: {result.exit_code}")
    print(f"Output: {result.output}")
    if result.exception:
        print(f"Exception: {result.exception}")
    
    # Check command executed successfully
    assert result.exit_code == 0, f"Command failed with exit code {result.exit_code}"
    
    # Get project name from fs_abs
    project_name = os.path.basename(fs_abs)
    
    # Check that project was created and set as current
    assert config_manager.current_project == project_name, "Project not set as current"
    assert config_manager.project_config_file is not None, "Project config file not set"
    
    # Check config file exists
    config_path = config_manager.project_config_file
    assert os.path.exists(config_path), f"Config file not found at {config_path}"
    
    # Check config file contents
    with open(config_path) as f:
        config = json.load(f)
    
    # Verify project name and path are set
    assert config.get('project_name') == project_name
    assert config.get('project_path') == fs_abs
    
    # Verify required keys exist
    required_keys = ['monitored_extensions', 'ignored_directories', 'ignored_files']
    for key in required_keys:
        assert key in config, f"Missing required key: {key}"

def test_custom_options(fs_abs, config_manager, cli_runner):
    """Test project initialization with custom options."""
    with cli_runner.isolation():  # Ensure proper isolation context
        try:
            # Run command with debug output
            result = cli_runner.invoke(cli, [
                'init', fs_abs,
                '--name', 'test_project',
                '--languages', 'python,javascript',
                '--exclude-dirs', 'node_modules,venv',
                '--exclude-files', '*.pyc,*.pyo',
                '--include-dirs', 'src,tests',
                '--standards', 'pep8,eslint',
                '--non-interactive'
            ], catch_exceptions=False)
            print(f"\nDebug - Exit code: {result.exit_code}")
            print(f"Debug - Output: {result.output}")
            if result.exception:
                print(f"Debug - Exception: {result.exception}")
                raise result.exception
            
            # Ensure stdout is flushed
            sys.stdout.flush()
            
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            config_path = os.path.join(fs_abs, 'config.json')
            assert os.path.exists(config_path), f"Config file not found at {config_path}"
            
            with open(config_path, 'r') as f:
                config = json.load(f)
                assert config['project']['name'] == 'test_project'
                assert config['project']['path'] == fs_abs
                assert config['project']['languages'] == ['python', 'javascript']
                assert 'node_modules' in config['file_filters']['exclude_dirs']
                assert 'venv' in config['file_filters']['exclude_dirs']
                assert '*.pyc' in config['file_filters']['exclude_files']
                assert '*.pyo' in config['file_filters']['exclude_files']
                assert 'src' in config['file_filters']['include_dirs']
                assert 'tests' in config['file_filters']['include_dirs']
                assert config['project']['standards'] == ['pep8', 'eslint']
        finally:
            # Ensure all file handles are closed
            sys.stdout.flush()
            sys.stderr.flush()

def test_interactive_mode(fs_abs, config_manager, cli_runner):
    """Test project initialization in interactive mode."""
    with cli_runner.isolation():  # Ensure proper isolation context
        try:
            input_data = '\n'.join([
                'test_project',
                'python,javascript',
                'node_modules,venv',
                '*.pyc,*.pyo',
                'src,tests',
                'pep8,eslint'
            ]) + '\n'
            
            # Run command with debug output
            result = cli_runner.invoke(cli, ['init', fs_abs], input=input_data, catch_exceptions=False)
            print(f"\nDebug - Exit code: {result.exit_code}")
            print(f"Debug - Output: {result.output}")
            if result.exception:
                print(f"Debug - Exception: {result.exception}")
                raise result.exception
            
            # Ensure stdout is flushed
            sys.stdout.flush()
            
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            config_path = os.path.join(fs_abs, 'config.json')
            assert os.path.exists(config_path), f"Config file not found at {config_path}"
            
            with open(config_path, 'r') as f:
                config = json.load(f)
                assert config['project']['name'] == 'test_project'
                assert config['project']['path'] == fs_abs
                assert config['project']['languages'] == ['python', 'javascript']
                assert 'node_modules' in config['file_filters']['exclude_dirs']
                assert 'venv' in config['file_filters']['exclude_dirs']
                assert '*.pyc' in config['file_filters']['exclude_files']
                assert '*.pyo' in config['file_filters']['exclude_files']
                assert 'src' in config['file_filters']['include_dirs']
                assert 'tests' in config['file_filters']['include_dirs']
                assert config['project']['standards'] == ['pep8', 'eslint']
        finally:
            # Ensure all file handles are closed
            sys.stdout.flush()
            sys.stderr.flush()

def test_project_update(fs_abs, config_manager, cli_runner):
    """Test updating an existing project."""
    with cli_runner.isolation():  # Ensure proper isolation context
        try:
            # First create a project
            result = cli_runner.invoke(cli, ['init', fs_abs, '--non-interactive'], catch_exceptions=False)
            assert result.exit_code == 0, f"Initial project creation failed: {result.output}"
            
            # Then update it
            result = cli_runner.invoke(cli, [
                'init', fs_abs,
                '--languages', 'python,typescript',
                '--standards', 'pylint,tslint',
                '--non-interactive'
            ], catch_exceptions=False)
            print(f"\nDebug - Update exit code: {result.exit_code}")
            print(f"Debug - Update output: {result.output}")
            if result.exception:
                print(f"Debug - Update exception: {result.exception}")
                raise result.exception
            
            # Ensure stdout is flushed
            sys.stdout.flush()
            
            assert result.exit_code == 0, f"Project update failed: {result.output}"
            config_path = os.path.join(fs_abs, 'config.json')
            assert os.path.exists(config_path), f"Config file not found at {config_path}"
            
            with open(config_path, 'r') as f:
                config = json.load(f)
                assert config['project']['languages'] == ['python', 'typescript']
                assert config['project']['standards'] == ['pylint', 'tslint']
        finally:
            # Ensure all file handles are closed
            sys.stdout.flush()
            sys.stderr.flush()

def test_multiple_projects(fs_abs, config_manager, cli_runner):
    """Test creating multiple projects."""
    with cli_runner.isolation():  # Ensure proper isolation context
        try:
            # Create first project
            project1_dir = os.path.join(fs_abs, 'project1')
            os.makedirs(project1_dir)
            result = cli_runner.invoke(cli, ['init', project1_dir, '--non-interactive'], catch_exceptions=False)
            assert result.exit_code == 0, f"First project creation failed: {result.output}"
            
            # Create second project
            project2_dir = os.path.join(fs_abs, 'project2')
            os.makedirs(project2_dir)
            result = cli_runner.invoke(cli, ['init', project2_dir, '--non-interactive'], catch_exceptions=False)
            assert result.exit_code == 0, f"Second project creation failed: {result.output}"
            
            # Verify both projects exist
            assert os.path.exists(os.path.join(project1_dir, 'config.json'))
            assert os.path.exists(os.path.join(project2_dir, 'config.json'))
            
            # Verify project configurations
            with open(os.path.join(project1_dir, 'config.json'), 'r') as f:
                config1 = json.load(f)
                assert config1['project']['path'] == project1_dir
            
            with open(os.path.join(project2_dir, 'config.json'), 'r') as f:
                config2 = json.load(f)
                assert config2['project']['path'] == project2_dir
        finally:
            # Ensure all file handles are closed
            sys.stdout.flush()
            sys.stderr.flush()

def test_project_update_cancel(fs_abs, config_manager, cli_runner):
    """Test cancelling project update."""
    with cli_runner.isolation():  # Ensure proper isolation context
        try:
            # First create a project
            result = cli_runner.invoke(cli, ['init', fs_abs, '--non-interactive'], catch_exceptions=False)
            assert result.exit_code == 0, f"Initial project creation failed: {result.output}"
            
            # Try to update it but cancel
            result = cli_runner.invoke(cli, ['init', fs_abs], input='n\n', catch_exceptions=False)
            print(f"\nDebug - Cancel exit code: {result.exit_code}")
            print(f"Debug - Cancel output: {result.output}")
            if result.exception:
                print(f"Debug - Cancel exception: {result.exception}")
                raise result.exception
            
            # Ensure stdout is flushed
            sys.stdout.flush()
            
            assert result.exit_code == 0, f"Project update cancellation failed: {result.output}"
            config_path = os.path.join(fs_abs, 'config.json')
            assert os.path.exists(config_path), f"Config file not found at {config_path}"
            
            with open(config_path, 'r') as f:
                config = json.load(f)
                assert config['project']['languages'] == ['python', 'javascript', 'typescript']
                assert config['project']['standards'] == ['pep8', 'eslint']
        finally:
            # Ensure all file handles are closed
            sys.stdout.flush()
            sys.stderr.flush()

def test_review_settings(fs_abs, config_manager, cli_runner):
    """Test review settings in project configuration."""
    with cli_runner.isolation():  # Ensure proper isolation context
        try:
            result = cli_runner.invoke(cli, ['init', fs_abs, '--non-interactive'], catch_exceptions=False)
            print(f"\nDebug - Review settings exit code: {result.exit_code}")
            print(f"Debug - Review settings output: {result.output}")
            if result.exception:
                print(f"Debug - Review settings exception: {result.exception}")
                raise result.exception
            
            # Ensure stdout is flushed
            sys.stdout.flush()
            
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            config_path = os.path.join(fs_abs, 'config.json')
            assert os.path.exists(config_path), f"Config file not found at {config_path}"
            
            with open(config_path, 'r') as f:
                config = json.load(f)
                assert 'review_settings' in config['project']
                assert config['project']['review_settings']['max_line_length'] == 100
                assert config['project']['review_settings']['max_function_length'] == 50
                assert config['project']['review_settings']['max_complexity'] == 10
                assert config['project']['review_settings']['enforce_docstrings'] is True
                assert config['project']['review_settings']['enforce_type_hints'] is True
        finally:
            # Ensure all file handles are closed
            sys.stdout.flush()
            sys.stderr.flush()

def test_project_logs_creation(fs_abs, config_manager, cli_runner):
    """Test creation of project logs directory."""
    with cli_runner.isolation():  # Ensure proper isolation context
        try:
            result = cli_runner.invoke(cli, ['init', fs_abs, '--non-interactive'], catch_exceptions=False)
            print(f"\nDebug - Logs creation exit code: {result.exit_code}")
            print(f"Debug - Logs creation output: {result.output}")
            if result.exception:
                print(f"Debug - Logs creation exception: {result.exception}")
                raise result.exception
            
            # Ensure stdout is flushed
            sys.stdout.flush()
            
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            logs_dir = os.path.join(fs_abs, 'logs')
            assert os.path.exists(logs_dir), f"Logs directory not found at {logs_dir}"
            assert os.path.isdir(logs_dir), f"Logs path exists but is not a directory: {logs_dir}"
        finally:
            # Ensure all file handles are closed
            sys.stdout.flush()
            sys.stderr.flush()

def test_project_reports_creation(fs_abs, config_manager, cli_runner):
    """Test creation of project reports directory."""
    with cli_runner.isolation():  # Ensure proper isolation context
        try:
            result = cli_runner.invoke(cli, ['init', fs_abs, '--non-interactive'], catch_exceptions=False)
            print(f"\nDebug - Reports creation exit code: {result.exit_code}")
            print(f"Debug - Reports creation output: {result.output}")
            if result.exception:
                print(f"Debug - Reports creation exception: {result.exception}")
                raise result.exception
            
            # Ensure stdout is flushed
            sys.stdout.flush()
            
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            reports_dir = os.path.join(fs_abs, 'reports')
            assert os.path.exists(reports_dir), f"Reports directory not found at {reports_dir}"
            assert os.path.isdir(reports_dir), f"Reports path exists but is not a directory: {reports_dir}"
        finally:
            # Ensure all file handles are closed
            sys.stdout.flush()
            sys.stderr.flush() 
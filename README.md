# AI Code Review Tool

A powerful tool for automated code review and analysis using AI.

## Installation

```bash
pip install ai-code-review
```

## Quick Start

1. Initialize a new project:
```bash
python -m ai_review.cli init /path/to/your/project
```

2. Run a code review:
```bash
python -m ai_review.cli review /path/to/your/project
```

## Project Initialization

The `init` command helps you set up a new project for code review. It creates a project-specific configuration and necessary directories.

### Basic Usage

```bash
python -m ai_review.cli init /path/to/your/project
```

### Options

- `--name, -n`: Project name (defaults to directory name)
- `--languages, -l`: Comma-separated list of programming languages
- `--exclude-dirs`: Additional directories to exclude (comma-separated)
- `--exclude-files`: Additional file patterns to exclude (comma-separated)
- `--include-dirs`: Directories to include (comma-separated, overrides defaults)
- `--standards`: Code review standards to follow (comma-separated)
- `--non-interactive`: Run in non-interactive mode

### Interactive Mode

By default, the init command runs in interactive mode and will prompt you for:

1. Project name
2. Programming languages used
3. Directories to exclude from analysis
4. File patterns to exclude
5. Directories to include in analysis
6. Code review standards to follow

Example:
```bash
$ python -m ai_review.cli init /path/to/project
Project name [project]: my-awesome-project
Programming languages (comma-separated) [python,javascript,typescript]: python,java
Additional directories to exclude (comma-separated) []: temp/,logs/
Additional file patterns to exclude (comma-separated) []: *.tmp,*.log
Directories to include (comma-separated, leave empty for defaults) []: src/,app/
Code review standards to follow (comma-separated) [pep8,eslint]: pep8,checkstyle
✅ Created and configured project 'my-awesome-project'
```

### Non-Interactive Mode

For automation or CI/CD pipelines, use the `--non-interactive` flag with required options:

```bash
python -m ai_review.cli init /path/to/project \
  --name my-project \
  --languages python,java \
  --exclude-dirs temp/,cache/ \
  --standards pep8,checkstyle \
  --non-interactive
```

### Configuration

The init command creates:

1. A project-specific `config.json` file in your project directory
2. Required directories:
   - `logs/`: For log files
   - `reports/`: For analysis reports

Example `config.json`:
```json
{
  "project": {
    "name": "my-project",
    "path": "/path/to/project",
    "languages": ["python", "java"],
    "standards": ["pep8", "checkstyle"]
  },
  "file_filters": {
    "exclude_dirs": [
      "node_modules/",
      ".git/",
      "temp/",
      "cache/"
    ],
    "include_dirs": [
      "src/",
      "app/"
    ],
    "exclude_files": [
      "*.min.js",
      "*.tmp",
      "*.log"
    ]
  }
}
```

### Multiple Projects

The tool supports multiple projects by:
1. Storing project-specific configurations in each project's directory
2. Maintaining a global list of projects in `~/.ai-code-review/projects.json`
3. Using project-specific settings during analysis

To list all projects:
```bash
python -m ai_review.cli review --list-projects
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

MIT 
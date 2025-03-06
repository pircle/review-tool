# AI Code Review Tool

A command-line tool for analyzing code complexity and generating AI-powered code reviews.

## Features

- **Code Analysis**: Analyzes code complexity, identifies complex functions, and provides metrics.
- **AI-Powered Code Review**: Leverages OpenAI's models to provide intelligent code suggestions and improvements.
- **Automatic Fix Application**: Automatically applies AI-suggested fixes to your code with a backup system.
- **Security Scanning**: Detects common security vulnerabilities in your code.
- **Dependency Scanning**: Identifies vulnerable dependencies in your project.
- **Unified Report Generation**: Creates comprehensive reports combining all analysis results in JSON or Markdown format.
- **Multi-Language Support**: Works with Python, JavaScript, TypeScript, and more.
- **Plugin System**: Extensible architecture allowing custom analyzers and integrations.
- **Robust Logging and Error Handling**: Comprehensive logging system for debugging and error tracking.
- **UI Validation with ChatGPT Vision**: Automated screenshot capturing and AI-powered UI validation.

## Automated Security Scanning

This tool can automatically detect common security vulnerabilities in your code:

- **Hardcoded Credentials**: API keys, passwords, and secrets embedded in code
- **SQL Injection**: Unparameterized SQL queries that could be exploited
- **Cross-Site Scripting (XSS)**: Vulnerabilities in JavaScript/TypeScript code
- **Insecure Cryptography**: Usage of weak cryptographic algorithms
- **Path Traversal**: Unsafe file path handling
- **Command Injection**: Unsafe command execution

Run a security scan:

```bash
ai-review review path/to/file.py --security-scan
```

You can combine security scanning with AI-powered code review:

```bash
ai-review review path/to/file.py --security-scan --ai --api-key "your-openai-api-key"
```

Example of security scan output:

```
========================================================================
🔒 SECURITY SCAN RESULTS
========================================================================

⚠️  Found 3 potential security issues:
   🔴 High severity: 2
   🟠 Medium severity: 1
   🟡 Low severity: 0

Detailed Issues:

  🔑 HARDCODED CREDENTIALS:
    1. Hardcoded credential detected 🔴
       Line: 12
       Detail: Hardcoded API key found: 1234****6789
       Recommendation: Store sensitive information in environment variables or a secure vault

  💉 SQL INJECTION:
    1. Potential SQL Injection vulnerability 🔴
       Line: 45
       Detail: String concatenation in SQL query detected
       Recommendation: Use parameterized queries or prepared statements instead of string concatenation

  🔐 INSECURE CRYPTOGRAPHY:
    1. Insecure cryptographic algorithm 🟠
       Line: 78
       Detail: Usage of MD5 hashing algorithm
       Recommendation: Replace MD5 with a more secure algorithm (e.g., SHA-256, AES)
========================================================================
```

## Dependency Vulnerability Scanning

This tool can analyze dependencies for known security vulnerabilities using:
- `safety` for Python (`requirements.txt`, `Pipfile`, `pyproject.toml`, `setup.py`)
- `npm audit` for JavaScript/TypeScript (`package.json`)

Run a dependency scan:

```bash
ai-review review path/to/project --dependency-scan
```

You can combine dependency scanning with other features:

```bash
ai-review review path/to/project --dependency-scan --security-scan --ai --api-key "your-openai-api-key"
```

Example of dependency scan output:

```
========================================================================
📦 DEPENDENCY VULNERABILITY SCAN RESULTS
========================================================================

⚠️  Found 4 potential vulnerabilities in dependencies:
   🔴 High severity: 1
   🟠 Medium severity: 2
   🟡 Low severity: 1

Detailed Issues:

  🐍 PYTHON DEPENDENCIES:
    1. django (2.2.0) 🔴
       Description: Cross-site scripting (XSS) vulnerability in Django admin's display of list_filter parameters
       Fix: Update to version 2.2.28 or later

    2. requests (2.25.0) 🟠
       Description: CRLF injection vulnerability in requests
       Fix: Update to version 2.25.1 or later

  🟨 JAVASCRIPT/TYPESCRIPT DEPENDENCIES:
    1. lodash 🔴
       Title: Prototype Pollution in lodash
       Fix: Update to version 4.17.21 or later
       More info: https://github.com/advisories/GHSA-35jh-r3h4-6jhm

    2. axios 🟡
       Title: Server-Side Request Forgery in axios
       Fix: Update to version 0.21.1 or later
       More info: https://github.com/advisories/GHSA-42xw-2xvc-qx8m
========================================================================
```

### Prerequisites

To use the dependency scanning feature, you need to install:

1. For Python dependencies:
   ```bash
   pip install safety
   ```

2. For JavaScript/TypeScript dependencies:
   - Node.js and npm must be installed on your system
   - Run the scan from the directory containing `package.json`

## Installation

```bash
pip install ai-code-review
```

Or clone the repository and install locally:

```bash
git clone https://github.com/yourusername/ai-code-review.git
cd ai-code-review
pip install -e .
```

## Usage

### Basic Analysis

```bash
ai-review review path/to/file.py
```

### AI-Powered Code Review

```bash
ai-review review path/to/file.py --ai --api-key "your-openai-api-key"
```

### Apply AI Suggestions

```bash
ai-review review path/to/file.py --ai --apply-fixes --api-key "your-openai-api-key"
```

### Multi-Language Support

The tool supports the following programming languages:

- Python (.py)
- JavaScript (.js)
- TypeScript (.ts, .tsx)

The system automatically detects the file type based on the extension and uses the appropriate analyzer. Each language analyzer extracts functions, methods, classes, interfaces, and complexity metrics.

Example for JavaScript:

```bash
ai-review review path/to/file.js --ai --api-key "your-openai-api-key"
```

Example for TypeScript:

```bash
ai-review review path/to/file.ts --ai --api-key "your-openai-api-key"
```

### Debugging and Logging

The tool includes a comprehensive logging system to help with debugging and error tracking. You can enable debug mode to get detailed logs:

```bash
ai-review review path/to/file.py --debug
```

Log files are stored in the following location:
- Linux/macOS: `~/.ai-code-review/logs/`
- Windows: `C:\Users\<username>\.ai-code-review\logs\`

Common log files:
- `ai_review.log`: Main application log
- `error.log`: Error-specific log

#### Troubleshooting Common Issues

1. **API Key Issues**: If you encounter API key errors, ensure your OpenAI API key is valid and has sufficient credits.

2. **File Access Errors**: Make sure the tool has read/write permissions for the files you're analyzing.

3. **Language Support**: If a file isn't being analyzed correctly, check that its extension is supported (.py, .js, .ts, .tsx).

4. **Memory Issues**: For very large files or directories, you might need to increase available memory or analyze files individually.

### Interaction Logging

The tool now includes an interaction logging system that tracks all human interactions with the AI Code Review Tool. This helps maintain a record of commands, approvals, rejections, and modifications made during code reviews.

Interaction logs are stored in the following location:
- Linux/macOS: `~/.ai-code-review/logs/interactions.log`
- Windows: `C:\Users\<username>\.ai-code-review\logs\interactions.log`

The interaction log captures:
- **Commands**: All commands executed with the tool, including parameters and options
- **Approvals**: When AI-suggested fixes are applied successfully
- **Rejections**: When AI-suggested fixes are rejected or fail to apply
- **Modifications**: When users modify AI suggestions before applying them

Example of interaction log entries:

```
[2023-03-06 14:30:22] COMMAND: review - Reviewing code at path: src/auth.py
[2023-03-06 14:31:05] APPROVAL: Applied fix to src/auth.py - Fixed insecure password storage
[2023-03-06 14:32:18] REJECTION: Failed to apply fix to src/database.py - Syntax error in suggested code
[2023-03-06 14:33:45] MODIFICATION: Modified suggestion for src/utils.py - Adjusted error handling logic
```

This logging system helps teams track changes, understand decision patterns, and maintain an audit trail of AI-assisted code modifications.

## Configuration

Create a configuration file at `~/.ai-code-review/config.json` to set default options, or use the `config init` command to generate a default configuration file:

```bash
# Generate global config file
ai-code-review config init

# Generate local config file (in current directory)
ai-code-review config init --local
```

Example configuration:

```json
{
  "openai_api_key": "your-api-key",
  "model": "gpt-4o",
  "complexity_threshold": 5,
  "log_level": "INFO",
  "file_filters": {
    "exclude_dirs": [
      "node_modules/",
      ".git/",
      "__pycache__/",
      "venv/",
      "env/",
      ".venv/",
      "dist/",
      "build/",
      ".next/",
      "out/",
      "coverage/"
    ],
    "include_dirs": [
      "src/",
      "app/",
      "backend/",
      "frontend/",
      "lib/",
      "utils/",
      "components/",
      "services/",
      "api/",
      "tests/"
    ],
    "exclude_files": [
      "*.min.js",
      "*.bundle.js",
      "*.map",
      "*.lock",
      "package-lock.json",
      "yarn.lock"
    ]
  }
}
```

### Configuration Commands

You can manage your configuration using the following commands:

```bash
# List all configuration settings
ai-code-review config list

# Get a specific configuration value
ai-code-review config get openai_api_key
ai-code-review config get file_filters.exclude_dirs

# Set a configuration value
ai-code-review config set openai_api_key "your-new-api-key"
ai-code-review config set file_filters.exclude_dirs '["node_modules/", ".git/", "build/"]'

# Use local configuration (in current directory)
ai-code-review config list --local
ai-code-review config set log_level "DEBUG" --local
```

### File Filtering

The tool now supports intelligent file filtering to focus on relevant source code:

- **exclude_dirs**: Directories to exclude from analysis (e.g., `node_modules/`, `.git/`)
- **include_dirs**: Directories to include in analysis (e.g., `src/`, `app/`)
- **exclude_files**: File patterns to exclude (e.g., `*.min.js`, `*.lock`)

If `include_dirs` is specified, only files within those directories will be analyzed (plus files in the root directory). This helps focus the analysis on your actual source code.

## AI-Powered Code Review Enhancements

The AI review system now provides:

- **Structured JSON Output**: All AI-generated reviews are formatted as structured JSON, making it easier to parse and integrate with other tools.
- **Detailed Issue Categorization**: Issues are categorized as security, performance, readability, maintainability, or bugs, allowing for better prioritization.
- **Severity Levels**: Each suggestion includes a severity level (high, medium, low) to help prioritize fixes.
- **Actionable Improvements**: Specific, actionable code snippets are provided for each suggestion.
- **Refactored Code Examples**: For complex functions, complete refactored versions are suggested.

Example of the enhanced CLI output:

```
========================================================================
🔍 AI-POWERED CODE REVIEW
========================================================================

📝 Summary: This code implements a user authentication system with password hashing and session management.

⭐ Overall Quality: 7/10

🛠️  Suggestions:

  🔒 SECURITY:
    1. Insecure Password Storage ❗❗
       Location: authenticate_user (line 45)
       Description: Passwords are being stored in plaintext, which is a serious security risk.
       Improvement: Use bcrypt or Argon2 for password hashing.

  ⚡ PERFORMANCE:
    1. Inefficient Database Query ❗
       Location: get_user_by_id (line 78)
       Description: The function loads all user data before filtering.
       Improvement: Use a direct query with WHERE clause instead.

📚 Best Practices:
  1. Add type hints to function parameters
  2. Use context managers for file operations
  3. Implement proper error handling for database operations

🐛 Potential Bugs:
  1. The session token is not checked for expiration
  2. No validation for user input which could lead to SQL injection
========================================================================
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Command Line Options

- `path`: Path to file or directory to review
- `--output, -o`: Output file path for results
- `--complexity-threshold, -c`: Complexity threshold for flagging functions (default: 5)
- `--ai, -a`: Enable AI-powered code review
- `--api-key, -k`: OpenAI API key (can also use OPENAI_API_KEY env var)
- `--model, -m`: OpenAI model to use (default: gpt-4o)
- `--apply-fixes, -f`: Automatically apply AI-suggested fixes
- `--security-scan, -s`: Perform security vulnerability scan
- `--dependency-scan, -d`: Scan dependencies for vulnerabilities
- `--generate-report, -r`: Generate a unified report of all analyses
- `--report-format`: Format for the generated report (choices: json, markdown, default: json)
- `--ui-validate, -u`: Validate UI changes using screenshots and ChatGPT Vision
- `--url`: URL of the web app for UI validation
- `--debug`: Enable debug mode with verbose logging

## Generating Unified Reports

The AI Code Review Tool can generate comprehensive reports that combine results from all analysis types:

```bash
python -m ai_review review path/to/code.py --ai --security-scan --dependency-scan --generate-report --report-format markdown --api-key YOUR_OPENAI_KEY
```

This command will:
1. Analyze the code for complexity and structure
2. Generate AI-powered code suggestions
3. Scan for security vulnerabilities
4. Check dependencies for known vulnerabilities
5. Combine all results into a unified report

### Report Formats

Reports can be generated in two formats:

- **JSON**: Machine-readable format, ideal for integration with other tools
- **Markdown**: Human-readable format with formatted tables and sections

### Report Sections

The unified report includes:

- **Code Analysis**: Metrics, complex functions, and class information
- **AI Code Review**: Suggestions and improvements from the AI model
- **Security Scan**: Detected security vulnerabilities and their severity
- **Dependency Scan**: Vulnerable dependencies and recommended fixes
- **Summary**: Overview of all issues found across all analysis types

### Saving Reports

Reports can be saved to a file by specifying the `--output` option:

```bash
python -m ai_review review path/to/code.py --generate-report --report-format markdown --output report.md
```

This will save the report to `report_report.md` (the tool appends `_report` and the appropriate extension to the output filename).

## Example Usage

```bash
# Basic code analysis
python -m ai_review review path/to/code.py

# AI-powered code review
python -m ai_review review path/to/code.py --ai --api-key YOUR_OPENAI_KEY

# Automatically apply AI-suggested fixes
python -m ai_review review path/to/code.py --ai --apply-fixes --api-key YOUR_OPENAI_KEY

# Security vulnerability scanning
python -m ai_review review path/to/code.py --security-scan

# Dependency vulnerability scanning
python -m ai_review review path/to/code.py --dependency-scan

# Generate a unified report in Markdown format
python -m ai_review review path/to/code.py --ai --security-scan --dependency-scan --generate-report --report-format markdown --api-key YOUR_OPENAI_KEY

# Save results to a file
python -m ai_review review path/to/code.py --ai --output results.json --api-key YOUR_OPENAI_KEY

# UI validation with ChatGPT Vision
python -m ai_review review path/to/file.js --ui-validate --url "http://localhost:3000" --api-key YOUR_OPENAI_KEY 
```

## UI Validation with ChatGPT Vision

This tool can automatically capture screenshots of your web application and use ChatGPT Vision to validate UI changes:

- **Screenshot Capturing**: Takes "before" and "after" screenshots of your web UI
- **Visual Difference Detection**: Identifies layout changes, color shifts, missing elements, and more
- **AI-Powered Analysis**: Uses ChatGPT Vision to provide detailed analysis of UI changes
- **Severity Assessment**: Rates changes as minor, moderate, major, or critical
- **Comprehensive Reports**: Generates detailed reports with screenshots and analysis in JSON or Markdown format
- **Structured Output**: Organizes changes by category (layout, color, elements, text) with clear visual indicators

Run a UI validation:

```bash
ai-review review path/to/file.js --ui-validate --url "http://localhost:3000" --api-key "your-openai-api-key"
```

Generate UI validation reports in specific formats:

```bash
# Generate a Markdown report (default)
ai-review review path/to/file.js --ui-validate --url "http://localhost:3000" --ui-report-format markdown

# Generate a JSON report
ai-review review path/to/file.js --ui-validate --url "http://localhost:3000" --ui-report-format json

# Generate both Markdown and JSON reports
ai-review review path/to/file.js --ui-validate --url "http://localhost:3000" --ui-report-format both
```

Example of enhanced UI validation output:

```
========================================================================
🖥️  UI VALIDATION RESULTS
========================================================================

✅ UI validation completed successfully

📸 Before screenshot: logs/screenshots/20250310_123045_before.png
📸 After screenshot: logs/screenshots/20250310_123050_after.png
📄 Markdown report saved to: logs/ui_reports/ui_report_20250310_123055.md
📄 JSON report saved to: logs/ui_reports/ui_report_20250310_123055.json

📊 Analysis Summary:
------------------------------------------------------------------------
🔍 **UI Validation Analysis**
----------------------------------
📝 **Summary**: The UI has undergone several visual modifications between the before and after screenshots.

📐 **Layout Changes:**
   - Navbar shifted by 3px (⚠️ Moderate)
   - Button position adjusted (✔️ Minor)

🎨 **Color Changes:**
   - Button color changed from blue to green (✔️ Minor)
   - Background color darkened (✔️ Minor)

🧩 **Element Changes:**
   - Logo size increased by 10% (✔️ Minor)
   - Added new social media icons (✔️ Minor)

📝 **Text Changes:**
   - Header text changed from "Welcome" to "Hello" (✔️ Minor)
   - Footer copyright year updated (✔️ Minor)

❌ **Critical Issues:**
   - ❗ Missing image in footer section
   - ❗ Text contrast issue in dark mode

📊 **Comparison Confidence:** 94%
========================================================================
```

### UI Validation Reports

The tool generates structured reports in two formats:

#### JSON Report Structure

```json
{
  "summary": "Brief summary of overall changes",
  "layout_changes": [
    {"description": "Navbar shifted by 3px", "severity": "moderate", "is_issue": true},
    {"description": "Button position adjusted", "severity": "minor", "is_issue": false}
  ],
  "color_changes": [
    {"description": "Button color changed from blue to green", "severity": "minor", "is_issue": false}
  ],
  "element_changes": [
    {"description": "Logo size increased by 10%", "severity": "minor", "is_issue": false},
    {"description": "Added new social media icons", "severity": "minor", "is_issue": false}
  ],
  "text_changes": [
    {"description": "Header text changed", "severity": "minor", "is_issue": false}
  ],
  "critical_issues": [
    {"description": "Missing image in footer section", "severity": "critical"},
    {"description": "Text contrast issue in dark mode", "severity": "critical"}
  ],
  "comparison_confidence": 94
}
```

#### Markdown Report

The Markdown report includes:
- Overview with date and screenshot information
- Formatted analysis with emojis and severity indicators
- Links to the original screenshots
- Visual categorization of changes by type

### Prerequisites

To use the UI validation feature, you need to install:

1. Selenium and ChromeDriver:
   ```bash
   pip install selenium
   ```
   
   You'll also need to install ChromeDriver:
   - On macOS: `brew install chromedriver`
   - On Linux: `apt install chromium-chromedriver`
   - On Windows: Download from https://chromedriver.chromium.org/downloads

2. Chrome browser must be installed on your system

## Command Line Options

- `path`: Path to file or directory to review
- `--output, -o`: Output file path for results
- `--complexity-threshold, -c`: Complexity threshold for flagging functions (default: 5)
- `--ai, -a`: Enable AI-powered code review
- `--api-key, -k`: OpenAI API key (can also use OPENAI_API_KEY env var)
- `--model, -m`: OpenAI model to use (default: gpt-4o)
- `--apply-fixes, -f`: Automatically apply AI-suggested fixes
- `--security-scan, -s`: Perform security vulnerability scan
- `--dependency-scan, -d`: Scan dependencies for vulnerabilities
- `--generate-report, -r`: Generate a unified report of all analyses
- `--report-format`: Format for the generated report (choices: json, markdown, default: json)
- `--ui-validate, -u`: Validate UI changes using screenshots and ChatGPT Vision
- `--url`: URL of the web app for UI validation
- `--ui-report-format`: Format for the UI validation report (choices: json, markdown, both, default: markdown)
- `--debug`: Enable debug mode with verbose logging

## Example Usage

```bash
# Basic code analysis
python -m ai_review review path/to/code.py

# AI-powered code review
python -m ai_review review path/to/code.py --ai --api-key YOUR_OPENAI_KEY

# Automatically apply AI-suggested fixes
python -m ai_review review path/to/code.py --ai --apply-fixes --api-key YOUR_OPENAI_KEY

# Security vulnerability scanning
python -m ai_review review path/to/code.py --security-scan

# Dependency vulnerability scanning
python -m ai_review review path/to/code.py --dependency-scan

# Generate a unified report in Markdown format
python -m ai_review review path/to/code.py --ai --security-scan --dependency-scan --generate-report --report-format markdown --api-key YOUR_OPENAI_KEY

# Save results to a file
python -m ai_review review path/to/code.py --ai --output results.json --api-key YOUR_OPENAI_KEY

# UI validation with ChatGPT Vision
python -m ai_review review path/to/file.js --ui-validate --url "http://localhost:3000" --api-key YOUR_OPENAI_KEY

# UI validation with custom report format
python -m ai_review review path/to/file.js --ui-validate --url "http://localhost:3000" --ui-report-format json --api-key YOUR_OPENAI_KEY
```

## Running Automated Tests

To validate the AI-powered code review system, run:

```bash
python -m unittest tests/test_suite.py
```

The test suite will check:
- ✅ AI-generated code suggestions
- ✅ Security & dependency scanning
- ✅ UI validation using ChatGPT Vision
- ✅ Unified report generation
- ✅ CLI functionality and error handling

### Test Suite Details

The comprehensive test suite (`tests/test_suite.py`) validates all core features of the local MVP:

1. **AI-powered code review & suggestion generation**
   - Tests the `SuggestionGenerator` class
   - Validates suggestion generation and AI review functionality
   - Ensures proper JSON structure of suggestions

2. **Security scanning & dependency analysis**
   - Tests the `SecurityScanner` class for detecting vulnerabilities
   - Tests the `DependencyScanner` class for identifying vulnerable dependencies
   - Validates detection of hardcoded credentials, SQL injection, etc.

3. **UI validation (screenshot comparison with ChatGPT Vision)**
   - Tests the `UIValidator` class for comparing screenshots
   - Validates the analysis of visual differences
   - Tests report generation in different formats

4. **Unified report generation (JSON & Markdown formats)**
   - Tests the `ReportGenerator` class
   - Validates JSON and Markdown report generation
   - Ensures proper structure of generated reports

5. **CLI usability & error handling**
   - Tests argument parsing
   - Validates the `review_code` function with various options
   - Tests error handling for different scenarios

### Interpreting Test Results

When running the test suite, you'll see output indicating the success or failure of each test:

- ✅ Success messages indicate that the feature is working as expected
- ❌ Failure messages provide details about what went wrong

If all tests pass, your local MVP is ready for real-world testing. If any tests fail, check the error messages for details on what needs to be fixed.
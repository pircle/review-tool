"""
Command-line interface for the AI code review system.
"""

import os
import sys
import json
import argparse
import traceback
import subprocess
import datetime
import platform
from typing import Dict, List, Any, Optional
import logging
import click
from pathlib import Path

from .analyzer import CodeAnalyzer, analyze_file, analyze_directory
from .suggestions import SuggestionGenerator, generate_ai_review
from .apply import FixApplier, CodeFixer
from .utils import save_json, is_supported_file, find_files_by_extension
from .plugin_loader import PluginLoader
from .logger import logger, enable_console_logging, set_log_level
from .report_generator import ReportGenerator
from .security_scanner import scan_code
from .dependency_scanner import DependencyScanner
from .ui_validator import UIValidator
from .config_manager import config_manager, ConfigManager
from .interaction_logger import InteractionLogger
from .constants import (
    LOGS_DIR, SCREENSHOTS_DIR, UI_REPORTS_DIR, REPORTS_DIR,
    CLI_LOG_PATH
)
from .models import ReviewResults, FileReviewResult
from .api import get_project_data

# Initialize the interaction logger
interaction_logger = InteractionLogger()

# Configure logging
LOG_DIR = os.path.expanduser("~/.ai-code-review/logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "system.log")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

config_manager = ConfigManager()

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="AI Code Review Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Review command
    review_parser = subparsers.add_parser("review", help="Review code")
    review_parser.add_argument("path", nargs="?", help="Path to file or directory to review")
    review_parser.add_argument("--output", "-o", help="Output file path")
    review_parser.add_argument("--complexity-threshold", "-c", type=int, default=5, 
                              help="Complexity threshold for flagging functions (default: 5)")
    review_parser.add_argument("--ai", "-a", action="store_true", help="Use AI to analyze code")
    review_parser.add_argument("--api-key", "-k", help="OpenAI API key")
    review_parser.add_argument("--model", "-m", default="gpt-4o", 
                              help="OpenAI model to use (default: gpt-4o)")
    review_parser.add_argument("--apply-fixes", "-f", action="store_true", 
                              help="Automatically apply AI-suggested fixes")
    review_parser.add_argument("--security-scan", "-s", action="store_true", 
                              help="Perform security vulnerability scan")
    review_parser.add_argument("--dependency-scan", "-d", action="store_true", 
                              help="Scan dependencies for vulnerabilities")
    review_parser.add_argument("--generate-report", "-r", action="store_true", 
                              help="Generate a unified report of all analyses")
    review_parser.add_argument("--report-format", choices=["json", "markdown"], default="json", 
                              help="Format for the generated report (default: json)")
    review_parser.add_argument("--ui-validate", "-u", action="store_true",
                              help="Validate UI changes using screenshots and ChatGPT Vision")
    review_parser.add_argument("--url", type=str,
                              help="URL of the web app for UI validation")
    review_parser.add_argument("--ui-report-format", choices=["json", "markdown", "both"], default="markdown",
                              help="Format for the UI validation report (default: markdown)")
    review_parser.add_argument("--skip-code-review", action="store_true",
                              help="Skip code review and only perform UI validation")
    review_parser.add_argument("--project", "-p", help="Project name to use for configuration and logs (default: directory name)")
    review_parser.add_argument("--create-project", action="store_true", 
                              help="Create a new project if it doesn't exist")
    review_parser.add_argument("--list-projects", action="store_true",
                              help="List all available projects")
    review_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Start the web dashboard")
    dashboard_parser.add_argument("--host", default="localhost", help="Host to bind the dashboard server to")
    dashboard_parser.add_argument("--port", type=int, default=5000, help="Port to run the dashboard server on")
    dashboard_parser.add_argument("--debug", action="store_true", help="Run the server in debug mode")
    
    # Plugin command
    plugin_parser = subparsers.add_parser("plugin", help="Manage plugins")
    plugin_parser.add_argument("action", choices=["list", "install", "remove"], 
                              help="Action to perform")
    plugin_parser.add_argument("--path", help="Path to plugin or plugin name")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Configure settings")
    config_parser.add_argument("action", choices=["get", "set", "list", "init"], 
                              help="Action to perform")
    config_parser.add_argument("--key", help="Configuration key")
    config_parser.add_argument("--value", help="Configuration value")
    config_parser.add_argument("--local", action="store_true", help="Use local config file")
    
    return parser.parse_args()


def get_complexity_level(complexity: int, threshold: int = 5) -> str:
    """
    Get a human-readable complexity level.
    
    Args:
        complexity: Complexity score
        threshold: Threshold for moderate complexity
        
    Returns:
        Complexity level as a string
    """
    if complexity <= threshold - 2:
        return "low"
    elif complexity <= threshold + 2:
        return "moderate"
    else:
        return "high"


def print_analysis_results(analysis: Dict[str, Any], verbose: bool = False, 
                          complexity_threshold: int = 5) -> None:
    """
    Print the analysis results to the console.
    
    Args:
        analysis: Analysis results
        verbose: Whether to show detailed output
        complexity_threshold: Threshold for highlighting complex functions
    """
    file_path = analysis.get("file_path", "Unknown")
    loc = analysis.get("loc", 0)
    language = analysis.get("language", "Unknown")
    
    print(f"\nAnalyzing {file_path}")
    print(f"Language: {language}")
    print(f"Lines of code: {loc}")
    
    # Print functions
    functions = analysis.get("functions", [])
    if functions:
        print("\nFunctions:")
        for func in functions:
            name = func.get("name", "Unknown")
            line = func.get("line_number", 0)
            complexity = func.get("complexity", 0)
            
            # Determine complexity level
            complexity_level = get_complexity_level(complexity, complexity_threshold)
            
            # Print function info
            if complexity_level == "high":
                print(f"  - {name} (line {line}): {complexity} (high complexity) ⚠️")
            elif complexity_level == "moderate":
                print(f"  - {name} (line {line}): {complexity} (moderate complexity) ⚠️")
            else:
                print(f"  - {name} (line {line}): {complexity} (low complexity)")
            
            # Print arguments if verbose
            if verbose and "args" in func:
                args = func.get("args", [])
                if args:
                    print(f"    Arguments: {', '.join(args)}")
    
    # Print classes
    classes = analysis.get("classes", [])
    if classes:
        print("\nClasses:")
        for cls in classes:
            name = cls.get("name", "Unknown")
            line = cls.get("line_number", 0)
            complexity = cls.get("complexity", 0)
            
            # Determine if this is a regular class or an interface/type (TypeScript)
            cls_type = cls.get("type", "class")
            
            # Print class info
            if cls_type != "class":
                print(f"  - {name} ({cls_type}, line {line})")
            else:
                print(f"  - {name} (line {line}): {complexity}")
            
            # Print methods if verbose
            if verbose and "methods" in cls:
                methods = cls.get("methods", [])
                if methods:
                    print(f"    Methods: {', '.join(methods)}")
    
    # Print complexity summary
    complex_functions = [f for f in functions if f.get("complexity", 0) >= complexity_threshold]
    if complex_functions:
        print(f"\nComplexity metrics: {len(complex_functions)} complex functions found (threshold: {complexity_threshold})")
    else:
        print(f"\nComplexity metrics: No complex functions found (threshold: {complexity_threshold})")


def print_ai_review(review: Dict[str, Any]) -> None:
    """
    Print AI review results in a readable format.
    
    Args:
        review: AI review results
    """
    if "error" in review:
        print(f"\n❌ Error generating AI review: {review['error']}")
        return
    
    if "raw_response" in review.get("review", {}):
        print("\n🔍 AI Review (raw response):")
        print(review["review"]["raw_response"])
        return
    
    review_data = review.get("review", {})
    
    # Print structured review with improved formatting
    print("\n" + "=" * 80)
    print("🔍 AI-POWERED CODE REVIEW")
    print("=" * 80)
    
    # Summary and overall quality
    summary = review_data.get("summary", "No summary provided")
    overall_quality = review_data.get("overall_quality", "N/A")
    print(f"\n📝 Summary: {summary}")
    print(f"⭐ Overall Quality: {overall_quality}/10")
    
    # Suggestions with improved formatting and categorization
    suggestions = review_data.get("suggestions", [])
    if suggestions:
        print("\n🛠️  Suggestions:")
        
        # Group suggestions by category
        categorized_suggestions = {}
        for suggestion in suggestions:
            category = suggestion.get("category", "general")
            if category not in categorized_suggestions:
                categorized_suggestions[category] = []
            categorized_suggestions[category].append(suggestion)
        
        # Print suggestions by category
        for category, category_suggestions in categorized_suggestions.items():
            # Use emojis for different categories
            category_emoji = {
                "security": "🔒",
                "performance": "⚡",
                "readability": "📖",
                "maintainability": "🔧",
                "bug": "🐛",
                "style": "🎨",
                "organization": "📂",
                "best_practices": "✅",
                "general": "ℹ️"
            }.get(category.lower(), "•")
            
            print(f"\n  {category_emoji} {category.upper()}:")
            
            for i, suggestion in enumerate(category_suggestions, 1):
                title = suggestion.get("title", "Untitled suggestion")
                severity = suggestion.get("severity", "medium").upper()
                severity_marker = {
                    "HIGH": "❗❗",
                    "MEDIUM": "❗",
                    "LOW": "ℹ️"
                }.get(severity, "•")
                
                location = suggestion.get("location", "Unknown location")
                description = suggestion.get("description", "No description provided")
                improvement = suggestion.get("improvement", "No improvement suggested")
                
                print(f"    {i}. {title} {severity_marker}")
                print(f"       Location: {location}")
                print(f"       Description: {description}")
                print(f"       Improvement: {improvement}")
                print()
    else:
        print("\n✅ No specific suggestions provided. Your code looks good!")
    
    # Best practices
    best_practices = review_data.get("best_practices", [])
    if best_practices:
        print("\n📚 Best Practices:")
        for i, practice in enumerate(best_practices, 1):
            print(f"  {i}. {practice}")
    
    # Potential bugs
    potential_bugs = review_data.get("potential_bugs", [])
    if potential_bugs:
        print("\n🐛 Potential Bugs:")
        for i, bug in enumerate(potential_bugs, 1):
            print(f"  {i}. {bug}")
    
    print("\n" + "=" * 80)


def print_fix_results(results: Dict[str, Any]) -> None:
    """
    Print fix application results in a readable format.
    
    Args:
        results: Fix application results
    """
    if results.get("success", False):
        print("\n" + "=" * 80)
        print("FIX APPLICATION RESULTS")
        print("=" * 80)
        print(f"\n{results.get('message', 'Fixes applied successfully!')}")
        
        if "applied_fixes" in results:
            applied_fixes = results["applied_fixes"]
            print(f"\nApplied {len(applied_fixes)} fixes:")
            
            for i, fix in enumerate(applied_fixes, 1):
                title = fix.get("title", "Untitled fix")
                location = fix.get("location", "Unknown location")
                severity = fix.get("severity", "medium").upper()
                
                print(f"{i}. {title} at {location} [{severity}]")
        
        print("\n" + "=" * 80)
    else:
        print(f"\nFailed to apply fixes: {results.get('message', 'Unknown error')}")


def apply_ai_fixes(file_path: str, ai_review: Dict[str, Any], api_key: Optional[str] = None, 
                  model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
    """
    Apply AI-suggested fixes to the code.
    
    Args:
        file_path: Path to the file to modify
        ai_review: AI review containing suggestions
        api_key: OpenAI API key
        model: OpenAI model to use
        
    Returns:
        Results of the fix application
    """
    try:
        # Initialize the fix applier
        fix_applier = FixApplier(api_key=api_key, model=model)
        
        # Log that we're attempting to apply fixes
        interaction_logger.log_interaction(
            interaction_type="apply_fixes_attempt",
            description=f"Attempting to apply AI-suggested fixes to {file_path}"
        )
        
        # Get the original code before applying fixes
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                original_code = file.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            original_code = ""
        
        # Apply the fixes
        results = fix_applier.apply_ai_fixes(file_path, ai_review)
        
        # Log the results
        if results.get("success", False):
            # Get the modified code after applying fixes
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    modified_code = file.read()
            except Exception as e:
                logger.error(f"Error reading modified file {file_path}: {str(e)}")
                modified_code = ""
            
            # Log the approval
            interaction_logger.log_approval(
                file=file_path,
                description=f"Applied {len(results.get('applied_fixes', []))} fixes to {file_path}",
                details={
                    "applied_fixes": results.get("applied_fixes", []),
                    "backup_path": results.get("backup_path", "")
                }
            )
            
            # If the code was modified, log the modification
            if original_code and modified_code and original_code != modified_code:
                interaction_logger.log_modification(
                    file=file_path,
                    original_suggestion=original_code,
                    modified_suggestion=modified_code,
                    description=f"Modified code in {file_path}",
                    details={
                        "applied_fixes": results.get("applied_fixes", [])
                    }
                )
        else:
            # Log the rejection
            interaction_logger.log_rejection(
                file=file_path,
                reason=results.get("message", "Unknown error"),
                description=f"Failed to apply fixes to {file_path}"
            )
        
        return results
    except Exception as e:
        logger.error(f"Error in apply_ai_fixes: {str(e)}")
        logger.debug(traceback.format_exc())
        return {
            "success": False,
            "message": f"Error applying fixes: {str(e)}"
        }


def print_security_scan_results(scan_results: Dict[str, Any]) -> None:
    """
    Print security scan results in a readable format.
    
    Args:
        scan_results: Security scan results
    """
    summary = scan_results.get("summary", {})
    issues = scan_results.get("issues", [])
    
    print("\n" + "=" * 80)
    print("🔒 SECURITY SCAN RESULTS")
    print("=" * 80)
    
    # Print summary
    total_issues = summary.get("total_issues", 0)
    high_severity = summary.get("high_severity", 0)
    medium_severity = summary.get("medium_severity", 0)
    low_severity = summary.get("low_severity", 0)
    
    if total_issues == 0:
        print("\n✅ No security issues found!")
    else:
        print(f"\n⚠️  Found {total_issues} potential security issues:")
        print(f"   🔴 High severity: {high_severity}")
        print(f"   🟠 Medium severity: {medium_severity}")
        print(f"   🟡 Low severity: {low_severity}")
    
    # Group issues by category
    issues_by_category = {}
    for issue in issues:
        category = issue.get("category", "other")
        if category not in issues_by_category:
            issues_by_category[category] = []
        issues_by_category[category].append(issue)
    
    # Print issues by category
    if issues:
        print("\nDetailed Issues:")
        
        # Define category emojis and titles
        category_info = {
            "credentials": ("🔑", "HARDCODED CREDENTIALS"),
            "sql_injection": ("💉", "SQL INJECTION"),
            "xss": ("🌐", "CROSS-SITE SCRIPTING (XSS)"),
            "crypto": ("🔐", "INSECURE CRYPTOGRAPHY"),
            "path_traversal": ("📁", "PATH TRAVERSAL"),
            "command_injection": ("⚡", "COMMAND INJECTION"),
            "other": ("❓", "OTHER ISSUES")
        }
        
        # Define severity markers
        severity_marker = {
            "high": "🔴",
            "medium": "🟠",
            "low": "🟡"
        }
        
        for category, category_issues in issues_by_category.items():
            emoji, title = category_info.get(category, ("❓", category.upper()))
            print(f"\n  {emoji} {title}:")
            
            for i, issue in enumerate(category_issues, 1):
                severity = issue.get("severity", "medium")
                marker = severity_marker.get(severity, "⚪")
                issue_title = issue.get("issue", "Unknown issue")
                detail = issue.get("detail", "No details provided")
                line = issue.get("line", "Unknown")
                recommendation = issue.get("recommendation", "No recommendation provided")
                
                print(f"    {i}. {issue_title} {marker}")
                print(f"       Line: {line}")
                print(f"       Detail: {detail}")
                print(f"       Recommendation: {recommendation}")
                print()
    
    print("=" * 80)


def print_dependency_scan_results(scan_results: Dict[str, Any]) -> None:
    """
    Print dependency scan results in a readable format.
    
    Args:
        scan_results: Dependency scan results
    """
    print("\n" + "=" * 80)
    print("📦 DEPENDENCY VULNERABILITY SCAN RESULTS")
    print("=" * 80)
    
    # Check for warnings about missing tools
    warnings = scan_results.get("warnings", [])
    if warnings:
        print("\n⚠️  DEPENDENCY SCANNING TOOLS MISSING:")
        for warning in warnings:
            tool = warning.get("tool", "Unknown tool")
            message = warning.get("message", "Unknown issue")
            install_cmd = warning.get("install_command", "")
            doc_url = warning.get("documentation_url", "")
            
            print(f"   ❌ {tool}: {message}")
            if install_cmd:
                print(f"      To install: {install_cmd}")
            if doc_url:
                print(f"      Documentation: {doc_url}")
        print()
    
    # Check if all tools are missing
    if scan_results.get("tools_missing", False):
        print("⚠️ No dependency scanning tools are available. No vulnerabilities were checked.")
        print("   Please install the required tools to enable dependency scanning.")
        print("=" * 80)
        return
    
    # Get vulnerability counts
    total_vulnerabilities = scan_results.get("total_vulnerabilities", 0)
    
    # Print summary
    if total_vulnerabilities == 0:
        print("\n✅ No dependency vulnerabilities found!")
    else:
        print(f"\n⚠️  Found {total_vulnerabilities} potential vulnerabilities in dependencies:")
        
        # Count vulnerabilities by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}
        
        for vuln in scan_results.get("vulnerable_dependencies", []):
            severity = vuln.get("severity", "unknown").lower()
            if severity == "critical":
                severity_counts["critical"] += 1
            elif severity == "high":
                severity_counts["high"] += 1
            elif severity == "medium" or severity == "moderate":
                severity_counts["medium"] += 1
            elif severity == "low":
                severity_counts["low"] += 1
            else:
                severity_counts["unknown"] += 1
        
        # Print severity counts
        if severity_counts["critical"] > 0:
            print(f"   💥 Critical severity: {severity_counts['critical']}")
        print(f"   🔴 High severity: {severity_counts['high']}")
        print(f"   🟠 Medium severity: {severity_counts['medium']}")
        print(f"   🟡 Low severity: {severity_counts['low']}")
        if severity_counts["unknown"] > 0:
            print(f"   ⚪ Unknown severity: {severity_counts['unknown']}")
        
        print("\nDetailed Issues:\n")
        
        # Print Python vulnerabilities
        python_results = scan_results.get("python", {})
        python_vulnerabilities = python_results.get("vulnerabilities", [])
        
        if python_vulnerabilities:
            print("  🐍 PYTHON DEPENDENCIES:")
            
            for i, vuln in enumerate(python_vulnerabilities, 1):
                # Handle error messages
                if "error" in vuln:
                    print(f"    ❌ {vuln.get('message', 'Unknown error')}")
                    continue
                
                # Get vulnerability details
                package = vuln.get("package_name", vuln.get("package", "Unknown package"))
                version = vuln.get("vulnerable_version", vuln.get("affected_versions", vuln.get("version", "Unknown version")))
                severity = vuln.get("severity", "unknown").lower()
                description = vuln.get("description", vuln.get("advisory", "No description available"))
                
                # Determine severity emoji
                severity_emoji = "⚪"
                if severity == "critical":
                    severity_emoji = "💥"
                elif severity == "high":
                    severity_emoji = "🔴"
                elif severity == "medium" or severity == "moderate":
                    severity_emoji = "🟠"
                elif severity == "low":
                    severity_emoji = "🟡"
                
                print(f"    {i}. {package} ({version}) {severity_emoji}")
                print(f"       Description: {description}")
                
                # Print fix if available
                fix = vuln.get("fixed_version", vuln.get("recommendation", vuln.get("fix", "")))
                if fix:
                    print(f"       Fix: {fix}")
                
                print()
        elif not python_results.get("tool_available", True):
            print("  🐍 PYTHON DEPENDENCIES: ❌ Scan skipped (safety tool not installed)")
        else:
            print("  🐍 PYTHON DEPENDENCIES: ✅ No vulnerabilities found")
        
        # Print JavaScript vulnerabilities
        js_results = scan_results.get("javascript", {})
        js_vulnerabilities = js_results.get("vulnerabilities", {})
        
        if js_vulnerabilities and isinstance(js_vulnerabilities, dict) and "advisories" in js_vulnerabilities:
            print("  🟨 JAVASCRIPT/TYPESCRIPT DEPENDENCIES:")
            
            # Process npm audit results
            for i, (vuln_id, vuln) in enumerate(js_vulnerabilities["advisories"].items(), 1):
                if isinstance(vuln, dict):
                    module_name = vuln.get("module_name", "Unknown package")
                    severity = vuln.get("severity", "unknown").lower()
                    title = vuln.get("title", "Unknown vulnerability")
                    
                    # Determine severity emoji
                    severity_emoji = "⚪"
                    if severity == "critical":
                        severity_emoji = "💥"
                    elif severity == "high":
                        severity_emoji = "🔴"
                    elif severity == "medium" or severity == "moderate":
                        severity_emoji = "🟠"
                    elif severity == "low":
                        severity_emoji = "🟡"
                    
                    print(f"    {i}. {module_name} {severity_emoji}")
                    print(f"       Title: {title}")
                    
                    # Print recommendation if available
                    recommendation = vuln.get("recommendation", "")
                    if recommendation:
                        print(f"       Fix: {recommendation}")
                    
                    # Print URL for more info
                    url = vuln.get("url", "")
                    if url:
                        print(f"       More info: {url}")
                    
                    print()
        elif not js_results.get("tool_available", True):
            print("  🟨 JAVASCRIPT/TYPESCRIPT DEPENDENCIES: ❌ Scan skipped (npm tool not installed)")
        else:
            print("  🟨 JAVASCRIPT/TYPESCRIPT DEPENDENCIES: ✅ No vulnerabilities found")
    
    print("=" * 80)


def print_ui_validation_results(results: Dict[str, Any]) -> None:
    """
    Print UI validation results.
    
    Args:
        results: UI validation results
    """
    print("\n" + "=" * 72)
    print("🖥️  UI VALIDATION RESULTS")
    print("=" * 72 + "\n")
    
    if not results:
        print("❌ No UI validation results available")
        return
    
    if not results.get("success", False):
        print(f"❌ UI validation failed: {results.get('error', 'Unknown error')}")
        return
    
    print(f"✅ UI validation completed successfully\n")
    
    # Print screenshot paths
    if "before_image" in results:
        print(f"📸 Before screenshot: {results['before_image']}")
    else:
        print("⚠️ Before screenshot not available")
        
    if "after_image" in results:
        print(f"📸 After screenshot: {results['after_image']}")
    else:
        print("⚠️ After screenshot not available")
    
    # Print report paths
    if "report_paths" in results and results["report_paths"]:
        print("\n📄 Generated reports:")
        for format_type, path in results["report_paths"].items():
            if "error" not in format_type:
                print(f"  - {format_type.capitalize()}: {path}")
            else:
                # Handle error cases
                format_type_clean = format_type.replace("_error", "")
                print(f"  - ⚠️ {format_type_clean.capitalize()} report generation failed: {path}")
    elif "report_path" in results:
        print(f"\n📄 Report saved to: {results['report_path']}")
    else:
        print("\n⚠️ No reports were generated")
    
    # Print analysis summary if available
    if "analysis" in results and results["analysis"]:
        print("\n📊 Analysis Summary:")
        print("-" * 72)
        
        # Print the formatted analysis
        analysis_lines = results['analysis'].strip().split('\n')
        
        # Print all lines of the analysis
        for line in analysis_lines:
            print(line)
    else:
        print("\n⚠️ No analysis summary available")
    
    print("\n" + "=" * 72)


def analyze_complexity(code: str, threshold: int = 5) -> Dict[str, Any]:
    """
    Analyze code complexity.
    
    Args:
        code: Code to analyze
        threshold: Complexity threshold
        
    Returns:
        Complexity analysis results
    """
    # This is a simplified implementation since the original module is missing
    logger.info(f"Analyzing code complexity with threshold {threshold}")
    
    # Return a placeholder result
    return {
        "complex_functions": [],
        "average_complexity": 0,
        "max_complexity": 0,
        "threshold": threshold
    }


def print_directory_results(results: List[Dict[str, Any]], complexity_threshold: int = 5) -> None:
    """
    Print analysis results for a directory.
    
    Args:
        results: Analysis results for each file
        complexity_threshold: Threshold for highlighting complex functions
    """
    if not results:
        print("No files analyzed.")
        return
    
    total_files = len(results)
    total_functions = sum(len(result.get("functions", [])) for result in results)
    total_classes = sum(len(result.get("classes", [])) for result in results)
    total_complex_functions = sum(
        len([f for f in result.get("functions", []) if f.get("complexity", 0) > complexity_threshold])
        for result in results
    )
    
    print(f"\nAnalysis Summary:")
    print(f"  Files analyzed: {total_files}")
    print(f"  Total functions: {total_functions}")
    print(f"  Total classes: {total_classes}")
    print(f"  Complex functions: {total_complex_functions} (threshold: {complexity_threshold})")
    print("\nDetailed Results:")
    
    for result in results:
        print(f"\n{result['file_path']}:")
        print(f"  Language: {result.get('language', 'Unknown')}")
        print(f"  Lines of code: {result.get('lines_of_code', 0)}")
        
        functions = result.get("functions", [])
        if functions:
            print(f"  Functions: {len(functions)}")
            complex_functions = [f for f in functions if f.get("complexity", 0) > complexity_threshold]
            if complex_functions:
                print(f"  Complex functions: {len(complex_functions)}")
                for func in complex_functions:
                    print(f"    - {func.get('name', 'Unknown')} (complexity: {func.get('complexity', 0)})")
        
        classes = result.get("classes", [])
        if classes:
            print(f"  Classes: {len(classes)}")
            for cls in classes:
                print(f"    - {cls.get('name', 'Unknown')}")


def review_code(
    path: str,
    verbose: bool = False,
    output: Optional[str] = None,
    complexity_threshold: int = 10,
    ai: bool = True,
    api_key: Optional[str] = None,
    model: str = "gpt-4",
    apply_fixes: bool = False,
    security_scan: bool = False,
    dependency_scan: bool = False,
    generate_report: bool = True,
    report_format: str = "markdown",
    ui_validate: bool = False,
    url: Optional[str] = None,
    ui_report_format: str = "markdown",
    skip_code_review: bool = False,
    debug: bool = False
) -> Dict[str, Any]:
    """Review code and generate analysis."""
    
    # Set up logging
    if debug:
        logger.setLevel(logging.DEBUG)
    
    # Validate inputs
    if not path:
        logger.error("No path provided")
        return {"error": "No path provided"}
    
    if ui_validate and not url:
        logger.error("URL is required for UI validation")
        return {"error": "URL is required for UI validation"}
    
    # Initialize results
    project_name = Path(path).name
    log_dir = Path(LOGS_DIR) / project_name
    log_dir.mkdir(parents=True, exist_ok=True)
    review_log_path = log_dir / "review_log.json"
    
    results = ReviewResults()
    
    try:
        # Analyze code
        if os.path.isdir(path):
            logger.info(f"Analyzing directory: {path}")
            try:
                files = analyze_directory(path)
                for analysis in files:
                    file_path = analysis.get("file_path", "unknown")
                    file_result = FileReviewResult(
                        path=file_path,
                        issues=len(analysis.get("issues", [])),
                        status="pending",
                        details=analysis
                    )
                    results.files.append(file_result)
                    results.total_reviews += 1
                    if analysis.get("issues"):
                        results.pending_fixes += len(analysis["issues"])
            except Exception as e:
                logger.error(f"Error analyzing directory: {str(e)}")
                if debug:
                    logger.error(traceback.format_exc())
                return {"error": f"Failed to analyze directory: {str(e)}"}
        else:
            logger.info(f"Analyzing file: {path}")
            try:
                with open(path) as f:
                    code = f.read()
                analyzer = CodeAnalyzer()
                analysis = analyzer.analyze(code, path)
                file_result = FileReviewResult(
                    path=path,
                    issues=len(analysis.get("issues", [])),
                    status="pending",
                    details=analysis
                )
                results.files.append(file_result)
                results.total_reviews += 1
                if analysis.get("issues"):
                    results.pending_fixes += len(analysis["issues"])
            except Exception as e:
                logger.error(f"Error analyzing file: {str(e)}")
                if debug:
                    logger.error(traceback.format_exc())
                return {"error": f"Failed to analyze file: {str(e)}"}
        
        # Apply fixes if requested
        if apply_fixes and results.pending_fixes > 0:
            logger.info("Applying fixes...")
            fixer = CodeFixer(project_name)
            fix_results = fixer.apply_fixes(auto_fix=True)
            results.applied_fixes = len(fix_results.get("applied", []))
            results.pending_fixes -= results.applied_fixes
            
            # Update file statuses
            for file_result in results.files:
                applied_fixes = [f for f in fix_results.get("applied", []) if f["file"] == file_result.path]
                if applied_fixes:
                    file_result.status = "fixed"
        
        # Perform security scan if requested
        if security_scan:
            logger.info("Performing security scan...")
            try:
                security_results = perform_security_scan(path)
                if "error" not in security_results:
                    # Add security results to output
                    if "security_scan" not in results.dict():
                        results.dict()["security_scan"] = security_results
            except Exception as e:
                logger.error(f"Error during security scan: {str(e)}")
                if debug:
                    logger.error(traceback.format_exc())
        
        # Perform dependency scan if requested
        if dependency_scan:
            logger.info("Performing dependency scan...")
            try:
                dependency_results = scan_dependencies(path)
                if "error" not in dependency_results:
                    # Add dependency results to output
                    if "dependency_scan" not in results.dict():
                        results.dict()["dependency_scan"] = dependency_results
            except Exception as e:
                logger.error(f"Error during dependency scan: {str(e)}")
                if debug:
                    logger.error(traceback.format_exc())
        
        # Perform UI validation if requested
        if ui_validate and url:
            logger.info("Performing UI validation...")
            try:
                validator = UIValidator(project_name, api_key)
                validation_results = validator.get_results()
                results.dict()["ui_validation"] = validation_results.dict()
            except Exception as e:
                logger.error(f"Error during UI validation: {str(e)}")
                if debug:
                    logger.error(traceback.format_exc())
        
        # Save results
        try:
            data = results.model_dump()
            data["timestamp"] = data["timestamp"].isoformat()
            with open(review_log_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Results saved to {review_log_path}")
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
            if debug:
                logger.error(traceback.format_exc())
        
        return results.model_dump()
        
    except Exception as e:
        error_msg = f"Unexpected error during code review: {str(e)}"
        logger.error(error_msg)
        if debug:
            logger.error(traceback.format_exc())
        return {"error": error_msg}


def handle_config_command(args):
    """
    Handle the config command.
    
    Args:
        args: Command line arguments
    """
    if args.action == "get":
        if not args.key:
            logger.error("Key is required for 'get' action")
            return
        
        value = config_manager.get(args.key)
        if value is None:
            logger.info(f"Configuration key '{args.key}' not found")
        else:
            if isinstance(value, dict):
                print(json.dumps(value, indent=2))
            else:
                print(value)
    
    elif args.action == "set":
        if not args.key or args.value is None:
            logger.error("Key and value are required for 'set' action")
            return
        
        # Handle nested keys (e.g., file_filters.exclude_dirs)
        keys = args.key.split('.')
        current = config_manager.config
        
        # Navigate to the nested dictionary
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        
        # Set the value (try to parse as JSON if possible)
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError:
            value = args.value
        
        current[keys[-1]] = value
        
        # Save the configuration
        if args.local:
            if config_manager.save_local():
                logger.info(f"Configuration key '{args.key}' set to '{value}' in local config")
        else:
            if config_manager.save():
                logger.info(f"Configuration key '{args.key}' set to '{value}' in global config")
    
    elif args.action == "list":
        print(json.dumps(config_manager.config, indent=2))
    
    elif args.action == "init":
        # Create a default configuration file
        if args.local:
            if config_manager.save_local():
                logger.info(f"Created default local configuration file at {config_manager.local_config_file}")
        else:
            if config_manager.save():
                logger.info(f"Created default global configuration file at {config_manager.config_file}")


def handle_review_command(args):
    """
    Handle the review command.
    
    Args:
        args: Command line arguments
    """
    # Set up logging
    cli_log_path = CLI_LOG_PATH
    os.makedirs(os.path.dirname(cli_log_path), exist_ok=True)
    
    if not os.path.exists(cli_log_path):
        with open(cli_log_path, "w") as log_file:
            log_file.write("# AI Code Review Tool - CLI Operation Log\n\n")
    
    # Handle list projects option
    if hasattr(args, 'list_projects') and args.list_projects:
        projects = config_manager.get_projects()
        if not projects:
            print("No projects found.")
            
            # Log the operation
            with open(cli_log_path, "a") as log_file:
                log_file.write(f"## {datetime.datetime.now()} - List Projects\n\n")
                log_file.write("No projects found.\n\n")
                
            return
        
        print("\nAvailable projects:")
        print("=" * 80)
        print(f"{'#':<5} {'Project Name':<30} {'Project Path':<45}")
        print("-" * 80)
        for i, project in enumerate(projects, 1):
            print(f"{i:<5} {project['name']:<30} {project['path']:<45}")
        print("=" * 80)
        
        # Log the operation
        with open(cli_log_path, "a") as log_file:
            log_file.write(f"## {datetime.datetime.now()} - List Projects\n\n")
            log_file.write(f"Found {len(projects)} projects:\n\n")
            for i, project in enumerate(projects, 1):
                log_file.write(f"{i}. {project['name']} - {project['path']}\n")
            log_file.write("\n")
            
        return
    
    # Check if path is provided when not skipping code review
    if not hasattr(args, 'skip_code_review') or not args.skip_code_review:
        if not hasattr(args, 'path') or args.path is None:
            print("Error: Path is required for code review.")
            print("Use --list-projects to list available projects.")
            return
    elif not hasattr(args, 'ui_validate') or not args.ui_validate:
        print("Error: When using --skip-code-review, you must specify --ui-validate.")
        return
    elif not hasattr(args, 'url') or args.url is None:
        print("Error: URL is required for UI validation.")
        return
    
    # Handle project selection or creation
    if hasattr(args, 'path') and args.path is not None:
        if not hasattr(args, 'project') or args.project is None:
            # Use current directory name as project name
            project_name = os.path.basename(os.path.abspath(args.path))
            print(f"⚠ Warning: No project name provided. Using '{project_name}' as project name.")
            args.project = project_name
            # Set create_project flag to True to create the project if it doesn't exist
            if not hasattr(args, 'create_project') or not args.create_project:
                print(f"⚠ Warning: Setting --create-project flag to create project if it doesn't exist.")
                args.create_project = True
        
        if args.project:
            project_name = args.project
            project_path = os.path.abspath(args.path)
            
            # Check if project exists
            project = config_manager.get_project(project_name)
            project_exists_by_path = False
            
            # Also check if a project with this path already exists
            for existing_project in config_manager.get_projects():
                if os.path.abspath(existing_project["path"]) == project_path:
                    project_exists_by_path = True
                    # If project exists by path but with a different name, use that project
                    if not project:
                        project = existing_project
                        project_name = existing_project["name"]
                        print(f"✅ Found existing project '{project_name}' at path '{project_path}'")
                        args.project = project_name
                    break
            
            if project:
                print(f"✅ Using existing project: {project_name}")
                # Continue with existing project
            elif project_exists_by_path:
                # This case is handled above
                pass
            elif args.create_project:
                # Continue with project creation
                print(f"🔄 Creating new project: {project_name}")
                # Add code here to create the project
                if config_manager.add_project(project_name, project_path):
                    print(f"✅ Project '{project_name}' created successfully")
                else:
                    print(f"❌ Failed to create project '{project_name}'")
    
    # Log the review command
    interaction_logger.log_command(
        command="review",
        description=f"Reviewing {'UI only' if hasattr(args, 'skip_code_review') and args.skip_code_review else f'code at path: {args.path}'}",
        additional_details={
            "path": args.path if hasattr(args, 'path') and args.path is not None else "None",
            "ai": args.ai,
            "apply_fixes": args.apply_fixes,
            "security_scan": args.security_scan,
            "dependency_scan": args.dependency_scan,
            "generate_report": args.generate_report,
            "project": args.project if args.project else "None",
            "ui_validate": args.ui_validate if hasattr(args, 'ui_validate') else False,
            "skip_code_review": args.skip_code_review if hasattr(args, 'skip_code_review') else False
        }
    )
    
    # Call the review_code function with the arguments from the command line
    result = review_code(
        path=args.path if hasattr(args, 'path') else None,
        verbose=True,
        output=args.output,
        complexity_threshold=args.complexity_threshold,
        ai=args.ai,
        api_key=args.api_key,
        model=args.model,
        apply_fixes=args.apply_fixes,
        security_scan=args.security_scan,
        dependency_scan=args.dependency_scan,
        generate_report=args.generate_report,
        report_format=args.report_format,
        ui_validate=args.ui_validate,
        url=args.url,
        ui_report_format=args.ui_report_format,
        skip_code_review=args.skip_code_review if hasattr(args, 'skip_code_review') else False,
        debug=args.debug
    )
    
    # Log the execution result
    with open(cli_log_path, "a") as log_file:
        log_file.write(f"## {datetime.datetime.now()} - AI Review Completed\n\n")
        log_file.write(f"Project: {args.project}\n")
        log_file.write(f"Path: {args.path}\n")
        if result and isinstance(result, dict):
            log_file.write(f"Result: {json.dumps(result, indent=2)}\n\n")
        else:
            log_file.write(f"Result: Completed successfully\n\n")


def handle_plugin_command(args):
    """
    Handle the plugin command.
    
    Args:
        args: Command line arguments
    """
    # Log the plugin command
    interaction_logger.log_command(
        command="plugin",
        description=f"Plugin command: {args.action}",
        additional_details={
            "action": args.action,
            "plugin_name": getattr(args, 'name', None)
        }
    )
    
    if args.action == "list":
        # List all available plugins
        plugin_loader = PluginLoader()
        plugins = plugin_loader.list_plugins()
        
        if not plugins:
            print("No plugins found.")
            return
        
        print("Available plugins:")
        for plugin in plugins:
            print(f"  - {plugin}")
    
    elif args.action == "info":
        if not args.name:
            logger.error("Plugin name is required for 'info' action")
            print("Error: Plugin name is required for 'info' action")
            return
        
        # Get plugin information
        plugin_loader = PluginLoader()
        plugin_info = plugin_loader.get_plugin_info(args.name)
        
        if not plugin_info:
            logger.error(f"Plugin '{args.name}' not found")
            print(f"Error: Plugin '{args.name}' not found")
            return
        
        print(f"Plugin: {args.name}")
        print(f"  Description: {plugin_info.get('description', 'No description')}")
        print(f"  Version: {plugin_info.get('version', 'Unknown')}")
        print(f"  Author: {plugin_info.get('author', 'Unknown')}")
    
    elif args.action == "install":
        if not args.name:
            logger.error("Plugin name is required for 'install' action")
            print("Error: Plugin name is required for 'install' action")
            return
        
        # Install plugin
        plugin_loader = PluginLoader()
        success = plugin_loader.install_plugin(args.name)
        
        if success:
            logger.info(f"Plugin '{args.name}' installed successfully")
            print(f"Plugin '{args.name}' installed successfully")
        else:
            logger.error(f"Failed to install plugin '{args.name}'")
            print(f"Error: Failed to install plugin '{args.name}'")
    
    elif args.action == "uninstall":
        if not args.name:
            logger.error("Plugin name is required for 'uninstall' action")
            print("Error: Plugin name is required for 'uninstall' action")
            return
        
        # Uninstall plugin
        plugin_loader = PluginLoader()
        success = plugin_loader.uninstall_plugin(args.name)
        
        if success:
            logger.info(f"Plugin '{args.name}' uninstalled successfully")
            print(f"Plugin '{args.name}' uninstalled successfully")
        else:
            logger.error(f"Failed to uninstall plugin '{args.name}'")
            print(f"Error: Failed to uninstall plugin '{args.name}'")


def generate_suggestions(code: str, analysis: Dict[str, Any], api_key: Optional[str] = None, 
                        model: str = "gpt-3.5-turbo") -> List[Dict[str, Any]]:
    """
    Generate suggestions for improving the code.
    
    Args:
        code: Source code to analyze
        analysis: Analysis results from the analyzer
        api_key: OpenAI API key
        model: OpenAI model to use
        
    Returns:
        List of suggestions
    """
    # Initialize the suggestion generator
    suggestion_generator = SuggestionGenerator(api_key=api_key, model=model)
    
    # Generate suggestions
    return suggestion_generator.generate_suggestions(code, analysis)


def scan_security(code: str, file_path: str) -> Dict[str, Any]:
    """
    Scan code for security vulnerabilities.
    
    Args:
        code: Source code to scan
        file_path: Path to the file being scanned
        
    Returns:
        Dictionary with scan results
    """
    return scan_code(code, file_path)


@click.group()
@click.option('--debug/--no-debug', default=False, help='Enable debug mode')
def cli(debug):
    """AI Code Review Tool - Analyze and improve your code with AI."""
    if debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")

@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--verbose', is_flag=True, help='Enable verbose output')
@click.option('--apply-fixes', is_flag=True, help='Automatically apply suggested fixes')
def review(path, verbose, apply_fixes):
    """Run AI code review on the specified path."""
    try:
        # Convert path to absolute path
        abs_path = os.path.abspath(path)
        logger.debug(f"Reviewing path: {abs_path}")
        
        # Check if this path belongs to an existing project
        for project in config_manager.get_projects():
            if os.path.commonpath([abs_path, project['path']]) == project['path']:
                logger.info(f"Found existing project: {project['name']}")
                config_manager.set_current_project(project['name'])
                break
        
        # Run the review
        review_code(abs_path, verbose=verbose, apply_fixes=apply_fixes)
        
    except Exception as e:
        logger.error(f"Error during review: {str(e)}")
        raise click.ClickException(str(e))

@cli.command()
def dashboard():
    """Start the dashboard server."""
    try:
        import uvicorn
        from .test19_api import app
        logger.info("Starting dashboard server...")
        uvicorn.run(app, host="127.0.0.1", port=5050)
    except Exception as e:
        logger.error(f"Error starting dashboard: {str(e)}")
        raise click.ClickException(str(e))

def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 
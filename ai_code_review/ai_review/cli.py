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
from .config_manager import config_manager
from .interaction_logger import InteractionLogger

# Initialize the interaction logger
interaction_logger = InteractionLogger()

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
    review_parser.add_argument("--project", "-p", help="Project name to use for configuration and logs (default: directory name)")
    review_parser.add_argument("--create-project", action="store_true", 
                              help="Create a new project if it doesn't exist")
    review_parser.add_argument("--list-projects", action="store_true",
                              help="List all available projects")
    review_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
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


def review_code(path: str, verbose: bool = False, output: Optional[str] = None,
               complexity_threshold: int = 5, ai: bool = False, 
               api_key: Optional[str] = None, model: str = "gpt-4o",
               apply_fixes: bool = False, security_scan: bool = False, 
               dependency_scan: bool = False, generate_report: bool = False,
               report_format: str = "json", ui_validate: bool = False,
               url: Optional[str] = None, ui_report_format: str = "markdown",
               debug: bool = False, project: Optional[str] = None) -> None:
    """
    Review code at the specified path.
    
    Args:
        path: Path to the file or directory to review
        verbose: Whether to show detailed output
        output: Path to the output file (JSON format)
        complexity_threshold: Threshold for highlighting complex functions
        ai: Whether to use AI-powered code review
        api_key: OpenAI API key
        model: OpenAI model to use
        apply_fixes: Whether to apply AI-suggested fixes
        security_scan: Whether to perform security scanning
        dependency_scan: Whether to scan dependencies for vulnerabilities
        generate_report: Whether to generate a unified report
        report_format: Format for the generated report ("json" or "markdown")
        ui_validate: Whether to validate UI changes
        url: URL of the web app for UI validation
        ui_report_format: Format for the UI validation report ("json", "markdown", or "both")
        debug: Whether to enable debug mode
        project: Project name to use for configuration and logs
    """
    # Configure logging based on debug flag
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Log the configuration settings
    logger.info("Starting code review with the following settings:")
    logger.info(f"  Path: {path}")
    logger.info(f"  Complexity threshold: {complexity_threshold}")
    logger.info(f"  AI-powered review: {ai}")
    logger.info(f"  Apply fixes: {apply_fixes}")
    logger.info(f"  Security scan: {security_scan}")
    logger.info(f"  Dependency scan: {dependency_scan}")
    logger.info(f"  Generate report: {generate_report}")
    if generate_report:
        logger.info(f"  Report format: {report_format}")
    logger.info(f"  UI validate: {ui_validate}")
    if ui_validate:
        logger.info(f"  URL: {url}")
        logger.info(f"  UI report format: {ui_report_format}")
    if project:
        logger.info(f"  Project: {project}")
    
    # Validate report formats
    valid_report_formats = ["json", "markdown"]
    if report_format not in valid_report_formats:
        logger.warning(f"Invalid report format: {report_format}. Must be one of {valid_report_formats}")
        report_format = "json"
        logger.info(f"Defaulting to {report_format} format")
    
    valid_ui_report_formats = ["json", "markdown", "both"]
    if ui_report_format not in valid_ui_report_formats:
        logger.warning(f"Invalid UI report format: {ui_report_format}. Must be one of {valid_ui_report_formats}")
        ui_report_format = "markdown"
        logger.info(f"Defaulting to {ui_report_format} format")
    
    # Validate UI validation parameters
    if ui_validate and not url:
        logger.error("URL is required for UI validation")
        print("Error: URL is required for UI validation. Please provide a URL using the --url option.")
        return
    
    logger.info(f"Reviewing code at {path}")
    print(f"Reviewing code at {path}")
    
    try:
        # Check if path exists
        if not os.path.exists(path):
            logger.error(f"Path does not exist: {path}")
            print(f"Error: Path does not exist: {path}")
            return
        
        # Load plugins to get supported extensions
        plugin_loader = PluginLoader()
        plugin_loader.load_all_plugins()
        supported_extensions = list(plugin_loader.language_analyzers.keys())
        logger.debug(f"Supported extensions: {supported_extensions}")
        
        # Check if the path is a directory
        if os.path.isdir(path):
            logger.info(f"Analyzing directory: {path}")
            
            try:
                # Log file filtering configuration
                logger.info("File filtering configuration:")
                logger.info(f"  Excluded directories: {', '.join(config_manager.config['file_filters']['exclude_dirs'])}")
                logger.info(f"  Included directories: {', '.join(config_manager.config['file_filters']['include_dirs'])}")
                logger.info(f"  Excluded file patterns: {', '.join(config_manager.config['file_filters']['exclude_files'])}")
                
                # Analyze all supported files in the directory
                results = analyze_directory(path)
                
                # Create output data structure
                output_data = {
                    "directory": path,
                    "files": results,
                    "metadata": {
                        "file_count": len(results),
                        "excluded_directories": list(config_manager.config["file_filters"]["exclude_dirs"]),
                        "included_directories": list(config_manager.config["file_filters"]["include_dirs"]),
                        "excluded_file_patterns": list(config_manager.config["file_filters"]["exclude_files"])
                    }
                }
                
                # Print results
                print_directory_results(results, complexity_threshold)
                
                # Generate XML log for transparency
                xml_log = f"""<log>
    <excluded_directories>
        {chr(10).join([f'        <directory>{dir}</directory>' for dir in config_manager.config["file_filters"]["exclude_dirs"]])}
    </excluded_directories>
    <scanned_files_count>{len(results)}</scanned_files_count>
</log>"""
                logger.info(f"Analysis log:\n{xml_log}")
                
                # Save results to file if requested
                if output:
                    # If using a project, save to project directory
                    if project and config_manager.current_project:
                        project_output = os.path.join(config_manager.get_project_logs_dir(), os.path.basename(output))
                        if save_json(output_data, project_output):
                            logger.info(f"Results saved to {project_output}")
                            print(f"Results saved to {project_output}")
                        else:
                            logger.error(f"Failed to save results to {project_output}")
                            print(f"Error: Failed to save results to {project_output}")
                    else:
                        if save_json(output_data, output):
                            logger.info(f"Results saved to {output}")
                            print(f"Results saved to {output}")
                        else:
                            logger.error(f"Failed to save results to {output}")
                            print(f"Error: Failed to save results to {output}")
                
                return
            except Exception as e:
                logger.error(f"Error analyzing directory: {str(e)}")
                logger.debug(traceback.format_exc())
                print(f"Error analyzing directory: {str(e)}")
                if debug:
                    print(traceback.format_exc())
                return
        
        # Analyze a single file
        logger.info(f"Analyzing file: {path}")
        
        try:
            # Read the file
            with open(path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Create analyzer
            analyzer = CodeAnalyzer(path)
            
            # Analyze the code
            result = analyzer.analyze()
            
            # Set complexity threshold
            result["complexity_threshold"] = complexity_threshold
            
            # Print results
            print_analysis_results(result, complexity_threshold)
            
            # Perform security scan if requested
            scan_results = {}
            if security_scan:
                logger.info(f"Performing security scan for {path}")
                print(f"\nPerforming security scan for {path}...")
                
                try:
                    # Scan the code
                    scan_results = scan_code(code, path)
                    
                    # Print scan results
                    print_security_scan_results(scan_results)
                except Exception as e:
                    logger.error(f"Error performing security scan: {str(e)}")
                    logger.debug(traceback.format_exc())
                    print(f"Error performing security scan: {str(e)}")
                    if debug:
                        print(traceback.format_exc())
                
                # Add security scan results to the output
                if "security_scan" not in result:
                    result["security_scan"] = scan_results
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            print(f"Error reading file {path}: {e}")
            return
        
        # Perform dependency scanning if requested
        if dependency_scan:
            try:
                logger.info(f"Performing dependency scan for project containing {path}")
                from .dependency_scanner import DependencyScanner
                
                # Use the directory containing the file as the project directory
                project_dir = os.path.dirname(os.path.abspath(path))
                scanner = DependencyScanner(project_dir)
                scan_results = scanner.run_scan()
                print_dependency_scan_results(scan_results)
                
                # Add dependency scan results to the output
                if "dependency_scan" not in result:
                    result["dependency_scan"] = scan_results
            except Exception as e:
                logger.error(f"Error during dependency scan: {e}")
                print(f"Error during dependency scan: {e}")
        
        # Perform AI-powered code review if requested
        if ai:
            # Check if API key is provided
            if not api_key:
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    logger.error("OpenAI API key is required for AI-powered code review")
                    print("Error: OpenAI API key is required for AI-powered code review.")
                    print("Please provide it with --api-key or set the OPENAI_API_KEY environment variable.")
                    return
            
            logger.info("Generating AI-powered code review")
            print("\nGenerating AI-powered code review...")
            
            try:
                # Generate AI review
                ai_review = generate_ai_review(code, path, api_key, model)
                
                # Print the AI review
                print_ai_review(ai_review)
                
                # Add AI review to the result
                result["ai_review"] = ai_review
                
                # Apply fixes if requested
                if apply_fixes:
                    try:
                        # Log that we're applying fixes
                        interaction_logger.log_interaction(
                            interaction_type="apply_fixes",
                            description=f"Applying AI-suggested fixes to {path}"
                        )
                        
                        fix_results = apply_ai_fixes(path, ai_review, api_key, model)
                        
                        # Log the results of applying fixes
                        for file_path, file_result in fix_results.items():
                            if file_result.get("success", False):
                                interaction_logger.log_approval(
                                    file=file_path,
                                    description=f"Applied fix to {file_path}",
                                    details={
                                        "changes": file_result.get("changes", []),
                                        "original": file_result.get("original", ""),
                                        "modified": file_result.get("modified", "")
                                    }
                                )
                            else:
                                interaction_logger.log_rejection(
                                    file=file_path,
                                    reason=file_result.get("error", "Unknown error"),
                                    description=f"Failed to apply fix to {file_path}"
                                )
                        
                        print_fix_results(fix_results)
                        result["fix_results"] = fix_results
                    except Exception as e:
                        logger.error(f"Error applying AI fixes: {e}")
                        print(f"Error applying AI fixes: {e}")
            except Exception as e:
                logger.error(f"Error generating AI review: {e}")
                print(f"Error generating AI review: {e}")
        
        # Generate unified report if requested
        if generate_report:
            try:
                logger.info(f"Generating unified report for {path}")
                print(f"\nGenerating unified report for {path}...")
                
                # Import here to avoid circular imports
                from .report_generator import ReportGenerator
                
                # Create report generator
                report_generator = ReportGenerator(
                    code_analysis=result,
                    ai_review=result.get("ai_review", {}),
                    security_scan=result.get("security_scan", {}),
                    dependency_scan=result.get("dependency_scan", {})
                )
                
                # Generate report
                report = report_generator.generate_report(report_format, path)
                
                # Save report to file
                if project and config_manager.current_project:
                    # Save to project reports directory
                    reports_dir = config_manager.get_project_reports_dir()
                    if reports_dir:
                        report_filename = f"{os.path.basename(path)}_report.{report_format}"
                        report_path = os.path.join(reports_dir, report_filename)
                        success = report_generator.save_report_to_file(report_path, report_format)
                        if success:
                            logger.info(f"Unified report saved to {report_path}")
                            print(f"Unified report saved to {report_path}")
                        else:
                            logger.error(f"Error saving unified report to {report_path}")
                            print(f"Error saving unified report to {report_path}")
                else:
                    # Save to output file if specified
                    if output:
                        report_path = f"{os.path.splitext(output)[0]}_report.{report_format}"
                        success = report_generator.save_report_to_file(report_path, report_format)
                        if success:
                            logger.info(f"Unified report saved to {report_path}")
                            print(f"Unified report saved to {report_path}")
                        else:
                            logger.error(f"Error saving unified report to {report_path}")
                            print(f"Error saving unified report to {report_path}")
                    else:
                        # Print report to console if no output file is specified
                        print("\n" + "=" * 80)
                        print(f"UNIFIED REPORT ({report_format.upper()})")
                        print("=" * 80)
                        print(report)
                        print("=" * 80)
                
                # Add report to the result
                result["unified_report"] = {
                    "format": report_format,
                    "content": report
                }
            except Exception as e:
                logger.error(f"Error generating unified report: {e}")
                print(f"Error generating unified report: {e}")
                if debug:
                    print(traceback.format_exc())
        
        # Perform UI validation if requested
        if ui_validate:
            try:
                logger.info(f"Validating UI changes for {url}")
                print(f"\nValidating UI changes for {url}...")
                
                # Import here to avoid circular imports
                from .ui_validator import validate_ui
                
                # Create report directory
                if project and config_manager.current_project:
                    # Use project reports directory
                    report_dir = config_manager.get_project_reports_dir()
                    if not report_dir:
                        report_dir = "logs/ui_reports"
                        os.makedirs(report_dir, exist_ok=True)
                else:
                    report_dir = "logs/ui_reports"
                    os.makedirs(report_dir, exist_ok=True)
                
                # Validate the UI
                results = validate_ui(
                    url=url, 
                    api_key=api_key,
                    report_format=ui_report_format,
                    report_dir=report_dir
                )
                
                # Print UI validation results
                print_ui_validation_results(results)
                
                # Add UI validation results to the overall result
                result["ui_validation"] = {
                    "success": results.get("success", False),
                    "report_paths": results.get("report_paths", {}),
                    "before_image": results.get("before_image", ""),
                    "after_image": results.get("after_image", "")
                }
            except Exception as e:
                logger.error(f"Error performing UI validation: {str(e)}")
                print(f"Error performing UI validation: {str(e)}")
                if debug:
                    print(traceback.format_exc())
        
        # Save results to file if requested
        if output:
            if project and config_manager.current_project:
                # Save to project logs directory
                project_output = os.path.join(config_manager.get_project_logs_dir(), os.path.basename(output))
                if save_json(result, project_output):
                    logger.info(f"Results saved to {project_output}")
                    print(f"Results saved to {project_output}")
                else:
                    logger.error(f"Failed to save results to {project_output}")
                    print(f"Error: Failed to save results to {project_output}")
            else:
                if save_json(result, output):
                    logger.info(f"Results saved to {output}")
                    print(f"Results saved to {output}")
                else:
                    logger.error(f"Failed to save results to {output}")
                    print(f"Error: Failed to save results to {output}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.debug(traceback.format_exc())
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)


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
    # Configure logging based on debug flag
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create CLI log file if it doesn't exist
    cli_log_path = os.path.join(logs_dir, "cli_log.md")
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
    
    # Check if path is provided
    if not hasattr(args, 'path') or args.path is None:
        print("Error: Path is required for code review.")
        print("Use --list-projects to list available projects.")
        return
    
    # Handle project selection or creation
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
        
        if not project:
            if args.create_project:
                # Prompt for confirmation before creating a new project
                confirm = input(f"Create new project '{project_name}' at path '{project_path}'? (Y/N): ")
                if confirm.lower() != "y":
                    print("Project creation cancelled.")
                    
                    # Log the operation
                    with open(cli_log_path, "a") as log_file:
                        log_file.write(f"## {datetime.datetime.now()} - Project Creation Cancelled\n\n")
                        log_file.write(f"Project: {project_name}\n")
                        log_file.write(f"Path: {project_path}\n\n")
                        
                    return
                
                # Create new project
                logger.info(f"Creating new project '{project_name}' at path '{project_path}'")
                if config_manager.add_project(project_name, project_path):
                    logger.info(f"Project '{project_name}' created successfully")
                    
                    # Log the operation
                    with open(cli_log_path, "a") as log_file:
                        log_file.write(f"## {datetime.datetime.now()} - Project Created\n\n")
                        log_file.write(f"Project: {project_name}\n")
                        log_file.write(f"Path: {project_path}\n\n")
                    
                    # Create virtual environment for the project
                    venv_path = os.path.join(project_path, "venv")
                    if not os.path.exists(venv_path):
                        print(f"🔄 Creating virtual environment for project: {project_name}")
                        try:
                            # Create virtual environment
                            subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
                            logger.info(f"Virtual environment created at {venv_path}")
                            
                            # Install ai_review in the virtual environment
                            print(f"🔄 Installing AI Code Review Tool in virtual environment...")
                            
                            # Determine the path to the ai_code_review package
                            ai_review_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
                            
                            # Use the appropriate pip command based on the OS
                            if platform.system() == "Windows":
                                pip_path = os.path.join(venv_path, "Scripts", "pip")
                                python_path = os.path.join(venv_path, "Scripts", "python")
                            else:  # Unix/Linux/Mac
                                pip_path = os.path.join(venv_path, "bin", "pip")
                                python_path = os.path.join(venv_path, "bin", "python")
                            
                            # Install the package in development mode
                            subprocess.run([pip_path, "install", "-e", ai_review_path], check=True)
                            
                            # Set PYTHONPATH environment variable
                            os.environ["PYTHONPATH"] = os.path.abspath(ai_review_path)
                            
                            logger.info(f"AI Code Review Tool installed in virtual environment")
                        except subprocess.CalledProcessError as e:
                            logger.error(f"Error setting up virtual environment: {str(e)}")
                            print(f"⚠ Warning: Failed to set up virtual environment. Continuing without it.")
                else:
                    logger.error(f"Failed to create project '{project_name}'")
                    print(f"Error: Failed to create project '{project_name}'")
                    
                    # Log the operation
                    with open(cli_log_path, "a") as log_file:
                        log_file.write(f"## {datetime.datetime.now()} - Project Creation Failed\n\n")
                        log_file.write(f"Project: {project_name}\n")
                        log_file.write(f"Path: {project_path}\n")
                        log_file.write(f"Error: Failed to create project\n\n")
                        
                    return
            else:
                logger.error(f"Project '{project_name}' not found. Use --create-project to create it.")
                print(f"Error: Project '{project_name}' not found. Use --create-project to create it.")
                
                # Log the operation
                with open(cli_log_path, "a") as log_file:
                    log_file.write(f"## {datetime.datetime.now()} - Project Not Found\n\n")
                    log_file.write(f"Project: {project_name}\n")
                    log_file.write(f"Path: {project_path}\n")
                    log_file.write(f"Error: Project not found and --create-project flag not set\n\n")
                    
                return
        
        # Set current project
        if not config_manager.set_current_project(project_name):
            logger.error(f"Failed to set current project to '{project_name}'")
            print(f"Error: Failed to set current project to '{project_name}'")
            
            # Log the operation
            with open(cli_log_path, "a") as log_file:
                log_file.write(f"## {datetime.datetime.now()} - Failed to Set Current Project\n\n")
                log_file.write(f"Project: {project_name}\n\n")
                
            return
        
        # Log the project selection
        with open(cli_log_path, "a") as log_file:
            log_file.write(f"## {datetime.datetime.now()} - Running AI Review\n\n")
            log_file.write(f"Project: {project_name}\n")
            log_file.write(f"Path: {project_path}\n")
            log_file.write(f"Options:\n")
            log_file.write(f"- AI: {args.ai}\n")
            log_file.write(f"- Apply Fixes: {args.apply_fixes}\n")
            log_file.write(f"- Security Scan: {args.security_scan}\n")
            log_file.write(f"- Dependency Scan: {args.dependency_scan}\n")
            log_file.write(f"- Generate Report: {args.generate_report}\n\n")
        
        # Check if virtual environment exists and activate it
        venv_path = os.path.join(project_path, "venv")
        if os.path.exists(venv_path):
            logger.info(f"Using virtual environment at {venv_path}")
            print(f"🔄 Using virtual environment for project: {project_name}")
            
            # Determine the appropriate activation script based on the OS
            if platform.system() == "Windows":
                activate_script = os.path.join(venv_path, "Scripts", "activate.bat")
                python_path = os.path.join(venv_path, "Scripts", "python")
            else:  # Unix/Linux/Mac
                activate_script = os.path.join(venv_path, "bin", "activate")
                python_path = os.path.join(venv_path, "bin", "python")
            
            # Set environment variables to use the virtual environment
            os.environ["VIRTUAL_ENV"] = venv_path
            
            # Set PYTHONPATH environment variable
            ai_review_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            os.environ["PYTHONPATH"] = os.path.abspath(ai_review_path)
            
            # Modify PATH to prioritize the virtual environment
            os.environ["PATH"] = os.pathsep.join([
                os.path.join(venv_path, "bin" if platform.system() != "Windows" else "Scripts"),
                os.environ.get("PATH", "")
            ])
            
            # Unset PYTHONHOME if it exists
            if "PYTHONHOME" in os.environ:
                del os.environ["PYTHONHOME"]
            
            # Try to activate the virtual environment
            try:
                if platform.system() == "Windows":
                    # On Windows, we can call the activate.bat script
                    subprocess.run([activate_script], shell=True, check=True)
                else:
                    # On Unix/Linux/Mac, we need to source the activate script
                    # This is a bit tricky because 'source' is a shell builtin, not a command
                    # First, try to determine the user's shell
                    shell = os.environ.get('SHELL', '/bin/bash')
                    
                    # Check if the shell exists
                    if not os.path.exists(shell):
                        # Try common shells in order of preference
                        for possible_shell in ['/bin/bash', '/bin/zsh', '/bin/sh']:
                            if os.path.exists(possible_shell):
                                shell = possible_shell
                                break
                    
                    # Use the appropriate source command based on the shell
                    source_cmd = "source"
                    if shell.endswith('csh') or shell.endswith('tcsh'):
                        source_cmd = "."
                        
                    # Run the activation command
                    subprocess.run(f"{source_cmd} {activate_script}", shell=True, executable=shell, check=True)
                
                logger.info(f"Virtual environment activated successfully")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to activate virtual environment: {str(e)}")
                print(f"⚠ Warning: Failed to activate virtual environment. Continuing anyway.")
            except Exception as e:
                logger.warning(f"Unexpected error activating virtual environment: {str(e)}")
                print(f"⚠ Warning: Failed to activate virtual environment. Continuing anyway.")
        else:
            logger.warning(f"Virtual environment not found at {venv_path}")
            print(f"⚠ Warning: Virtual environment not found. Creating one...")
            
            try:
                # Create virtual environment
                subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
                logger.info(f"Virtual environment created at {venv_path}")
                
                # Install ai_review in the virtual environment
                print(f"🔄 Installing AI Code Review Tool in virtual environment...")
                
                # Determine the path to the ai_code_review package
                ai_review_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
                
                # Use the appropriate pip command based on the OS
                if platform.system() == "Windows":
                    pip_path = os.path.join(venv_path, "Scripts", "pip")
                    python_path = os.path.join(venv_path, "Scripts", "python")
                    activate_script = os.path.join(venv_path, "Scripts", "activate.bat")
                else:  # Unix/Linux/Mac
                    pip_path = os.path.join(venv_path, "bin", "pip")
                    python_path = os.path.join(venv_path, "bin", "python")
                
                # Install the package in development mode
                subprocess.run([pip_path, "install", "-e", ai_review_path], check=True)
                
                # Set environment variables to use the virtual environment
                os.environ["VIRTUAL_ENV"] = venv_path
                
                # Set PYTHONPATH environment variable
                os.environ["PYTHONPATH"] = os.path.abspath(ai_review_path)
                
                # Modify PATH to prioritize the virtual environment
                os.environ["PATH"] = os.pathsep.join([
                    os.path.join(venv_path, "bin" if platform.system() != "Windows" else "Scripts"),
                    os.environ.get("PATH", "")
                ])
                
                # Unset PYTHONHOME if it exists
                if "PYTHONHOME" in os.environ:
                    del os.environ["PYTHONHOME"]
                
                # Try to activate the virtual environment
                try:
                    if platform.system() == "Windows":
                        # On Windows, we can call the activate.bat script
                        subprocess.run([activate_script], shell=True, check=True)
                    else:
                        # On Unix/Linux/Mac, we need to source the activate script
                        # This is a bit tricky because 'source' is a shell builtin, not a command
                        # First, try to determine the user's shell
                        shell = os.environ.get('SHELL', '/bin/bash')
                        
                        # Check if the shell exists
                        if not os.path.exists(shell):
                            # Try common shells in order of preference
                            for possible_shell in ['/bin/bash', '/bin/zsh', '/bin/sh']:
                                if os.path.exists(possible_shell):
                                    shell = possible_shell
                                    break
                        
                        # Use the appropriate source command based on the shell
                        source_cmd = "source"
                        if shell.endswith('csh') or shell.endswith('tcsh'):
                            source_cmd = "."
                            
                        # Run the activation command
                        subprocess.run(f"{source_cmd} {activate_script}", shell=True, executable=shell, check=True)
                
                logger.info(f"Virtual environment activated successfully")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to activate virtual environment: {str(e)}")
                print(f"⚠ Warning: Failed to activate virtual environment. Continuing anyway.")
            except Exception as e:
                logger.warning(f"Unexpected error activating virtual environment: {str(e)}")
                print(f"⚠ Warning: Failed to activate virtual environment. Continuing anyway.")
        
        logger.info(f"Using project '{project_name}' for configuration and logs")
        print(f"Using project '{project_name}' for configuration and logs")
        
        # Create project configuration if it doesn't exist
        project_config_file = os.path.join(project_path, "config.json")
        if not os.path.exists(project_config_file):
            logger.info(f"Creating project configuration file at '{project_config_file}'")
            if config_manager.save_project_config():
                logger.info(f"Project configuration file created successfully")
            else:
                logger.error(f"Failed to create project configuration file")
                print(f"Error: Failed to create project configuration file")
                return
    
    # Log the review command
    interaction_logger.log_command(
        command="review",
        description=f"Reviewing code at path: {args.path}",
        additional_details={
            "path": args.path,
            "ai": args.ai,
            "apply_fixes": args.apply_fixes,
            "security_scan": args.security_scan,
            "dependency_scan": args.dependency_scan,
            "generate_report": args.generate_report,
            "project": args.project if args.project else "None"
        }
    )
    
    # Call the review_code function with the arguments from the command line
    result = review_code(
        path=args.path,
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
        debug=args.debug,
        project=args.project
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


def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Configure logging based on debug flag
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Handle commands
    if args.command == "review":
        handle_review_command(args)
    elif args.command == "plugin":
        handle_plugin_command(args)
    elif args.command == "config":
        handle_config_command(args)
    else:
        logger.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main() 
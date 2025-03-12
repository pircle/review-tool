"""
Report Generator for AI Code Review Tool.

This module provides functionality to generate unified reports from various analysis results.
"""

import os
import json
import datetime
from typing import Dict, Any, Optional, List, Union
from .logger import logger

class ReportGenerator:
    """
    Generates unified reports from various analysis results.
    
    This class collects results from different analyses (code analysis, AI review,
    security scan, dependency scan) and formats them into readable reports.
    """
    
    def __init__(
        self,
        code_analysis: Dict[str, Any] = None,
        ai_review: Dict[str, Any] = None,
        security_scan: Dict[str, Any] = None,
        dependency_scan: Dict[str, Any] = None
    ):
        """
        Initialize the ReportGenerator with analysis results.
        
        Args:
            code_analysis: Results from code analysis
            ai_review: Results from AI-powered code review
            security_scan: Results from security scanning
            dependency_scan: Results from dependency scanning
        """
        self.code_analysis = code_analysis or {}
        self.ai_review = ai_review or {}
        self.security_scan = security_scan or {}
        self.dependency_scan = dependency_scan or {}
        
    def generate_report(self, format_type: str, file_path: str) -> str:
        """
        Generate a unified report in the specified format.
        
        Args:
            format_type: Format of the report ('json' or 'markdown')
            file_path: Path to the file being analyzed
            
        Returns:
            Formatted report as a string
        """
        if format_type.lower() == 'json':
            return self._generate_json_report(file_path)
        elif format_type.lower() == 'markdown' or format_type.lower() == 'md':
            return self._generate_markdown_report(file_path)
        else:
            logger.error(f"Unsupported report format: {format_type}")
            return f"Error: Unsupported report format '{format_type}'. Supported formats: json, markdown"
    
    def _generate_json_report(self, file_path: str) -> str:
        """
        Generate a JSON report.
        
        Args:
            file_path: Path to the file being analyzed
            
        Returns:
            JSON-formatted report as a string
        """
        report = {
            "report_type": "unified_code_review",
            "timestamp": datetime.datetime.now().isoformat(),
            "file_path": file_path,
            "code_analysis": self.code_analysis,
            "ai_review": self.ai_review,
            "security_scan": self.security_scan,
            "dependency_scan": self.dependency_scan
        }
        
        try:
            return json.dumps(report, indent=2)
        except Exception as e:
            logger.error(f"Error generating JSON report: {e}")
            return json.dumps({"error": f"Failed to generate JSON report: {str(e)}"})
    
    def _generate_markdown_report(self, file_path: str) -> str:
        """
        Generate a Markdown report.
        
        Args:
            file_path: Path to the file being analyzed
            
        Returns:
            Markdown-formatted report as a string
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Start building the markdown report
        md = f"# Unified Code Review Report\n\n"
        md += f"**File:** {file_path}  \n"
        md += f"**Generated:** {timestamp}  \n\n"
        
        # Code Analysis Section
        md += "## Code Analysis\n\n"
        if self.code_analysis:
            functions = self.code_analysis.get("functions", [])
            classes = self.code_analysis.get("classes", [])
            
            md += f"**Lines of Code:** {self.code_analysis.get('loc', 'N/A')}  \n"
            
            if functions:
                md += "\n### Functions\n\n"
                md += "| Name | Line | Complexity | Status |\n"
                md += "|------|------|------------|--------|\n"
                
                for func in functions:
                    name = func.get("name", "Unknown")
                    line = func.get("line", "N/A")
                    complexity = func.get("complexity", "N/A")
                    status = "Complex" if func.get("is_complex", False) else "Normal"
                    
                    md += f"| {name} | {line} | {complexity} | {status} |\n"
            
            if classes:
                md += "\n### Classes\n\n"
                md += "| Name | Line | Methods |\n"
                md += "|------|------|--------|\n"
                
                for cls in classes:
                    name = cls.get("name", "Unknown")
                    line = cls.get("line", "N/A")
                    methods = len(cls.get("methods", []))
                    
                    md += f"| {name} | {line} | {methods} |\n"
        else:
            md += "*No code analysis results available.*\n\n"
        
        # AI Review Section
        md += "\n## AI Code Review\n\n"
        if self.ai_review:
            suggestions = self.ai_review.get("suggestions", [])
            
            if suggestions:
                md += "### Suggestions\n\n"
                
                for i, suggestion in enumerate(suggestions, 1):
                    md += f"**{i}. {suggestion.get('title', 'Suggestion')}**\n\n"
                    md += f"{suggestion.get('description', '')}\n\n"
                    
                    if "code" in suggestion:
                        md += "```\n"
                        md += f"{suggestion.get('code', '')}\n"
                        md += "```\n\n"
            else:
                md += "*No AI suggestions available.*\n\n"
        else:
            md += "*No AI review results available.*\n\n"
        
        # Security Scan Section
        md += "\n## Security Scan\n\n"
        if self.security_scan:
            vulnerabilities = self.security_scan.get("vulnerabilities", [])
            
            if vulnerabilities:
                md += "| Type | Line | Severity | Description |\n"
                md += "|------|------|----------|-------------|\n"
                
                for vuln in vulnerabilities:
                    vuln_type = vuln.get("type", "Unknown")
                    line = vuln.get("line", "N/A")
                    severity = vuln.get("severity", "Medium").capitalize()
                    description = vuln.get("description", vuln.get("detail", "No description"))
                    
                    md += f"| {vuln_type} | {line} | {severity} | {description} |\n"
            else:
                md += "*No security vulnerabilities detected.*\n\n"
        else:
            md += "*No security scan results available.*\n\n"
        
        # Dependency Scan Section
        md += "\n## Dependency Scan\n\n"
        if self.dependency_scan:
            vulnerable_deps = self.dependency_scan.get("vulnerable_dependencies", [])
            
            if vulnerable_deps:
                md += "| Package | Version | Severity | Vulnerability |\n"
                md += "|---------|---------|----------|---------------|\n"
                
                for dep in vulnerable_deps:
                    package = dep.get("package", "Unknown")
                    version = dep.get("version", "N/A")
                    severity = dep.get("severity", "Medium").capitalize()
                    vuln_desc = dep.get("vulnerability", "No description")
                    
                    md += f"| {package} | {version} | {severity} | {vuln_desc} |\n"
            else:
                md += "*No vulnerable dependencies detected.*\n\n"
        else:
            md += "*No dependency scan results available.*\n\n"
        
        # Summary Section
        md += "\n## Summary\n\n"
        
        # Count issues
        complex_funcs = sum(1 for f in self.code_analysis.get("functions", []) if f.get("complexity", 0) > self.code_analysis.get("complexity_threshold", 5))
        ai_suggestions = len(self.ai_review.get("suggestions", []))
        security_issues = len(self.security_scan.get("vulnerabilities", []))
        dependency_issues = len(self.dependency_scan.get("vulnerable_dependencies", []))
        
        total_issues = complex_funcs + ai_suggestions + security_issues + dependency_issues
        
        md += f"**Total Issues:** {total_issues}  \n"
        md += f"- Complex Functions: {complex_funcs}  \n"
        md += f"- AI Suggestions: {ai_suggestions}  \n"
        md += f"- Security Vulnerabilities: {security_issues}  \n"
        md += f"- Vulnerable Dependencies: {dependency_issues}  \n\n"
        
        return md
    
    def save_report_to_file(self, file_path: str, format_type: str) -> bool:
        """
        Save the report to a file.
        
        Args:
            file_path: Path to save the report
            format_type: Format of the report ('json' or 'markdown')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the directory path
            dir_path = os.path.dirname(file_path)
            
            # Create directory if it doesn't exist
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
            
            # Generate the report
            report_content = self.generate_report(format_type, os.path.basename(file_path))
            
            # Write to file
            with open(file_path, 'w') as f:
                f.write(report_content)
            
            logger.info(f"Report saved to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving report to {file_path}: {e}")
            return False


if __name__ == "__main__":
    # Sample test
    ai_review = {
        "summary": "Code looks good but has performance issues.",
        "quality": 7,
        "suggestions": {
            "performance": [
                {
                    "title": "Inefficient Database Query",
                    "severity": "high",
                    "location": "get_user_by_id (line 78)",
                    "description": "The function loads all user data before filtering.",
                    "improvement": "Use a direct query with WHERE clause instead."
                }
            ]
        },
        "best_practices": ["Add type hints to function parameters", "Use context managers for file operations"],
        "bugs": ["The session token is not checked for expiration"]
    }
    
    security_scan = {
        "summary": {
            "total_issues": 1,
            "high_severity": 1,
            "medium_severity": 0,
            "low_severity": 0
        },
        "issues": [
            {
                "type": "hardcoded_credentials",
                "title": "Hardcoded API Key",
                "severity": "high",
                "line": 45,
                "detail": "API key found in source code",
                "recommendation": "Store sensitive information in environment variables"
            }
        ]
    }
    
    dependency_scan = {
        "summary": {
            "total_issues": 2,
            "high_severity": 1,
            "medium_severity": 1,
            "low_severity": 0,
            "unknown_severity": 0
        },
        "python": [
            {
                "package_name": "django",
                "vulnerable_version": "2.2.0",
                "severity": "high",
                "description": "Cross-site scripting vulnerability",
                "fixed_version": "2.2.28"
            }
        ],
        "javascript": [
            {
                "module_name": "axios",
                "severity": "medium",
                "title": "Server-Side Request Forgery",
                "recommendation": "Update to version 0.21.1 or later",
                "url": "https://github.com/advisories/GHSA-42xw-2xvc-qx8m"
            }
        ]
    }
    
    code_analysis = {
        "file_path": "example.py",
        "language": "Python",
        "loc": 150,
        "functions": [
            {"name": "get_user", "line": 10, "complexity": 2},
            {"name": "process_data", "line": 25, "complexity": 8}
        ],
        "classes": [
            {"name": "UserManager", "line": 50, "methods": 5}
        ]
    }
    
    # Create report generator and test both formats
    report_generator = ReportGenerator(ai_review, security_scan, dependency_scan, code_analysis)
    
    json_report = report_generator.generate_report("json", "example.py")
    print("JSON Report:")
    print(json_report)
    print("\n" + "=" * 80 + "\n")
    
    md_report = report_generator.generate_report("markdown", "example.py")
    print("Markdown Report:")
    print(md_report) 
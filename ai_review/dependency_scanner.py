"""
Dependency vulnerability scanner for the AI code review system.
Scans Python and JavaScript/TypeScript dependencies for known vulnerabilities.
"""

import os
import json
import subprocess
from typing import Dict, List, Any, Optional
from pathlib import Path
import shutil

from .logger import logger

class DependencyScanner:
    """
    Scanner for detecting vulnerabilities in dependencies.
    Supports Python (using safety) and JavaScript/TypeScript (using npm audit).
    """
    
    def __init__(self, project_dir: Optional[str] = None):
        """
        Initialize the dependency scanner.
        
        Args:
            project_dir: Directory containing the project files (requirements.txt, package.json)
                         If None, uses the current directory
        """
        self.project_dir = project_dir or os.getcwd()
        logger.debug(f"Initializing dependency scanner for directory: {self.project_dir}")
    
    def _find_requirements_file(self) -> Optional[str]:
        """Find requirements.txt file in the project directory."""
        req_file = os.path.join(self.project_dir, "requirements.txt")
        if os.path.exists(req_file):
            return req_file
        
        # Look for other common Python dependency files
        for filename in ["Pipfile", "pyproject.toml", "setup.py"]:
            file_path = os.path.join(self.project_dir, filename)
            if os.path.exists(file_path):
                logger.info(f"Found Python dependency file: {filename}")
                return file_path
        
        return None
    
    def _find_package_json(self) -> Optional[str]:
        """Find package.json file in the project directory."""
        pkg_file = os.path.join(self.project_dir, "package.json")
        if os.path.exists(pkg_file):
            return pkg_file
        return None
    
    def scan_python_dependencies(self) -> List[Dict[str, Any]]:
        """
        Runs safety check for Python dependencies.
        
        Returns:
            List of vulnerability dictionaries
        """
        requirements_file = self._find_requirements_file()
        if not requirements_file:
            logger.warning("No Python dependency file found (requirements.txt, Pipfile, etc.)")
            return []
        
        try:
            logger.info(f"Scanning Python dependencies using safety: {requirements_file}")
            
            # Check if safety is installed
            if not shutil.which("safety"):
                logger.error("Safety not installed. Please install with: pip install safety")
                return [{
                    "package": "unknown",
                    "vulnerability_id": "TOOL_MISSING",
                    "affected_versions": "all",
                    "description": "Safety tool is not installed. Cannot scan Python dependencies.",
                    "severity": "unknown",
                    "recommendation": "Install safety with: pip install safety"
                }]
                
            # Run safety check
            cmd = ["safety", "check", "--json", "-r", requirements_file]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Parse the output
            if result.returncode == 0:
                logger.info("No Python vulnerabilities found")
                return []
            
            try:
                vulnerabilities = json.loads(result.stdout)
                if isinstance(vulnerabilities, dict):
                    return vulnerabilities.get("vulnerabilities", [])
                return vulnerabilities  # In some versions, safety returns a list directly
            except json.JSONDecodeError:
                # Handle case where safety doesn't output valid JSON
                logger.warning("Could not parse safety output as JSON")
                if result.stdout:
                    # Try to extract information from text output
                    return [{
                        "package": line.split("[")[0].strip() if "[" in line else line,
                        "severity": "unknown",
                        "description": line,
                        "raw_output": True
                    } for line in result.stdout.splitlines() if line.strip()]
                return []
                
        except Exception as e:
            logger.error(f"Error running safety check: {e}")
            return [{
                "error": str(e),
                "message": "Error running safety check",
                "severity": "high"
            }]
    
    def scan_js_dependencies(self) -> Dict[str, Any]:
        """
        Runs npm audit for JavaScript/TypeScript dependencies.
        
        Returns:
            Dictionary of vulnerability advisories
        """
        package_json = self._find_package_json()
        if not package_json:
            logger.warning("No package.json file found")
            return {}
        
        try:
            logger.info(f"Scanning JavaScript dependencies using npm audit: {package_json}")
            
            # Check if npm is installed
            if not shutil.which("npm"):
                logger.error("npm not installed. Please install Node.js and npm")
                return {
                    "error": "npm not installed",
                    "message": "Please install Node.js and npm from https://nodejs.org/",
                    "severity": "unknown",
                    "recommendation": "Install Node.js from https://nodejs.org/"
                }
            
            # Change to directory containing package.json
            original_dir = os.getcwd()
            os.chdir(os.path.dirname(package_json))
            
            try:
                # Run npm audit
                result = subprocess.run(["npm", "audit", "--json"], capture_output=True, text=True)
                
                # Parse the output
                try:
                    audit_result = json.loads(result.stdout)
                    return audit_result.get("advisories", {})
                except json.JSONDecodeError:
                    logger.warning("Could not parse npm audit output as JSON")
                    return {
                        "error": "Invalid JSON output",
                        "message": "npm audit did not return valid JSON",
                        "raw_output": result.stdout
                    }
            finally:
                # Change back to the original directory
                os.chdir(original_dir)
                
        except Exception as e:
            logger.error(f"Error running npm audit: {e}")
            return {
                "error": str(e),
                "message": "Error running npm audit",
                "severity": "high"
            }
    
    def run_scan(self) -> Dict[str, Any]:
        """
        Runs all dependency checks and returns structured results.
        
        Returns:
            Dictionary containing scan results for Python and JavaScript dependencies
        """
        logger.info("Starting dependency vulnerability scan")
        
        # Check for required tools before running scans
        
        # Check for safety (Python dependency scanner)
        safety_available = shutil.which("safety") is not None
        if not safety_available:
            logger.warning("⚠️ Warning: `safety` is not installed. Skipping Python dependency scan.")
            logger.info("To install safety, run: pip install safety")
        
        # Check for npm (JavaScript dependency scanner)
        npm_available = shutil.which("npm") is not None
        if not npm_available:
            logger.warning("⚠️ Warning: `npm` is not installed. Skipping JavaScript dependency scan.")
            logger.info("To install npm, install Node.js from https://nodejs.org/")
        
        # Run scans based on available tools
        python_vulnerabilities = self.scan_python_dependencies() if safety_available else []
        js_vulnerabilities = self.scan_js_dependencies() if npm_available else {}
        
        # Add warnings to results if tools are missing
        warnings = []
        
        if not safety_available:
            warnings.append({
                "tool": "safety",
                "message": "Python dependency scanner (safety) is not installed",
                "install_command": "pip install safety",
                "documentation_url": "https://pypi.org/project/safety/"
            })
            
        if not npm_available:
            warnings.append({
                "tool": "npm",
                "message": "JavaScript dependency scanner (npm) is not installed",
                "install_command": "Install Node.js from https://nodejs.org/",
                "documentation_url": "https://nodejs.org/en/download/"
            })
        
        # Combine results
        results = {
            "python": {
                "vulnerabilities": python_vulnerabilities,
                "count": len(python_vulnerabilities),
                "tool_available": safety_available
            },
            "javascript": {
                "vulnerabilities": js_vulnerabilities,
                "count": len(js_vulnerabilities.get("advisories", {})),
                "tool_available": npm_available
            },
            "warnings": warnings,
            "tools_missing": not (safety_available or npm_available)
        }
        
        # Add summary information
        all_vulnerabilities = []
        if python_vulnerabilities:
            all_vulnerabilities.extend(python_vulnerabilities)
        
        if js_vulnerabilities and "advisories" in js_vulnerabilities:
            for advisory_id, advisory in js_vulnerabilities["advisories"].items():
                all_vulnerabilities.append({
                    "package": advisory.get("module_name", "unknown"),
                    "vulnerability_id": advisory_id,
                    "affected_versions": advisory.get("vulnerable_versions", "unknown"),
                    "description": advisory.get("overview", "No description available"),
                    "severity": advisory.get("severity", "unknown"),
                    "recommendation": advisory.get("recommendation", "Update to the latest version")
                })
        
        results["vulnerable_dependencies"] = all_vulnerabilities
        results["total_vulnerabilities"] = len(all_vulnerabilities)
        
        logger.info(f"Dependency scan complete. Found {results['total_vulnerabilities']} vulnerabilities.")
        return results


if __name__ == "__main__":
    # When run directly, scan the current directory and print results
    scanner = DependencyScanner()
    results = scanner.run_scan()
    print(json.dumps(results, indent=2)) 
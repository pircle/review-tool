"""
Security scanner module for detecting vulnerabilities in code.
"""

import re
import json
import shutil
from typing import Dict, List, Any, Optional
import os

from .logger import get_logger

logger = get_logger()

def check_dependency_tools() -> Dict[str, bool]:
    """
    Check if required dependency scanning tools are installed.
    
    Returns:
        Dictionary with tool availability status
    """
    tools = {
        "safety": shutil.which("safety") is not None,
        "npm": shutil.which("npm") is not None
    }
    
    # Log warnings for missing tools
    if not tools["safety"]:
        logger.warning("⚠️ Warning: `safety` is not installed. Skipping Python dependency scan.")
    
    if not tools["npm"]:
        logger.warning("⚠️ Warning: `npm` is not installed. Skipping JavaScript dependency scan.")
    
    return tools

class SecurityScanner:
    """
    Scans code for security vulnerabilities and issues.
    Supports Python, JavaScript, and TypeScript code.
    """
    
    def __init__(self, code: str, file_path: Optional[str] = None):
        """
        Initialize the security scanner.
        
        Args:
            code: Source code to scan
            file_path: Path to the file being scanned (optional, used for language detection)
        """
        self.code = code
        self.file_path = file_path
        self.issues = []
        self.language = self._determine_language()
        logger.info(f"Initialized SecurityScanner for language: {self.language}")
    
    def _determine_language(self) -> str:
        """
        Determine the language of the code based on file extension.
        
        Returns:
            Language name
        """
        if not self.file_path:
            return "unknown"
        
        file_extension = os.path.splitext(self.file_path)[1].lower()
        
        if file_extension == ".py":
            return "python"
        elif file_extension == ".js":
            return "javascript"
        elif file_extension in [".ts", ".tsx"]:
            return "typescript"
        elif file_extension in [".java"]:
            return "java"
        elif file_extension in [".c", ".cpp", ".h", ".hpp"]:
            return "c++"
        else:
            return "unknown"
    
    def scan_hardcoded_secrets(self) -> None:
        """
        Detects hardcoded API keys, passwords, and credentials.
        """
        logger.debug("Scanning for hardcoded secrets")
        
        # Common patterns across languages
        patterns = [
            (r'(?i)(api_key|apikey|secret|password|passwd|pwd|token|auth_token|credentials)\s*=\s*[\'"]([^\'"]{8,})[\'"]', 
             "Hardcoded credential", "high"),
            (r'(?i)(aws_access_key_id|aws_secret_access_key|aws_session_token)\s*=\s*[\'"]([^\'"]+)[\'"]', 
             "AWS credential", "high"),
            (r'(?i)(AKIA[0-9A-Z]{16})', 
             "AWS Access Key ID", "high"),
            (r'(?i)github_token\s*=\s*[\'"]([^\'"]+)[\'"]', 
             "GitHub token", "high"),
            (r'(?i)(sk-[a-zA-Z0-9]{48})', 
             "OpenAI API key", "high"),
            (r'(?i)(SG\.[a-zA-Z0-9]{22}\.[a-zA-Z0-9]{43})', 
             "SendGrid API key", "high"),
            (r'(?i)(xox[pboa]-[0-9]{12}-[0-9]{12}-[0-9]{12}-[a-z0-9]{32})', 
             "Slack API token", "high"),
            (r'(?i)([a-z0-9_-]{23}\.ey[a-z0-9_-]+\.[a-z0-9_-]{10,})', 
             "JSON Web Token", "medium")
        ]
        
        # Language-specific patterns
        if self.language == "python":
            patterns.extend([
                (r'(?i)os\.environ\.get\([\'"]([^\'"]+_key|[^\'"]+_secret|password|token)[\'"].*?,\s*[\'"]([^\'"]+)[\'"]', 
                 "Hardcoded fallback in environment variable", "medium"),
                (r'(?i)config\[[\'"]([^\'"]+_key|[^\'"]+_secret|password|token)[\'"]\]\s*=\s*[\'"]([^\'"]+)[\'"]', 
                 "Hardcoded credential in config", "high")
            ])
        elif self.language in ["javascript", "typescript"]:
            patterns.extend([
                (r'(?i)process\.env\.([A-Z_]+_KEY|[A-Z_]+_SECRET|PASSWORD|TOKEN)\s*\|\|\s*[\'"]([^\'"]+)[\'"]', 
                 "Hardcoded fallback in environment variable", "medium"),
                (r'(?i)config\.([a-zA-Z]+[kK]ey|[a-zA-Z]+[sS]ecret|password|token)\s*=\s*[\'"]([^\'"]+)[\'"]', 
                 "Hardcoded credential in config", "high")
            ])
        
        line_number = 0
        for line in self.code.splitlines():
            line_number += 1
            for pattern, issue_type, severity in patterns:
                matches = re.findall(pattern, line)
                if matches:
                    for match in matches:
                        # If match is a tuple (from capturing groups), use the last group as the credential
                        credential = match[-1] if isinstance(match, tuple) else match
                        # Mask the credential for security
                        masked_credential = self._mask_credential(credential)
                        
                        self.issues.append({
                            "type": "security",
                            "category": "credentials",
                            "issue": f"{issue_type} detected",
                            "detail": f"Hardcoded {issue_type.lower()} found: {masked_credential}",
                            "line": line_number,
                            "severity": severity,
                            "recommendation": "Store sensitive information in environment variables or a secure vault"
                        })
                        logger.info(f"Found hardcoded credential at line {line_number}")
    
    def _mask_credential(self, credential: str) -> str:
        """
        Mask a credential for security purposes.
        
        Args:
            credential: The credential to mask
            
        Returns:
            Masked credential (first 4 and last 4 characters visible)
        """
        if len(credential) <= 8:
            return "****"
        return credential[:4] + "*" * (len(credential) - 8) + credential[-4:]
    
    def scan_sql_injection(self) -> None:
        """
        Detects potential SQL injection vulnerabilities.
        """
        logger.debug("Scanning for SQL injection vulnerabilities")
        
        # Common patterns across languages
        patterns = []
        
        # Language-specific patterns
        if self.language == "python":
            patterns = [
                (r"execute\([\"']SELECT.*?WHERE.*?\+.*?\)", 
                 "String concatenation in SQL query"),
                (r"execute\([\"']SELECT.*?WHERE.*?%.*?%.*?\)", 
                 "String formatting in SQL query"),
                (r"execute\([\"']SELECT.*?WHERE.*?\{.*?\}.*?\.format", 
                 "String formatting in SQL query"),
                (r"execute\([\"']SELECT.*?WHERE.*?f[\"']", 
                 "f-string in SQL query"),
                (r"execute\([\"']INSERT INTO.*?\+.*?\)", 
                 "String concatenation in SQL query"),
                (r"execute\([\"']UPDATE.*?SET.*?\+.*?\)", 
                 "String concatenation in SQL query"),
                (r"execute\([\"']DELETE FROM.*?WHERE.*?\+.*?\)", 
                 "String concatenation in SQL query"),
                (r"cursor\.execute\([\"'].*?[\"']\s*\+\s*", 
                 "String concatenation in SQL query"),
                (r"cursor\.executemany\([\"'].*?[\"']\s*\+\s*", 
                 "String concatenation in SQL query")
            ]
        elif self.language == "javascript":
            patterns = [
                (r"connection\.query\([\"']SELECT.*?WHERE.*?\+.*?\)", 
                 "String concatenation in SQL query"),
                (r"connection\.query\([\"']INSERT INTO.*?\+.*?\)", 
                 "String concatenation in SQL query"),
                (r"connection\.query\([\"']UPDATE.*?SET.*?\+.*?\)", 
                 "String concatenation in SQL query"),
                (r"connection\.query\([\"']DELETE FROM.*?WHERE.*?\+.*?\)", 
                 "String concatenation in SQL query"),
                (r"db\.query\([\"'].*?[\"']\s*\+\s*", 
                 "String concatenation in SQL query"),
                (r"`SELECT.*?WHERE.*?${.*?}`", 
                 "Template literal in SQL query")
            ]
        elif self.language == "typescript":
            patterns = [
                (r"connection\.query\([\"']SELECT.*?WHERE.*?\+.*?\)", 
                 "String concatenation in SQL query"),
                (r"connection\.query\([\"']INSERT INTO.*?\+.*?\)", 
                 "String concatenation in SQL query"),
                (r"connection\.query\([\"']UPDATE.*?SET.*?\+.*?\)", 
                 "String concatenation in SQL query"),
                (r"connection\.query\([\"']DELETE FROM.*?WHERE.*?\+.*?\)", 
                 "String concatenation in SQL query"),
                (r"db\.query\([\"'].*?[\"']\s*\+\s*", 
                 "String concatenation in SQL query"),
                (r"`SELECT.*?WHERE.*?${.*?}`", 
                 "Template literal in SQL query")
            ]
        
        line_number = 0
        for line in self.code.splitlines():
            line_number += 1
            for pattern, issue_type in patterns:
                if re.search(pattern, line):
                    self.issues.append({
                        "type": "security",
                        "category": "sql_injection",
                        "issue": "Potential SQL Injection vulnerability",
                        "detail": f"{issue_type} detected",
                        "line": line_number,
                        "severity": "high",
                        "recommendation": "Use parameterized queries or prepared statements instead of string concatenation"
                    })
                    logger.info(f"Found potential SQL injection at line {line_number}")
    
    def scan_xss_vulnerabilities(self) -> None:
        """
        Detects potential Cross-Site Scripting (XSS) vulnerabilities.
        Only applicable for JavaScript and TypeScript.
        """
        if self.language not in ["javascript", "typescript"]:
            return
            
        logger.debug("Scanning for XSS vulnerabilities")
        
        patterns = [
            (r"innerHTML\s*=\s*.*?(?:params|query|input|data|request|req\.body|req\.query|req\.params)",
             "Unescaped data assigned to innerHTML"),
            (r"document\.write\s*\(.*?(?:params|query|input|data|request|req\.body|req\.query|req\.params)",
             "Unescaped data in document.write()"),
            (r"\.html\s*\(.*?(?:params|query|input|data|request|req\.body|req\.query|req\.params)",
             "Unescaped data in jQuery .html()"),
            (r"eval\s*\(.*?(?:params|query|input|data|request|req\.body|req\.query|req\.params)",
             "User input in eval()"),
            (r"setTimeout\s*\(.*?(?:params|query|input|data|request|req\.body|req\.query|req\.params)",
             "User input in setTimeout()"),
            (r"setInterval\s*\(.*?(?:params|query|input|data|request|req\.body|req\.query|req\.params)",
             "User input in setInterval()"),
            (r"new Function\s*\(.*?(?:params|query|input|data|request|req\.body|req\.query|req\.params)",
             "User input in Function constructor")
        ]
        
        line_number = 0
        for line in self.code.splitlines():
            line_number += 1
            for pattern, issue_type in patterns:
                if re.search(pattern, line):
                    self.issues.append({
                        "type": "security",
                        "category": "xss",
                        "issue": "Potential Cross-Site Scripting (XSS) vulnerability",
                        "detail": f"{issue_type}",
                        "line": line_number,
                        "severity": "high",
                        "recommendation": "Sanitize user input before inserting it into the DOM"
                    })
                    logger.info(f"Found potential XSS vulnerability at line {line_number}")
    
    def scan_insecure_crypto(self) -> None:
        """
        Detects usage of insecure cryptographic algorithms.
        """
        logger.debug("Scanning for insecure cryptographic algorithms")
        
        # Common patterns across languages
        weak_algorithms = [
            "MD5", "SHA1", "DES", "RC4", "Blowfish"
        ]
        
        # Language-specific patterns
        if self.language == "python":
            patterns = [
                (r"hashlib\.md5\(", "MD5 hashing algorithm"),
                (r"hashlib\.sha1\(", "SHA1 hashing algorithm"),
                (r"Crypto\.Cipher\.DES", "DES encryption algorithm"),
                (r"Crypto\.Cipher\.Blowfish", "Blowfish encryption algorithm"),
                (r"Crypto\.Cipher\.ARC4", "RC4 encryption algorithm"),
                (r"cryptography\.hazmat\.primitives\.hashes\.MD5", "MD5 hashing algorithm"),
                (r"cryptography\.hazmat\.primitives\.hashes\.SHA1", "SHA1 hashing algorithm")
            ]
        elif self.language in ["javascript", "typescript"]:
            patterns = [
                (r"crypto\.createHash\([\"']md5[\"']\)", "MD5 hashing algorithm"),
                (r"crypto\.createHash\([\"']sha1[\"']\)", "SHA1 hashing algorithm"),
                (r"crypto\.createCipheriv\([\"']des[\"']", "DES encryption algorithm"),
                (r"crypto\.createCipheriv\([\"']des-ede3[\"']", "Triple DES encryption algorithm"),
                (r"crypto\.createCipheriv\([\"']rc4[\"']", "RC4 encryption algorithm"),
                (r"crypto\.createCipheriv\([\"']bf[\"']", "Blowfish encryption algorithm")
            ]
        
        line_number = 0
        for line in self.code.splitlines():
            line_number += 1
            
            # Check for weak algorithm names in the line
            for algorithm in weak_algorithms:
                if algorithm.lower() in line.lower():
                    # Further check with more specific patterns
                    for pattern, issue_type in patterns:
                        if re.search(pattern, line):
                            self.issues.append({
                                "type": "security",
                                "category": "crypto",
                                "issue": "Insecure cryptographic algorithm",
                                "detail": f"Usage of {issue_type}",
                                "line": line_number,
                                "severity": "medium",
                                "recommendation": f"Replace {algorithm} with a more secure algorithm (e.g., SHA-256, AES)"
                            })
                            logger.info(f"Found insecure cryptographic algorithm at line {line_number}")
                            break
    
    def scan_path_traversal(self) -> None:
        """
        Detects potential path traversal vulnerabilities.
        """
        logger.debug("Scanning for path traversal vulnerabilities")
        
        # Language-specific patterns
        if self.language == "python":
            patterns = [
                (r"open\s*\(.*?\+.*?\)", "File path concatenation"),
                (r"open\s*\(f[\"'].*?\{.*?\}.*?[\"']\)", "File path interpolation"),
                (r"os\.path\.join\s*\(.*?,\s*.*?(?:request|input|data|params).*?\)", "User input in file path"),
                (r"with\s+open\s*\(.*?(?:request|input|data|params).*?\)", "User input in file path")
            ]
        elif self.language in ["javascript", "typescript"]:
            patterns = [
                (r"fs\.readFile\s*\(.*?\+.*?\)", "File path concatenation"),
                (r"fs\.readFileSync\s*\(.*?\+.*?\)", "File path concatenation"),
                (r"fs\.writeFile\s*\(.*?\+.*?\)", "File path concatenation"),
                (r"fs\.writeFileSync\s*\(.*?\+.*?\)", "File path concatenation"),
                (r"path\.join\s*\(.*?,\s*.*?(?:req\.params|req\.query|req\.body).*?\)", "User input in file path"),
                (r"require\s*\(.*?\+.*?\)", "Dynamic require with concatenation")
            ]
        
        line_number = 0
        for line in self.code.splitlines():
            line_number += 1
            for pattern, issue_type in patterns:
                if re.search(pattern, line):
                    self.issues.append({
                        "type": "security",
                        "category": "path_traversal",
                        "issue": "Potential path traversal vulnerability",
                        "detail": f"{issue_type} detected",
                        "line": line_number,
                        "severity": "high",
                        "recommendation": "Validate and sanitize file paths, use path.resolve() to normalize paths"
                    })
                    logger.info(f"Found potential path traversal vulnerability at line {line_number}")
    
    def scan_command_injection(self) -> None:
        """
        Detects potential command injection vulnerabilities.
        """
        logger.debug("Scanning for command injection vulnerabilities")
        
        # Language-specific patterns
        if self.language == "python":
            patterns = [
                (r"os\.system\s*\(.*?\+.*?\)", "Command string concatenation"),
                (r"os\.system\s*\(f[\"'].*?\{.*?\}.*?[\"']\)", "Command string interpolation"),
                (r"subprocess\.call\s*\(.*?\+.*?\)", "Command string concatenation"),
                (r"subprocess\.call\s*\(f[\"'].*?\{.*?\}.*?[\"']\)", "Command string interpolation"),
                (r"subprocess\.Popen\s*\(.*?\+.*?\)", "Command string concatenation"),
                (r"subprocess\.Popen\s*\(f[\"'].*?\{.*?\}.*?[\"']\)", "Command string interpolation"),
                (r"eval\s*\(.*?(?:request|input|data|params).*?\)", "User input in eval()")
            ]
        elif self.language in ["javascript", "typescript"]:
            patterns = [
                (r"child_process\.exec\s*\(.*?\+.*?\)", "Command string concatenation"),
                (r"child_process\.execSync\s*\(.*?\+.*?\)", "Command string concatenation"),
                (r"child_process\.spawn\s*\(.*?\+.*?\)", "Command string concatenation"),
                (r"child_process\.spawnSync\s*\(.*?\+.*?\)", "Command string concatenation"),
                (r"child_process\.exec\s*\(`.*?${.*?}.*?`\)", "Command string interpolation"),
                (r"eval\s*\(.*?(?:req\.params|req\.query|req\.body).*?\)", "User input in eval()")
            ]
        
        line_number = 0
        for line in self.code.splitlines():
            line_number += 1
            for pattern, issue_type in patterns:
                if re.search(pattern, line):
                    self.issues.append({
                        "type": "security",
                        "category": "command_injection",
                        "issue": "Potential command injection vulnerability",
                        "detail": f"{issue_type} detected",
                        "line": line_number,
                        "severity": "high",
                        "recommendation": "Avoid using user input in command strings, use parameterized commands or argument lists"
                    })
                    logger.info(f"Found potential command injection vulnerability at line {line_number}")
    
    def run_scan(self) -> Dict[str, Any]:
        """
        Run the security scan.
        
        Returns:
            Dictionary with scan results
        """
        logger.info(f"Running security scan for {self.file_path or 'unknown file'}")
        
        # Initialize results
        results = {
            "file_path": self.file_path,
            "vulnerabilities": [],
            "summary": {
                "total_issues": 0,
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0
            }
        }
        
        # Scan for common vulnerabilities
        vulnerabilities = []
        
        # Scan for hardcoded credentials
        self.scan_hardcoded_secrets()
        
        # Scan for SQL injection vulnerabilities
        self.scan_sql_injection()
        
        # Scan for command injection vulnerabilities
        self.scan_command_injection()
        
        # Scan for insecure cryptographic algorithms
        self.scan_insecure_crypto()
        
        # Add vulnerabilities to results
        results["vulnerabilities"] = self.issues
        
        # Update summary
        results["summary"]["total_issues"] = len(self.issues)
        results["summary"]["high_severity"] = sum(1 for v in self.issues if v.get("severity") == "high")
        results["summary"]["medium_severity"] = sum(1 for v in self.issues if v.get("severity") == "medium")
        results["summary"]["low_severity"] = sum(1 for v in self.issues if v.get("severity") == "low")
        
        logger.info(f"Security scan complete: {results['summary']['total_issues']} issues found")
        return results


def scan_code(code: str, file_path: str) -> Dict[str, Any]:
    """
    Scan code for security vulnerabilities.
    
    Args:
        code: Source code to scan
        file_path: Path to the file being scanned
        
    Returns:
        Dictionary with scan results
    """
    logger.info(f"Scanning code for security vulnerabilities: {file_path}")
    
    # Initialize results
    results = {
        "file_path": file_path,
        "vulnerabilities": [],
        "summary": {
            "total_issues": 0,
            "high_severity": 0,
            "medium_severity": 0,
            "low_severity": 0
        }
    }
    
    vulnerabilities = []
    
    # Scan for hardcoded credentials
    for i, line in enumerate(code.splitlines(), 1):
        # Check for API keys
        if re.search(r'(?i)API_KEY\s*=\s*["\']([^"\']+)["\']', line):
            vulnerabilities.append({
                "type": "HARDCODED_CREDENTIALS",
                "line": i,
                "severity": "high",
                "detail": "Hardcoded API key found",
                "recommendation": "Store sensitive information in environment variables or a secure vault"
            })
        
        # Check for SQL injection
        if "SELECT * FROM users WHERE id =" in line and not "?" in line:
            vulnerabilities.append({
                "type": "SQL_INJECTION",
                "line": i,
                "severity": "high",
                "detail": "Potential SQL injection vulnerability",
                "recommendation": "Use parameterized queries or prepared statements"
            })
        
        # Check for command injection
        if "os.system(" in line and not line.strip().startswith("#"):
            vulnerabilities.append({
                "type": "COMMAND_INJECTION",
                "line": i,
                "severity": "high",
                "detail": "Potential command injection vulnerability",
                "recommendation": "Avoid using user input in system commands or use proper input validation"
            })
    
    # Add vulnerabilities to results
    results["vulnerabilities"] = vulnerabilities
    
    # Update summary
    results["summary"]["total_issues"] = len(vulnerabilities)
    results["summary"]["high_severity"] = sum(1 for v in vulnerabilities if v.get("severity") == "high")
    results["summary"]["medium_severity"] = sum(1 for v in vulnerabilities if v.get("severity") == "medium")
    results["summary"]["low_severity"] = sum(1 for v in vulnerabilities if v.get("severity") == "low")
    
    logger.info(f"Security scan complete: {results['summary']['total_issues']} issues found")
    return results


if __name__ == "__main__":
    # Example usage
    test_code = """
    api_key = "1234567890abcdef"
    password = "mypassword123"
    
    def authenticate(username, password):
        query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'"
        cursor.execute(query)
        return cursor.fetchone()
    
    def get_user_data(user_id):
        with open("data/" + user_id + ".txt", "r") as f:
            return f.read()
    
    def run_command(command):
        os.system("ls -la " + command)
    """
    
    scanner = SecurityScanner(test_code, "example.py")
    results = scanner.run_scan()
    logger.debug(json.dumps(results, indent=2)) 
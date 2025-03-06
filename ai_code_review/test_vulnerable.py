"""
Test file with various security vulnerabilities to test the security scanner.
DO NOT USE THIS CODE IN PRODUCTION - it contains deliberate security flaws.
"""

import os
import hashlib
import sqlite3
import subprocess

# Hardcoded credentials (vulnerability)
API_KEY = "sk-1234567890abcdefghijklmnopqrstuvwxyz1234567890"
PASSWORD = "super_secret_password123"
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# Environment variable with hardcoded fallback (vulnerability)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "ghp_1234567890abcdefghijklmnopqrstuvwxyz")


def authenticate_user(username, password):
    """
    Authenticate a user with SQL injection vulnerability.
    """
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # SQL Injection vulnerability
    query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'"
    cursor.execute(query)
    
    user = cursor.fetchone()
    conn.close()
    
    return user is not None


def hash_password(password):
    """
    Hash a password using insecure algorithm.
    """
    # Insecure hashing algorithm (vulnerability)
    return hashlib.md5(password.encode()).hexdigest()


def get_user_data(user_id):
    """
    Get user data with path traversal vulnerability.
    """
    # Path traversal vulnerability
    file_path = "data/" + user_id + "/profile.json"
    
    with open(file_path, "r") as f:
        return f.read()


def execute_command(command):
    """
    Execute a command with command injection vulnerability.
    """
    # Command injection vulnerability
    result = subprocess.check_output("ls -la " + command, shell=True)
    return result.decode()


def create_backup(filename):
    """
    Create a backup with command injection vulnerability.
    """
    # Command injection vulnerability
    os.system(f"cp {filename} {filename}.bak")
    return f"{filename}.bak"


class UserDatabase:
    """
    User database class with SQL injection vulnerabilities.
    """
    
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
    
    def get_user(self, user_id):
        # SQL Injection vulnerability
        query = "SELECT * FROM users WHERE id = " + user_id
        self.cursor.execute(query)
        return self.cursor.fetchone()
    
    def update_user(self, user_id, name, email):
        # SQL Injection vulnerability
        query = f"UPDATE users SET name = '{name}', email = '{email}' WHERE id = {user_id}"
        self.cursor.execute(query)
        self.conn.commit()
    
    def delete_user(self, user_id):
        # SQL Injection vulnerability
        self.cursor.execute("DELETE FROM users WHERE id = " + user_id)
        self.conn.commit()


# JavaScript-like code (for testing XSS detection)
"""
function displayUserData(userData) {
    // XSS vulnerability
    document.getElementById('user-profile').innerHTML = userData.profile;
    
    // XSS vulnerability
    document.write('<div>' + userData.name + '</div>');
    
    // XSS vulnerability
    eval('console.log(' + userData.settings + ')');
}

function processUserInput(input) {
    // Command injection vulnerability
    const result = execSync('grep ' + input + ' logs.txt');
    return result.toString();
}
"""

if __name__ == "__main__":
    print("This is a test file with deliberate security vulnerabilities.")
    print("DO NOT USE THIS CODE IN PRODUCTION!") 
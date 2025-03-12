"""
A simple test file for the AI Code Review Tool.
"""

def simple_function():
    """A simple function with low complexity."""
    print("Hello, world!")
    return True

def complex_function(a, b, c):
    """A more complex function with moderate complexity."""
    result = 0
    
    if a > 0:
        if b > 0:
            result = a + b
        else:
            result = a - b
    else:
        if c > 0:
            result = a * c
        else:
            result = 0
    
    for i in range(10):
        if i % 2 == 0:
            result += i
    
    return result

class TestClass:
    """A test class with methods."""
    
    def __init__(self, value):
        self.value = value
    
    def get_value(self):
        """Get the value."""
        return self.value
    
    def set_value(self, value):
        """Set the value."""
        self.value = value
        return True

# Potential security vulnerability: hardcoded credentials
API_KEY = "sk_test_1234567890abcdef"

# Potential security vulnerability: SQL injection
def get_user(user_id):
    """Get a user from the database."""
    query = f"SELECT * FROM users WHERE id = {user_id}"
    # Execute query (not implemented)
    return {"id": user_id, "name": "Test User"}

# Potential security vulnerability: command injection
def run_command(command):
    """Run a system command."""
    import os
    os.system(command)  # Vulnerable to command injection
    return True 
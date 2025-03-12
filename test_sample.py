"""
Sample Python file for testing the AI code review system.
"""

import os
import sys
from typing import List, Dict, Any, Optional


class SampleClass:
    """A sample class for testing."""
    
    def __init__(self, name: str, value: int = 0):
        """Initialize the class with a name and value."""
        self.name = name
        self.value = value
        
    def get_name(self) -> str:
        """Return the name."""
        return self.name
    
    def get_value(self) -> int:
        """Return the value."""
        return self.value
    
    def set_value(self, value: int) -> None:
        """Set the value."""
        self.value = value


def simple_function(a: int, b: int) -> int:
    """A simple function that adds two numbers."""
    return a + b


def complex_function(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    A more complex function with higher cyclomatic complexity.
    
    This function processes a list of dictionaries and returns statistics.
    """
    if not data:
        return {"error": "No data provided"}
    
    result = {
        "count": len(data),
        "keys": set(),
        "values": []
    }
    
    for item in data:
        if not isinstance(item, dict):
            continue
            
        for key, value in item.items():
            result["keys"].add(key)
            
            if isinstance(value, (int, float)):
                result["values"].append(value)
                
    if result["values"]:
        result["avg"] = sum(result["values"]) / len(result["values"])
        result["max"] = max(result["values"])
        result["min"] = min(result["values"])
    else:
        result["avg"] = 0
        result["max"] = 0
        result["min"] = 0
        
    # Convert set to list for better serialization
    result["keys"] = list(result["keys"])
    
    return result


def very_complex_function(data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    A very complex function with high cyclomatic complexity.
    
    This function processes data based on various options and conditions.
    """
    result = {}
    options = options or {}
    
    # Process based on data type
    if "type" in data:
        data_type = data["type"]
        
        if data_type == "user":
            if "name" in data:
                result["user_name"] = data["name"]
            else:
                result["error"] = "User name not provided"
                
            if "age" in data and isinstance(data["age"], int):
                if data["age"] < 0:
                    result["error"] = "Invalid age"
                elif data["age"] < 18:
                    result["status"] = "minor"
                else:
                    result["status"] = "adult"
        elif data_type == "product":
            if "price" in data:
                price = data["price"]
                
                if price <= 0:
                    result["error"] = "Invalid price"
                else:
                    # Apply discount if specified in options
                    if "discount" in options and isinstance(options["discount"], (int, float)):
                        discount = options["discount"]
                        
                        if discount > 0 and discount < 100:
                            price = price * (1 - discount / 100)
                            result["discounted_price"] = price
                    
                    result["price"] = price
            
            if "stock" in data:
                stock = data["stock"]
                
                if stock <= 0:
                    result["availability"] = "out_of_stock"
                elif stock < 10:
                    result["availability"] = "low_stock"
                else:
                    result["availability"] = "in_stock"
        else:
            result["error"] = f"Unknown data type: {data_type}"
    else:
        result["error"] = "Data type not specified"
    
    # Add metadata if requested
    if options.get("include_metadata", False):
        result["metadata"] = {
            "processed_at": "2023-01-01",
            "version": "1.0"
        }
    
    return result


if __name__ == "__main__":
    # Example usage
    sample = SampleClass("Test", 42)
    print(f"Name: {sample.get_name()}, Value: {sample.get_value()}")
    
    print(f"Simple function result: {simple_function(5, 7)}")
    
    test_data = [
        {"name": "Item 1", "value": 10},
        {"name": "Item 2", "value": 20},
        {"name": "Item 3", "value": 30}
    ]
    
    print(f"Complex function result: {complex_function(test_data)}")
    
    user_data = {
        "type": "user",
        "name": "John Doe",
        "age": 25
    }
    
    options = {
        "include_metadata": True
    }
    
    print(f"Very complex function result: {very_complex_function(user_data, options)}") 
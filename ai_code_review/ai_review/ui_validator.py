"""
UI Validator module for capturing screenshots and validating UI changes using ChatGPT Vision.

This module provides functionality to:
1. Capture screenshots of web UIs before and after changes
2. Compare screenshots using ChatGPT Vision to detect visual differences
3. Generate text-based analysis of UI changes
"""

import os
import time
import logging
import base64
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Union
import traceback

# Third-party imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
import openai

# Local imports
from .logger import get_logger

# Set up logging
logger = get_logger()

class UIScreenCapture:
    """Class for capturing screenshots of web UIs."""
    
    def __init__(self, url: str, output_dir: str = "logs/screenshots"):
        """
        Initialize the UI screen capture.
        
        Args:
            url: URL of the web page to capture
            output_dir: Directory to save screenshots
        """
        self.url = url
        self.output_dir = output_dir
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        # Initialize Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--window-size=1920,1080")  # Set window size
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info(f"WebDriver initialized for URL: {url}")
        except WebDriverException as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def capture_screenshot(self, label: str = "screenshot") -> str:
        """
        Capture a screenshot of the web page.
        
        Args:
            label: Label for the screenshot (e.g., "before", "after")
            
        Returns:
            Path to the saved screenshot
        """
        filename = f"{self.timestamp}_{label}.png"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            logger.info(f"Navigating to {self.url}")
            self.driver.get(self.url)
            
            # Wait for page to load
            logger.debug("Waiting for page to load")
            time.sleep(2)  # Basic wait
            
            # Capture screenshot
            logger.info(f"Capturing screenshot: {filepath}")
            self.driver.save_screenshot(filepath)
            logger.info(f"Screenshot saved: {filepath}")
            
            return filepath
        except WebDriverException as e:
            logger.error(f"Failed to capture screenshot: {str(e)}")
            raise

    def close(self) -> None:
        """Close the WebDriver."""
        if hasattr(self, 'driver'):
            logger.info("Closing WebDriver")
            self.driver.quit()


class UIValidator:
    """Class for validating UI changes using ChatGPT Vision."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the UI validator.
        
        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("No OpenAI API key provided")
            raise ValueError("OpenAI API key is required for UI validation")
        
        # Set OpenAI API key
        openai.api_key = self.api_key
        logger.info("UIValidator initialized")

    def _encode_image(self, image_path: str) -> str:
        """
        Encode an image file as base64.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64-encoded image
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def compare_screenshots(self, before_image: str, after_image: str) -> Dict[str, Any]:
        """
        Compare two screenshots using ChatGPT Vision API.
        
        Args:
            before_image: Path to the before screenshot
            after_image: Path to the after screenshot
            
        Returns:
            Dictionary containing analysis results
        """
        logger.info(f"Comparing screenshots: {before_image} and {after_image}")
        
        try:
            # Encode images to base64
            try:
                with open(before_image, "rb") as f:
                    before_base64 = base64.b64encode(f.read()).decode("utf-8")
                
                with open(after_image, "rb") as f:
                    after_base64 = base64.b64encode(f.read()).decode("utf-8")
            except (IOError, FileNotFoundError) as e:
                error_msg = f"Failed to read image files: {str(e)}"
                logger.error(error_msg)
                return {
                    "before_image": before_image,
                    "after_image": after_image,
                    "analysis_json": {"error": error_msg},
                    "formatted_analysis": f"❌ Error: {error_msg}. Please verify the screenshot files exist and are accessible.",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            
            # Prepare prompt
            prompt = """
            Analyze these two UI screenshots (before and after) and identify all visual differences.
            
            Focus on these aspects:
            1. Layout changes (positioning, alignment, spacing)
            2. Color changes (background, text, borders)
            3. Missing or added elements
            4. Text content changes
            5. Responsive design issues
            
            For each change, determine if it's likely an unintentional regression or an intentional improvement.
            Assign a severity level (Critical, High, Medium, Low) to each issue.
            
            Respond with a JSON object containing:
            {
                "layout_changes": [{"description": "...", "severity": "...", "likely_intentional": true/false}],
                "color_changes": [{"description": "...", "severity": "...", "likely_intentional": true/false}],
                "element_changes": [{"description": "...", "severity": "...", "likely_intentional": true/false}],
                "text_changes": [{"description": "...", "severity": "...", "likely_intentional": true/false}],
                "critical_issues": ["..."],
                "comparison_confidence": 0-100
            }
            
            Severity levels:
            - Critical: Breaks functionality or severely impacts usability
            - High: Significantly impacts user experience but doesn't break functionality
            - Medium: Noticeable but doesn't significantly impact user experience
            - Low: Minor visual differences that most users wouldn't notice
            
            Intentional vs. Unintentional:
            - Intentional: Changes that appear to be deliberate improvements
            - Unintentional: Changes that appear to be regressions or bugs
            """
            
            # Prepare request
            messages = [
                {
                    "role": "system",
                    "content": "You are a UI/UX analyst specializing in visual regression testing. Your task is to compare before and after screenshots of a web application and identify visual differences."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{before_base64}", "detail": "high"}},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{after_base64}", "detail": "high"}}
                    ]
                }
            ]
            
            # Make API call
            try:
                logger.info("Calling ChatGPT Vision API for screenshot comparison")
                response = openai.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=messages,
                    max_tokens=4096
                )
                logger.info("Screenshot comparison completed")
                
                # Extract JSON from response
                response_text = response.choices[0].message.content
                
                # Try to extract JSON using regex
                json_match = re.search(r'({[\s\S]*})', response_text)
                
                if json_match:
                    try:
                        analysis_json = json.loads(json_match.group(1))
                        logger.info("Successfully parsed analysis JSON")
                    except json.JSONDecodeError as e:
                        error_msg = f"Failed to parse JSON from response: {str(e)}"
                        logger.warning(error_msg)
                        logger.warning(f"Raw response: {response_text}")
                        analysis_json = {"error": error_msg, "raw_text": response_text}
                else:
                    error_msg = "No JSON found in response"
                    logger.warning(error_msg)
                    analysis_json = {"error": error_msg, "raw_text": response_text}
                
                # Format the analysis for display
                formatted_analysis = self._format_analysis(analysis_json)
                
                return {
                    "before_image": before_image,
                    "after_image": after_image,
                    "analysis_json": analysis_json,
                    "formatted_analysis": formatted_analysis,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            except openai.OpenAIError as e:
                error_msg = f"ChatGPT Vision API failed: {str(e)}"
                logger.error(error_msg)
                
                # Determine the specific type of error for a more user-friendly message
                user_friendly_msg = "❌ Error: UI validation could not be completed. Please check your API connection."
                
                if "authentication" in str(e).lower() or "api key" in str(e).lower():
                    user_friendly_msg = "❌ Error: Authentication failed. Please check your OpenAI API key."
                elif "rate limit" in str(e).lower() or "quota" in str(e).lower():
                    user_friendly_msg = "❌ Error: API rate limit exceeded. Please try again later or check your OpenAI usage limits."
                elif "timeout" in str(e).lower() or "timed out" in str(e).lower():
                    user_friendly_msg = "❌ Error: API request timed out. Please check your network connection and try again."
                elif "server" in str(e).lower() or "5xx" in str(e).lower():
                    user_friendly_msg = "❌ Error: OpenAI server error. Please try again later."
                elif "model" in str(e).lower() and "not found" in str(e).lower():
                    user_friendly_msg = "❌ Error: The GPT-4 Vision model is not available. Please check your OpenAI account access."
                
                # Add technical details for debugging
                technical_details = f"\n\nTechnical details (for debugging): {str(e)}"
                
                return {
                    "before_image": before_image,
                    "after_image": after_image,
                    "analysis_json": {"error": error_msg},
                    "formatted_analysis": user_friendly_msg + technical_details,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        except Exception as e:
            error_msg = f"Unexpected error during screenshot comparison: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())  # Log the full traceback for debugging
            
            # Create a user-friendly error message
            user_friendly_msg = "❌ Error: UI validation encountered an unexpected problem."
            
            # Categorize common errors for better user feedback
            if isinstance(e, (IOError, OSError)):
                user_friendly_msg = "❌ Error: File system error during UI validation. Please check file permissions and disk space."
            elif isinstance(e, json.JSONDecodeError):
                user_friendly_msg = "❌ Error: Failed to parse JSON response from the API."
            elif "memory" in str(e).lower():
                user_friendly_msg = "❌ Error: System ran out of memory during UI validation."
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                user_friendly_msg = "❌ Error: Network error during UI validation. Please check your internet connection."
            
            # Add technical details for debugging
            technical_details = f"\n\nTechnical details (for debugging): {str(e)}"
            
            return {
                "before_image": before_image,
                "after_image": after_image,
                "analysis_json": {"error": error_msg},
                "formatted_analysis": user_friendly_msg + technical_details,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    def _format_analysis(self, analysis: Dict[str, Any]) -> str:
        """
        Format the analysis JSON into a readable string with emojis and colors.
        
        Args:
            analysis: Analysis JSON from compare_screenshots
            
        Returns:
            Formatted analysis string
        """
        # Handle error cases
        if not analysis:
            return "Error: No analysis data available"
            
        if "error" in analysis:
            return f"Error: {analysis['error']}"
            
        if "raw_text" in analysis:
            return f"Raw Analysis (JSON parsing failed):\n{analysis['raw_text']}"
            
        if "raw_analysis" in analysis:
            return analysis["raw_analysis"]
        
        # Check if we have a valid analysis structure
        if not isinstance(analysis, dict):
            return f"Error: Invalid analysis format - expected dictionary, got {type(analysis)}"
        
        formatted = []
        
        # Add summary
        formatted.append("🔍 **UI Validation Analysis**")
        formatted.append("----------------------------------")
        
        # Handle new format (with likely_intentional) or old format (with is_issue)
        if "layout_changes" in analysis and isinstance(analysis["layout_changes"], list) and analysis["layout_changes"]:
            # Determine format based on first item
            first_item = analysis["layout_changes"][0] if analysis["layout_changes"] else {}
            using_new_format = "likely_intentional" in first_item
            
            # Add summary if available
            if "summary" in analysis:
                formatted.append(f"📝 **Summary**: {analysis['summary']}")
            else:
                formatted.append("📝 **Summary**: Analysis completed successfully")
            formatted.append("")
            
            # Add layout changes
            layout_changes = analysis.get("layout_changes", [])
            if layout_changes:
                formatted.append("📐 **Layout Changes:**")
                for change in layout_changes:
                    severity = change.get("severity", "low").lower()
                    
                    # Handle different formats
                    if using_new_format:
                        is_intentional = change.get("likely_intentional", True)
                        emoji = self._get_severity_emoji_new(severity, is_intentional)
                        formatted.append(f"   - {change.get('description', 'No description')} ({emoji} {severity.capitalize()}, {'Intentional' if is_intentional else 'Unintentional'})")
                    else:
                        is_issue = change.get("is_issue", False)
                        emoji = self._get_severity_emoji(severity, is_issue)
                        formatted.append(f"   - {change.get('description', 'No description')} ({emoji} {severity.capitalize()})")
                formatted.append("")
            
            # Add color changes
            color_changes = analysis.get("color_changes", [])
            if color_changes:
                formatted.append("🎨 **Color Changes:**")
                for change in color_changes:
                    severity = change.get("severity", "low").lower()
                    
                    # Handle different formats
                    if using_new_format:
                        is_intentional = change.get("likely_intentional", True)
                        emoji = self._get_severity_emoji_new(severity, is_intentional)
                        formatted.append(f"   - {change.get('description', 'No description')} ({emoji} {severity.capitalize()}, {'Intentional' if is_intentional else 'Unintentional'})")
                    else:
                        is_issue = change.get("is_issue", False)
                        emoji = self._get_severity_emoji(severity, is_issue)
                        formatted.append(f"   - {change.get('description', 'No description')} ({emoji} {severity.capitalize()})")
                formatted.append("")
            
            # Add element changes
            element_changes = analysis.get("element_changes", [])
            if element_changes:
                formatted.append("🧩 **Element Changes:**")
                for change in element_changes:
                    severity = change.get("severity", "low").lower()
                    
                    # Handle different formats
                    if using_new_format:
                        is_intentional = change.get("likely_intentional", True)
                        emoji = self._get_severity_emoji_new(severity, is_intentional)
                        formatted.append(f"   - {change.get('description', 'No description')} ({emoji} {severity.capitalize()}, {'Intentional' if is_intentional else 'Unintentional'})")
                    else:
                        is_issue = change.get("is_issue", False)
                        emoji = self._get_severity_emoji(severity, is_issue)
                        formatted.append(f"   - {change.get('description', 'No description')} ({emoji} {severity.capitalize()})")
                formatted.append("")
            
            # Add text changes
            text_changes = analysis.get("text_changes", [])
            if text_changes:
                formatted.append("📝 **Text Changes:**")
                for change in text_changes:
                    severity = change.get("severity", "low").lower()
                    
                    # Handle different formats
                    if using_new_format:
                        is_intentional = change.get("likely_intentional", True)
                        emoji = self._get_severity_emoji_new(severity, is_intentional)
                        formatted.append(f"   - {change.get('description', 'No description')} ({emoji} {severity.capitalize()}, {'Intentional' if is_intentional else 'Unintentional'})")
                    else:
                        is_issue = change.get("is_issue", False)
                        emoji = self._get_severity_emoji(severity, is_issue)
                        formatted.append(f"   - {change.get('description', 'No description')} ({emoji} {severity.capitalize()})")
                formatted.append("")
            
            # Add responsive issues
            responsive_issues = analysis.get("responsive_issues", [])
            if responsive_issues:
                formatted.append("📱 **Responsive Design Issues:**")
                for issue in responsive_issues:
                    severity = issue.get("severity", "low").lower()
                    emoji = self._get_severity_emoji(severity, True)
                    formatted.append(f"   - {issue.get('description', 'No description')} ({emoji} {severity.capitalize()})")
                formatted.append("")
            
            # Add critical issues (highlighted in red)
            critical_issues = analysis.get("critical_issues", [])
            if critical_issues:
                formatted.append("❌ **Critical Issues:**")
                for issue in critical_issues:
                    if isinstance(issue, dict):
                        formatted.append(f"   - ❗ {issue.get('description', 'No description')}")
                    else:
                        formatted.append(f"   - ❗ {issue}")
                formatted.append("")
            
            # Add comparison confidence
            confidence = analysis.get("comparison_confidence", 0)
            formatted.append(f"📊 **Comparison Confidence:** {confidence}%")
        else:
            # Fallback for unexpected format
            formatted.append("⚠️ **Analysis Format Warning**: The analysis structure is not in the expected format.")
            formatted.append("")
            formatted.append("Raw Analysis Data:")
            formatted.append(json.dumps(analysis, indent=2))
        
        return "\n".join(formatted)

    def _get_severity_emoji(self, severity: str, is_issue: bool) -> str:
        """
        Get the appropriate emoji for a severity level.
        
        Args:
            severity: Severity level (minor, moderate, major, critical)
            is_issue: Whether the change is an issue
            
        Returns:
            Emoji representing the severity
        """
        if severity == "critical":
            return "❗"
        elif severity == "major" and is_issue:
            return "⚠️"
        elif severity == "moderate" and is_issue:
            return "⚠️"
        elif severity == "minor" and is_issue:
            return "ℹ️"
        else:
            return "✔️"

    def _get_severity_emoji_new(self, severity: str, is_intentional: bool) -> str:
        """
        Get the appropriate emoji for a severity level using the new format.
        
        Args:
            severity: Severity level (critical, high, medium, low)
            is_intentional: Whether the change is intentional
            
        Returns:
            Emoji representing the severity
        """
        severity = severity.lower()
        if severity == "critical":
            return "❗"
        elif severity == "high" and not is_intentional:
            return "⚠️"
        elif severity == "medium" and not is_intentional:
            return "⚠️"
        elif severity == "low" and not is_intentional:
            return "ℹ️"
        else:
            return "✔️"

    def generate_report(self, analysis: Dict[str, Any], format_type: str = "markdown", output_dir: str = "logs/ui_reports") -> Dict[str, str]:
        """
        Generate a formatted report from the analysis.
        
        Args:
            analysis: Analysis results from compare_screenshots
            format_type: Report format (markdown, json, or both)
            output_dir: Directory to save the report
            
        Returns:
            Dictionary with report paths
        """
        logger.info(f"Generating UI validation report in {format_type} format")
        
        # Validate format_type
        valid_formats = ["markdown", "json", "both"]
        if format_type not in valid_formats:
            logger.error(f"Invalid report format: {format_type}. Must be one of {valid_formats}")
            # Default to markdown if invalid format is provided
            format_type = "markdown"
            logger.info(f"Defaulting to {format_type} format")
        
        # Create output directory if it doesn't exist
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create output directory {output_dir}: {str(e)}")
            # Use a fallback directory
            output_dir = "logs"
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Using fallback directory: {output_dir}")
        
        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Initialize report paths
        report_paths = {}
        
        # Generate JSON report
        if format_type == "json" or format_type == "both":
            json_path = os.path.join(output_dir, f"ui_report_{timestamp}.json")
            try:
                with open(json_path, "w") as f:
                    json.dump(analysis["analysis_json"], f, indent=2)
                logger.info(f"JSON report saved to {json_path}")
                report_paths["json"] = json_path
            except (IOError, KeyError) as e:
                logger.error(f"Failed to generate JSON report: {str(e)}")
                report_paths["json_error"] = str(e)
        
        # Generate Markdown report
        if format_type == "markdown" or format_type == "both":
            markdown_path = os.path.join(output_dir, f"ui_report_{timestamp}.md")
            
            try:
                # Format the report
                report = f"""
# UI Validation Report

## Overview

- **Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Before Screenshot**: {os.path.basename(analysis.get("before_image", "N/A"))}
- **After Screenshot**: {os.path.basename(analysis.get("after_image", "N/A"))}

## Analysis

{analysis.get("formatted_analysis", "No analysis available")}

## Screenshots

Before: {analysis.get("before_image", "N/A")}
After: {analysis.get("after_image", "N/A")}
"""
                
                with open(markdown_path, "w") as f:
                    f.write(report)
                logger.info(f"Markdown report saved to {markdown_path}")
                report_paths["markdown"] = markdown_path
            except (IOError, KeyError) as e:
                logger.error(f"Failed to generate Markdown report: {str(e)}")
                report_paths["markdown_error"] = str(e)
        
        return report_paths


def validate_ui(url: str, api_key: Optional[str] = None, output_dir: str = "logs/screenshots", 
               report_format: str = "markdown", report_dir: str = "logs/ui_reports") -> Dict[str, Any]:
    """
    Capture screenshots and validate UI changes.
    
    Args:
        url: URL of the web page to validate
        api_key: OpenAI API key
        output_dir: Directory to save screenshots
        report_format: Format for the report (markdown, json, or both)
        report_dir: Directory to save reports
        
    Returns:
        Dictionary containing validation results
    """
    logger.info(f"Starting UI validation for {url}")
    
    # Validate URL format
    if not url.startswith(('http://', 'https://')):
        error_msg = f"Invalid URL format: {url}. URL must start with http:// or https://"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
    
    # Validate report format
    valid_formats = ["markdown", "json", "both"]
    if report_format not in valid_formats:
        logger.warning(f"Invalid report format: {report_format}. Must be one of {valid_formats}")
        report_format = "markdown"
        logger.info(f"Defaulting to {report_format} format")
    
    screen_capture = None
    try:
        # Create output directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(report_dir, exist_ok=True)
        
        # Initialize screen capture
        screen_capture = UIScreenCapture(url, output_dir)
        
        # Capture before screenshot
        before_image = screen_capture.capture_screenshot("before")
        logger.info(f"Before screenshot captured: {before_image}")
        
        # Prompt user to make changes
        input("Make UI changes and press Enter to continue...")
        
        # Capture after screenshot
        after_image = screen_capture.capture_screenshot("after")
        logger.info(f"After screenshot captured: {after_image}")
        
        # Close WebDriver
        screen_capture.close()
        
        # Initialize UI validator
        ui_validator = UIValidator(api_key)
        
        # Compare screenshots
        analysis = ui_validator.compare_screenshots(before_image, after_image)
        
        # Check if analysis contains an error
        if "error" in analysis.get("analysis_json", {}):
            logger.error(f"Error in screenshot comparison: {analysis['analysis_json']['error']}")
            return {
                "success": False,
                "error": f"Screenshot comparison failed: {analysis['analysis_json']['error']}",
                "before_image": before_image,
                "after_image": after_image
            }
        
        # Generate report
        report_paths = ui_validator.generate_report(analysis, report_format, report_dir)
        
        # Prepare result
        result = {
            "before_image": before_image,
            "after_image": after_image,
            "analysis": analysis.get("formatted_analysis", "No analysis available"),
            "analysis_json": analysis.get("analysis_json", {}),
            "report_paths": report_paths,
            "success": True
        }
        
        # Add report path for backward compatibility
        if "markdown" in report_paths:
            result["report_path"] = report_paths["markdown"]
        elif "json" in report_paths:
            result["report_path"] = report_paths["json"]
        
        return result
        
    except Exception as e:
        logger.error(f"UI validation failed: {str(e)}")
        # Ensure WebDriver is closed in case of error
        if screen_capture:
            try:
                screen_capture.close()
            except Exception as close_error:
                logger.error(f"Error closing WebDriver: {str(close_error)}")
        
        return {
            "success": False,
            "error": str(e)
        } 
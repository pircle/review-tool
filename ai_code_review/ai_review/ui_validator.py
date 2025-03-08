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
from pathlib import Path

# Third-party imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
import openai
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage
from webdriver_manager.chrome import ChromeDriverManager

# Local imports
from .logger import logger  # Import the logger directly
from .constants import SCREENSHOTS_DIR, UI_REPORTS_DIR, get_project_screenshots_dir, get_project_ui_reports_dir, LOGS_DIR
from .config_manager import config_manager
from .models import UIValidationResult, UIValidationResults

class UIScreenCapture:
    """Class for capturing screenshots of web UIs."""
    
    def __init__(self, url: str, output_dir: Optional[str] = None):
        """
        Initialize the UI screen capture.
        
        Args:
            url: URL of the web page to capture
            output_dir: Directory to save screenshots (defaults to project screenshots directory)
        """
        self.url = url
        
        # Use the provided output_dir or get it from the project config
        if output_dir is None:
            if config_manager.current_project:
                project = config_manager.get_project(config_manager.current_project)
                if project:
                    # Use project-specific screenshots directory
                    output_dir = get_project_screenshots_dir(project["path"])
                    logger.info(f"Using project screenshots directory: {output_dir}")
                else:
                    logger.warning("Current project not found in config, using default screenshots directory")
                    output_dir = SCREENSHOTS_DIR
            else:
                logger.warning("No current project set, using default screenshots directory")
                output_dir = SCREENSHOTS_DIR
        
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Screenshots will be saved to: {self.output_dir}")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
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
    
    def __init__(self, project_name: str, api_key: Optional[str] = None):
        self.project_name = project_name
        self.log_dir = Path(LOGS_DIR) / project_name
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.ui_log_path = self.log_dir / "ui_validation_log.json"
        self.validation_results = UIValidationResults()
        self._load_existing_results()
        
        self.client = OpenAI(api_key=api_key) if api_key else None

    def _load_existing_results(self):
        """Load existing validation results from the log file."""
        if self.ui_log_path.exists():
            with open(self.ui_log_path) as f:
                data = json.load(f)
                for validation in data.get("validations", []):
                    validation['timestamp'] = datetime.fromisoformat(validation['timestamp'])
                    self.validation_results.validations.append(UIValidationResult(**validation))

    def _save_results(self):
        """Save validation results to the log file."""
        data = self.validation_results.dict()
        data['timestamp'] = data['timestamp'].isoformat()
        for validation in data['validations']:
            validation['timestamp'] = validation['timestamp'].isoformat()
        
        with open(self.ui_log_path, 'w') as f:
            json.dump(data, f, indent=2)

    def compare_screenshots(self, before_image: str, after_image: str) -> UIValidationResult:
        """Compare two screenshots and analyze the differences."""
        try:
            # Read and encode images
            with open(before_image, 'rb') as f:
                before_base64 = base64.b64encode(f.read()).decode('utf-8')
            with open(after_image, 'rb') as f:
                after_base64 = base64.b64encode(f.read()).decode('utf-8')

            # Prepare messages for the API
            messages = [
                {
                    "role": "system",
                    "content": self._get_analysis_prompt()
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Compare these two UI screenshots and identify any visual changes:"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{before_base64}",
                                "detail": "high"
                            }
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{after_base64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]

            # Make API call
            response = self.client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=messages,
                max_tokens=1000,
                temperature=0
            )

            # Parse response
            analysis = response.choices[0].message.content
            changes = self._parse_changes(analysis)

            # Create validation result
            result = UIValidationResult(
                url=before_image,  # Using image path as URL for now
                status="passed" if not changes else "failed",
                summary=analysis,
                changes=changes,
                timestamp=datetime.now()
            )

            # Add to results and save
            self.validation_results.validations.append(result)
            self._save_results()

            return result

        except Exception as e:
            logger.error(f"Error comparing screenshots: {str(e)}")
            raise

    def _get_analysis_prompt(self) -> str:
        """Get the prompt for UI analysis."""
        return """You are a UI/UX expert analyzing visual changes between two versions of a user interface.
        Please analyze the following aspects and provide a structured response:
        1. Layout changes (position, size, alignment)
        2. Color changes (background, text, borders)
        3. Element changes (added, removed, modified)
        4. Text content changes
        
        Format your response as a clear summary followed by specific changes in each category.
        Focus on user impact and potential issues. Be precise in describing locations and changes."""

    def _parse_changes(self, analysis: str) -> List[Dict[str, Any]]:
        """Parse the analysis text into structured changes."""
        changes = []
        
        # Simple parsing - can be enhanced based on actual API response format
        categories = ["Layout changes", "Color changes", "Element changes", "Text content changes"]
        current_category = None
        
        for line in analysis.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check if line is a category header
            for category in categories:
                if category in line:
                    current_category = category
                    break
            
            # If we have a category and this isn't a header, it's a change
            if current_category and not any(category in line for category in categories):
                changes.append({
                    "category": current_category,
                    "description": line
                })
        
        return changes

    def get_results(self) -> UIValidationResults:
        """Get all validation results."""
        return self.validation_results

    def _get_vision_model(self) -> str:
        """
        Get an available vision-capable model.
        
        Returns:
            Name of an available vision model
        
        Raises:
            ValueError: If no suitable vision model is available
        """
        # Preferred models in order of preference (latest to oldest)
        preferred_models = [
            "gpt-4-vision",         # Latest stable vision model
            "gpt-4.5-vision",       # Future model (if available)
            "gpt-4-turbo-vision",   # Alternative name
            "gpt-4o"                # Fallback option
        ]
        
        try:
            # Get available models if not already cached
            if self._available_models is None:
                logger.info("Fetching available models from OpenAI")
                response = self.client.models.list()
                self._available_models = [model.id for model in response.data]
                logger.debug(f"Available models: {', '.join(self._available_models)}")
            
            # First try to find vision-specific models
            vision_models = [model for model in self._available_models if any(
                keyword in model.lower() for keyword in ["vision", "gpt-4o"]
            )]
            logger.debug(f"Found vision-capable models: {', '.join(vision_models)}")
            
            # Check preferred models first
            for model in preferred_models:
                if model in self._available_models:
                    logger.info(f"Using preferred vision model: {model}")
                    return model
            
            # If no preferred models are available, try any vision-capable model
            if vision_models:
                # Sort by version number to get the latest
                sorted_models = sorted(vision_models, reverse=True)
                selected_model = sorted_models[0]
                logger.info(f"Using available vision model: {selected_model}")
                return selected_model
            
            # If no vision models are found, try GPT-4 models as they might support vision
            gpt4_models = [model for model in self._available_models if "gpt-4" in model.lower()]
            if gpt4_models:
                selected_model = sorted(gpt4_models, reverse=True)[0]
                logger.warning(f"No dedicated vision models found. Trying GPT-4 model: {selected_model}")
                return selected_model
            
            # If no suitable models are found, raise an error
            raise ValueError("No suitable vision-capable models available")
            
        except Exception as e:
            error_msg = f"Error getting available models: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Available models: {self._available_models}")
            raise ValueError(f"Failed to find a suitable vision model: {str(e)}")

    def _prepare_vision_request(self, messages: List[Dict[str, Any]], model: str) -> Dict[str, Any]:
        """
        Prepare the vision request based on the selected model.
        
        Args:
            messages: List of message dictionaries
            model: Selected model name
            
        Returns:
            Dictionary containing the request parameters
        """
        request = {
            "model": model,
            "messages": messages,
            "max_tokens": 4096
        }
        
        # Add model-specific parameters
        if "gpt-4" in model.lower():
            request["temperature"] = 0.2  # Lower temperature for more consistent analysis
        
        logger.debug(f"Prepared vision request for model {model}")
        return request

    def _encode_image(self, image_path: str) -> str:
        """
        Encode an image to base64.
        
        Args:
            image_path: Path to the image
            
        Returns:
            Base64-encoded image
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _normalize_analysis_json(self, analysis_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize and validate the analysis JSON.
        
        Args:
            analysis_json: Raw analysis JSON from the API
            
        Returns:
            Normalized analysis JSON
        """
        # Define required fields and their default values
        required_fields = {
            "layout_changes": [],
            "color_changes": [],
            "element_changes": [],
            "text_changes": [],
            "critical_issues": [],
            "comparison_confidence": 0
        }
        
        # Ensure all required fields exist
        for field, default_value in required_fields.items():
            if field not in analysis_json:
                analysis_json[field] = default_value
        
        # Ensure arrays are properly initialized
        array_fields = ["layout_changes", "color_changes", "element_changes", "text_changes", "critical_issues"]
        for field in array_fields:
            if not isinstance(analysis_json[field], list):
                analysis_json[field] = []
        
        # Calculate comparison confidence based on the number and severity of changes
        total_changes = sum(len(analysis_json[field]) for field in array_fields[:-1])  # Exclude critical_issues
        
        if total_changes == 0:
            # No changes detected
            if any(analysis_json[field] for field in array_fields):  # Check if any field has content
                analysis_json["comparison_confidence"] = 85  # High confidence in finding no changes
            else:
                analysis_json["comparison_confidence"] = 50  # Medium confidence when no analysis is provided
        else:
            # Calculate weighted confidence based on severity of changes
            severity_weights = {
                "Critical": 1.0,
                "High": 0.8,
                "Medium": 0.6,
                "Low": 0.4
            }
            
            weighted_sum = 0
            total_weight = 0
            
            for field in array_fields[:-1]:  # Exclude critical_issues
                for change in analysis_json[field]:
                    if isinstance(change, dict):
                        severity = change.get("severity", "Low")
                        weight = severity_weights.get(severity, 0.4)
                        weighted_sum += weight
                        total_weight += 1
            
            if total_weight > 0:
                # Calculate confidence based on:
                # 1. Number of changes (more changes = higher confidence)
                # 2. Severity of changes (more severe changes = higher confidence)
                # 3. Consistency of changes (similar severities = higher confidence)
                base_confidence = 60  # Start with a base confidence
                change_factor = min(20, total_changes * 2)  # More changes increase confidence
                severity_factor = (weighted_sum / total_weight) * 20  # Higher severity increases confidence
                
                confidence = base_confidence + change_factor + severity_factor
                analysis_json["comparison_confidence"] = max(50, min(95, round(confidence)))
            else:
                analysis_json["comparison_confidence"] = 50
        
        # Validate and normalize each change entry
        for field in array_fields[:-1]:  # Exclude critical_issues
            normalized_changes = []
            for change in analysis_json[field]:
                if isinstance(change, dict):
                    normalized_change = {
                        "description": change.get("description", "No description provided"),
                        "severity": change.get("severity", "Low"),
                        "likely_intentional": change.get("likely_intentional", True)
                    }
                    
                    # Normalize severity
                    severity = normalized_change["severity"].capitalize()
                    if severity not in ["Critical", "High", "Medium", "Low"]:
                        severity = "Low"
                    normalized_change["severity"] = severity
                    
                    # Determine if the change is likely intentional based on description
                    if "likely_intentional" not in change:
                        description = normalized_change["description"].lower()
                        normalized_change["likely_intentional"] = not any(word in description for word in [
                            "issue", "problem", "error", "bug", "regression", "unintended", "broken"
                        ])
                    
                    normalized_changes.append(normalized_change)
            analysis_json[field] = normalized_changes
        
        # Normalize critical issues
        if isinstance(analysis_json["critical_issues"], list):
            normalized_issues = []
            for issue in analysis_json["critical_issues"]:
                if isinstance(issue, str):
                    normalized_issues.append(issue)
                elif isinstance(issue, dict) and "description" in issue:
                    normalized_issues.append(issue["description"])
            analysis_json["critical_issues"] = normalized_issues
        
        return analysis_json

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

    def generate_report(self, analysis: Dict[str, Any], format_type: str = "markdown", output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Generate a report from the analysis.
        
        Args:
            analysis: Analysis results
            format_type: Format for the report (markdown, json, or both)
            output_dir: Directory to save the report (defaults to project UI reports directory)
            
        Returns:
            Dictionary with paths to the generated reports
        """
        # Use the provided output_dir or get it from the project config
        if output_dir is None:
            if config_manager.current_project:
                project = config_manager.get_project(config_manager.current_project)
                if project:
                    # Use project-specific UI reports directory
                    output_dir = get_project_ui_reports_dir(project["path"])
                    logger.info(f"Using project UI reports directory: {output_dir}")
                else:
                    logger.warning("Current project not found in config, using default UI reports directory")
                    output_dir = UI_REPORTS_DIR
            else:
                logger.warning("No current project set, using default UI reports directory")
                output_dir = UI_REPORTS_DIR
        
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Reports will be saved to: {output_dir}")

        # Validate format_type
        valid_formats = ["markdown", "json", "both"]
        if format_type not in valid_formats:
            logger.error(f"Invalid report format: {format_type}. Must be one of {valid_formats}")
            # Default to markdown if invalid format is provided
            format_type = "markdown"
            logger.info(f"Defaulting to {format_type} format")
        
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

    def _extract_analysis_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract structured analysis from text response when JSON parsing fails.
        
        Args:
            text: Raw text response from the API
            
        Returns:
            Dictionary containing structured analysis
        """
        analysis = {
            "layout_changes": [],
            "color_changes": [],
            "element_changes": [],
            "text_changes": [],
            "critical_issues": [],
            "comparison_confidence": 50  # Default to medium confidence for text-based analysis
        }
        
        # Define patterns to match different types of changes
        patterns = {
            "layout": [r"(?i)layout.*?(?:change|difference|moved|shifted|resized)",
                      r"(?i)(?:position|alignment|spacing).*?(?:change|difference|modified)"],
            "color": [r"(?i)color.*?(?:change|difference|modified)",
                     r"(?i)(?:background|foreground|text).*?color.*?(?:change|difference)"],
            "element": [r"(?i)(?:element|component|button|input|form).*?(?:added|removed|changed|modified)",
                       r"(?i)(?:new|missing).*?(?:element|component|button|input|form)"],
            "text": [r"(?i)text.*?(?:change|difference|modified|updated)",
                    r"(?i)(?:content|label|heading).*?(?:change|difference|modified)"]
        }
        
        # Extract severity levels
        severity_patterns = {
            "critical": r"(?i)critical|severe|major|significant",
            "high": r"(?i)high|important|notable",
            "medium": r"(?i)medium|moderate|noticeable",
            "low": r"(?i)low|minor|subtle"
        }
        
        # Process each line of the text
        lines = text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Determine if this line starts a new section
            if any(section in line.lower() for section in ["layout", "color", "element", "text"]):
                for section in ["layout", "color", "element", "text"]:
                    if section in line.lower():
                        current_section = section
                        break
                continue
            
            # Process the line based on patterns
            for change_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if re.search(pattern, line):
                        # Determine severity
                        severity = "low"  # Default severity
                        for sev, sev_pattern in severity_patterns.items():
                            if re.search(sev_pattern, line):
                                severity = sev
                                break
                        
                        # Determine if change is likely intentional
                        likely_intentional = not any(word in line.lower() for word in 
                            ["issue", "problem", "error", "bug", "regression", "unintended"])
                        
                        # Add the change to the appropriate category
                        change = {
                            "description": line,
                            "severity": severity.capitalize(),
                            "likely_intentional": likely_intentional
                        }
                        
                        if change_type == "layout":
                            analysis["layout_changes"].append(change)
                        elif change_type == "color":
                            analysis["color_changes"].append(change)
                        elif change_type == "element":
                            analysis["element_changes"].append(change)
                        elif change_type == "text":
                            analysis["text_changes"].append(change)
                        
                        break  # Stop checking patterns once we've found a match
        
        # Extract critical issues
        critical_pattern = r"(?i)(?:critical|severe).*?(?:issue|problem|error)"
        critical_issues = re.findall(critical_pattern, text)
        analysis["critical_issues"].extend(critical_issues)
        
        # Calculate comparison confidence based on the quality of the analysis
        total_changes = sum(len(changes) for changes in [
            analysis["layout_changes"],
            analysis["color_changes"],
            analysis["element_changes"],
            analysis["text_changes"]
        ])
        
        if total_changes > 0:
            # More changes detected = higher confidence in the analysis
            analysis["comparison_confidence"] = min(85, 50 + (total_changes * 5))
        else:
            # No changes detected = lower confidence
            analysis["comparison_confidence"] = 50
        
        return analysis


def validate_ui(url: str, api_key: Optional[str] = None, output_dir: Optional[str] = None, 
               report_format: str = "markdown", report_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Capture screenshots and validate UI changes.
    
    Args:
        url: URL of the web page to validate
        api_key: OpenAI API key
        output_dir: Directory to save screenshots (defaults to SCREENSHOTS_DIR from constants)
        report_format: Format for the report (markdown, json, or both)
        report_dir: Directory to save reports (defaults to UI_REPORTS_DIR from constants)
        
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
        # Initialize screen capture with the appropriate output directory
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
        ui_validator = UIValidator(url, api_key)
        
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
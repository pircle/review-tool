from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class FileReviewResult(BaseModel):
    """Model for storing file review results."""
    path: str
    issues: int
    status: str  # 'fixed', 'pending', or 'error'
    details: Optional[str] = None

class AppliedFix(BaseModel):
    """Model for storing applied fix details."""
    file: str
    description: str
    category: str
    before: str
    after: str
    timestamp: datetime

class UIValidationResult(BaseModel):
    """Model for storing UI validation results."""
    url: str
    status: str  # 'passed' or 'failed'
    summary: str
    changes: List[dict]
    timestamp: datetime

class ReviewResults(BaseModel):
    """Model for storing overall review results."""
    total_reviews: int = 0
    applied_fixes: int = 0
    pending_fixes: int = 0
    files: List[FileReviewResult] = []
    applied_fixes_details: List[AppliedFix] = []
    timestamp: datetime = datetime.now()

class UIValidationResults(BaseModel):
    """Model for storing UI validation results."""
    validations: List[UIValidationResult] = []
    timestamp: datetime = datetime.now()

class ProjectData(BaseModel):
    """Model for storing all project data."""
    review_results: ReviewResults
    ui_validation_results: UIValidationResults 
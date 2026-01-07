"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# ============ Auth Schemas ============
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ============ RFP Analysis Schemas ============
class DocumentMatch(BaseModel):
    required_document: str
    status: str
    matched_file: Optional[str] = "N/A"
    confidence_score: Optional[float] = None
    details: Optional[str] = None
    description: Optional[str] = ""

class AnalysisResult(BaseModel):
    total: int
    present: int
    review: int
    missing: int
    completion_rate: float
    matches: List[DocumentMatch]
    extraction_cost: float

class AnalysisHistoryItem(BaseModel):
    """Single analysis history record"""
    id: int
    rfp_filename: str
    num_provided_docs: int
    num_required_docs: int
    num_matched: int
    num_review: int
    num_missing: int
    completion_rate: float
    api_cost: float
    created_at: datetime

    class Config:
        from_attributes = True

class AnalysisHistoryDetail(AnalysisHistoryItem):
    """Detailed analysis with full results"""
    results_json: Optional[str] = None  # Changed to str
    
    @property
    def results(self) -> Optional[Dict[str, Any]]:
        """Parse JSON string to dict"""
        if self.results_json:
            import json
            return json.loads(self.results_json)
        return None
    
class RFPAnalysisResult(BaseModel):
    """Results for a single RFP"""
    rfp_filename: str
    total: int
    present: int
    review: int
    missing: int
    completion_rate: float
    matches: List[DocumentMatch]
    extraction_cost: float

class BatchAnalysisResult(BaseModel):
    """Results for multiple RFPs analyzed together"""
    batch_id: str
    total_rfps: int
    total_cost: float
    rfp_results: List[RFPAnalysisResult]
    
class BatchAnalysisHistoryItem(BaseModel):
    """History item for batch analysis"""
    id: int
    batch_id: str
    num_rfps: int
    total_api_cost: float
    created_at: datetime
    
    class Config:
        from_attributes = True

class HealthCheck(BaseModel):
    status: str
    openai_available: bool
    anthropic_available: bool

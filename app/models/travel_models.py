from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TravelInquiryData(BaseModel):
    """Structured travel inquiry data extracted from emails"""
    
    # Basic Travel Information
    number_of_travelers: Optional[int] = Field(None, ge=1, le=50)
    destinations: List[str] = Field(default_factory=list)
    travel_dates: Optional[Dict[str, Any]] = None  # {"start": "2024-06-01", "end": "2024-06-10"}
    departure_city: Optional[str] = None
    
    # Accommodation & Meals
    hotel_preferences: Dict[str, Any] = Field(default_factory=dict)
    meal_preferences: List[str] = Field(default_factory=list)
    
    # Activities & Sightseeing
    sightseeing_activities: List[str] = Field(default_factory=list)
    guide_language_preferences: List[str] = Field(default_factory=list)
    
    # Services Required
    visa_required: Optional[bool] = None
    insurance_required: Optional[bool] = None
    flight_required: Optional[bool] = None
    
    # Budget & Timeline
    budget_range: Optional[Dict[str, float]] = None  # {"min": 50000, "max": 100000}
    inquiry_deadline: Optional[datetime] = None
    
    # Additional Information
    special_requirements: Optional[str] = None
    
    # Processing Metadata
    extraction_confidence: int = Field(default=0, ge=0, le=100)
    requires_clarification: bool = Field(default=False)
    clarification_notes: Optional[str] = None
    original_language: Optional[str] = None
    
    @validator('travel_dates')
    def validate_travel_dates(cls, v):
        if v and isinstance(v, dict):
            if 'start' in v and 'end' in v:
                try:
                    start = datetime.fromisoformat(v['start']) if isinstance(v['start'], str) else v['start']
                    end = datetime.fromisoformat(v['end']) if isinstance(v['end'], str) else v['end']
                    if start >= end:
                        raise ValueError("End date must be after start date")
                except (ValueError, TypeError):
                    raise ValueError("Invalid date format in travel_dates")
        return v

class TravelQuoteData(BaseModel):
    """Travel quote data structure"""
    
    # Quote Identification
    quote_id: str
    version: int = 1
    inquiry_id: int
    
    # Travel Summary
    summary: Dict[str, Any]
    
    # Pricing Options (up to 3 options)
    pricing_options: List[Dict[str, Any]] = Field(default_factory=list, max_items=3)
    
    # Detailed Breakdown
    itinerary: List[Dict[str, Any]] = Field(default_factory=list)
    inclusions: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    
    # Terms & Conditions
    terms_conditions: List[str] = Field(default_factory=list)
    cancellation_policy: Optional[str] = None
    
    # Validity
    valid_until: Optional[datetime] = None
    
    # Generated Files
    excel_file_path: Optional[str] = None
    
    # Timestamps
    generated_at: datetime = Field(default_factory=datetime.now)
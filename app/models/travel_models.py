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
    special_requirements: Optional[List[str]] = None
    
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

    @staticmethod
    def create_placeholder(inquiry: 'TravelInquiryData') -> 'TravelQuoteData':
        """Generate a placeholder quote based on the inquiry data."""
        from datetime import timedelta
        import random
        # Generate a random quote ID
        quote_id = f"Q{random.randint(1000, 9999)}"
        # Use today's date for validity (30 days)
        valid_until = datetime.now() + timedelta(days=30)
        # Dummy summary
        summary = {
            "destinations": inquiry.destinations or ["To be decided"],
            "number_of_travelers": inquiry.number_of_travelers or 2,
            "travel_dates": inquiry.travel_dates or {"start": "2024-07-01", "end": "2024-07-07"},
            "departure_city": inquiry.departure_city or "To be decided"
        }
        # Dummy pricing options (Economy, Standard, Premium)
        base_price = 20000
        pricing_options = [
            {
                "Accommodation": base_price,
                "Transportation": 5000,
                "Meals": 3000,
                "Sightseeing": 4000,
                "Guide Services": 2000,
                "Miscellaneous": 1000,
                "Total per person": base_price + 5000 + 3000 + 4000 + 2000 + 1000
            },
            {
                "Accommodation": base_price + 5000,
                "Transportation": 6000,
                "Meals": 4000,
                "Sightseeing": 5000,
                "Guide Services": 2500,
                "Miscellaneous": 1500,
                "Total per person": base_price + 5000 + 6000 + 4000 + 5000 + 2500 + 1500
            },
            {
                "Accommodation": base_price + 10000,
                "Transportation": 8000,
                "Meals": 6000,
                "Sightseeing": 7000,
                "Guide Services": 3500,
                "Miscellaneous": 2000,
                "Total per person": base_price + 10000 + 8000 + 6000 + 7000 + 3500 + 2000
            }
        ]
        # Dummy itinerary
        itinerary = []
        travel_dates = inquiry.travel_dates or {"start": "2024-07-01", "end": "2024-07-07"}
        try:
            start = travel_dates.get("start", "2024-07-01")
            end = travel_dates.get("end", "2024-07-07")
            start_date = datetime.fromisoformat(start)
            end_date = datetime.fromisoformat(end)
            days = (end_date - start_date).days + 1
        except Exception:
            days = 7
            start_date = datetime.now()
        for i in range(days):
            day_date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            itinerary.append({
                "day": i + 1,
                "date": day_date,
                "city": (inquiry.destinations[0] if inquiry.destinations else "City"),
                "activities": "Sightseeing, leisure, and local experiences",
                "meals": ", ".join(inquiry.meal_preferences) if inquiry.meal_preferences else "Breakfast",
                "accommodation": f"Hotel (Day {i+1})"
            })
        # Inclusions and exclusions
        inclusions = [
            "Accommodation as per itinerary",
            "Daily breakfast",
            "Transportation as per itinerary",
            "Sightseeing as mentioned",
            "Professional guide services",
            "All applicable taxes"
        ]
        exclusions = [
            "Airfare (unless specified)",
            "Visa fees",
            "Travel insurance",
            "Personal expenses",
            "Tips and gratuities",
            "Any services not mentioned in inclusions"
        ]
        # Terms and cancellation
        terms_conditions = [
            "Booking confirmation subject to advance payment",
            "Cancellation charges as per company policy",
            "Travel dates subject to availability",
            "Company not responsible for any delays due to weather or political conditions",
            "All disputes subject to local jurisdiction",
            "This quotation is valid for 30 days from date of issue"
        ]
        cancellation_policy = "Non-refundable after confirmation. Please refer to company policy for details."
        return TravelQuoteData(
            quote_id=quote_id,
            version=1,
            inquiry_id=random.randint(1, 10000),
            summary=summary,
            pricing_options=pricing_options,
            itinerary=itinerary,
            inclusions=inclusions,
            exclusions=exclusions,
            terms_conditions=terms_conditions,
            cancellation_policy=cancellation_policy,
            valid_until=valid_until
        )
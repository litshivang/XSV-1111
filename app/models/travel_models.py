from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class InquiryComplexity(str, Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"

class DestinationDetail(BaseModel):
    """Detailed information for a specific destination"""
    destination_name: str
    nights: Optional[int] = None
    hotel_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    meal_preferences: Optional[List[str]] = Field(default_factory=list)
    activities: Optional[List[str]] = Field(default_factory=list)
    transportation: Optional[str] = None
    guide_requirements: Optional[str] = None
    special_notes: Optional[List[str]] = Field(default_factory=list)

class TravelerInfo(BaseModel):
    """Detailed traveler information"""
    adults: Optional[int] = None
    children: Optional[int] = None
    total: Optional[int] = None
    couples: Optional[int] = None
    singles: Optional[int] = None
    visa_required_count: Optional[int] = None
    special_requirements: Optional[List[str]] = Field(default_factory=list)

class TravelInquiryData(BaseModel):
    """Enhanced structured travel inquiry data extracted from emails"""
    
    # Inquiry Classification
    inquiry_complexity: InquiryComplexity = InquiryComplexity.SIMPLE
    
    # Enhanced Traveler Information
    traveler_info: TravelerInfo = Field(default_factory=TravelerInfo)
    
    # Enhanced Destination Information
    destinations: Optional[List[str]] = Field(default_factory=list)
    destination_details: Optional[List[DestinationDetail]] = Field(default_factory=list)
    
    # Travel Logistics
    travel_dates: Optional[Dict[str, Any]] = None
    duration: Optional[Dict[str, Any]] = None  # {"total_days": 8, "total_nights": 7}
    departure_city: Optional[str] = None
    
    # Global Preferences (for simple inquiries)
    global_hotel_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    global_meal_preferences: Optional[List[str]] = Field(default_factory=list)
    global_activities: Optional[List[str]] = Field(default_factory=list)
    
    # Services Required
    visa_assistance: Optional[bool] = None
    insurance_required: Optional[bool] = None
    flight_required: Optional[bool] = None
    airport_transfers: Optional[bool] = None
    
    # Guide Requirements
    guide_language_preferences: Optional[List[str]] = Field(default_factory=list)
    guide_required_destinations: Optional[List[str]] = Field(default_factory=list)
    
    # Budget Information
    budget_per_person: Optional[float] = None
    total_budget: Optional[float] = None
    budget_currency: Optional[str] = Field(default="INR")
    
    # Quote Requirements
    number_of_quote_options: int = 1
    quote_deadline: Optional[str] = None
    urgent_request: bool = False
    
    # Special Requirements
    accessibility_requirements: Optional[List[str]] = Field(default_factory=list)
    dietary_restrictions: Optional[List[str]] = Field(default_factory=list)
    special_occasions: Optional[List[str]] = Field(default_factory=list)
    
    # Processing Metadata
    extraction_confidence: int = Field(default=0, ge=0, le=100)
    requires_clarification: bool = Field(default=False)
    clarification_notes: Optional[str] = None
    original_language: Optional[str] = None
    key_information_extracted: Optional[List[str]] = Field(default_factory=list)
    
    @field_validator('travel_dates')
    @classmethod
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
    """Enhanced travel quote data structure"""
    
    # Quote Identification
    quote_id: str
    version: int = 1
    inquiry_id: int
    inquiry_complexity: InquiryComplexity = InquiryComplexity.SIMPLE
    
    # Travel Summary
    summary: Dict[str, Any]
    
    # Enhanced Pricing Options
    pricing_options: List[Dict[str, Any]] = Field(default_factory=list, max_items=3)
    pricing_notes: List[str] = Field(default_factory=list)
    
    # Detailed Breakdown by Destination
    destination_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Enhanced Itinerary
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
    def create_enhanced_placeholder(inquiry: 'TravelInquiryData') -> 'TravelQuoteData':
        """Generate an enhanced placeholder quote based on the inquiry complexity."""
        from datetime import timedelta
        import random
        
        quote_id = f"Q{random.randint(10000, 99999)}"
        valid_until = datetime.now() + timedelta(days=30)
        
        # Enhanced summary based on inquiry complexity
        summary = {
            "inquiry_type": inquiry.inquiry_complexity.value,
            "destinations": inquiry.destinations or ["To be decided"],
            "traveler_details": {
                "total": inquiry.traveler_info.total or 2,
                "adults": inquiry.traveler_info.adults,
                "children": inquiry.traveler_info.children,
                "couples": inquiry.traveler_info.couples,
                "singles": inquiry.traveler_info.singles
            },
            "travel_dates": inquiry.travel_dates or {"start": "2024-07-01", "end": "2024-07-08"},
            "duration": inquiry.duration or {"total_days": 8, "total_nights": 7},
            "departure_city": inquiry.departure_city or "To be decided",
            "budget_per_person": inquiry.budget_per_person,
            "special_requirements": (inquiry.accessibility_requirements or []) + (inquiry.dietary_restrictions or [])
        }
        
        # Generate pricing based on complexity
        if inquiry.inquiry_complexity == InquiryComplexity.COMPLEX:
            pricing_options = TravelQuoteData._generate_complex_pricing(inquiry)
            destination_breakdown = TravelQuoteData._generate_destination_breakdown(inquiry)
        else:
            pricing_options = TravelQuoteData._generate_simple_pricing(inquiry)
            destination_breakdown = []
        
        # Enhanced itinerary
        itinerary = TravelQuoteData._generate_enhanced_itinerary(inquiry)
        
        # Enhanced inclusions/exclusions
        inclusions, exclusions = TravelQuoteData._generate_enhanced_inclusions_exclusions(inquiry)
        
        return TravelQuoteData(
            quote_id=quote_id,
            version=1,
            inquiry_id=random.randint(1, 100000),
            inquiry_complexity=inquiry.inquiry_complexity,
            summary=summary,
            pricing_options=pricing_options,
            destination_breakdown=destination_breakdown,
            itinerary=itinerary,
            inclusions=inclusions,
            exclusions=exclusions,
            terms_conditions=TravelQuoteData._generate_terms(),
            cancellation_policy="Cancellation charges as per company policy",
            valid_until=valid_until
        )
    
    @staticmethod
    def _generate_complex_pricing(inquiry: 'TravelInquiryData') -> List[Dict[str, Any]]:
        """Generate destination-wise pricing for complex inquiries"""
        pricing_options = []
        base_multipliers = [1.0, 1.3, 1.6]  # Economy, Standard, Premium
        option_names = ["Economy Package", "Standard Package", "Premium Package"]
        
        for i, (multiplier, name) in enumerate(zip(base_multipliers, option_names)):
            option = {"package_name": name, "destinations": []}
            
            for dest_detail in (inquiry.destination_details or []):
                dest_pricing = {
                    "destination": dest_detail.destination_name,
                    "nights": dest_detail.nights or 3,
                    "accommodation": int(15000 * multiplier),
                    "meals": int(3000 * multiplier),
                    "activities": int(5000 * multiplier),
                    "transportation": int(2000 * multiplier),
                    "guide_services": int(1500 * multiplier) if dest_detail.guide_requirements else 0,
                    "subtotal": int(26500 * multiplier)
                }
                option["destinations"].append(dest_pricing)
            
            # Add global costs
            option["global_costs"] = {
                "visa_assistance": 2000 if inquiry.visa_assistance else 0,
                "insurance": 1500 if inquiry.insurance_required else 0,
                "airport_transfers": 1000 if inquiry.airport_transfers else 0,
                "miscellaneous": int(2000 * multiplier)
            }
            
            # Calculate total
            dest_total = sum(d["subtotal"] for d in option["destinations"])
            global_total = sum(option["global_costs"].values())
            option["total_per_person"] = dest_total + global_total
            
            pricing_options.append(option)
        
        return pricing_options
    
    @staticmethod
    def _generate_simple_pricing(inquiry: 'TravelInquiryData') -> List[Dict[str, Any]]:
        """Generate simple pricing structure"""
        base_price = inquiry.budget_per_person or 50000
        multipliers = [0.8, 1.0, 1.2]
        option_names = ["Economy Package", "Standard Package", "Premium Package"]
        
        pricing_options = []
        for multiplier, name in zip(multipliers, option_names):
            total_price = int(base_price * multiplier)
            option = {
                "package_name": name,
                "accommodation": int(total_price * 0.4),
                "transportation": int(total_price * 0.15),
                "meals": int(total_price * 0.15),
                "sightseeing": int(total_price * 0.15),
                "guide_services": int(total_price * 0.1),
                "miscellaneous": int(total_price * 0.05),
                "total_per_person": total_price
            }
            pricing_options.append(option)
        
        return pricing_options
    
    @staticmethod
    def _generate_destination_breakdown(inquiry: 'TravelInquiryData') -> List[Dict[str, Any]]:
        """Generate detailed breakdown by destination"""
        breakdown = []
        for dest_detail in (inquiry.destination_details or []):
            dest_info = {
                "destination": dest_detail.destination_name,
                "duration": f"{dest_detail.nights} nights" if dest_detail.nights else "TBD",
                "accommodation": dest_detail.hotel_preferences,
                "meals": dest_detail.meal_preferences,
                "activities": dest_detail.activities,
                "transportation": dest_detail.transportation,
                "guide": dest_detail.guide_requirements,
                "special_notes": dest_detail.special_notes
            }
            breakdown.append(dest_info)
        return breakdown
    
    @staticmethod
    def _generate_enhanced_itinerary(inquiry: 'TravelInquiryData') -> List[Dict[str, Any]]:
        """Generate enhanced itinerary based on inquiry details"""
        itinerary = []
        
        if inquiry.inquiry_complexity == InquiryComplexity.COMPLEX:
            day_counter = 1
            for dest_detail in (inquiry.destination_details or []):
                nights = dest_detail.nights or 3
                for night in range(nights):
                    day_info = {
                        "day": day_counter,
                        "destination": dest_detail.destination_name,
                        "activities": "; ".join(dest_detail.activities or []) if dest_detail.activities else "Leisure and local exploration",
                        "meals": "; ".join(dest_detail.meal_preferences or []) if dest_detail.meal_preferences else "As per package",
                        "accommodation": f"{(dest_detail.hotel_preferences or {}).get('category', 'Standard')} hotel",
                        "transportation": dest_detail.transportation or "As per itinerary",
                        "special_notes": ", ".join(dest_detail.special_notes or []) if dest_detail.special_notes else ""
                    }
                    itinerary.append(day_info)
                    day_counter += 1
        else:
            # Simple itinerary
            duration = inquiry.duration or {"total_days": 7}
            total_days = (duration or {}).get("total_days", 7)
            
            for day in range(1, total_days + 1):
                day_info = {
                    "day": day,
                    "destination": (inquiry.destinations or ["Destination"])[0] if inquiry.destinations else "Destination",
                    "activities": "; ".join(inquiry.global_activities or []) if inquiry.global_activities else "Sightseeing and leisure",
                    "meals": "; ".join(inquiry.global_meal_preferences or []) if inquiry.global_meal_preferences else "As per package",
                    "accommodation": f"{(inquiry.global_hotel_preferences or {}).get('category', 'Standard')} hotel",
                    "transportation": "As per itinerary",
                    "special_notes": ""
                }
                itinerary.append(day_info)
        
        return itinerary
    
    @staticmethod
    def _generate_enhanced_inclusions_exclusions(inquiry: 'TravelInquiryData') -> tuple:
        """Generate enhanced inclusions and exclusions based on inquiry"""
        base_inclusions = [
            "Accommodation as per itinerary",
            "Transportation as mentioned",
            "Sightseeing as per program",
            "Professional guide services (where specified)",
            "All applicable taxes"
        ]
        
        base_exclusions = [
            "Personal expenses and tips",
            "Any services not mentioned in inclusions"
        ]
        
        # Add specific inclusions based on inquiry
        if inquiry.global_meal_preferences or any((d.meal_preferences or []) for d in (inquiry.destination_details or [])):
            base_inclusions.insert(1, "Meals as specified in itinerary")
        
        if inquiry.visa_assistance:
            base_inclusions.append("Visa assistance and documentation")
        else:
            base_exclusions.append("Visa fees and documentation")
        
        if inquiry.insurance_required:
            base_inclusions.append("Travel insurance coverage")
        else:
            base_exclusions.append("Travel insurance")
        
        if inquiry.flight_required:
            base_inclusions.append("Domestic/International flights as specified")
        else:
            base_exclusions.append("Airfare (unless specified)")
        
        if inquiry.airport_transfers:
            base_inclusions.append("Airport pickup and drop-off")
        else:
            base_exclusions.append("Airport transfers (unless specified)")
        
        return base_inclusions, base_exclusions
    
    @staticmethod
    def _generate_terms() -> List[str]:
        """Generate standard terms and conditions"""
        return [
            "Booking confirmation subject to advance payment",
            "Cancellation charges as per company policy",
            "Travel dates subject to availability",
            "Company not responsible for delays due to weather or political conditions",
            "All disputes subject to local jurisdiction",
            "This quotation is valid for 30 days from date of issue",
            "Final confirmation required within 48 hours of acceptance",
            "Payment terms: 25% advance, balance before travel"
        ]

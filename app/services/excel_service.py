import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

from app.config import settings
from app.models.travel_models import TravelInquiryData, TravelQuoteData
from app.utils.logger import get_logger
from app.utils.exceptions import ExcelServiceError

logger = get_logger(__name__)

class ExcelQuoteGenerator:
    """Service for generating Excel travel quotes"""
    
    def __init__(self):
        self.template_path = os.path.join(settings.template_path, "travel_quote_template.xlsx")
        self.output_path = settings.file_storage_path
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        os.makedirs(self.output_path, exist_ok=True)
        os.makedirs(settings.template_path, exist_ok=True)
    
    async def generate_quote(self, inquiry: TravelInquiryData, quote_data: TravelQuoteData) -> str:
        """Generate Excel quote from travel inquiry and quote data"""
        try:
            # Create new workbook
            wb = Workbook()
            
            # Create multiple sheets
            self._create_summary_sheet(wb, inquiry, quote_data)
            self._create_itinerary_sheet(wb, quote_data)
            self._create_pricing_sheet(wb, quote_data)
            self._create_terms_sheet(wb, quote_data)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"travel_quote_{quote_data.quote_id}_{timestamp}.xlsx"
            filepath = os.path.join(self.output_path, filename)
            
            # Save the workbook
            wb.save(filepath)
            
            logger.info(f"Excel quote generated successfully: {filename}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate Excel quote: {e}")
            raise ExcelServiceError(f"Excel generation failed: {e}")
    
    def _create_summary_sheet(self, wb: Workbook, inquiry: TravelInquiryData, quote_data: TravelQuoteData):
        """Create summary sheet with travel overview"""
        ws = wb.active
        ws.title = "Travel Summary"
        
        # Header styling
        header_font = Font(bold=True, size=14, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                       top=Side(style='thin'), bottom=Side(style='thin'))
        
        # Company header
        ws.merge_cells('A1:G1')
        ws['A1'] = "TRAVEL QUOTATION"
        ws['A1'].font = Font(bold=True, size=16)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        # Quote information
        row = 3
        ws[f'A{row}'] = "Quote ID:"
        ws[f'B{row}'] = quote_data.quote_id
        ws[f'E{row}'] = "Date:"
        ws[f'F{row}'] = datetime.now().strftime("%Y-%m-%d")
        
        row += 1
        ws[f'A{row}'] = "Version:"
        ws[f'B{row}'] = quote_data.version
        ws[f'E{row}'] = "Valid Until:"
        ws[f'F{row}'] = quote_data.valid_until.strftime("%Y-%m-%d") if quote_data.valid_until else "30 days"
        
        # Travel details section
        row += 3
        ws[f'A{row}'] = "TRAVEL DETAILS"
        ws[f'A{row}'].font = header_font
        ws[f'A{row}'].fill = header_fill
        ws.merge_cells(f'A{row}:G{row}')
        
        row += 2
        details = [
            ("Number of Travelers:", inquiry.number_of_travelers or "Not specified"),
            ("Destinations:", ", ".join(inquiry.destinations) if inquiry.destinations else "Not specified"),
            ("Travel Dates:", self._format_travel_dates(inquiry.travel_dates)),
            ("Departure City:", inquiry.departure_city or "Not specified"),
            ("Duration:", self._calculate_duration(inquiry.travel_dates)),
        ]
        
        for label, value in details:
            ws[f'A{row}'] = label
            ws[f'B{row}'] = str(value)
            ws[f'A{row}'].font = Font(bold=True)
            row += 1
        
        # Preferences section
        row += 2
        ws[f'A{row}'] = "PREFERENCES & REQUIREMENTS"
        ws[f'A{row}'].font = header_font
        ws[f'A{row}'].fill = header_fill
        ws.merge_cells(f'A{row}:G{row}')
        
        row += 2
        preferences = [
            ("Hotel Preferences:", self._format_preferences(inquiry.hotel_preferences)),
            ("Meal Preferences:", ", ".join(inquiry.meal_preferences) if inquiry.meal_preferences else "Standard"),
            ("Sightseeing:", ", ".join(inquiry.sightseeing_activities) if inquiry.sightseeing_activities else "As per itinerary"),
            ("Guide Language:", ", ".join(inquiry.guide_language_preferences) if inquiry.guide_language_preferences else "English"),
            ("Special Requirements:", inquiry.special_requirements or "None"),
        ]
        
        for label, value in preferences:
            ws[f'A{row}'] = label
            ws[f'B{row}'] = str(value)
            ws[f'A{row}'].font = Font(bold=True)
            row += 1
        
        # Services section
        row += 2
        ws[f'A{row}'] = "SERVICES INCLUDED"
        ws[f'A{row}'].font = header_font
        ws[f'A{row}'].fill = header_fill
        ws.merge_cells(f'A{row}:G{row}')
        
        row += 2
        services = [
            ("Visa Assistance:", "Yes" if inquiry.visa_required else "No"),
            ("Travel Insurance:", "Yes" if inquiry.insurance_required else "No"),
            ("Flight Booking:", "Yes" if inquiry.flight_required else "No"),
        ]
        
        for label, value in services:
            ws[f'A{row}'] = label
            ws[f'B{row}'] = value
            ws[f'A{row}'].font = Font(bold=True)
            row += 1
        
        # Apply borders and styling
        self._apply_sheet_styling(ws)
    
    def _create_itinerary_sheet(self, wb: Workbook, quote_data: TravelQuoteData):
        """Create detailed itinerary sheet"""
        ws = wb.create_sheet("Detailed Itinerary")
        
        # Header
        ws.merge_cells('A1:F1')
        ws['A1'] = "DETAILED TRAVEL ITINERARY"
        ws['A1'].font = Font(bold=True, size=14)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        # Column headers
        headers = ["Day", "Date", "City", "Activities", "Meals", "Accommodation"]
        for i, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=i, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="E6E6FA", end_color="E6E6FA", fill_type="solid")
        
        # Itinerary data
        row = 4
        for day_info in quote_data.itinerary:
            ws.cell(row=row, column=1, value=day_info.get('day', ''))
            ws.cell(row=row, column=2, value=day_info.get('date', ''))
            ws.cell(row=row, column=3, value=day_info.get('city', ''))
            ws.cell(row=row, column=4, value=day_info.get('activities', ''))
            ws.cell(row=row, column=5, value=day_info.get('meals', ''))
            ws.cell(row=row, column=6, value=day_info.get('accommodation', ''))
            row += 1
        
        # Add placeholder rows if itinerary is empty
        if not quote_data.itinerary:
            for day in range(1, 8):  # 7-day placeholder
                ws.cell(row=row, column=1, value=f"Day {day}")
                ws.cell(row=row, column=2, value="[Date]")
                ws.cell(row=row, column=3, value="[City]")
                ws.cell(row=row, column=4, value="[Activities to be finalized]")
                ws.cell(row=row, column=5, value="[Breakfast/Lunch/Dinner]")
                ws.cell(row=row, column=6, value="[Hotel details]")
                row += 1
        
        self._apply_sheet_styling(ws)
    
    def _create_pricing_sheet(self, wb: Workbook, quote_data: TravelQuoteData):
        """Create pricing options sheet"""
        ws = wb.create_sheet("Pricing Options")
        
        # Header
        ws.merge_cells('A1:F1')
        ws['A1'] = "PRICING OPTIONS"
        ws['A1'].font = Font(bold=True, size=14)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        row = 3
        
        # Create pricing options (up to 3)
        option_headers = ["Economy Package", "Standard Package", "Premium Package"]
        
        for i, (option_name, pricing) in enumerate(zip(option_headers, quote_data.pricing_options[:3])):
            # Option header
            ws.merge_cells(f'A{row}:F{row}')
            ws[f'A{row}'] = option_name
            ws[f'A{row}'].font = Font(bold=True, size=12)
            ws[f'A{row}'].fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
            row += 1
            
            # Pricing details
            if pricing:
                for item, cost in pricing.items():
                    ws[f'A{row}'] = item
                    ws[f'E{row}'] = f"₹ {cost:,.2f}" if isinstance(cost, (int, float)) else cost
                    row += 1
            else:
                # Placeholder pricing structure
                placeholder_items = [
                    "Accommodation (per person)",
                    "Transportation",
                    "Meals",
                    "Sightseeing",
                    "Guide Services",
                    "Miscellaneous",
                    "Total per person"
                ]
                
                for item in placeholder_items:
                    ws[f'A{row}'] = item
                    ws[f'E{row}'] = "[To be quoted]"
                    if item == "Total per person":
                        ws[f'A{row}'].font = Font(bold=True)
                        ws[f'E{row}'].font = Font(bold=True)
                    row += 1
            
            row += 2  # Space between options
        
        # Terms section
        row += 2
        ws.merge_cells(f'A{row}:F{row}')
        ws[f'A{row}'] = "PRICING TERMS"
        ws[f'A{row}'].font = Font(bold=True, size=12)
        ws[f'A{row}'].fill = PatternFill(start_color="FFE4B5", end_color="FFE4B5", fill_type="solid")
        row += 1
        
        terms = [
            "• All prices are per person on twin sharing basis",
            "• Single room supplement charges applicable",
            "• Prices subject to change based on availability",
            "• Final confirmation required within 48 hours",
            "• Payment terms: 25% advance, balance before travel"
        ]
        
        for term in terms:
            ws[f'A{row}'] = term
            row += 1
        
        self._apply_sheet_styling(ws)
    
    def _create_terms_sheet(self, wb: Workbook, quote_data: TravelQuoteData):
        """Create terms and conditions sheet"""
        ws = wb.create_sheet("Terms & Conditions")
        
        # Header
        ws.merge_cells('A1:E1')
        ws['A1'] = "TERMS & CONDITIONS"
        ws['A1'].font = Font(bold=True, size=14)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        row = 3
        
        # Inclusions
        ws[f'A{row}'] = "INCLUSIONS"
        ws[f'A{row}'].font = Font(bold=True, size=12, color="008000")
        row += 1
        
        inclusions = quote_data.inclusions if quote_data.inclusions else [
            "Accommodation as per itinerary",
            "Daily breakfast",
            "Transportation as per itinerary",
            "Sightseeing as mentioned",
            "Professional guide services",
            "All applicable taxes"
        ]
        
        for inclusion in inclusions:
            ws[f'A{row}'] = f"✓ {inclusion}"
            row += 1
        
        row += 2
        
        # Exclusions
        ws[f'A{row}'] = "EXCLUSIONS"
        ws[f'A{row}'].font = Font(bold=True, size=12, color="FF0000")
        row += 1
        
        exclusions = quote_data.exclusions if quote_data.exclusions else [
            "Airfare (unless specified)",
            "Visa fees",
            "Travel insurance",
            "Personal expenses",
            "Tips and gratuities",
            "Any services not mentioned in inclusions"
        ]
        
        for exclusion in exclusions:
            ws[f'A{row}'] = f"✗ {exclusion}"
            row += 1
        
        row += 2
        
        # General Terms
        ws[f'A{row}'] = "GENERAL TERMS"
        ws[f'A{row}'].font = Font(bold=True, size=12)
        row += 1
        
        general_terms = quote_data.terms_conditions if quote_data.terms_conditions else [
            "Booking confirmation subject to advance payment",
            "Cancellation charges as per company policy",
            "Travel dates subject to availability",
            "Company not responsible for any delays due to weather or political conditions",
            "All disputes subject to local jurisdiction",
            "This quotation is valid for 30 days from date of issue"
        ]
        
        for i, term in enumerate(general_terms, 1):
            ws[f'A{row}'] = f"{i}. {term}"
            row += 1
        
        row += 2
        
        # Cancellation Policy
        if quote_data.cancellation_policy:
            ws[f'A{row}'] = "CANCELLATION POLICY"
            ws[f'A{row}'].font = Font(bold=True, size=12)
            row += 1
            ws[f'A{row}'] = quote_data.cancellation_policy
            row += 1
        
        self._apply_sheet_styling(ws)
    
    def _format_travel_dates(self, travel_dates: Optional[Dict]) -> str:
        """Format travel dates for display"""
        if not travel_dates:
            return "Not specified"
        
        try:
            if isinstance(travel_dates, dict):
                start = travel_dates.get('start', '')
                end = travel_dates.get('end', '')
                if start and end:
                    return f"{start} to {end}"
            return str(travel_dates)
        except Exception:
            return "Not specified"
    
    def _calculate_duration(self, travel_dates: Optional[Dict]) -> str:
        """Calculate travel duration"""
        if not travel_dates:
            return "Not specified"
        
        try:
            if isinstance(travel_dates, dict):
                start_str = travel_dates.get('start', '')
                end_str = travel_dates.get('end', '')
                if start_str and end_str:
                    start = datetime.fromisoformat(start_str)
                    end = datetime.fromisoformat(end_str)
                    duration = (end - start).days
                    return f"{duration} days, {duration-1} nights" if duration > 0 else "1 day"
        except Exception:
            pass
        
        return "Not specified"
    
    def _format_preferences(self, preferences: Dict) -> str:
        """Format preferences dictionary for display in Excel."""
        if not preferences:
            return "Standard"
        if isinstance(preferences, dict):
            return "; ".join(f"{k}: {v}" for k, v in preferences.items() if v)
        if isinstance(preferences, list):
            return ", ".join(str(p) for p in preferences)
        return str(preferences)
    
    def _apply_sheet_styling(self, ws):
        """Apply consistent borders, font, and alignment to all cells with data in the worksheet."""
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    cell.border = thin_border
                    cell.alignment = Alignment(vertical='center', wrap_text=True)
                    if not cell.font.bold:
                        cell.font = Font(size=11)
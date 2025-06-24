import os
import pytest
from app.services.excel_service import ExcelQuoteGenerator
from app.models.travel_models import TravelInquiryData, TravelQuoteData
from datetime import datetime

@pytest.fixture
def inquiry_data():
    return TravelInquiryData(
        number_of_travelers=2,
        destinations=["Paris", "Rome"],
        travel_dates={"start": "2024-07-01", "end": "2024-07-10"},
        departure_city="Delhi",
        hotel_preferences={"star": 4},
        meal_preferences=["Breakfast"],
        sightseeing_activities=["Eiffel Tower"],
        guide_language_preferences=["English"],
        visa_required=True,
        insurance_required=True,
        flight_required=True,
        budget_range={"min": 50000, "max": 100000},
        inquiry_deadline=datetime(2024, 6, 1),
        special_requirements="None"
    )

@pytest.fixture
def quote_data():
    return TravelQuoteData(
        quote_id="Q123",
        version=1,
        inquiry_id=1,
        summary={},
        pricing_options=[{"Accommodation": 20000, "Transportation": 10000}],
        itinerary=[{"day": 1, "date": "2024-07-01", "city": "Paris", "activities": "Arrival", "meals": "Breakfast", "accommodation": "Hotel Paris"}],
        inclusions=["Hotel", "Breakfast"],
        exclusions=["Flights"],
        terms_conditions=["Payment in advance"],
        cancellation_policy="Non-refundable",
        valid_until=datetime(2024, 6, 30)
    )

def test_generate_quote(tmp_path, inquiry_data, quote_data, monkeypatch):
    generator = ExcelQuoteGenerator()
    # Patch output path to temp
    generator.output_path = str(tmp_path)
    filepath = pytest.run(generator.generate_quote(inquiry_data, quote_data))
    assert os.path.exists(filepath)
    assert filepath.endswith(".xlsx")

def test_generate_quote_missing_data(tmp_path, inquiry_data, quote_data, monkeypatch):
    generator = ExcelQuoteGenerator()
    generator.output_path = str(tmp_path)
    # Remove destinations
    inquiry_data.destinations = []
    filepath = pytest.run(generator.generate_quote(inquiry_data, quote_data))
    assert os.path.exists(filepath)

def test_generate_quote_error(monkeypatch, inquiry_data, quote_data):
    generator = ExcelQuoteGenerator()
    # Force an error by patching save
    def fail_save(*args, **kwargs):
        raise Exception("Save failed")
    monkeypatch.setattr("openpyxl.workbook.workbook.Workbook.save", fail_save)
    with pytest.raises(Exception):
        pytest.run(generator.generate_quote(inquiry_data, quote_data))

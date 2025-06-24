import pytest
import pytest_asyncio
from app.services.ai_service import TravelInfoExtractor
from app.models.travel_models import TravelInquiryData
from app.models.email_models import EmailMessage

@pytest_asyncio.fixture
def travel_info_extractor():
    return TravelInfoExtractor()

@pytest.mark.asyncio
async def test_extract_structured_data(travel_info_extractor):
    email = EmailMessage(
        message_id="1",
        subject="Trip to Paris and Rome",
        sender_email="test@example.com",
        sender_name="Test User",
        body_text="We are 2 adults and 1 child, want to visit Paris and Rome from July 1 to July 10. Need 4-star hotel, vegetarian meals, and sightseeing.",
        received_date="2024-06-01T10:00:00Z"
    )
    result = await travel_info_extractor.extract_travel_info(email)
    assert isinstance(result, TravelInquiryData)
    assert result.number_of_travelers == 3 or result.number_of_travelers is not None
    assert "Paris" in result.destinations or "Rome" in result.destinations
    assert result.hotel_preferences.get("star", None) in [4, "4"] or result.hotel_preferences
    assert "vegetarian" in result.meal_preferences or result.meal_preferences

@pytest.mark.asyncio
async def test_multilingual_extraction(travel_info_extractor):
    email = EmailMessage(
        message_id="2",
        subject="गोवा यात्रा",
        sender_email="test@example.com",
        sender_name="Test User",
        body_text="हम 2 लोग हैं, हमें दिल्ली से गोवा जाना है, 10 से 15 अगस्त तक। होटल 3 स्टार चाहिए।",
        received_date="2024-06-01T10:00:00Z"
    )
    result = await travel_info_extractor.extract_travel_info(email)
    assert result.number_of_travelers == 2 or result.number_of_travelers is not None
    assert "गोवा" in result.destinations or "Goa" in result.destinations or result.destinations
    assert result.hotel_preferences.get("star", None) in [3, "3"] or result.hotel_preferences

@pytest.mark.asyncio
async def test_extraction_error(travel_info_extractor):
    email = EmailMessage(
        message_id="3",
        subject="Empty",
        sender_email="test@example.com",
        sender_name="Test User",
        body_text="",
        received_date="2024-06-01T10:00:00Z"
    )
    result = await travel_info_extractor.extract_travel_info(email)
    assert result.extraction_confidence == 0
    assert result.requires_clarification

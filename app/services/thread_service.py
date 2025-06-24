from app.models.database_models import EmailThread, EmailMessage, TravelInquiry, TravelQuote
from app.models.email_models import EmailThread as EmailThreadModel, EmailMessage as EmailMessageModel
from app.models.travel_models import TravelInquiryData, TravelQuoteData
from app.database import SessionLocal
from sqlalchemy.orm import Session
from typing import Optional, List
from app.utils.logger import get_logger
from app.utils.exceptions import AppError

logger = get_logger(__name__)

class ThreadService:
    """Service for managing email conversation threads and inquiry versioning."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db or SessionLocal()

    def get_thread_by_id(self, thread_id: str) -> Optional[EmailThread]:
        return self.db.query(EmailThread).filter(EmailThread.thread_id == thread_id).first()

    def create_or_update_thread(self, thread_data: EmailThreadModel) -> EmailThread:
        thread = self.get_thread_by_id(thread_data.thread_id)
        if thread:
            thread.subject = thread_data.subject
            thread.sender_email = thread_data.sender_email
            thread.sender_name = thread_data.sender_name
            thread.updated_at = thread_data.updated_at or thread.updated_at
            thread.status = thread_data.status
        else:
            thread = EmailThread(
                thread_id=thread_data.thread_id,
                subject=thread_data.subject,
                sender_email=thread_data.sender_email,
                sender_name=thread_data.sender_name,
                created_at=thread_data.created_at,
                status=thread_data.status
            )
            self.db.add(thread)
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def add_message_to_thread(self, thread: EmailThread, message_data: EmailMessageModel) -> EmailMessage:
        message = EmailMessage(
            message_id=message_data.message_id,
            thread_id=thread.id,
            subject=message_data.subject,
            sender_email=message_data.sender_email,
            recipient_email=message_data.recipient_email,
            body_text=message_data.body_text,
            body_html=message_data.body_html,
            received_date=message_data.received_date,
            processed=False,
            processing_status=message_data.processing_status.value,
            error_message=message_data.error_message
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def update_inquiry_version(self, inquiry: TravelInquiry, new_data: TravelInquiryData) -> TravelInquiry:
        # Update fields and increment version if needed
        inquiry.number_of_travelers = new_data.number_of_travelers
        inquiry.destinations = new_data.destinations
        inquiry.travel_dates = new_data.travel_dates
        inquiry.departure_city = new_data.departure_city
        inquiry.hotel_preferences = new_data.hotel_preferences
        inquiry.meal_preferences = new_data.meal_preferences
        inquiry.sightseeing_activities = new_data.sightseeing_activities
        inquiry.guide_language_preferences = new_data.guide_language_preferences
        inquiry.visa_required = new_data.visa_required
        inquiry.insurance_required = new_data.insurance_required
        inquiry.flight_required = new_data.flight_required
        inquiry.budget_range = new_data.budget_range
        inquiry.special_requirements = new_data.special_requirements
        inquiry.inquiry_deadline = new_data.inquiry_deadline
        inquiry.extraction_confidence = new_data.extraction_confidence
        inquiry.requires_clarification = new_data.requires_clarification
        inquiry.clarification_notes = new_data.clarification_notes
        self.db.commit()
        self.db.refresh(inquiry)
        return inquiry

    def get_latest_quote_for_inquiry(self, inquiry: TravelInquiry) -> Optional[TravelQuote]:
        return (
            self.db.query(TravelQuote)
            .filter(TravelQuote.inquiry_id == inquiry.id)
            .order_by(TravelQuote.version.desc())
            .first()
        )

    def close(self):
        self.db.close()

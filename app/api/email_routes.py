from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from typing import List, Optional
from app.models.email_models import EmailMessage, EmailThread, EmailProcessingRequest, EmailProcessingResponse
from app.models.travel_models import TravelInquiryData, TravelQuoteData
from app.services.ai_service import TravelInfoExtractor, ConversationManager
from app.services.email_service import EmailService
from app.services.excel_service import ExcelQuoteGenerator
from app.services.thread_service import ThreadService
from app.utils.logger import get_logger
from app.utils.exceptions import AppError

router = APIRouter()
logger = get_logger(__name__)

email_service = EmailService()
travel_info_extractor = TravelInfoExtractor()
conversation_manager = ConversationManager()
excel_service = ExcelQuoteGenerator()

@router.post("/ingest", response_model=EmailProcessingResponse)
def ingest_emails(request: EmailProcessingRequest, background_tasks: BackgroundTasks):
    """Ingest emails from Gmail/Outlook and start processing."""
    try:
        # In a real system, this would enqueue a Celery task
        background_tasks.add_task(email_service.get_messages, request.email_ids)
        return EmailProcessingResponse(
            task_id="dummy-task-id",
            status="processing",
            processed_count=0,
            failed_count=0,
            errors=[]
        )
    except Exception as e:
        logger.error(f"Email ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract-inquiry", response_model=TravelInquiryData)
async def extract_inquiry(email: EmailMessage):
    """Extract structured travel inquiry from email content."""
    try:
        result = await travel_info_extractor.extract_travel_info(email)
        return result
    except Exception as e:
        logger.error(f"Inquiry extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-quote", response_model=TravelQuoteData)
def generate_quote(inquiry: TravelInquiryData, quote: TravelQuoteData):
    """Generate an Excel quote for a travel inquiry."""
    try:
        file_path = excel_service.generate_quote(inquiry, quote)
        quote.excel_file_path = file_path
        return quote
    except Exception as e:
        logger.error(f"Quote generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/thread/{thread_id}", response_model=EmailThread)
def get_thread(thread_id: str):
    """Get email thread and its messages."""
    try:
        service = ThreadService()
        thread = service.get_thread_by_id(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        # Convert ORM to Pydantic model
        return EmailThread(
            thread_id=thread.thread_id,
            subject=thread.subject,
            sender_email=thread.sender_email,
            sender_name=thread.sender_name,
            messages=[],  # Populate as needed
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            status=thread.status
        )
    except Exception as e:
        logger.error(f"Get thread failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/thread/{thread_id}", response_model=EmailThread)
def update_thread(thread_id: str, thread_data: EmailThread):
    """Update thread details (e.g., status, subject)."""
    try:
        service = ThreadService()
        thread = service.create_or_update_thread(thread_data)
        return thread_data
    except Exception as e:
        logger.error(f"Update thread failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

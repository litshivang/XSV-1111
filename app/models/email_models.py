from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import Field
from app.models.travel_models import ProcessingStatus

class EmailMessage(BaseModel):
    """Email message data structure"""
    
    message_id: str
    thread_id: Optional[str] = None
    subject: str
    sender_email: EmailStr
    sender_name: Optional[str] = None
    recipient_email: Optional[EmailStr] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    received_date: datetime
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Processing metadata
    language_detected: Optional[str] = None
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: Optional[str] = None

class EmailThread(BaseModel):
    """Email thread data structure"""
    
    thread_id: str
    subject: str
    sender_email: EmailStr
    sender_name: Optional[str] = None
    messages: List[EmailMessage] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None
    status: str = "active"

class EmailProcessingRequest(BaseModel):
    """Request to process email(s)"""
    
    email_ids: List[str]
    priority: int = Field(default=5, ge=1, le=10)
    force_reprocess: bool = Field(default=False)

class EmailProcessingResponse(BaseModel):
    """Response from email processing"""
    
    task_id: str
    status: ProcessingStatus
    processed_count: int
    failed_count: int
    errors: List[str] = Field(default_factory=list)

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class EmailThread(Base):
    """Email conversation thread tracking"""
    __tablename__ = "email_threads"
    
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(255), unique=True, index=True, nullable=False)
    subject = Column(String(500), nullable=False)
    sender_email = Column(String(255), nullable=False)
    sender_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    status = Column(String(50), default="active")  # active, completed, archived
    
    # Relationships
    emails = relationship("EmailMessage", back_populates="thread")
    inquiries = relationship("TravelInquiry", back_populates="thread")

class EmailMessage(Base):
    """Individual email messages within a thread"""
    __tablename__ = "email_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), unique=True, index=True, nullable=False)
    thread_id = Column(Integer, ForeignKey("email_threads.id"), nullable=False)
    subject = Column(String(500))
    sender_email = Column(String(255), nullable=False)
    recipient_email = Column(String(255))
    body_text = Column(Text)
    body_html = Column(Text)
    received_date = Column(DateTime(timezone=True), nullable=False)
    processed = Column(Boolean, default=False)
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    thread = relationship("EmailThread", back_populates="emails")
    inquiry = relationship("TravelInquiry", back_populates="email", uselist=False)

class TravelInquiry(Base):
    """Extracted travel inquiry data"""
    __tablename__ = "travel_inquiries"
    
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("email_threads.id"), nullable=False)
    email_id = Column(Integer, ForeignKey("email_messages.id"), nullable=False)
    
    # Travel Details
    number_of_travelers = Column(Integer)
    destinations = Column(JSON)  # List of destinations
    travel_dates = Column(JSON)  # Start and end dates
    departure_city = Column(String(255))
    
    # Preferences
    hotel_preferences = Column(JSON)
    meal_preferences = Column(JSON)
    sightseeing_activities = Column(JSON)
    guide_language_preferences = Column(JSON)
    
    # Requirements
    visa_required = Column(Boolean)
    insurance_required = Column(Boolean)
    flight_required = Column(Boolean)
    budget_range = Column(JSON)  # Min and max budget
    
    # Additional Information
    special_requirements = Column(Text)
    inquiry_deadline = Column(DateTime(timezone=True))
    
    # Processing Information
    extraction_confidence = Column(Integer)  # 1-100 confidence score
    requires_clarification = Column(Boolean, default=False)
    clarification_notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    thread = relationship("EmailThread", back_populates="inquiries")
    email = relationship("EmailMessage", back_populates="inquiry")
    quotes = relationship("TravelQuote", back_populates="inquiry")

class TravelQuote(Base):
    """Generated travel quotes"""
    __tablename__ = "travel_quotes"
    
    id = Column(Integer, primary_key=True, index=True)
    inquiry_id = Column(Integer, ForeignKey("travel_inquiries.id"), nullable=False)
    version = Column(Integer, default=1)
    
    # Quote Details
    quote_data = Column(JSON)  # Structured quote information
    excel_file_path = Column(String(500))
    
    # Status
    status = Column(String(50), default="generated")  # generated, sent, updated
    sent_to_email = Column(String(255))
    sent_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    inquiry = relationship("TravelInquiry", back_populates="quotes")
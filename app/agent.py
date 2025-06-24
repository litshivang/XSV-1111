import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from app.config import settings
from app.services.email_service import EmailService
from app.services.ai_service import AIService
from app.services.excel_service import ExcelService
from app.models.email_models import EmailMessage
from app.models.travel_models import ProcessingStatus
from app.utils.logger import get_logger
from app.database import get_redis

logger = get_logger(__name__)

class TravelAgent:
    """Main agent class that orchestrates the entire workflow"""
    
    def __init__(self):
        self.email_service = EmailService()
        self.ai_service = AIService()
        self.excel_service = ExcelService()
        self.redis = get_redis()
        
    async def _is_email_processed(self, message_id: str) -> bool:
        """Check if an email has been processed already"""
        return bool(await self.redis.get(f"processed_email:{message_id}"))
        
    async def _mark_email_processed(self, message_id: str):
        """Mark an email as processed in Redis with TTL"""
        await self.redis.set(
            f"processed_email:{message_id}",
            "1",
            ex=settings.processed_emails_cache_ttl
        )
    
    async def _mark_email_as_read(self, message: EmailMessage):
        """Mark email as read in the email service"""
        try:
            # Only mark emails from our sender as read
            if message.sender_email == settings.sender_email:
                if message.message_id.startswith('gmail_'):
                    await self.email_service.gmail_service.mark_as_read(message.message_id)
                elif message.message_id.startswith('outlook_'):
                    await self.email_service.outlook_service.mark_as_read(message.message_id)
        except Exception as e:
            logger.error(f"Failed to mark email as read: {e}")
    
    async def process_single_email(self, message: EmailMessage) -> bool:
        """Process a single email message"""
        try:
            # Skip if already processed
            if await self._is_email_processed(message.message_id):
                logger.info(f"Skipping already processed email: {message.message_id}")
                return False
                
            # Only process emails from our sender
            if message.sender_email != settings.sender_email:
                logger.info(f"Skipping email from unauthorized sender: {message.sender_email}")
                return False
            
            # Extract trip requirements using AI
            trip_requirements = await self.ai_service.extract_trip_requirements(
                message.body_text or message.body_html
            )
            
            # Generate Excel quote
            quote_file = await self.excel_service.generate_quote(trip_requirements)
            
            # Send response email with quote
            await self.email_service.send_response(
                message_id=message.message_id,
                thread_id=message.thread_id,
                recipient=message.sender_email,
                subject=f"Re: {message.subject}",
                body="Please find attached the travel quote as requested.",
                attachments=[quote_file]
            )
            
            # Mark as processed and read
            await self._mark_email_processed(message.message_id)
            await self._mark_email_as_read(message)
            
            logger.info(f"Successfully processed email: {message.message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process email {message.message_id}: {e}")
            message.processing_status = ProcessingStatus.FAILED
            message.error_message = str(e)
            return False
    
    async def process_batch(self, max_emails: Optional[int] = None) -> int:
        """Process a batch of unread emails"""
        try:
            # Get unread travel inquiries
            messages = await self.email_service.get_travel_inquiries(
                source="both",
                max_results=max_emails or settings.max_emails_per_batch
            )
            
            # Process each message
            processed_count = 0
            for message in messages:
                if await self.process_single_email(message):
                    processed_count += 1
                    
                # Rate limiting
                if processed_count >= settings.rate_limit_per_minute:
                    logger.warning("Rate limit reached, pausing processing")
                    break
                    
            return processed_count
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return 0
    
    async def run_continuous(self):
        """Run the agent continuously"""
        while True:
            try:
                processed = await self.process_batch()
                logger.info(f"Processed {processed} emails in this batch")
                
                # Sleep if no emails were processed
                if processed == 0:
                    await asyncio.sleep(60)  # Wait 1 minute before next check
                    
            except Exception as e:
                logger.error(f"Agent run failed: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
                
async def main():
    """Main entry point"""
    agent = TravelAgent()
    await agent.run_continuous()
    
if __name__ == "__main__":
    asyncio.run(main()) 
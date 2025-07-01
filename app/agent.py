import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timedelta
import time

from app.config import settings
from app.services.email_service import EmailService
from app.services.ai_service import EnhancedTravelInfoExtractor
from app.services.excel_service import EnhancedExcelQuoteGenerator
from app.models.email_models import EmailMessage
from app.models.travel_models import ProcessingStatus, TravelQuoteData
from app.utils.logger import get_logger
from app.utils.redis_client import get_redis_client

logger = get_logger(__name__)

class TravelAgent:
    """Main agent class that orchestrates the entire workflow"""
    
    def __init__(self):
        self.email_service = EmailService()
        self.ai_extractor = EnhancedTravelInfoExtractor()
        self.excel_generator = EnhancedExcelQuoteGenerator()
        self.redis = get_redis_client()
        
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
    
    async def process_single_email(self, message: EmailMessage):
        """Process a single email message and return token/time info for table"""
        start_time = time.monotonic()
        try:
            # Skip if already processed
            if await self._is_email_processed(message.message_id):
                logger.info(f"Skipping already processed email: {message.message_id}")
                return False, None
                
            # Only process emails from our sender
            if message.sender_email != settings.sender_email:
                logger.info(f"Skipping email from unauthorized sender: {message.sender_email}")
                return False, None
            
            # Extract trip requirements using AI
            inquiry, token_info = await self.ai_extractor.extract_travel_info(message)
            # Generate enhanced quote data (should be replaced with real pricing logic)
            quote_data = TravelQuoteData.create_enhanced_placeholder(inquiry)
            # Generate Excel quote
            quote_file = await self.excel_generator.generate_quote(inquiry, quote_data)
            
            # Send response email with quote (uncomment if needed)
            # await self.email_service.send_response(
            #     message_id=message.message_id,
            #     thread_id=message.thread_id,
            #     recipient=message.sender_email,
            #     subject=f"Re: {message.subject}",
            #     body=("Dear Wanderer,\n\nThank you for your inquiry. Please find attached your customized travel quotation.\n"
            #           "If you have any questions or need further customization, feel free to reply to this email.\n\nBest regards,\nYour Trip Maker"),
            #     attachments=[quote_file]
            # )
            
            # Mark as processed and read
            # await self._mark_email_processed(message.message_id)
            # await self._mark_email_as_read(message)
            
            elapsed = time.monotonic() - start_time
            logger.info(f"Successfully processed email: {message.message_id} | Time taken: {elapsed:.2f} seconds")
            # Add message_id to token_info for table
            if token_info is not None:
                token_info['message_id'] = message.message_id
            return True, token_info
            
        except Exception as e:
            elapsed = time.monotonic() - start_time
            logger.error(f"Failed to process email {message.message_id} after {elapsed:.2f} seconds: {e}")
            message.processing_status = ProcessingStatus.FAILED
            message.error_message = str(e)
            return False, {
                'message_id': message.message_id,
                'prompt_tokens': 0,
                'response_tokens': 0,
                'total_tokens': 0,
                'time_taken': elapsed
            }
    
    async def process_batch(self, max_emails: Optional[int] = None) -> int:
        """Process a batch of unread emails and log a table of tokens/time"""
        batch_start = time.monotonic()
        token_rows = []
        try:
            messages = await self.email_service.get_travel_inquiries(
                source="both",
                max_results=max_emails or settings.max_emails_per_batch
            )
            if not messages:
                logger.info("No new travel inquiry emails found from Gmail or Outlook.")
                return 0
            processed_count = 0
            for message in messages:
                success, token_info = await self.process_single_email(message)
                if token_info is not None:
                    token_rows.append(token_info)
                if success:
                    processed_count += 1
                if processed_count >= settings.rate_limit_per_minute:
                    logger.warning("Rate limit reached, pausing processing")
                    break
            batch_elapsed = time.monotonic() - batch_start
            # Compute totals
            total_prompt = sum(row.get('prompt_tokens', 0) for row in token_rows)
            total_response = sum(row.get('response_tokens', 0) for row in token_rows)
            total_tokens = sum(row.get('total_tokens', 0) for row in token_rows)
            total_time = sum(row.get('time_taken', 0) for row in token_rows)
            # Build table
            table_lines = [
                "\nBatch Processing Summary (Tokens & Time):",
                f"{'Email ID':<30} | {'Prompt':>8} | {'Response':>8} | {'Total':>8} | {'Time (s)':>9}",
                "-"*75
            ]
            for row in token_rows:
                table_lines.append(f"{row.get('message_id','')[:30]:<30} | {row.get('prompt_tokens',0):>8} | {row.get('response_tokens',0):>8} | {row.get('total_tokens',0):>8} | {row.get('time_taken',0):>9.2f}")
            table_lines.append("-"*75)
            table_lines.append(f"{'TOTAL':<30} | {total_prompt:>8} | {total_response:>8} | {total_tokens:>8} | {total_time:>9.2f}")
            logger.info("\n" + "\n".join(table_lines))
            logger.info(f"Batch processing complete: {processed_count} emails processed | Total time: {batch_elapsed:.2f} seconds")
            return processed_count
        except Exception as e:
            batch_elapsed = time.monotonic() - batch_start
            logger.error(f"Batch processing failed after {batch_elapsed:.2f} seconds: {e}")
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
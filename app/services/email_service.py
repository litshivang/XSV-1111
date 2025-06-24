import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from msal import ConfidentialClientApplication
import httpx
import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings
from app.models.email_models import EmailMessage, EmailThread
from app.utils.logger import get_logger
from app.utils.exceptions import EmailServiceError

logger = get_logger(__name__)

class GmailService:
    """Gmail API integration service"""
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Gmail API service"""
        try:
            # Load credentials from file
            if os.path.exists(settings.gmail_token_file):
                self.credentials = Credentials.from_authorized_user_file(
                    settings.gmail_token_file, settings.gmail_scopes
                )
            
            # If credentials are not valid, initiate OAuth flow
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    flow = Flow.from_client_secrets_file(
                        settings.gmail_credentials_file, settings.gmail_scopes
                    )
                    flow.redirect_uri = 'http://localhost:8080/callback'
                    
                    # Note: In production, implement proper OAuth flow
                    logger.warning("Gmail credentials need manual authorization")
                    raise EmailServiceError("Gmail authentication required")
            
            # Build the service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info("Gmail service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            raise EmailServiceError(f"Gmail initialization failed: {e}")
    
    async def get_messages(self, query: str = "", max_results: int = 50) -> List[EmailMessage]:
        """Retrieve email messages from Gmail"""
        try:
            # Search for messages
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            email_messages = []
            
            for msg in messages:
                # Get full message details
                message = self.service.users().messages().get(
                    userId='me', id=msg['id'], format='full'
                ).execute()
                
                # Parse message
                email_msg = self._parse_gmail_message(message)
                if email_msg:
                    email_messages.append(email_msg)
            
            logger.info(f"Retrieved {len(email_messages)} Gmail messages")
            return email_messages
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise EmailServiceError(f"Failed to retrieve Gmail messages: {e}")
    
    def _parse_gmail_message(self, message: Dict) -> Optional[EmailMessage]:
        """Parse Gmail message into EmailMessage model"""
        try:
            payload = message['payload']
            headers = {h['name'].lower(): h['value'] for h in payload.get('headers', [])}
            
            # Extract basic information
            message_id = message['id']
            thread_id = message['threadId']
            subject = headers.get('subject', 'No Subject')
            sender = headers.get('from', '')
            recipient = headers.get('to', '')
            date_str = headers.get('date', '')
            
            # Parse sender email and name
            sender_email, sender_name = self._parse_email_address(sender)
            recipient_email, _ = self._parse_email_address(recipient)
            
            # Parse date
            received_date = self._parse_email_date(date_str)
            
            # Extract body
            body_text, body_html = self._extract_message_body(payload)
            
            return EmailMessage(
                message_id=message_id,
                thread_id=thread_id,
                subject=subject,
                sender_email=sender_email,
                sender_name=sender_name,
                recipient_email=recipient_email,
                body_text=body_text,
                body_html=body_html,
                received_date=received_date
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Gmail message: {e}")
            return None
    
    def _extract_message_body(self, payload: Dict) -> tuple[Optional[str], Optional[str]]:
        """Extract text and HTML body from message payload"""
        body_text = None
        body_html = None
        
        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain' and 'data' in part['body']:
                    body_text = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif mime_type == 'text/html' and 'data' in part['body']:
                    body_html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        else:
            # Single part message
            if payload.get('mimeType') == 'text/plain' and 'data' in payload['body']:
                body_text = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            elif payload.get('mimeType') == 'text/html' and 'data' in payload['body']:
                body_html = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        return body_text, body_html
    
    @staticmethod
    def _parse_email_address(email_str: str) -> tuple[str, Optional[str]]:
        """Parse email address and name from string"""
        try:
            if '<' in email_str and '>' in email_str:
                # Format: "Name <email@domain.com>"
                name = email_str.split('<')[0].strip().strip('"')
                email_addr = email_str.split('<')[1].split('>')[0].strip()
                return email_addr, name if name else None
            else:
                # Format: "email@domain.com"
                return email_str.strip(), None
        except Exception:
            return email_str.strip(), None
    
    @staticmethod
    def _parse_email_date(date_str: str) -> datetime:
        """Parse email date string to datetime"""
        try:
            # Gmail typically uses RFC 2822 format
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            return datetime.now()

class OutlookService:
    """Microsoft Outlook/Graph API integration service"""
    
    def __init__(self):
        self.app = ConfidentialClientApplication(
            settings.outlook_client_id,
            authority=f"https://login.microsoftonline.com/{settings.outlook_tenant_id}",
            client_credential=settings.outlook_client_secret
        )
        self.access_token = None
        self._get_access_token()
    
    def _get_access_token(self):
        """Get access token for Microsoft Graph API"""
        try:
            result = self.app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                logger.info("Outlook access token acquired successfully")
            else:
                logger.error(f"Failed to acquire Outlook token: {result.get('error_description')}")
                raise EmailServiceError("Failed to authenticate with Outlook")
                
        except Exception as e:
            logger.error(f"Outlook authentication error: {e}")
            raise EmailServiceError(f"Outlook authentication failed: {e}")
    
    async def get_messages(self, user_email: str, max_results: int = 50) -> List[EmailMessage]:
        """Retrieve email messages from Outlook"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Microsoft Graph API endpoint
            url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages"
            params = {
                '$top': max_results,
                '$orderby': 'receivedDateTime desc',
                '$select': 'id,subject,from,toRecipients,receivedDateTime,body,conversationId'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                messages = data.get('value', [])
                
                email_messages = []
                for msg in messages:
                    email_msg = self._parse_outlook_message(msg)
                    if email_msg:
                        email_messages.append(email_msg)
                
                logger.info(f"Retrieved {len(email_messages)} Outlook messages")
                return email_messages
                
        except httpx.HTTPError as e:
            logger.error(f"Outlook API error: {e}")
            raise EmailServiceError(f"Failed to retrieve Outlook messages: {e}")
    
    def _parse_outlook_message(self, message: Dict) -> Optional[EmailMessage]:
        """Parse Outlook message into EmailMessage model"""
        try:
            message_id = message['id']
            thread_id = message.get('conversationId')
            subject = message.get('subject', 'No Subject')
            
            # Parse sender
            from_data = message.get('from', {})
            sender_data = from_data.get('emailAddress', {})
            sender_email = sender_data.get('address', '')
            sender_name = sender_data.get('name')
            
            # Parse recipients
            recipients = message.get('toRecipients', [])
            recipient_email = recipients[0]['emailAddress']['address'] if recipients else None
            
            # Parse date
            received_date_str = message.get('receivedDateTime')
            received_date = datetime.fromisoformat(received_date_str.replace('Z', '+00:00'))
            
            # Extract body
            body_data = message.get('body', {})
            body_content = body_data.get('content', '')
            body_type = body_data.get('contentType', 'text')
            
            body_text = body_content if body_type == 'text' else None
            body_html = body_content if body_type == 'html' else None
            
            return EmailMessage(
                message_id=message_id,
                thread_id=thread_id,
                subject=subject,
                sender_email=sender_email,
                sender_name=sender_name,
                recipient_email=recipient_email,
                body_text=body_text,
                body_html=body_html,
                received_date=received_date
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Outlook message: {e}")
            return None

class EmailService:
    """Unified email service for Gmail and Outlook"""
    
    def __init__(self):
        self.gmail_service = GmailService()
        self.outlook_service = OutlookService()
    
    async def get_travel_inquiries(self, source: str = "both", max_results: int = 50) -> List[EmailMessage]:
        """Get travel inquiry emails from specified source(s)"""
        all_messages = []
        
        # Gmail search query for travel-related emails
        travel_query = 'subject:("travel" OR "trip" OR "tour" OR "vacation" OR "holiday" OR "package")'
        
        try:
            if source in ["gmail", "both"]:
                gmail_messages = await self.gmail_service.get_messages(
                    query=travel_query, max_results=max_results
                )
                all_messages.extend(gmail_messages)
            
            if source in ["outlook", "both"]:
                # Note: You'll need to specify user email for Outlook
                # This should be configured based on your organization's setup
                outlook_messages = await self.outlook_service.get_messages(
                    user_email="travel@yourcompany.com", max_results=max_results
                )
                all_messages.extend(outlook_messages)
            
            # Sort by received date (newest first)
            all_messages.sort(key=lambda x: x.received_date, reverse=True)
            
            logger.info(f"Retrieved {len(all_messages)} travel inquiry emails")
            return all_messages
            
        except Exception as e:
            logger.error(f"Failed to retrieve travel inquiries: {e}")
            raise EmailServiceError(f"Email retrieval failed: {e}")
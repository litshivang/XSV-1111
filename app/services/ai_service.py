import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import json
import re
from datetime import datetime, timedelta
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import BaseOutputParser
from langchain.output_parsers import PydanticOutputParser
from langdetect import detect
from googletrans import Translator

from app.config import settings
from app.models.travel_models import TravelInquiryData
from app.models.email_models import EmailMessage
from app.utils.logger import get_logger
from app.utils.exceptions import AIServiceError

logger = get_logger(__name__)

class TravelInfoExtractor:
    """AI service for extracting travel information from emails"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.ai_temperature,
            openai_api_key=settings.openai_api_key
        )
        self.translator = Translator()
        self.output_parser = PydanticOutputParser(pydantic_object=TravelInquiryData)
        self._setup_prompts()
    
    def _setup_prompts(self):
        """Setup LangChain prompts for travel information extraction"""
        
        # System prompt for travel extraction
        system_template = """
        You are an expert AI assistant specializing in extracting structured travel information from unstructured email inquiries.
        You work for a B2B travel agency and need to extract detailed travel requirements from customer emails.
        
        Your task is to analyze email content and extract the following information:
        - Number of travelers
        - Destinations (cities, countries, regions)
        - Travel dates (start and end dates)
        - Departure city
        - Hotel preferences (star rating, type, special requirements)
        - Meal preferences (vegetarian, non-vegetarian, specific diets)
        - Sightseeing activities and attractions
        - Guide and language preferences
        - Service requirements (visa, insurance, flights)
        - Budget range (if mentioned)
        - Special requirements or requests
        - Inquiry deadline
        
        IMPORTANT GUIDELINES:
        1. Extract only explicitly mentioned information - do not assume or infer details
        2. For dates, convert to ISO format (YYYY-MM-DD) when possible
        3. Normalize location names to standard formats
        4. Set extraction_confidence (0-100) based on clarity of information
        5. Set requires_clarification=True if critical information is missing or unclear
        6. Handle multilingual content (English, Hindi, or mixed)
        7. If budget is mentioned in any currency, normalize to INR if possible
        
        Output the extracted information in the exact JSON format specified by the schema.
        
        {format_instructions}
        """
        
        human_template = """
        Please extract travel information from the following email:
        
        Email Subject: {subject}
        Email Content: {content}
        Sender: {sender}
        Language Detected: {language}
        
        Extract all relevant travel information and provide a confidence score.
        """
        
        system_message = SystemMessagePromptTemplate.from_template(system_template)
        human_message = HumanMessagePromptTemplate.from_template(human_template)
        
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            system_message,
            human_message
        ])
    
    async def extract_travel_info(self, email: EmailMessage) -> TravelInquiryData:
        """Extract travel information from an email message"""
        try:
            # Detect language and translate if necessary
            content = email.body_text or email.body_html or ""
            language = self._detect_language(content)
            
            # Translate to English if needed for better processing
            translated_content = content
            if language and language != 'en':
                try:
                    translated_content = self.translator.translate(content, dest='en').text
                    logger.info(f"Translated email from {language} to English")
                except Exception as e:
                    logger.warning(f"Translation failed: {e}, using original content")
            
            # Prepare prompt
            formatted_prompt = self.extraction_prompt.format_prompt(
                subject=email.subject,
                content=translated_content,
                sender=f"{email.sender_name} <{email.sender_email}>",
                language=language,
                format_instructions=self.output_parser.get_format_instructions()
            )
            
            # Get AI response
            response = await self._get_ai_response(formatted_prompt.to_messages())
            
            # Parse response
            travel_info = self.output_parser.parse(response.content)
            
            # Add metadata
            travel_info.original_language = language
            
            # Validate and enhance extracted data
            travel_info = self._validate_and_enhance(travel_info, email)
            
            logger.info(f"Successfully extracted travel info with {travel_info.extraction_confidence}% confidence")
            return travel_info
            
        except Exception as e:
            logger.error(f"Failed to extract travel information: {e}")
            # Return minimal structure with error indication
            return TravelInquiryData(
                extraction_confidence=0,
                requires_clarification=True,
                clarification_notes=f"Extraction failed: {str(e)}",
                original_language=self._detect_language(email.body_text or "")
            )
    
    async def _get_ai_response(self, messages):
        """Get response from AI model with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.llm.agenerate([messages])
                return response.generations[0][0]
            except Exception as e:
                logger.warning(f"AI request attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise AIServiceError(f"AI request failed after {max_retries} attempts: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language of the text"""
        try:
            if not text or len(text.strip()) < 10:
                return None
            return detect(text)
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return None
    
    def _validate_and_enhance(self, travel_info: TravelInquiryData, email: EmailMessage) -> TravelInquiryData:
        """Validate and enhance extracted travel information"""
        
        # Validate travel dates
        if travel_info.travel_dates:
            try:
                dates = travel_info.travel_dates
                if isinstance(dates, dict) and 'start' in dates and 'end' in dates:
                    start_date = datetime.fromisoformat(dates['start']) if isinstance(dates['start'], str) else dates['start']
                    end_date = datetime.fromisoformat(dates['end']) if isinstance(dates['end'], str) else dates['end']
                    
                    # Check if dates are in the past
                    if start_date < datetime.now():
                        travel_info.requires_clarification = True
                        travel_info.clarification_notes = (travel_info.clarification_notes or "") + " Travel dates appear to be in the past."
                    
                    # Check for reasonable trip duration
                    duration = (end_date - start_date).days
                    if duration < 1 or duration > 365:
                        travel_info.requires_clarification = True
                        travel_info.clarification_notes = (travel_info.clarification_notes or "") + f" Unusual trip duration: {duration} days."
            except Exception as e:
                logger.warning(f"Date validation failed: {e}")
        
        # Validate number of travelers
        if travel_info.number_of_travelers:
            if travel_info.number_of_travelers < 1 or travel_info.number_of_travelers > 100:
                travel_info.requires_clarification = True
                travel_info.clarification_notes = (travel_info.clarification_notes or "") + " Unusual number of travelers."
        
        # Check for missing critical information
        critical_missing = []
        if not travel_info.destinations:
            critical_missing.append("destinations")
        if not travel_info.travel_dates:
            critical_missing.append("travel dates")
        if not travel_info.number_of_travelers:
            critical_missing.append("number of travelers")
        
        if critical_missing:
            travel_info.requires_clarification = True
            travel_info.clarification_notes = (travel_info.clarification_notes or "") + f" Missing critical information: {', '.join(critical_missing)}."
        
        # Adjust confidence based on completeness
        completeness_score = self._calculate_completeness_score(travel_info)
        travel_info.extraction_confidence = min(travel_info.extraction_confidence, completeness_score)
        
        return travel_info
    
    def _calculate_completeness_score(self, travel_info: TravelInquiryData) -> int:
        """Calculate completeness score based on available information"""
        score = 0
        max_score = 100
        
        # Critical information (70 points)
        if travel_info.destinations:
            score += 25
        if travel_info.travel_dates:
            score += 25
        if travel_info.number_of_travelers:
            score += 20
        
        # Important information (20 points)
        if travel_info.departure_city:
            score += 5
        if travel_info.budget_range:
            score += 5
        if travel_info.hotel_preferences:
            score += 5
        if travel_info.special_requirements:
            score += 5
        
        # Additional information (10 points)
        if travel_info.meal_preferences:
            score += 2
        if travel_info.sightseeing_activities:
            score += 2
        if travel_info.guide_language_preferences:
            score += 2
        if travel_info.visa_required is not None:
            score += 2
        if travel_info.flight_required is not None:
            score += 2
        
        return min(score, max_score)

class ConversationManager:
    """Manages conversation threads and updates"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.1,
            openai_api_key=settings.openai_api_key
        )
        self._setup_update_detection_prompt()
    
    def _setup_update_detection_prompt(self):
        """Setup prompt for detecting updates in conversation"""
        
        system_template = """
        You are an expert at analyzing email conversations to detect changes and updates in travel requirements.
        
        Given a previous travel inquiry and a new email in the same conversation thread, determine:
        1. Whether the new email contains updates to the original travel requirements
        2. What specific changes have been made
        3. Whether this is a clarification, modification, or addition to the original request
        
        Analyze the following aspects:
        - Changes in travel dates
        - Changes in number of travelers
        - Addition or removal of destinations
        - Changes in budget or preferences
        - New requirements or special requests
        - Clarifications or corrections to previous information
        
        Return a JSON response with:
        {{
            "has_updates": boolean,
            "update_type": "clarification|modification|addition|cancellation",
            "changes_detected": [list of specific changes],
            "confidence": integer (0-100),
            "requires_new_quote": boolean
        }}
        """
        
        human_template = """
        Original Travel Inquiry:
        {original_inquiry}
        
        New Email Content:
        Subject: {new_subject}
        Content: {new_content}
        
        Analyze if there are any updates or changes in the new email compared to the original inquiry.
        """
        
        self.update_detection_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ])
    
    async def detect_updates(self, original_inquiry: TravelInquiryData, new_email: EmailMessage) -> Dict[str, Any]:
        """Detect updates in a conversation thread"""
        try:
            # Format the prompt
            formatted_prompt = self.update_detection_prompt.format_prompt(
                original_inquiry=original_inquiry.dict(),
                new_subject=new_email.subject,
                new_content=new_email.body_text or new_email.body_html or ""
            )
            
            # Get AI response
            response = await self.llm.agenerate([formatted_prompt.to_messages()])
            result_text = response.generations[0][0].content
            
            # Parse JSON response
            result = json.loads(result_text)
            
            logger.info(f"Update detection completed with {result.get('confidence', 0)}% confidence")
            return result
            
        except Exception as e:
            logger.error(f"Failed to detect updates: {e}")
            return {
                "has_updates": False,
                "update_type": "unknown",
                "changes_detected": [],
                "confidence": 0,
                "requires_new_quote": False,
                "error": str(e)
            }
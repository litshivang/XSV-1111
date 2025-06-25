
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import json
import re
from datetime import datetime, timedelta
from langchain_community.llms import OpenAI
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import BaseOutputParser
from langchain.output_parsers import PydanticOutputParser
from langdetect import detect
from googletrans import Translator

from app.config import settings
from app.models.travel_models import TravelInquiryData, InquiryComplexity, DestinationDetail, TravelerInfo
from app.models.email_models import EmailMessage
from app.utils.logger import get_logger
from app.utils.exceptions import AIServiceError

logger = get_logger(__name__)

class EnhancedTravelInfoExtractor:
    """Enhanced AI service for extracting travel information from emails with high accuracy"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.1,  # Lower temperature for more consistent extraction
            openai_api_key=settings.openai_api_key
        )
        self.translator = Translator()
        self.output_parser = PydanticOutputParser(pydantic_object=TravelInquiryData)
        self._setup_enhanced_prompts()
    
    def _setup_enhanced_prompts(self):
        """Setup enhanced LangChain prompts for high-accuracy travel information extraction"""
        
        system_template = """
        You are an EXPERT AI assistant specializing in extracting structured travel information from unstructured email inquiries with 95%+ accuracy.
        You work for a premium B2B travel agency and must extract EVERY detail mentioned in customer emails.

        CRITICAL GUIDELINES FOR 95% ACCURACY:
        1. EXTRACT EVERYTHING: Every number, location, preference, date, requirement mentioned
        2. DIFFERENTIATE INQUIRY TYPES:
           - SIMPLE: General requirements for entire trip (same preferences for all destinations)
           - COMPLEX: Specific requirements per destination (different preferences per location)
        3. BE PRECISE: Extract exact values, don't approximate or assume
        4. CAPTURE NUANCES: Special requests, accessibility needs, dietary requirements
        5. MAINTAIN CONTEXT: Understand relationships between information pieces

        EXTRACTION TARGETS:
        
        TRAVELER INFORMATION:
        - Total number of travelers (exact count)
        - Breakdown: adults, children, couples, singles
        - Visa requirements (who needs visa assistance)
        - Special needs (wheelchair access, medical requirements)

        DESTINATIONS & DURATION:
        - All destinations mentioned
        - Duration per destination (nights/days)
        - Total trip duration
        - Departure city

        ACCOMMODATION PREFERENCES:
        - For SIMPLE inquiries: Global hotel preferences
        - For COMPLEX inquiries: Hotel preferences per destination
        - Star rating, hotel type (resort, villa, etc.)
        - Room requirements (twin sharing, single rooms)

        MEAL PREFERENCES:
        - For SIMPLE inquiries: Global meal preferences
        - For COMPLEX inquiries: Meal preferences per destination
        - Dietary restrictions (veg, non-veg, specific diets)
        - Meal types (all meals, breakfast only, etc.)

        ACTIVITIES & SIGHTSEEING:
        - Specific attractions mentioned (e.g., "Kintamani sunrise", "Eiffel Tower")
        - Activity types (beach hopping, temple visits, tours)
        - Per destination activities for complex inquiries

        SERVICES REQUIRED:
        - Visa assistance needed (and for how many travelers)
        - Travel insurance requirements
        - Flight booking needs
        - Airport transfers
        - Transportation preferences (private car, hotel shuttle, Eurail)

        GUIDE REQUIREMENTS:
        - Language preferences (English speaking guide)
        - Specific destinations requiring guides
        - Guide type preferences

        BUDGET INFORMATION:
        - Budget per person (extract exact amounts: ₹60000, ₹50000)
        - Total budget if mentioned
        - Currency (INR, USD, EUR)

        QUOTE REQUIREMENTS:
        - Number of quote options needed ("2 package options", "two quotes")
        - Specific quote variations requested
        - Deadline urgency ("ASAP", "by EOD")

        SPECIAL REQUIREMENTS:
        - Accessibility needs (wheelchair access)
        - Special occasions (honeymoon, anniversary)
        - Unique requests

        CRITICAL EXTRACTION RULES:
        1. For COMPLEX inquiries, create separate DestinationDetail entries for each location
        2. Extract location-specific preferences accurately
        3. Differentiate between global and destination-specific requirements
        4. Capture exact budget figures with currency
        5. Note specific activities and attractions by name
        6. Record transportation preferences per destination
        7. Extract visa requirements with exact counts

        {format_instructions}
        """
        
        human_template = """
        TRAVEL INQUIRY ANALYSIS:
        
        Email Subject: {subject}
        Email Content: {content}
        Sender: {sender}
        Language: {language}
        
        EXTRACTION TASK:
        1. First, determine if this is a SIMPLE or COMPLEX inquiry
        2. Extract ALL information mentioned in the email
        3. For complex inquiries, create destination-specific details
        4. Capture exact numbers, amounts, and specific requirements
        5. Note any missing critical information for clarification
        
        Provide extraction confidence score based on completeness and clarity.
        """
        
        system_message = SystemMessagePromptTemplate.from_template(system_template)
        human_message = HumanMessagePromptTemplate.from_template(human_template)
        
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            system_message,
            human_message
        ])
    
    async def extract_travel_info(self, email: EmailMessage) -> TravelInquiryData:
        """Extract travel information with enhanced accuracy"""
        try:
            # Detect language and translate if necessary
            content = email.body_text or email.body_html or ""
            language = self._detect_language(content)
            
            # Translate to English if needed
            translated_content = content
            if language and language != 'en':
                try:
                    translated_content = self.translator.translate(content, dest='en').text
                    logger.info(f"Translated email from {language} to English")
                except Exception as e:
                    logger.warning(f"Translation failed: {e}, using original content")
            
            # Prepare enhanced prompt
            formatted_prompt = self.extraction_prompt.format_prompt(
                subject=email.subject,
                content=translated_content,
                sender=f"{email.sender_name} <{email.sender_email}>",
                language=language,
                format_instructions=self.output_parser.get_format_instructions()
            )
            
            # Get AI response with retries
            response = await self._get_ai_response_with_retries(formatted_prompt.to_messages())
            
            # Parse response
            travel_info = self.output_parser.parse(response.text)
            
            # Post-process and validate
            travel_info = self._post_process_extraction(travel_info, email, content)
            
            logger.info(f"Successfully extracted travel info with {travel_info.extraction_confidence}% confidence")
            return travel_info
            
        except Exception as e:
            logger.error(f"Failed to extract travel information: {e}")
            return self._create_fallback_response(email, str(e))
    
    async def _get_ai_response_with_retries(self, messages, max_retries=3):
        """Get AI response with enhanced retry logic"""
        for attempt in range(max_retries):
            try:
                response = await self.llm.agenerate([messages])
                return response.generations[0][0]
            except Exception as e:
                logger.warning(f"AI request attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise AIServiceError(f"AI request failed after {max_retries} attempts: {e}")
                await asyncio.sleep(2 ** attempt)
    
    def _post_process_extraction(self, travel_info: TravelInquiryData, email: EmailMessage, original_content: str) -> TravelInquiryData:
        """Post-process extracted information for accuracy"""
        
        # Determine inquiry complexity if not set
        if not travel_info.inquiry_complexity:
            travel_info.inquiry_complexity = self._determine_complexity(travel_info, original_content)
        
        # Extract additional patterns not caught by AI
        travel_info = self._extract_additional_patterns(travel_info, original_content)
        
        # Validate and enhance data
        travel_info = self._validate_and_enhance_data(travel_info)
        
        # Calculate confidence score
        travel_info.extraction_confidence = self._calculate_enhanced_confidence(travel_info, original_content)
        
        # Set key information extracted
        travel_info.key_information_extracted = self._list_extracted_information(travel_info)
        
        return travel_info
    
    def _determine_complexity(self, travel_info: TravelInquiryData, content: str) -> InquiryComplexity:
        """Determine if inquiry is simple or complex"""
        complexity_indicators = [
            len(travel_info.destinations) > 1,
            len(travel_info.destination_details) > 0,
            "each destination" in content.lower(),
            "per location" in content.lower(),
            "different" in content.lower() and ("hotel" in content.lower() or "meal" in content.lower()),
            re.search(r'\d+\s*nights?\s+in\s+\w+', content.lower()),
            "for singapore" in content.lower() or "for goa" in content.lower() or "in switzerland" in content.lower()
        ]
        
        return InquiryComplexity.COMPLEX if any(complexity_indicators) else InquiryComplexity.SIMPLE
    
    def _extract_additional_patterns(self, travel_info: TravelInquiryData, content: str) -> TravelInquiryData:
        """Extract additional patterns using regex and NLP"""
        
        # Extract budget patterns
        budget_patterns = [
            r'₹\s*(\d+(?:,\d+)*)\s*per\s*person',
            r'budget.*?₹\s*(\d+(?:,\d+)*)',
            r'(\d+(?:,\d+)*)\s*per\s*person',
            r'around\s*₹\s*(\d+(?:,\d+)*)'
        ]
        
        for pattern in budget_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match and not travel_info.budget_per_person:
                try:
                    travel_info.budget_per_person = float(match.group(1).replace(',', ''))
                    break
                except ValueError:
                    pass
        
        # Extract traveler count patterns
        traveler_patterns = [
            r'(\d+)\s*adults?\s*and\s*(\d+)\s*child(?:ren)?',
            r'(\d+)\s*adults?\s*(\d+)\s*child(?:ren)?',
            r'total\s*(\d+)\s*people',
            r'group\s*of\s*(\d+)',
            r'(\d+)\s*travelers?'
        ]
        
        for pattern in traveler_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:  # adults and children
                    adults = int(match.group(1))
                    children = int(match.group(2))
                    travel_info.traveler_info.adults = adults
                    travel_info.traveler_info.children = children
                    travel_info.traveler_info.total = adults + children
                elif len(match.groups()) == 1:  # total travelers
                    travel_info.traveler_info.total = int(match.group(1))
                break
        
        # Extract quote option requirements
        quote_patterns = [
            r'(\d+)\s*package\s*options?',
            r'(\d+)\s*quotes?',
            r'two\s*quotes?',
            r'multiple\s*options?'
        ]
        
        for pattern in quote_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                if match.group(0).lower().startswith('two'):
                    travel_info.number_of_quote_options = 2
                elif match.group(1).isdigit():
                    travel_info.number_of_quote_options = int(match.group(1))
                break
        
        # Extract urgency indicators
        urgency_patterns = ['asap', 'urgent', 'by eod', 'end of day', 'immediately']
        if any(pattern in content.lower() for pattern in urgency_patterns):
            travel_info.urgent_request = True
            travel_info.quote_deadline = "ASAP"
        
        # Extract specific activities and attractions
        activity_patterns = [
            r'(kintamani sunrise|ubud tour|tanah lot temple)',
            r'(gardens by the bay|sentosa tour)',
            r'(eiffel tower|tower of pisa)',
            r'(dudhsagar falls|beach hopping)',
            r'(site-?seeings?|sightseeing)'
        ]
        
        for pattern in activity_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if match and match not in travel_info.global_activities:
                    travel_info.global_activities.append(match.title())
        
        return travel_info
    
    def _validate_and_enhance_data(self, travel_info: TravelInquiryData) -> TravelInquiryData:
        """Validate and enhance extracted data"""
        
        # Ensure traveler info consistency
        if travel_info.traveler_info.total and not (travel_info.traveler_info.adults or travel_info.traveler_info.children):
            # If only total is provided, assume all adults
            travel_info.traveler_info.adults = travel_info.traveler_info.total
        
        # Validate travel dates
        if travel_info.travel_dates:
            try:
                start_str = travel_info.travel_dates.get('start', '')
                end_str = travel_info.travel_dates.get('end', '')
                if start_str and end_str:
                    start_date = datetime.fromisoformat(start_str) if isinstance(start_str, str) else start_str
                    end_date = datetime.fromisoformat(end_str) if isinstance(end_str, str) else end_str
                    
                    duration_days = (end_date - start_date).days + 1
                    duration_nights = duration_days - 1
                    
                    travel_info.duration = {
                        "total_days": duration_days,
                        "total_nights": duration_nights
                    }
            except Exception as e:
                logger.warning(f"Date validation failed: {e}")
        
        # Set requires_clarification based on missing critical info
        critical_missing = []
        if not travel_info.destinations:
            critical_missing.append("destinations")
        if not travel_info.travel_dates:
            critical_missing.append("travel dates")
        if not travel_info.traveler_info.total:
            critical_missing.append("number of travelers")
        
        if critical_missing:
            travel_info.requires_clarification = True
            travel_info.clarification_notes = f"Missing: {', '.join(critical_missing)}"
        
        return travel_info
    
    def _calculate_enhanced_confidence(self, travel_info: TravelInquiryData, content: str) -> int:
        """Calculate enhanced confidence score"""
        score = 0
        
        # Critical information (60 points)
        if travel_info.destinations:
            score += 20
        if travel_info.travel_dates:
            score += 20
        if travel_info.traveler_info.total:
            score += 20
        
        # Important information (25 points)
        if travel_info.budget_per_person:
            score += 8
        if travel_info.global_hotel_preferences or travel_info.destination_details:
            score += 8
        if travel_info.departure_city:
            score += 5
        if travel_info.global_activities or any(d.activities for d in travel_info.destination_details):
            score += 4
        
        # Additional details (15 points)
        if travel_info.global_meal_preferences or any(d.meal_preferences for d in travel_info.destination_details):
            score += 3
        if travel_info.visa_assistance is not None:
            score += 3
        if travel_info.accessibility_requirements:
            score += 3
        if travel_info.number_of_quote_options > 1:
            score += 3
        if travel_info.guide_language_preferences:
            score += 3
        
        return min(score, 100)
    
    def _list_extracted_information(self, travel_info: TravelInquiryData) -> List[str]:
        """List key information that was successfully extracted"""
        extracted = []
        
        if travel_info.destinations:
            extracted.append(f"Destinations: {', '.join(travel_info.destinations)}")
        if travel_info.traveler_info.total:
            extracted.append(f"Travelers: {travel_info.traveler_info.total}")
        if travel_info.budget_per_person:
            extracted.append(f"Budget: ₹{travel_info.budget_per_person}/person")
        if travel_info.travel_dates:
            extracted.append("Travel dates")
        if travel_info.global_activities or any(d.activities for d in travel_info.destination_details):
            extracted.append("Activities")
        if travel_info.number_of_quote_options > 1:
            extracted.append(f"Quote options: {travel_info.number_of_quote_options}")
        
        return extracted
    
    def _create_fallback_response(self, email: EmailMessage, error: str) -> TravelInquiryData:
        """Create fallback response when extraction fails"""
        return TravelInquiryData(
            extraction_confidence=0,
            requires_clarification=True,
            clarification_notes=f"Extraction failed: {error}",
            original_language=self._detect_language(email.body_text or ""),
            inquiry_complexity=InquiryComplexity.SIMPLE
        )
    
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language of the text"""
        try:
            if not text or len(text.strip()) < 10:
                return None
            return detect(text)
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return None

# Keep the existing ConversationManager class unchanged
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

# Export the enhanced class with the original name for compatibility
TravelInfoExtractor = EnhancedTravelInfoExtractor

import google.generativeai as genai
import time
import json
import re
from typing import Any, Dict, List, Optional
from config.settings import GEMINI_API_KEY, GEMINI_MODEL_NAME
from src.utils.logging_config import setup_logging

logger = setup_logging(__name__)

class GeminiClient:
    def __init__(self):
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not found in environment variables")
            # We don't raise error here to allow app to start, but methods will fail
        else:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel(GEMINI_MODEL_NAME)

    def _clean_json_string(self, json_str: str) -> str:
        """Clean JSON string from markdown code blocks and other artifacts."""
        # Remove markdown code blocks
        json_str = re.sub(r'```json\s*', '', json_str)
        json_str = re.sub(r'```\s*', '', json_str)
        return json_str.strip()

    def generate_structured_response(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Generate a structured JSON response from Gemini.
        
        Args:
            prompt (str): The prompt to send.
            
        Returns:
            Optional[Dict[str, Any]]: Parsed JSON response or None if failed.
        """
        if not GEMINI_API_KEY:
            logger.error("Cannot generate response: GEMINI_API_KEY missing")
            return None

        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                # Add instruction to return JSON
                full_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON."
                
                response = self.model.generate_content(full_prompt)
                
                if not response.text:
                    logger.warning("Empty response from Gemini")
                    continue
                    
                cleaned_json = self._clean_json_string(response.text)
                return json.loads(cleaned_json)
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error on attempt {attempt + 1}: {e}")
                logger.debug(f"Raw response: {response.text}")
            except Exception as e:
                logger.error(f"Gemini API error on attempt {attempt + 1}: {e}")
                if "429" in str(e): # Rate limit
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    time.sleep(retry_delay)
        
        logger.error("Failed to generate structured response after retries")
        return None

    def batch_generate(self, prompts: List[str]) -> List[Optional[Dict[str, Any]]]:
        """
        Process multiple prompts efficiently (sequentially for now to respect rate limits).
        """
        results = []
        for prompt in prompts:
            results.append(self.generate_structured_response(prompt))
            time.sleep(1) # Basic rate limiting
        return results

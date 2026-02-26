import logging
import random
import time
from typing import Dict, List, Optional

from google import genai
from google.genai import types

from src.interfaces.llm_provider import LLMProvider

# Initialize logger for this module
logger = logging.getLogger(__name__)


class GeminiAdapter(LLMProvider):
    """
    Adapter implementation for Google Gemini API using the 'google-genai' SDK.
    Includes Exponential Backoff strategy and Dynamic Few-Shot Prompting (RAG).
    """

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Gemini API Key is missing.")

        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-flash-latest"

    def classify_ticket(
        self, 
        description: str, 
        categories: List[str],
        context_examples: Optional[List[Dict[str, str]]] = None
    ) -> str:

        # --- DYNAMIC PROMPT CONSTRUCTION (RAG / FEW-SHOT) ---
        prompt = f"""
        Role: IT Service Desk Automation Bot.
        Task: Classify the ticket below into exactly one of these categories: {categories}.
        """

        # Inject historical context if available (Human-in-the-Loop learning)
        if context_examples:
            prompt += "\nHere are some past examples of similar tickets and their CORRECT classifications:\n"
            for ex in context_examples:
                # Sanitize inputs to prevent prompt injection or formatting breaks
                ex_desc = ex.get("description", "").replace("\n", " ")
                ex_cat = ex.get("category", "Unclassified")
                prompt += f"- Ticket: '{ex_desc}' -> Category: '{ex_cat}'\n"

        prompt += f"""
        Now, classify this NEW ticket:
        Ticket: "{description}"

        Constraint: Return ONLY the category name. No markdown, no punctuation.
        """

        # --- RETRY LOGIC CONFIGURATION ---
        max_retries = 5
        base_delay = 4.0

        for attempt in range(max_retries):
            try:
                # Attempt to generate content
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0 # Zero temperature for deterministic classification
                    ),
                )

                logger.debug(f"Ticket classified successfully on attempt {attempt + 1}")
                return response.text.strip()

            except Exception as e:
                error_str = str(e)

                # Check if the error is related to Rate Limiting (Quota Exceeded)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt == max_retries - 1:
                        logger.error(
                            "Max retries exceeded for ticket.",
                            extra={"error": error_str, "ticket_snippet": description[:30]}
                        )
                        return "Unclassified"

                    # Exponential Backoff + Jitter Strategy
                    sleep_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)

                    logger.warning(
                        f"Rate limit hit (429). Retrying in {sleep_time:.2f}s...",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "sleep_time": sleep_time
                        }
                    )
                    time.sleep(sleep_time)

                else:
                    # Non-retriable errors
                    logger.error("Gemini API Error (Non-Retriable)", extra={"error": error_str})
                    return "Unclassified"

        return "Unclassified"
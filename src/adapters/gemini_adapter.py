from google import genai
from google.genai import types
from src.interfaces.llm_provider import LLMProvider
from typing import List

class GeminiAdapter(LLMProvider):
    """
    Adapter implementation for Google Gemini API using the new 'google-genai' SDK.
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Gemini API Key is missing.")

        # Initialize the new Client
        self.client = genai.Client(api_key=api_key)
        # We switch to 'gemini-2.5-flash' which is the current standard for speed/efficiency
        self.model_name = "gemini-2.5-flash"

    def classify_ticket(self, description: str, categories: List[str]) -> str:
        prompt = f"""
        Role: IT Service Desk Automation Bot.
        Task: Classify the ticket below into exactly one of these categories: {categories}.

        Ticket: "{description}"

        Constraint: Return ONLY the category name. No markdown, no punctuation.
        """

        try:
            # New API syntax calls for models.generate_content
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0  # Zero temperature for deterministic classification
                )
            )
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return "Unclassified"
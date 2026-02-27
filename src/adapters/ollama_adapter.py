import logging
import requests
from typing import Dict, List, Optional

from src.interfaces.llm_provider import LLMProvider

# Initialize logger for the local LLM adapter
logger = logging.getLogger(__name__)

class OllamaAdapter(LLMProvider):
    """
    Adapter implementation for local LLMs using Ollama.
    Ensures complete data sovereignty with zero external API calls.
    """

    def __init__(self, host: str = "http://ollama:11434", model_name: str = "llama3") -> None:
        self.api_url = f"{host}/api/generate"
        self.model_name = model_name
        logger.info(f"Ollama Adapter initialized. Targeting model: {self.model_name} at {host}")

    def classify_ticket(
        self,
        description: str,
        categories: List[str],
        context_examples: Optional[List[Dict[str, str]]] = None
    ) -> str:

        # --- PROMPT ENGINEERING FOR LOCAL LLM ---
        prompt = f"Role: IT Service Desk Bot. Classify the ticket below into EXACTLY ONE of these categories: {categories}.\n\n"

        if context_examples:
            prompt += "Historical Context (Learn from these):\n"
            for ex in context_examples:
                prompt += f"- Ticket: '{ex.get('description', '')}' -> Category: '{ex.get('category', '')}'\n"

        prompt += f"\nNew Ticket to classify: '{description}'\n"
        prompt += "Constraint: Output ONLY the category name. No explanations, no markdown."

        try:
            # Execute synchronous HTTP POST to the local Ollama container
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0 # Zero temperature for deterministic classification
                    }
                },
                timeout=60 # Extended timeout because local CPU inference is slow
            )
            response.raise_for_status()

            # Parse the JSON response
            result = response.json()
            return result.get("response", "Unclassified").strip()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to communicate with local Ollama engine: {e}")
            return "Unclassified"
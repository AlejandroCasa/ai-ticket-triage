from abc import ABC, abstractmethod
from typing import List


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    This enforces a Strategy Pattern, allowing the application to swap 
    underlying models (Gemini, Mistral, Local, OpenAI) at runtime 
    without changing the core business logic.
    """

    @abstractmethod
    def classify_ticket(self, description: str, categories: List[str]) -> str:
        """
        Classifies a ticket description into one of the provided categories.

        This method must be implemented to handle the specific API calls,
        error handling, and response parsing for the chosen provider.

        Args:
            description (str): The raw text of the IT ticket.
            categories (List[str]): A list of valid categories to choose from.

        Returns:
            str: The selected category name. If classification fails, 
                 implementations should return a fallback (e.g., 'Unclassified').
        """
        pass
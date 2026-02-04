from abc import ABC, abstractmethod
from typing import List

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    This enforces a strategy pattern, allowing us to swap models
    (Gemini, Mistral, Local) without changing the core logic.
    """

    @abstractmethod
    def classify_ticket(self, description: str, categories: List[str]) -> str:
        """
        Classifies a ticket description into one of the provided categories.

        Args:
            description (str): The raw text of the IT ticket.
            categories (List[str]): A list of valid categories to choose from.

        Returns:
            str: The selected category.
        """
        pass
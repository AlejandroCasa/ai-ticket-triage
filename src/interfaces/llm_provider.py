from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    This enforces a Strategy Pattern, allowing the application to swap 
    underlying models at runtime without changing the core business logic.
    """

    @abstractmethod
    def classify_ticket(
        self, 
        description: str, 
        categories: List[str],
        context_examples: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Classifies a ticket description into one of the provided categories.

        Args:
            description (str): The raw text of the IT ticket.
            categories (List[str]): A list of valid categories to choose from.
            context_examples (Optional[List[Dict[str, str]]]): Historical examples 
                for Few-Shot Prompting. Expected format:
                [{"description": "...", "category": "..."}]

        Returns:
            str: The selected category name. If classification fails, 
                 implementations should return a fallback (e.g., 'Unclassified').
        """
        pass
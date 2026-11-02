
from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Common interface for all AI providers."""

    @abstractmethod
    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate a response from the AI provider."""
        raise NotImplementedError

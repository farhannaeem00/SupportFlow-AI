
import logging

from app.schemas.ai import AIReply
from app.services.ai.groq_provider import GroqProvider

logger = logging.getLogger(__name__)

REPLY_SYSTEM_PROMPT = """
You are a professional customer-support assistant.

Guidelines:
- Be polite, clear, concise, and empathetic.
- Use only facts present in the supplied conversation context.
- Never invent order status, refund approval, delivery dates,
  account information, or company policies.
- Ask for clarification when information is missing.
- Never claim that a human agent has taken action unless confirmed.
"""


class ConversationReplyService:
    def __init__(self, provider: GroqProvider | None = None):
        self.provider = provider or GroqProvider()

    def generate_reply(
        self,
        message: str,
        conversation_context: str = "",
    ) -> AIReply:
        user_prompt = f"""
Conversation context:
{conversation_context or "No previous conversation."}

Latest customer message:
{message}

Write an appropriate customer-support response.
"""

        try:
            response = self.provider.generate_response(
                system_prompt=REPLY_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )

            return AIReply(response=response)

        except Exception:
            logger.exception(
                "AI reply generation failed. Using fallback response."
            )

            return AIReply(
                response=(
                    "Thank you for contacting our support team. "
                    "We've received your message. A support agent "
                    "will review your request and assist you."
                )
            )


import json
import logging

from pydantic import ValidationError

from app.schemas.ai import ConversationAnalysis
from app.services.ai.groq_provider import GroqProvider

logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM_PROMPT = """
You are an expert customer-support conversation analyst.

Return ONLY valid JSON with these fields:
{
  "intent": "short intent label",
  "sentiment": "positive | neutral | negative",
  "priority": "low | normal | high | urgent",
  "confidence": 0.0,
  "requires_human": false,
  "reasoning": "brief explanation"
}

Rules:
- Detect the customer's actual support intent.
- Negative sentiment alone does not always mean urgent priority.
- Mark urgent for safety risks or serious time-critical situations.
- Require human attention for sensitive matters or uncertain cases.
- Never invent facts.
"""


class ConversationAnalysisService:
    def __init__(self, provider: GroqProvider | None = None):
        self.provider = provider or GroqProvider()

    def analyze(
        self,
        message: str,
        conversation_context: str = "",
    ) -> ConversationAnalysis:
        user_prompt = f"""
Conversation context:
{conversation_context or "No previous conversation."}

Latest customer message:
{message}

Analyze the latest message and return the required JSON.
"""

        try:
            raw_response = self.provider.generate_response(
                system_prompt=ANALYSIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )

            result = json.loads(raw_response)
            analysis = ConversationAnalysis.model_validate(result)

            return self._apply_escalation_rules(analysis)

        except (Exception, ValidationError):
            logger.exception(
                "AI analysis failed. Using conservative fallback."
            )
            return self._fallback_analysis()

    @staticmethod
    def _fallback_analysis() -> ConversationAnalysis:
        return ConversationAnalysis(
            intent="general_support",
            sentiment="neutral",
            priority="normal",
            confidence=0.0,
            requires_human=True,
            reasoning=(
                "Automated analysis was unavailable or invalid. "
                "Human review is required."
            ),
        )

    @staticmethod
    def _apply_escalation_rules(
        analysis: ConversationAnalysis,
    ) -> ConversationAnalysis:
        if analysis.priority == "urgent":
            analysis.requires_human = True

        if analysis.confidence < 0.60:
            analysis.requires_human = True

        return analysis

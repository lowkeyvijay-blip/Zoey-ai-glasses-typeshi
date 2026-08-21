"""V2.0 Assistant package."""

from backend.assistant.interface import AssistantInterface
from backend.assistant.rule_engine import RuleBasedAssistant

__all__ = ["AssistantInterface", "RuleBasedAssistant"]

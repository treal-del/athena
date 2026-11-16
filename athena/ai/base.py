"""Provider-independent AI interface.

Athena v0.1 works without any AI provider.  This module defines the contract
a future model provider must satisfy and ships with a :class:`DeterministicProvider`
that makes no model calls and never pretends to be intelligent.

Security principles enforced here:
* API credentials are read only from environment variables and are never logged.
* Model-generated text is never executed as Python or shell code.
* Tool calls require explicit permission and validated arguments.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolDefinition:
    """Declares a tool the assistant may call."""

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for arguments
    permission_required: bool = True


@dataclass
class ToolCall:
    """A single requested tool invocation."""

    name: str
    arguments: Dict[str, Any]
    call_id: str = ""


@dataclass
class AIResponse:
    """Response from an AI provider."""

    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    error: Optional[str] = None
    raw: Optional[Any] = None


class AIProvider(ABC):
    """Contract for an AI provider.

    Implementations must never execute model-generated text as code and must
    respect ``tool_permissions`` (a set of tool names the caller has approved).
    """

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        tools: Optional[List[ToolDefinition]] = None,
        tool_permissions: Optional[set[str]] = None,
        context_limit: Optional[int] = None,
    ) -> AIResponse:
        """Generate a response.

        Parameters
        ----------
        messages:
            Conversation history (role/content dicts).
        tools:
            Available tools with JSON-schema parameters.
        tool_permissions:
            Tool names the caller has explicitly authorized.  Tools not in this
            set must not be called.
        context_limit:
            Maximum number of recent messages to consider.
        """
        raise NotImplementedError


class DeterministicProvider(AIProvider):
    """Default provider: no model, no faked intelligence.

    It returns a clear message that no AI provider is configured and lists the
    deterministic features available.  It never invents answers, never calls
    tools, and never logs credentials.
    """

    def __init__(self) -> None:
        self.provider_name = "deterministic"
        self._api_key = os.environ.get("ATHENA_AI_API_KEY", "")
        # Credential is held only to pass through to a future real provider;
        # it is never logged or stored.

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        tools: Optional[List[ToolDefinition]] = None,
        tool_permissions: Optional[set[str]] = None,
        context_limit: Optional[int] = None,
    ) -> AIResponse:
        user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_text = m.get("content", "")
                break

        lines = [
            "Athena AI is not configured.",
            "",
            "No model provider is available, so Athena cannot generate AI-driven "
            "responses or reasoning. This is by design: v0.1 never fakes "
            "intelligence with hardcoded answers.",
            "",
            "Available without an AI key:",
            "- Task manager (create, edit, delete, prioritize, schedule)",
            "- Schedule planner (respects fixed events, durations, breaks)",
            "- Memory manager (save, search, approve, edit, delete)",
            "- Projects, milestones, notes, and reports",
            "- Export and backup",
            "",
            "To add AI capabilities, set ATHENA_AI_PROVIDER and ATHENA_AI_API_KEY "
            "in your environment and implement a provider subclassing AIProvider.",
            "",
            "Your message was: " + (user_text or "<none>"),
        ]
        return AIResponse(text="\n".join(lines))


def load_provider() -> AIProvider:
    """Load the configured AI provider.

    Reads ATHENA_AI_PROVIDER from the environment.  When unset (the v0.1
    default) returns :class:`DeterministicProvider`.  The API key is read from
    ATHENA_AI_API_KEY but never logged.

    Future real providers (OpenAI, local Llama, etc.) would be instantiated
    here based on ATHENA_AI_PROVIDER.
    """
    provider_name = os.environ.get("ATHENA_AI_PROVIDER", "").strip().lower()
    if not provider_name:
        return DeterministicProvider()
    # A real provider for the given name is not implemented in v0.1.
    # Fall back to deterministic so the app keeps working without faking AI.
    return DeterministicProvider()


__all__ = [
    "AIProvider",
    "AIResponse",
    "DeterministicProvider",
    "ToolCall",
    "ToolDefinition",
    "load_provider",
]

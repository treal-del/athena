"""Provider-independent AI interface for Athena.

v0.1 ships with a deterministic provider that makes no model calls and never
fakes intelligence.  Real providers can be added later by subclassing
:class:`AIProvider`.
"""

from .base import AIProvider, AIResponse, DeterministicProvider, ToolCall, ToolDefinition, load_provider

__all__ = [
    "AIProvider",
    "AIResponse",
    "DeterministicProvider",
    "ToolCall",
    "ToolDefinition",
    "load_provider",
]

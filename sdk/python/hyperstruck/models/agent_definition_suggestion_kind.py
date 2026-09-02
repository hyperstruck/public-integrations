from enum import Enum


class AgentDefinitionSuggestionKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    TEMPLATE = "template"
    REASONING_PROFILE = "reasoning_profile"
    MCP_SERVER = "mcp_server"
    GUARDRAIL = "guardrail"
    CODE_EXAMPLE = "code_example"

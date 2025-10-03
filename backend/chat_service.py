from typing import List, Dict, Any, Tuple
from .assistant import LLMAssistant, AssistantResponse
from simulator.config import GenesisConfig

_ASSISTANT_CACHE: dict[Tuple[str, str], LLMAssistant] = {}

def get_or_create_assistant(model: str, device: str = "auto") -> LLMAssistant:
    key = (model, device)
    if key not in _ASSISTANT_CACHE:
        _ASSISTANT_CACHE[key] = LLMAssistant(model, device)
    return _ASSISTANT_CACHE[key]

def build_prompt(assistant: LLMAssistant, conversation_history: List[Dict[str, Any]]) -> str:
    """
    conversation_history is a list of messages like:
      {"role": "system"|"user"|"assistant", "content": "text"}
    """
    if not conversation_history or conversation_history[0].get("role") != "system":
        conversation_history = [
            {
                "role": "system",
                "content": "You are a helpful AI assistant that provides structured responses in JSON format."
            },
            *conversation_history,
        ]
    return assistant.chat2prompt(conversation_history)

def generate_structured_response(
    model: str,
    device: str,
    max_tokens: int,
    conversation_history: List[Dict[str, Any]],
) -> Any:
    """
    Core business logic:
    - Load/cached model
    - Turn chat history into prompt
    - Generate structured JSON via your GenesisConfig schema
    - Return the structured_response (a Python object)
    """
    assistant = get_or_create_assistant(model, device)
    prompt = build_prompt(assistant, conversation_history)
    structured_response = assistant.generate_json(
        prompt,
        AssistantResponse,
        max_length=max_tokens,
    )
    return structured_response

from typing import List, Any, Tuple
from .assistant import LLMAssistant, Message, Role, AssistantResponse

_ASSISTANT_CACHE: dict[Tuple[str, str], LLMAssistant] = {}

def get_or_create_assistant(model: str, device: str = "auto") -> LLMAssistant:
    key = (model, device)
    if key not in _ASSISTANT_CACHE:
        _ASSISTANT_CACHE[key] = LLMAssistant(model, device)
    return _ASSISTANT_CACHE[key]

def generate_structured_response(
    model: str,
    device: str,
    max_tokens: int,
    conversation_history: List[Message]
) -> AssistantResponse:
    """
    Generate a structured response from the LLM based on the conversation history.
    args:
        model: The name of the LLM model to use.
        device: The device to run the model on, e.g., 'cpu' or 'cuda'.
        max_tokens: The maximum number of tokens to generate in the response.
        conversation_history: A list of Message objects representing the conversation history.
    returns:
        An AssistantResponse object containing the model's response.
    """
    assistant = get_or_create_assistant(model, device)
    prompt = assistant.build_prompt(conversation_history)
    structured_response = assistant.generate_json(
        prompt,
        max_length=max_tokens
    )
    return structured_response

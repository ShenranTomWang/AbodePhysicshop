from typing import List, Any, Tuple
from .assistant import LLMAssistant, Message, Role, AssistantResponse

_ASSISTANT_CACHE: dict[Tuple[str, str], LLMAssistant] = {}

def get_or_create_assistant(model: str, device: str = "auto") -> LLMAssistant:
    key = (model, device)
    if key not in _ASSISTANT_CACHE:
        _ASSISTANT_CACHE[key] = LLMAssistant(model, device)
    return _ASSISTANT_CACHE[key]

def build_prompt(assistant: LLMAssistant, conversation_history: List[Message]) -> str:
    if not conversation_history or conversation_history[0].role != Role.SYSTEM:
        conversation_history = [
            Message(
                role=Role.SYSTEM,
                content="""
                    You are a helpful AI assistant that provides config for Genesis physics simulation structured in JSON format. \
                    You will provide a textual response or anything you want to ask the user in the "content" field, and a detailed "chain_of_thought" field for your reasoning. \
                    Finally, you will provide a "config" field containing the GenesisConfig JSON schema. \
                    Make assumptions about what the user wants, what objects should be static or dynamic, etc. You do not always need to make changes to the config; if the user is just chatting, you can keep the config the same. \
                """# TODO: Add example response
            ),
            *conversation_history,
        ]
    return assistant.chat2prompt(conversation_history)

def generate_structured_response(
    model: str,
    device: str,
    max_tokens: int,
    conversation_history: List[Message],
    return_raw: bool = False,
) -> AssistantResponse:
    """
    Generate a structured response from the LLM based on the conversation history.
    args:
        model: The name of the LLM model to use.
        device: The device to run the model on, e.g., 'cpu' or 'cuda'.
        max_tokens: The maximum number of tokens to generate in the response.
        conversation_history: A list of Message objects representing the conversation history.
        return_raw: If True, return the raw response from the model without validation.
    returns:
        An AssistantResponse object containing the model's response.
    """
    assistant = get_or_create_assistant(model, device)
    prompt = build_prompt(assistant, conversation_history)
    structured_response = assistant.generate_json(
        prompt,
        max_length=max_tokens,
        return_raw=return_raw
    )
    return structured_response

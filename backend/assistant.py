import outlines
from transformers import AutoTokenizer, AutoModelForCausalLM
from pydantic import BaseModel
from enum import Enum
from simulator.config import GenesisConfig

outlines.models.from_transformers

class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class Message(BaseModel):
    role: Role
    content: str

class AssistantResponse(Message):
    chain_of_thought: str
    config: GenesisConfig

class LLMAssistant:
    def __init__(self, model_name: str, device: str = "cpu"):
        self.model = outlines.from_transformers(
            AutoModelForCausalLM.from_pretrained(model_name, device_map=device),
            AutoTokenizer.from_pretrained(model_name)
        )
        
    def chat2prompt(self, messages: list[Message]) -> str:
        messages = [m.model_dump_json() for m in messages]
        prompt = self.model.hf_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        return prompt

    def generate_json(self, prompt: str, max_length: int = 512) -> AssistantResponse:
        response = self.model(prompt, AssistantResponse, max_length=max_length)
        response = AssistantResponse.model_validate_json(response)
        return response
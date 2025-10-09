import outlines
import logging
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
    
class GenesisConfigWithResponse(BaseModel):
    response: str
    chain_of_thought: str
    config: GenesisConfig

class AssistantResponse(BaseModel):
    role: Role
    content: GenesisConfigWithResponse

class LLMAssistant:
    def __init__(self, model_name: str, device: str = "cpu"):
        self.model = outlines.from_transformers(
            AutoModelForCausalLM.from_pretrained(model_name, device_map=device),
            AutoTokenizer.from_pretrained(model_name)
        )
        
    def chat2prompt(self, messages: list[Message]) -> str:
        prompt = ""
        for message in messages:
            prompt += f"<|im_start|>{message.role}\n: {message.content}<|im_end|>\n"
        return prompt

    def generate_json(self, prompt: str, max_length: int = 512) -> AssistantResponse:
        response = self.model(prompt, AssistantResponse, max_length=max_length)
        response = AssistantResponse.model_validate_json(response)
        return response
import outlines
from transformers import AutoTokenizer, AutoModelForCausalLM
from pydantic import BaseModel
from simulator.config import GenesisConfig

outlines.models.from_transformers

class Message(BaseModel):
    role: str
    content: str

class AssistantResponse(Message):
    config: GenesisConfig
class LLMAssistant:
    def __init__(self, model_name: str, device: str = "cpu"):
        self.model = outlines.from_transformers(
            AutoModelForCausalLM.from_pretrained(model_name, device_map=device),
            AutoTokenizer.from_pretrained(model_name)
        )
        
    def chat2prompt(self, messages: list[Message]) -> str:
        messages = [m.dict() for m in messages]
        prompt = self.model.hf_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        return prompt

    def generate_json(self, prompt: str, formatter: BaseModel, max_length: int = 512) -> dict:
        response = self.model(prompt, formatter, max_length=max_length)
        response = formatter.model_validate_json(response)
        return response
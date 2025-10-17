import outlines
import logging
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
from pydantic import BaseModel
from enum import Enum
from simulator.config import GenesisConfig
from typing import List
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

outlines.models.from_transformers

class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class GenesisConfigWithResponse(BaseModel):
    response: str
    chain_of_thought: str
    config: GenesisConfig

class Message(BaseModel):
    role: Role
    content: str | GenesisConfigWithResponse

class AssistantResponse(Message):
    content: GenesisConfigWithResponse

class LLMAssistant:
    def __init__(self, model_name: str, device: str = "cpu"):
        self.model = outlines.from_transformers(
            AutoModelForCausalLM.from_pretrained(model_name, device_map=device),
            AutoTokenizer.from_pretrained(model_name)
        )
        self.streamer = None
        
    def chat2prompt(self, messages: list[Message]) -> str:
        messages = [msg.model_dump() for msg in messages]
        return self.model.tokenizer.apply_chat_template(messages)
    
    def build_prompt(self, conversation_history: List[Message]) -> str:
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
        return self.chat2prompt(conversation_history)
    
    def get_streamer(self) -> TextIteratorStreamer:
        if self.streamer:
            return self.streamer
        tokenizer = self.model.tokenizer
        self.streamer = TextIteratorStreamer(
            tokenizer,
            skip_special_tokens=True,
            skip_prompt=True
        )
        return self.streamer

    def generate_json(self, prompt: str, max_length: int = 512, streamer: TextIteratorStreamer = None) -> AssistantResponse:
        gen_kwargs = {
            "max_length": max_length
        }
        if streamer:
            gen_kwargs["streamer"] = streamer
        response = self.model(prompt, AssistantResponse, **gen_kwargs)
        response = AssistantResponse.model_validate_json(response)
        return response
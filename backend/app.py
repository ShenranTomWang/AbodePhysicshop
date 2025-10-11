from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .chat_service import generate_structured_response, get_or_create_assistant
from .assistant import AssistantResponse, Message, Role
from logging import getLogger, basicConfig, DEBUG
basicConfig(level=DEBUG)
logger = getLogger(__name__)
app = FastAPI()

class GenerateRequest(BaseModel):
    model: str = Field(..., description="The name of the LLM model to use.")
    device: str = Field("cpu", description="The device to run the model on, e.g., 'cpu' or 'cuda'.")
    conversation_history: list[dict] = Field(
        ..., 
        description="A list of messages representing the conversation history."
    )
    max_tokens: int = Field(51200, description="The maximum number of tokens to generate in the response.")
    
class SetModelRequest(BaseModel):
    model: str = Field(..., description="The name of the LLM model to use.")
    device: str = Field("cpu", description="The device to run the model on, e.g., 'cpu' or 'cuda'.")

def prepare_history(history: list[dict]) -> list[Message]:
    messages = []
    for entry in history:
        try:
            if entry["role"] in {Role.SYSTEM, Role.USER}:
                messages.append(Message.model_validate(entry))
            elif entry["role"] == Role.ASSISTANT:
                messages.append(AssistantResponse.model_validate(entry))
            else:
                raise ValueError(f"Unknown role: {entry['role']}")
        except Exception as e:
            raise ValueError(f"Invalid message format: {entry}. Error: {e}")
    return messages

@app.post("/generate")
def generate(request: GenerateRequest):
    logger.debug("Received generate request")
    try:
        logger.debug(f"Preparing conversation history with {len(request.conversation_history)} messages")
        history = prepare_history(request.conversation_history)
        response = generate_structured_response(
            model=request.model,
            device=request.device,
            max_tokens=request.max_tokens,
            conversation_history=history
        )
        response.role = Role.ASSISTANT
        logger.debug(f"Generated response successfully. Response: {response}")
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.put("/set_model")
def set_model(request: SetModelRequest):
    logger.debug("Received set_model request")
    try:
        logger.debug(f"Setting model to {request.model}, device to {request.device}")
        _ = get_or_create_assistant(request.model, request.device)
        return {"status": 200}
    except Exception as e:
        logger.error(f"Error setting model: {e}")
        raise HTTPException(status_code=500, detail=str(e))
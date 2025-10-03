from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .chat_service import generate_structured_response
from .assistant import AssistantResponse, Message
app = FastAPI()

class GenerateRequest(BaseModel):
    model: str = Field(..., description="The name of the LLM model to use.")
    device: str = Field("cpu", description="The device to run the model on, e.g., 'cpu' or 'cuda'.")
    conversation_history: list[Message] = Field(
        ..., 
        description="A list of messages representing the conversation history. Each message is a dict with 'role' and 'content'."
    )
    max_tokens: int = Field(51200, description="The maximum number of tokens to generate in the response.")

@app.post("/generate")
def generate(request: GenerateRequest):
    try:
        history = [m.dict() for m in request.conversation_history]
        response = generate_structured_response(
            model=request.model,
            device=request.device,
            max_tokens=request.max_tokens,
            conversation_history=history
        )
        return AssistantResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

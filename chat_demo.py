import argparse
from pydantic import BaseModel
from typing import List, Optional
import sys, json
from assistant import LLMAssistant

# Define your response schema using Pydantic
class ChatResponse(BaseModel):
    response: str
    confidence: Optional[float] = None
    categories: List[str]
    sentiment: Optional[str] = None

def main():
    parser = argparse.ArgumentParser(
        description="Chat with an open-source LLM using structured JSON output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            python chat_script.py --model microsoft/Phi-3-mini-4k-instruct
            python chat_script.py -m mistralai/Mistral-7B-Instruct-v0.2 --device cuda
            python chat_script.py -m Qwen/Qwen2-7B-Instruct --max-tokens 256
        """
    )
    
    parser.add_argument(
        '-m', '--model',
        type=str,
        required=True,
        help='Hugging Face model name (e.g., microsoft/Phi-3-mini-4k-instruct)'
    )
    
    parser.add_argument(
        '-d', '--device',
        type=str,
        default='auto',
        help='Device to run the model on (auto, cpu, cuda, cuda:0, etc.)'
    )
    
    parser.add_argument(
        '--max-tokens',
        type=int,
        default=512,
        help='Maximum tokens to generate in the response'
    )
    
    args = parser.parse_args()
    
    try:
        print(f"Loading model: {args.model}")
        assistant = LLMAssistant(args.model, args.device)
        print("Model loaded successfully!")
        
        print("\n" + "="*50)
        print("Chat with the AI (type 'quit' or 'exit' to end)")
        print("Responses will be structured as JSON")
        print("="*50)
        
        conversation_history = []
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("Goodbye!")
                    break
                    
                if not user_input:
                    continue
                
                # Build conversation messages
                if not conversation_history:
                    conversation_history.append({
                        "role": "system",
                        "content": "You are a helpful AI assistant that provides structured responses in JSON format."
                    })
                
                conversation_history.append({
                    "role": "user",
                    "content": user_input
                })
                
                # Convert conversation to prompt
                prompt = assistant.chat2prompt(conversation_history)
                
                # Generate structured response
                print("Generating response...")
                structured_response = assistant.generate_json(
                    prompt, 
                    ChatResponse,
                    max_length=args.max_tokens
                )
                
                # Add assistant response to conversation history
                conversation_history.append({
                    "role": "assistant", 
                    "content": json.dumps(structured_response)
                })
                
                # Display the structured response
                print("\n" + "-" * 30)
                print("AI Response:")
                print(f"💬 {json.dumps(structured_response)}")
                print("-" * 30)
                
            except KeyboardInterrupt:
                print("\n\nChat session interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"Error generating response: {e}")
                print("Please try again with a different message.")
                
    except Exception as e:
        print(f"Failed to initialize the model: {e}")
        print("Please check the model name and your internet connection.")
        sys.exit(1)

if __name__ == "__main__":
    main()
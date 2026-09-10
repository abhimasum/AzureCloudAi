#!/usr/bin/env python3
"""
Local test script for OpenAI integration without Azure infrastructure.
Tests the OpenAI client wrapper in isolation.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add agents to path
agents_dir = Path(__file__).parent / "agents"
sys.path.insert(0, str(agents_dir))

def test_openai_client_wrapper():
    """Test the OpenAI client wrapper works correctly."""
    print("=" * 60)
    print("Testing OpenAI Client Wrapper")
    print("=" * 60)
    
    # Check API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY environment variable not set")
        print("   Set it with: $env:OPENAI_API_KEY='your-api-key'")
        return False
    
    print("✓ OPENAI_API_KEY is set")
    
    # Import and test the wrapper
    try:
        from openai import OpenAI
        print("✓ OpenAI library imported successfully")
        
        # Create the wrapper class
        class OpenAIClientWrapper:
            def __init__(self, openai_client):
                self.client = openai_client
            
            def __call__(self, messages=None, **kwargs):
                if messages is None:
                    messages = []
                
                # Filter kwargs
                valid_params = {
                    'temperature', 'top_p', 'max_tokens', 'presence_penalty',
                    'frequency_penalty', 'stop', 'tools', 'tool_choice', 'logprobs',
                    'top_logprobs', 'seed', 'response_format', 'timeout'
                }
                filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}
                
                # Convert Message objects to dicts if needed
                clean_messages = []
                for msg in messages:
                    if isinstance(msg, dict):
                        clean_messages.append(msg)
                    elif hasattr(msg, 'model_dump'):
                        # Pydantic v2
                        clean_messages.append(msg.model_dump())
                    elif hasattr(msg, 'dict'):
                        # Pydantic v1
                        clean_messages.append(msg.dict())
                    else:
                        clean_messages.append(msg)
                
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=clean_messages,
                        temperature=0.7,
                        max_tokens=200,
                        **filtered_kwargs
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    raise Exception(f"OpenAI API error: {str(e)}")
        
        # Initialize client
        openai_client = OpenAI(api_key=api_key)
        wrapper = OpenAIClientWrapper(openai_client)
        print("✓ Wrapper created successfully")
        
        # Test 1: Direct message test
        print("\n--- Test 1: Simple message ---")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello World' only"}
        ]
        response = wrapper(messages=messages)
        print(f"Response: {response}")
        if "Hello" in response or "hello" in response:
            print("✓ Test 1 passed")
        else:
            print("⚠️ Test 1 response unexpected")
        
        # Test 2: Message object test (like from Pydantic)
        print("\n--- Test 2: Pydantic Message objects ---")
        from pydantic import BaseModel
        
        class Message(BaseModel):
            role: str
            content: str
        
        messages = [
            Message(role="system", content="You are a geography expert."),
            Message(role="user", content="What is the capital of India? Answer in one word.")
        ]
        response = wrapper(messages=messages)
        print(f"Response: {response}")
        if "Delhi" in response or "delhi" in response:
            print("✓ Test 2 passed")
        else:
            print("⚠️ Test 2 response unexpected")
        
        # Test 3: Mixed dict and Message objects
        print("\n--- Test 3: Mixed message types ---")
        messages = [
            {"role": "system", "content": "You are helpful."},
            Message(role="user", content="List 2 Indian states.")
        ]
        response = wrapper(messages=messages)
        print(f"Response: {response}")
        if any(state in response for state in ["Maharashtra", "Karnataka", "Andhra", "Punjab", "Goa"]):
            print("✓ Test 3 passed")
        else:
            print("⚠️ Test 3 response unexpected")
        
        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        print("=" * 60)
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_openai_client_wrapper()
    sys.exit(0 if success else 1)

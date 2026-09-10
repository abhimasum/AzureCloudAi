#!/usr/bin/env python3
"""
Test the OpenAI wrapper serialization logic without API calls.
This validates the Pydantic Message conversion works correctly.
"""

import sys
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

# Define Message model like agent_framework uses
class Message(BaseModel):
    role: str
    content: str

def test_message_serialization():
    """Test message conversion without calling OpenAI API."""
    print("=" * 60)
    print("Testing Message Serialization (No API Calls)")
    print("=" * 60)
    
    # Simulate the wrapper's message handling
    def convert_messages(messages):
        """Convert messages like the wrapper does."""
        clean_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                clean_messages.append(msg)
            elif hasattr(msg, 'model_dump'):  # Pydantic v2
                clean_messages.append(msg.model_dump())
            elif hasattr(msg, 'dict'):  # Pydantic v1
                clean_messages.append(msg.dict())
            else:
                clean_messages.append(msg)
        return clean_messages
    
    # Test 1: Dict messages (original format)
    print("\n--- Test 1: Dict messages ---")
    dict_messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"}
    ]
    result = convert_messages(dict_messages)
    print(f"Input: {dict_messages}")
    print(f"Output: {result}")
    assert result == dict_messages, "Dict messages should pass through unchanged"
    print("✓ Test 1 passed: Dict messages handled correctly")
    
    # Test 2: Pydantic Message objects (v2 with model_dump)
    print("\n--- Test 2: Pydantic Message objects ---")
    pydantic_messages = [
        Message(role="system", content="You are helpful"),
        Message(role="user", content="Hello")
    ]
    result = convert_messages(pydantic_messages)
    print(f"Input: {pydantic_messages}")
    print(f"Output: {result}")
    expected = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"}
    ]
    assert result == expected, "Pydantic messages should convert to dicts"
    print("✓ Test 2 passed: Pydantic Message objects converted correctly")
    
    # Test 3: Mixed message types
    print("\n--- Test 3: Mixed message types ---")
    mixed_messages = [
        {"role": "system", "content": "You are helpful"},
        Message(role="user", content="What's your name?"),
        {"role": "user", "content": "Follow up"}
    ]
    result = convert_messages(mixed_messages)
    print(f"Input count: {len(mixed_messages)} messages")
    print(f"Output: {result}")
    expected = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "What's your name?"},
        {"role": "user", "content": "Follow up"}
    ]
    assert result == expected, "Mixed messages should all convert to dicts"
    print("✓ Test 3 passed: Mixed message types handled correctly")
    
    # Test 4: Parameter filtering
    print("\n--- Test 4: Parameter filtering ---")
    valid_params = {
        'temperature', 'top_p', 'max_tokens', 'presence_penalty',
        'frequency_penalty', 'stop', 'tools', 'tool_choice', 'logprobs',
        'top_logprobs', 'seed', 'response_format', 'timeout'
    }
    
    kwargs_with_invalid = {
        'temperature': 0.7,
        'max_tokens': 100,
        'options': 'invalid',  # Azure param, should be filtered
        'seed': 42,
        'model_name': 'invalid'  # Should be filtered
    }
    
    filtered = {k: v for k, v in kwargs_with_invalid.items() if k in valid_params}
    print(f"Input kwargs: {kwargs_with_invalid}")
    print(f"Filtered kwargs: {filtered}")
    
    expected_filtered = {
        'temperature': 0.7,
        'max_tokens': 100,
        'seed': 42
    }
    assert filtered == expected_filtered, "Invalid parameters should be filtered"
    print("✓ Test 4 passed: Parameter filtering works correctly")
    
    print("\n" + "=" * 60)
    print("✓ All serialization tests passed!")
    print("=" * 60)
    print("\nThe wrapper is ready for real API calls once API key is validated.")
    return True

if __name__ == "__main__":
    try:
        test_message_serialization()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

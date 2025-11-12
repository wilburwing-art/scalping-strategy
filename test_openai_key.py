#!/usr/bin/env python3
"""Quick test to verify OpenAI API key works"""

import os
import sys

try:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Simple test call
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Use cheaper model for testing
        messages=[{"role": "user", "content": "Reply with just 'OK' if you can read this."}],
        max_tokens=10
    )

    result = response.choices[0].message.content.strip()
    print(f"✅ OpenAI API key verified successfully!")
    print(f"   Test response: {result}")
    print(f"   Model: {response.model}")
    sys.exit(0)

except Exception as e:
    print(f"❌ OpenAI API key test failed: {e}")
    sys.exit(1)

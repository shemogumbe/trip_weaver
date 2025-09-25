import os

from openai import OpenAI
    
from dotenv import load_dotenv

load_dotenv()
# Load variables from .env into environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

print(f"Key {os.getenv("OPENAI_API_KEY")}")

def call_gpt(prompt: str, model="gpt-4o-mini", response_format=None):
    """Call GPT with optional response format for structured output"""
    
    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    
    # Add response_format if specified
    if response_format:
        kwargs["response_format"] = response_format
    
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content

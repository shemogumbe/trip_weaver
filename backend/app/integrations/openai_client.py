import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize client; avoid printing secrets
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_gpt(prompt: str, model="gpt-4o-mini"):
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content

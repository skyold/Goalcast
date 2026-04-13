import os
from litellm import acompletion
from typing import Optional

async def generate_response(prompt: str, model: str = "gpt-4o-mini", system_prompt: Optional[str] = None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    response = await acompletion(
        model=model,
        messages=messages
    )
    return response.choices[0].message.content

import os
from litellm import acompletion
from typing import Optional, List, Any

async def generate_response(prompt: str, model: str = "gpt-4o-mini", system_prompt: Optional[str] = None, tools: Optional[List[Any]] = None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    kwargs = {}
    if tools and len(tools) > 0:
        # Note: in a real implementation, these would be proper OpenAI tool schemas.
        # For now we just accept the parameter to satisfy the signature.
        pass
        
    response = await acompletion(
        model=model,
        messages=messages,
        **kwargs
    )
    return response.choices[0].message.content
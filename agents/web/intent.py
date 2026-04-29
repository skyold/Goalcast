import json

async def parse_intent(text: str, adapter) -> dict:
    prompt = f"""
    Parse the following user request into JSON.
    Format: {{"leagues": [], "date": "YYYY-MM-DD", "models": []}}
    Request: {text}
    Return ONLY valid JSON.
    """
    # Assuming adapter has run_agent or similar call
    response_text = await adapter.run_agent("roles/orchestrator", prompt)
    
    # Strip potential markdown code blocks
    cleaned = response_text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"leagues": [], "date": None, "models": ["v4.0"]}

import json
from datetime import datetime, timedelta, timezone


_CST = timezone(timedelta(hours=8))


def _normalize_intent_payload(payload: dict) -> dict:
    leagues = payload.get("leagues")
    if not isinstance(leagues, list):
        leagues = []

    date = payload.get("date")
    if date is not None and not isinstance(date, str):
        date = None

    models = payload.get("models")
    if not isinstance(models, list) or not models:
        models = ["v4.0"]

    return {
        "leagues": leagues,
        "date": date,
        "models": models,
    }

async def parse_intent(text: str, adapter) -> dict:
    today = datetime.now(_CST).strftime("%Y-%m-%d")
    prompt = f"""
    Parse the following user request into JSON.
    Format: {{"leagues": [], "date": "YYYY-MM-DD", "models": []}}
    Today is {today}.
    If the request says today, use {today} as the date.
    `leagues` may contain either league names or numeric league IDs.
    If `models` is omitted, return an empty list.
    Request: {text}
    Return ONLY valid JSON.
    """
    
    try:
        # Use the adapter with the correct role directory path
        result = await adapter.run_agent("agents/roles/orchestrator", prompt)
        response_text = result.final_text
        
        # Strip potential markdown code blocks
        cleaned = response_text.replace("```json", "").replace("```", "").strip()
        return _normalize_intent_payload(json.loads(cleaned))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Intent parsing failed: {e}")
        return {"leagues": [], "date": None, "models": ["v4.0"]}

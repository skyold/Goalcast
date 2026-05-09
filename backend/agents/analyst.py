"""
Analyst Agent — 唯一的 LLM agent。
输入：单场比赛 raw_data（来自所有激活 provider）。
输出：xG、亚盘方向、置信度、Kelly 注额。
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_CST = timezone(timedelta(hours=8))

ROLE_PATH = "backend/agents/roles/analyst"


def _now_iso() -> str:
    return datetime.now(_CST).isoformat()


def _parse_output(text: str) -> dict:
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {
        "raw_output": text[:2000],
        "note": "failed to parse structured JSON from analyst output",
    }


async def run_analyst(
    adapter,
    metadata: dict,
    raw_data: dict,
    model: str = "v4.0",
) -> dict:
    """
    调用 Analyst role 分析一场比赛。

    Args:
        adapter:  ClaudeAdapter 实例
        metadata: 比赛元数据（队名、联赛、开球时间等）
        raw_data: 所有激活 provider 收集的原始数据
        model:    分析模型版本标识（默认 v4.0）

    Returns:
        分析结果 dict，包含 home_xg/away_xg/ah_recommendation/
        confidence/kelly_fraction/analyzed_at，失败时包含 error 字段。
    """
    context = {
        "metadata": metadata,
        "raw_data": raw_data,
    }
    prompt = (
        f"请使用 {model} skill 分析这场比赛。\n"
        "所需数据均已在下方提供，请勿再调用工具获取新数据。\n"
        "分析完成后请以 JSON 格式输出结果，必须包含以下字段：\n"
        "  home_xg (float), away_xg (float),\n"
        "  ah_recommendation (str，如 '主队 -0.5'),\n"
        "  confidence (float 0-1),\n"
        "  kelly_fraction (float 0-1)\n"
        f"{json.dumps(context, ensure_ascii=False)}"
    )

    try:
        result = await adapter.run_agent(ROLE_PATH, prompt)
        analysis = _parse_output(result.final_text)
    except Exception as exc:
        logger.error("[Analyst] 分析异常 %s vs %s: %s",
                     metadata.get("home_team"), metadata.get("away_team"), exc)
        return {"error": str(exc), "analyzed_at": _now_iso()}

    analysis["analyzed_at"] = _now_iso()
    logger.info("[Analyst] 完成: %s vs %s (confidence=%.2f)",
                metadata.get("home_team"), metadata.get("away_team"),
                analysis.get("confidence", 0))
    return analysis

"""
RD 循环流水线步骤：Analyst → Trader → Reviewer → Reporter。
每个步骤由对应的 Agent 独立执行，通过 match_store 读取/写入比赛文件。
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from agents.core import match_store

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
_CST = timezone(timedelta(hours=8))
ROLE_PATHS = {
    "analyst": "backend/agents/roles/analyst",
    "trader": "backend/agents/roles/trader",
    "reviewer": "backend/agents/roles/reviewer",
    "reporter": "backend/agents/roles/reporter",
}


def _now_iso() -> str:
    return datetime.now(_CST).isoformat()


class MatchPipeline:
    def __init__(self, adapter, semi_mode: bool = False):
        self.adapter = adapter
        self.semi_mode = semi_mode

    # ── Analyst 步骤 ────────────────────────────────────────────────

    async def run_analyst_step(self, record: dict) -> dict:
        from agents.core.blackboard import load_partial, merge_update
        
        match_id = record["match_id"]
        filepath = match_store.MATCHES_DIR / f"{match_id}.json"
        
        # 1. Precise extraction: Load only metadata and raw_data
        context = load_partial(filepath, ["metadata", "raw_data"])
        models = context.get("metadata", {}).get("requested_models", ["v4.0"])
        
        analysis_results = {}
        for model in models:
            # Construct a targeted prompt for the specific skill
            prompt = (
                f"请使用 {model} skill 分析这场比赛。\n"
                f"所需的所有数据均已在下方提供，请勿再调用工具获取新数据。\n"
                f"最终请以 JSON 格式输出分析结果，包含 home_xg, away_xg, ah_recommendation, confidence 等字段。\n"
                f"{json.dumps(context, ensure_ascii=False)}"
            )
            # Execute the agent role (Analyst)
            result = await self.adapter.run_agent(ROLE_PATHS["analyst"], prompt)
            analysis = self._parse_analysis_output(result.final_text, context.get("metadata", {}))
            analysis["analyzed_at"] = _now_iso()
            analysis_results[model] = analysis
            
        # 2. Write back to Blackboard
        analysis_payload = analysis_results
        if len(analysis_results) == 1:
            only_model, only_result = next(iter(analysis_results.items()))
            analysis_payload = {**only_result, only_model: only_result}

        updates = {
            "analysis": analysis_payload,
            "state": {"analyst": "done"}
        }
        merge_update(filepath, updates)
        
        # 3. Update legacy status
        match_store.update_status(match_id, "analyzed")
        logger.info("[Pipeline] Analyst 完成: %s", match_id)
        return analysis_results

    def _parse_analysis_output(self, text: str, orche: dict) -> dict:
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {
            "home_xg": 0.0,
            "away_xg": 0.0,
            "raw_output": text[:2000],
            "note": "failed to parse structured JSON from agent output",
        }

    # ── Trader 步骤 ─────────────────────────────────────────────────

    async def run_trader_step(self, record: dict) -> dict:
        from agents.core.blackboard import load_partial, merge_update
        
        match_id = record["match_id"]
        filepath = match_store.MATCHES_DIR / f"{match_id}.json"
        
        # 1. Precise extraction: Load metadata and analysis, SKIP raw_data
        context = load_partial(filepath, ["metadata", "analysis"])
        
        prompt = (
            "请作为 Trader 角色。针对下方上下文中提供的每一种分析模型的结果，"
            "评估投注机会并做出交易决策。\n"
            "最终请以 JSON 格式输出交易决策结果。\n"
            f"{json.dumps(context, ensure_ascii=False, indent=2)}"
        )
        
        result = await self.adapter.run_agent(ROLE_PATHS["trader"], prompt)
        trade = self._parse_trade_output(result.final_text)
        trade["traded_at"] = _now_iso()
        
        # 2. Write back to Blackboard
        updates = {
            "trading": {"results": trade},
            "state": {"trader": "done"}
        }
        merge_update(filepath, updates)
        
        # 3. Update legacy status
        match_store.update_status(match_id, "traded")
        logger.info("[Pipeline] Trader 完成: %s", match_id)
        return trade

    def _parse_trade_output(self, text: str) -> dict:
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_output": text[:2000], "note": "failed to parse structured JSON"}

    # ── Reviewer 步骤 ───────────────────────────────────────────────

    async def run_reviewer_step(self, record: dict) -> str:
        from agents.core.blackboard import load_partial, merge_update

        match_id = record["match_id"]
        filepath = match_store.MATCHES_DIR / f"{match_id}.json"
        context = load_partial(filepath, ["metadata", "analysis", "trading"])
        metadata = context.get("metadata", {})
        analysis = context.get("analysis", {})
        trade = context.get("trading", {}).get("results", {})
        prompt = (
            f"审核以下比赛的预测和交易决策:\n"
            f"比赛: {metadata.get('home_team')} vs {metadata.get('away_team')}\n"
            f"分析:\n{json.dumps(analysis, ensure_ascii=False, indent=2)}\n"
            f"交易:\n{json.dumps(trade, ensure_ascii=False, indent=2)}\n"
            f"\n请检查 xG ↔ AH 方向是否一致、赔率是否合理、凯利注额是否审慎。"
            f"输出审核结论: VERDICT: approved | feedback | rejected\n"
            f"如果 feedback，说明具体改进建议。"
        )
        result = await self.adapter.run_agent(ROLE_PATHS["reviewer"], prompt)
        verdict = self._parse_verdict(result.final_text)
        review_data = {
            "verdict": verdict,
            "checks": {},
            "notes": result.final_text[:1000],
            "reviewed_at": _now_iso(),
        }
        match_store.append_layer(match_id, "review", review_data)
        merge_update(filepath, {"state": {"reviewer": "done"}})

        if verdict == "feedback":
            match_store.update_status(match_id, "feedback")
            logger.info("[Pipeline] Reviewer 打回: %s", match_id)
        elif verdict == "rejected":
            match_store.update_status(match_id, "rejected")
            logger.info("[Pipeline] Reviewer 拒绝: %s", match_id)
        else:
            logger.info("[Pipeline] Reviewer 通过: %s", match_id)
        return verdict

    def _parse_verdict(self, text: str) -> str:
        m = re.search(r"VERDICT:\s*(approved|feedback|rejected)", text, re.IGNORECASE)
        if m:
            return m.group(1).lower()
        if "通过" in text or "approved" in text.lower():
            return "approved"
        if "打回" in text or "feedback" in text.lower():
            return "feedback"
        return "rejected"

    # ── Reporter 步骤 ───────────────────────────────────────────────

    async def run_reporter_step(self, match_ids: list[str]) -> str:
        from agents.core.blackboard import merge_update

        records = []
        for mid in match_ids:
            r = match_store.load(mid)
            if r and r.get("review", {}).get("verdict") == "approved":
                records.append(r)

        if not records:
            logger.warning("[Pipeline] Reporter 无已审核比赛可报告")
            return ""

        prompt = (
            f"为以下 {len(records)} 场已审核通过的比赛生成赛事洞察报告:\n"
            f"{json.dumps(records, ensure_ascii=False, indent=2)}\n"
            f"\n请以 Markdown 格式输出结构化报告，包含赛事摘要、xG 分析、亚盘推荐、风险提示。"
        )
        result = await self.adapter.run_agent(ROLE_PATHS["reporter"], prompt)
        report_content = result.final_text

        today = datetime.now(_CST).strftime("%Y-%m-%d")
        reports_dir = match_store.MATCHES_DIR.parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"{today}.md"
        report_path.write_text(report_content, encoding="utf-8")
        report_ref = str(report_path.relative_to(match_store.MATCHES_DIR.parent))

        for r in records:
            match_store.finalize(r["match_id"], report_ref=report_ref)
            filepath = match_store.MATCHES_DIR / f"{r['match_id']}.json"
            merge_update(filepath, {"state": {"reporter": "done"}})

        logger.info(
            "[Pipeline] Reporter 完成: %s (%d 场比赛)", report_ref, len(records)
        )
        return report_ref

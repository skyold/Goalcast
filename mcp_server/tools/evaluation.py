"""Goalcast 评估与复盘相关 MCP 工具。"""

from __future__ import annotations

from typing import Any, Dict, Optional
import datetime

# 延迟导入以避免循环依赖或过早初始化
def _get_backtest_module():
    import scripts.backtest_engine as bt
    return bt

def _get_review_module():
    import scripts.review_engine as re
    return re


def register_goalcast_evaluation_tools(mcp: Any) -> None:
    """注册赛后复盘与历史回测相关 MCP 工具。"""

    @mcp.tool(
        description="执行单场或多场比赛的赛后复盘 (Review)。自动拉取实际赛果并与预测对比，计算 Brier Score 等指标，持久化到本地并更新日志。返回复盘概览。"
    )
    async def goalcast_run_review() -> Dict[str, Any]:
        """
        触发复盘引擎。扫描 data/predictions/ 下未复盘的比赛，
        获取实际赛果并生成对账报告。
        
        Returns:
            Dict 包含本次复盘了多少场比赛以及状态。
        """
        re = _get_review_module()
        try:
            # review_matches 已经是 async 函数
            await re.review_matches()
            return {
                "status": "success",
                "message": "Review process completed successfully. Check data/results and diary/ directories for details.",
                "action_taken": "Fetched actual results and compared with predictions."
            }
        except Exception as exc:
            return {
                "status": "error",
                "error": "REVIEW_ERROR",
                "message": str(exc)
            }

    @mcp.tool(
        description="执行历史预测的回测 (Backtest)。计算指定日期范围内的整体 ROI、命中率、Brier Score 等核心量化指标。返回详尽的回测报告 JSON。"
    )
    async def goalcast_run_backtest(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        method: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        触发回测引擎。汇总 data/predictions/ 和 data/results/ 中的数据，
        生成多维度的模型表现评估报告。
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)，默认今天
            end_date: 结束日期 (YYYY-MM-DD)，默认今天
            method: 仅评估特定模型 (如 'v3.0', 'v4.0')，可选
            
        Returns:
            Dict 回测报告的 JSON 结构，包含 ROI、Hit Rate 等。
        """
        bt = _get_backtest_module()
        
        # 处理默认日期
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        effective_start = start_date or today
        effective_end = end_date or today

        try:
            predictions = bt.load_predictions(effective_start, effective_end, method)
            results = bt.load_results()

            if not predictions:
                return {
                    "status": "warning",
                    "message": f"No predictions found for period {effective_start} to {effective_end}.",
                    "period": {"start": effective_start, "end": effective_end}
                }

            report = bt.generate_report(predictions, results, effective_start, effective_end)
            
            # 同时将报告落盘，保持与独立脚本一致的行为
            output_path = bt.BACKTESTS_DIR / f"backtest_{effective_start}_to_{effective_end}.json"
            bt.BACKTESTS_DIR.mkdir(parents=True, exist_ok=True)
            
            import json
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
                
            # 生成 Markdown (复用引擎内方法)
            bt.generate_markdown_report(report, str(output_path))
            
            report["status"] = "success"
            report["saved_to"] = str(output_path)
            
            return report
            
        except Exception as exc:
            return {
                "status": "error",
                "error": "BACKTEST_ERROR",
                "message": str(exc)
            }

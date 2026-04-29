# Goalcast Orchestrator 黑板模式实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 重构 Orchestrator，根据 Skill 定义预先获取所有模型所需的数据，并通过 `MC-xxx.json` 文件实现基于“黑板模式”的多 Agent 协同。

**架构:** 
Orchestrator 将解析请求的模型，读取相应的 skill 定义以提取数据依赖，并通过 MCP 获取所有必需的原始数据。它会初始化包含严格结构（`metadata`, `state`, `raw_data`, `analysis`, `trading`）的 `MC-xxx.json` 文件。执行框架（例如 `_analyst_loop`）随后会选择性地加载必要的 JSON 节点（如给 Analyst 仅加载 `metadata` 和 `raw_data`）到 LLM 上下文中以防止上下文溢出，执行对应的 skills，并将结果合并写回该单一文件。

**技术栈:** Python 3, `asyncio`, JSON 文件操作, Trae/Goalcast Skill 定义。

---

### Task 1: 创建 Blackboard 数据管理辅助类

**涉及文件:**
- Create: `agents/core/blackboard.py`

- [ ] **Step 1: 创建 Blackboard JSON 管理器**
创建 `agents/core/blackboard.py`，用于实现 `MC-xxx.json` 的局部加载和合并更新功能。

```python
import json
from pathlib import Path
from typing import Any, Dict

def load_partial(filepath: str | Path, sections: list[str]) -> Dict[str, Any]:
    """从 JSON 文件中仅加载指定的顶级节点，以节省 LLM 上下文空间。"""
    path = Path(filepath)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if k in sections}

def merge_update(filepath: str | Path, updates: Dict[str, Any]) -> None:
    """将更新的内容深度合并到现有的 JSON 文件中。"""
    path = Path(filepath)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
        
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(data.get(k), dict):
            data[k].update(v)
        else:
            data[k] = v
            
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

- [ ] **Step 2: 提交 Task 1**
```bash
git add agents/core/blackboard.py
git commit -m "feat(core): 增加 blackboard 局部加载与合并更新工具"
```

### Task 2: 在 Orchestrator 中实现“模型感知”的数据收集

**涉及文件:**
- Modify: `agents/core/orchestrator.py`

- [ ] **Step 1: 更新 `_fetch_and_prepare` 以读取 skill 依赖并预取数据**

修改 `_fetch_and_prepare` 方法。模拟读取 skill 数据需求并获取数据，最后按黑板结构初始化文件。（本任务中我们将增加一个 `_fetch_raw_data_for_models` 委托给 MCP 处理）。

```python
# 在 agents/core/orchestrator.py 中, 更新 _fetch_and_prepare
    async def _fetch_and_prepare(
        self, leagues: list[str] | None, date: str | None, models: list[str] = ["v4.0"]
    ) -> int:
        from agents.adapters.tool_executor import ToolExecutor
        from agents.core.blackboard import merge_update
        from agents.core import match_store
        import os

        executor = ToolExecutor()
        today = date or datetime.now(_CST).strftime("%Y-%m-%d")

        league_ids = None
        if leagues:
            league_ids = self._resolve_league_ids(leagues)
            if not league_ids:
                logger.warning("[Orchestrator] 联赛字典中未找到: %s", leagues)
                return 0

        result = await executor._tool_goalcast_sportmonks_get_matches(
            date=today, league_ids=league_ids,
        )
        fixtures = result.get("data", [])

        count = 0
        for fixture in fixtures:
            match_id = match_store.generate_match_id()
            fixture_id = fixture.get("fixture_id", fixture.get("id"))
            
            # 读取 skill 依赖并预先获取原始数据
            raw_data = await self._fetch_raw_data_for_models(executor, fixture_id, models)
            
            record = {
                "metadata": {
                    "match_id": match_id,
                    "fixture_id": fixture_id,
                    "home_team": fixture.get("home_team", fixture.get("name", "").split(" vs ")[0]),
                    "away_team": fixture.get("away_team", fixture.get("name", "").split(" vs ")[-1]),
                    "league": fixture.get("league", fixture.get("league_name", "")),
                    "kickoff_time": fixture.get("kickoff_time", fixture.get("starting_at", "")),
                    "requested_models": models,
                    "prepared_at": datetime.now(_CST).isoformat(),
                },
                "state": {
                    "orchestrator": "done",
                    "analyst": "pending",
                    "trader": "pending",
                    "reporter": "pending"
                },
                "raw_data": raw_data,
                "analysis": {},
                "trading": {}
            }
            
            # 使用 Blackboard 结构保存
            filepath = os.path.join(match_store.DATA_DIR, f"{match_id}.json")
            merge_update(filepath, record)
            
            # 保留旧版 match_store 内存兼容性（如果需要）
            legacy_record = {"match_id": match_id, "status": "pending"}
            match_store.save(legacy_record)
            count += 1
        return count

    async def _fetch_raw_data_for_models(self, executor, fixture_id: int, models: list[str]) -> dict:
        """
        动态读取模型 skill 定义并获取所需数据。
        针对 v3.0 和 v4.0 依赖的示例实现。
        """
        raw_data = {}
        # 实际情况中，这里将解析 goalcast-analyzer-v40/SKILL.md 等文件
        if "v4.0" in models or "v3.0" in models:
            # 示例: 两者都需要 sportmonks 的 match context
            if hasattr(executor, "_tool_goalcast_sportmonks_resolve_match"):
                res = await executor._tool_goalcast_sportmonks_resolve_match(fixture_id=fixture_id)
                raw_data["sportmonks"] = res.get("data", {})
        return raw_data
```

- [ ] **Step 2: 提交 Task 2**
```bash
git add agents/core/orchestrator.py
git commit -m "feat(orchestrator): 实现模型感知的数据预取与黑板初始化"
```

### Task 3: 重构 Analyst 循环以实现上下文裁剪

**涉及文件:**
- Modify: `agents/core/pipeline.py` （假设 `run_analyst_step` 在此处）

- [ ] **Step 1: 修改 Analyst 执行逻辑，使用 `load_partial`**

更新 pipeline 逻辑，仅将 `metadata` 和 `raw_data` 传递给 Analyst 提示词，并将结果写回 `analysis` 节点。

```python
# 在 agents/core/pipeline.py 中 (或包含 run_analyst_step 的对应文件)
# 我们将在把记录传递给 adapter/LLM 前进行拦截和裁剪

    async def run_analyst_step(self, record: dict):
        from agents.core.blackboard import load_partial, merge_update
        import os
        from agents.core import match_store
        
        match_id = record["match_id"]
        filepath = os.path.join(match_store.DATA_DIR, f"{match_id}.json")
        
        # 1. 精准提取: 仅加载 metadata 和 raw_data
        context = load_partial(filepath, ["metadata", "raw_data"])
        models = context.get("metadata", {}).get("requested_models", ["v4.0"])
        
        analysis_results = {}
        for model in models:
            # 构建针对特定 skill 的提示词
            prompt = (
                f"请使用 {model} skill 分析这场比赛。 "
                f"所需的所有数据均已在下方提供，请勿再调用工具获取新数据。\n"
                f"{json.dumps(context, ensure_ascii=False)}"
            )
            # 执行 Agent 角色 (Analyst)
            result = await self.adapter.run_agent("roles/analyst", prompt)
            analysis_results[model] = result
            
        # 2. 写回黑板
        updates = {
            "analysis": analysis_results,
            "state": {"analyst": "done"}
        }
        merge_update(filepath, updates)
        
        # 3. 更新旧版状态
        match_store.update_status(match_id, "analyzed")
```

- [ ] **Step 2: 提交 Task 3**
```bash
git add agents/core/pipeline.py
git commit -m "refactor(pipeline): 为 analyst 启用黑板局部加载并更新状态"
```

### Task 4: 重构 Trader 循环以实现上下文裁剪

**涉及文件:**
- Modify: `agents/core/pipeline.py`

- [ ] **Step 1: 修改 Trader 执行逻辑，跳过庞大的 `raw_data`**

```python
# 在 agents/core/pipeline.py 中

    async def run_trader_step(self, record: dict):
        from agents.core.blackboard import load_partial, merge_update
        import os
        from agents.core import match_store
        
        match_id = record["match_id"]
        filepath = os.path.join(match_store.DATA_DIR, f"{match_id}.json")
        
        # 1. 精准提取: 加载 metadata 和 analysis，跳过 raw_data
        context = load_partial(filepath, ["metadata", "analysis"])
        
        prompt = (
            "请作为 Trader 角色。针对下方上下文中提供的每一种分析模型的结果，"
            "评估投注机会。请输出你的交易决策。\n"
            f"{json.dumps(context, ensure_ascii=False)}"
        )
        
        # 执行 Agent 角色 (Trader)
        trading_results = await self.adapter.run_agent("roles/trader", prompt)
        
        # 2. 写回黑板
        updates = {
            "trading": {"results": trading_results},
            "state": {"trader": "done"}
        }
        merge_update(filepath, updates)
        
        # 3. 更新旧版状态
        match_store.update_status(match_id, "traded")
```

- [ ] **Step 2: 提交 Task 4**
```bash
git add agents/core/pipeline.py
git commit -m "refactor(pipeline): 为 trader 启用黑板上下文裁剪"
```

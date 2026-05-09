#!/usr/bin/env bash
# 在 worktree 根目录执行此脚本，完成所有任务的测试与提交
# 用法: cd /Users/zhengningdai/workspace/skyold/Goalcast/.claude/worktrees/backend-restructure && bash commit_all.sh

set -e
cd "$(dirname "$0")"
BACKEND="backend"

echo "=== 安装依赖 ==="
(cd $BACKEND && pip3 install -q -r requirements.txt)

echo ""
echo "=== 运行所有测试 ==="
(cd $BACKEND && python3 -m pytest tests/ -v)

echo ""
echo "=== Task 1: Provider Registry ==="
git add backend/config/providers.json \
        backend/provider/registry.py \
        backend/tests/provider/__init__.py \
        backend/tests/provider/test_registry.py
git commit -m "feat(registry): 新增 Provider Registry，统一管理数据源开关"

echo ""
echo "=== Task 2: collect_match 抽象方法 + OddAlerts/FootyStats/Understat 实现 ==="
git add backend/provider/base.py \
        backend/provider/oddalerts/client.py \
        backend/provider/footystats/client.py \
        backend/provider/understat/client.py
git commit -m "feat(provider): BaseProvider 新增 collect_match 抽象方法，各 provider 实现"

echo ""
echo "=== Task 3: Sportmonks collect_match ==="
git add backend/provider/sportmonks/client.py
git commit -m "feat(provider): Sportmonks 实现 collect_match，直接 HTTP 调用"

echo ""
echo "=== Task 4: 统一 Match Store ==="
git add backend/store/__init__.py \
        backend/store/match_store.py \
        backend/tests/store/__init__.py \
        backend/tests/store/test_match_store.py
git commit -m "feat(store): 新增统一 Match Store，单一写入路径，消除双写"

echo ""
echo "=== Task 5: Pipeline Discovery ==="
git add backend/pipeline/__init__.py \
        backend/pipeline/discovery.py \
        backend/tests/pipeline/__init__.py \
        backend/tests/pipeline/test_discovery.py
git commit -m "feat(pipeline): 新增 discovery 模块，并行 fixture 发现与合并"

echo ""
echo "=== Task 6: Pipeline Collector ==="
git add backend/pipeline/collector.py \
        backend/tests/pipeline/test_collector.py
git commit -m "feat(pipeline): 新增 collector 模块，并行从各 provider 收集比赛数据"

echo ""
echo "=== Task 7: League Resolver ==="
git add backend/pipeline/league_resolver.py \
        backend/requirements.txt
git commit -m "feat(pipeline): 新增 league_resolver，用 fuzzy 匹配替代 LLM 联赛解析"

echo ""
echo "=== Task 8: Analyst Agent ==="
git add backend/agents/analyst.py
git commit -m "feat(analyst): 新增简化版 Analyst agent，合并分析与投注推荐"

echo ""
echo "=== Task 9: Pipeline Runner ==="
git add backend/pipeline/runner.py \
        backend/tests/pipeline/test_runner.py
git commit -m "feat(pipeline): 新增 Pipeline Runner，顺序执行 discover→collect→analyze"

echo ""
echo "=== Task 10: Pipeline Scheduler ==="
git add backend/pipeline/scheduler.py
git commit -m "feat(pipeline): 新增 Scheduler，支持定时 + 手动触发"

echo ""
echo "=== Task 11: API Routes ==="
git add backend/server/routes/pipeline.py \
        backend/server/routes/config.py \
        backend/server/server.py
git commit -m "feat(api): 重写 pipeline 和 config 路由，对齐新架构，删除旧 WebSocket chat"

echo ""
echo "=== Task 12: main.py ==="
git add backend/main.py
git commit -m "refactor(main): 用 PipelineScheduler 替代旧 Orchestrator 启动逻辑"

echo ""
echo "=== Task 13: 迁移脚本 ==="
git add backend/scripts/migrate_matches.py
git commit -m "feat(scripts): 新增 migrate_matches 迁移脚本，规范化旧格式 match 文件"

echo ""
echo "=== Task 14: 删除旧文件 ==="
rm -f  backend/agents/core/orchestrator.py
rm -f  backend/agents/core/pipeline.py
rm -f  backend/agents/core/blackboard.py
rm -f  backend/agents/core/data_collector.py
rm -f  backend/agents/core/directory_agent.py
rm -f  backend/agents/core/events.py
rm -f  backend/agents/core/league_config.py
rm -f  backend/agents/core/coordinator.py
rm -f  backend/agents/scheduler.py
rm -f  backend/agents/llm_router.py
rm -rf backend/agents/roles/trader
rm -rf backend/agents/roles/reviewer
rm -rf backend/agents/roles/reporter
rm -rf backend/agents/roles/backtester
rm -rf backend/agents/roles/prediction
rm -rf backend/datasource
rm -rf backend/mcp_server
rm -f  backend/server/routes/agents.py
rm -f  backend/server/routes/board.py
rm -f  backend/server/routes/chat.py
rm -f  backend/agents/core/match_store.py

# 验证删除后 server 仍可导入
(cd backend && python3 -c "from server.server import app; print('server OK')")
(cd backend && python3 -c "from pipeline.runner import run_pipeline; print('runner OK')")

git add -A
git commit -m "chore: 删除旧 Orchestrator、Trader、Reviewer、Reporter 及相关文件"

echo ""
echo "=== Task 15: 前端重构 ==="
# 删除误建目录
rm -rf .claire 2>/dev/null || true

# 删除旧页面和旧组件
rm -f  frontend/src/pages/DashboardPage.tsx
rm -f  frontend/src/pages/BoardPage.tsx
rm -f  frontend/src/pages/TokenStatsPage.tsx
rm -f  frontend/src/pages/ChatPanel.tsx
rm -f  frontend/src/pages/PipelineMonitor.tsx
rm -f  frontend/src/components/SideNav.tsx
rm -f  frontend/src/components/LogViewer.tsx
rm -f  frontend/src/components/AgentDetailDrawer.tsx
rm -f  frontend/src/components/MatchSourcePanel.tsx
rm -f  frontend/src/services/ws.ts
rm -f  frontend/src/services/extensions.ts
rm -rf frontend/src/extensions
rm -f  frontend/src/types/extensions.ts
rm -f  frontend/src/config.ts

git add -A frontend/src/
git commit -m "feat(frontend): 重构为单页 Pipeline UI，对齐新后端 API，删除旧页面"

echo ""
echo "=== 完成！运行最终验证 ==="
(cd backend && python3 -m pytest tests/ -v)
echo ""
echo "✅ 全部提交完成。可以运行迁移脚本："
echo "   cd backend && python scripts/migrate_matches.py --dry-run"

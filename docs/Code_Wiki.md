# Goalcast Code Wiki

## 1. 项目整体架构

Goalcast 是一个基于 Python 的足球赛事数据聚合与量化分析工具包。它的核心定位是作为 **MCP (Model Context Protocol) Server** 运行，为 AI 助手（如 Claude 等）提供无缝的足球数据查询、融合以及量化模型计算能力。

项目采用了清晰的分层架构（Layered Architecture）和“异步优先 (Async-first)”的设计理念，主要分为以下几个层次：

- **Provider 接入层**：负责与外部数据源（FootyStats, Sportmonks, Understat）进行底层 HTTP 交互，统一处理请求超时、重试和并发速率限制。
- **数据策略与融合层**：作为系统的核心数据引擎，负责将多个异构数据源的数据进行并行拉取、降级兜底和结构化映射，最终向上层输出统一的数据契约。
- **量化分析层**：纯函数式的确定性数学模型引擎，不依赖大语言模型的“心算”，直接进行泊松分布、预期价值 (EV) 计算和置信度评分。
- **MCP Server 层**：使用 `FastMCP` 将底层的数据接口和分析模型包装为 AI 可直接调用的标准化 Tool，供外部集成。

---

## 2. 主要模块职责

### 2.1 数据策略与融合层 (`data_strategy/`)
这是代码库中最复杂且最重要的模块，它解决了异构数据源（API）的数据拼装问题。
- **[fusion.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/data_strategy/fusion.py)**: 包含核心的数据融合引擎类，负责并行拉取和降级兜底。
- **[models.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/data_strategy/models.py)**: 定义了数据模型契约，明确声明所有可用数据及缺失项。
- **[resolvers/](file:///Users/zhengningdai/workspace/skyold/Goalcast/data_strategy/resolvers/)**: 包含对具体 Provider 原始响应进行解析的解析器，如 `FootyStatsResolver` 和 `SportmonksResolver`。

### 2.2 量化分析层 (`analytics/`)
该模块包含比赛预测的核心算法，提供纯粹的数学计算支持。
- **[poisson.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/analytics/poisson.py)**: 实现了基础泊松分布以及带有低比分修正因子的 Dixon-Coles 分布模型。
- **[ev_calculator.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/analytics/ev_calculator.py)**: 包含单向投注预期价值计算、凯利公式计算以及风险调整后的 EV 计算逻辑。
- **[confidence.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/analytics/confidence.py)**: 计算预测和数据的置信度评分。

### 2.3 Provider 层 (`provider/`)
负责与各个外部 API 进行通信的客户端封装。
- **[base.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/provider/base.py)**: 定义了带有重试机制和速率限制处理的异步基类。
- **[footystats/](file:///Users/zhengningdai/workspace/skyold/Goalcast/provider/footystats/)**, **[sportmonks/](file:///Users/zhengningdai/workspace/skyold/Goalcast/provider/sportmonks/)**, **[understat/](file:///Users/zhengningdai/workspace/skyold/Goalcast/provider/understat/)**: 具体数据源的客户端实现。

### 2.4 MCP Server 层 (`mcp_server/`)
为 AI 助手提供标准化的工具接口。
- **[server.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/mcp_server/server.py)**: MCP 的入口文件，将底层功能注册为工具。

### 2.5 多 Agent 编排层 (`agents/`)
用于把“数据采集（DataFusion / MCP）→ Skill/LLM 分析 → 监督/复盘”串成可定时运行的工作流。该层采用层级状态机模式：由 `Coordinator` 按既定顺序调度多个角色 Agent，通过 `WorkflowState` 在步骤之间传递状态与 `MatchContext`。
- **[core/state.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/agents/core/state.py)**: `WorkflowState`，工作流的强类型上下文（重点字段：`match_contexts: List[MatchContext]`）。
- **[core/base.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/agents/core/base.py)**: `BaseAgent` 抽象基类（所有角色 Agent 统一接口：`execute(state) -> state`）。
- **[core/coordinator.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/agents/core/coordinator.py)**: `Coordinator`，负责状态机的 step 顺序执行与错误收集。
- **[roles/](file:///Users/zhengningdai/workspace/skyold/Goalcast/agents/roles/)**: 角色 Agent 实现：`DataGatherer` / `Analyst` / `Supervisor` / `Reviewer`。
- **[llm_router.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/agents/llm_router.py)**: 多模型 LLM 调用封装（基于 `litellm` 的 `acompletion`）。
- **[scheduler.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/agents/scheduler.py)**: 定时调度入口（基于 APScheduler 的 AsyncIO Scheduler）。

---

## 3. 关键类与函数说明

### 3.1 DataFusion 引擎
- **类**: `DataFusion` ([data_strategy/fusion.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/data_strategy/fusion.py))
- **方法**: `build()` - 利用 `asyncio.gather` 并行拉取单场比赛的多维度数据（xG、近期表现、积分榜、赔率、阵容等）。自动处理降级（例如 xG 数据优先取 Understat，没有则取 Footystats 代理值），并计算综合数据质量 (`overall_quality`)。

### 3.2 MatchContext 数据契约
- **类**: `MatchContext` ([data_strategy/models.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/data_strategy/models.py))
- **说明**: `DataFusion` 最终返回的不可变数据类，声明了所有可用数据及缺失项（`data_gaps`），供分析层统一调用。

### 3.3 泊松与 Dixon-Coles 分布
- **函数**: `poisson_distribution` & `dixon_coles_distribution` ([analytics/poisson.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/analytics/poisson.py))
- **说明**: 基于主客队预期进球（xG - $\lambda$ 值），生成 0-6 球的比分概率矩阵。Dixon-Coles 模型通过 $\tau$ 因子对 0-0, 1-0 等低比分进行了修正。

### 3.4 预期价值 (EV) 与风险计算
- **函数**: `calculate_ev`, `calculate_kelly`, `calculate_risk_adjusted_ev` ([analytics/ev_calculator.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/analytics/ev_calculator.py))
- **说明**: 分别用于计算单向预期价值、基于凯利公式的投注比例建议（默认 25% 分数凯利以控制风险），以及结合阵容不确定性、市场置信度和数据质量的风险调整后 EV 值。

### 3.5 基础 Provider 客户端
- **类**: `BaseProvider` ([provider/base.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/provider/base.py))
- **方法**: `_request()` - 封装了带有重试机制的异步 `httpx.AsyncClient` 请求，并自动处理 `429 Rate Limited` 的退避逻辑。

### 3.6 MCP 核心工具
- **函数**: `goalcast_resolve_match` ([mcp_server/server.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/mcp_server/server.py))
- **说明**: 封装了 `DataFusion` 逻辑，使得 AI 只需要一次调用即可获取完整且经过清洗的单场比赛数据包。

### 3.7 多 Agent 工作流核心对象
- **类**: `WorkflowState` ([agents/core/state.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/agents/core/state.py))
- **说明**: 工作流中所有 Agent 的共享状态。与 `MatchContext` 的兼容策略是：数据采集与分析之间仅通过 `match_contexts: List[MatchContext]` 传递结构化数据，避免分析层直接依赖 Provider/MCP。
- **类**: `Coordinator` ([agents/core/coordinator.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/agents/core/coordinator.py))
- **说明**: 一个最小可用的“顺序状态机调度器”，按传入 `sequence` 依次执行已注册的 step，并把错误写入 `WorkflowState.errors`。

---

## 4. 依赖关系

项目的依赖配置在 [pyproject.toml](file:///Users/zhengningdai/workspace/skyold/Goalcast/pyproject.toml) 和 [requirements.txt](file:///Users/zhengningdai/workspace/skyold/Goalcast/requirements.txt) 中。项目要求 Python 3.10 及以上版本。

**核心依赖项：**
- **网络与并发**: `httpx[asyncio]==0.27.0` 和 `aiohttp>=3.9.0` 用于高性能的异步网络请求。
- **配置**: `python-dotenv` 和 `PyYAML` 用于读取环境变量和 YAML 配置文件。
- **专业数据源**: `understatapi>=0.6.1` 用于免密钥抓取 Understat 的高级 xG 数据。
- **日志系统**: `loguru==0.7.2` 提供结构化的异步日志。
- **LLM 路由**: `litellm>=1.0.0` 用于多模型兼容的异步 completion 封装（当前由 `agents/llm_router.py` 使用）。
- **定时调度**: `apscheduler>=3.10.0` 用于异步定时任务（当前由 `agents/scheduler.py` 使用）。

**可选/开发依赖项：**
- **数据分析**: `pandas` 和 `numpy`。
- **测试与开发**: `pytest` 和 `pytest-asyncio`。

---

## 5. 项目运行方式

根据项目结构和 [README.md](file:///Users/zhengningdai/workspace/skyold/Goalcast/README.md)，Goalcast 主要支持以下运行模式。

### 5.1 前提准备：配置环境变量
首先，必须配置 API 密钥（Understat 是免费的，但 FootyStats 和 Sportmonks 需要 Key）：
```bash
cp .env.example .env
# 编辑 .env 文件，填入 FOOTYSTATS_API_KEY 和 SPORTMONKS_API_KEY
```

### 5.2 本地开发与运行 (推荐)
推荐在本地虚拟环境中运行，直接作为 MCP 服务器启动：
```bash
# 1. 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动 MCP Server
python mcp_server/server.py
# 也可以使用自动化脚本
./scripts/start_mcp_local.sh
```

### 5.3 Docker 容器化部署
适合生产环境或与跨环境的服务进行网络互通：
```bash
docker build -t goalcast-mcp .
docker-compose up -d
```

### 5.4 与 AI 客户端集成 (MCP)
若要将 Goalcast 作为 AI（如 Claude Desktop 或 Cursor）的工具集成：
1. 复制 MCP 配置模板：`cp mcporter.json.example mcporter.json`。
2. 将此 Server 的路径（或 Docker SSE 端点）配置到 AI 的 MCP Config 中，随后 AI 便能调用诸如 `goalcast_resolve_match`、`footystats_get_todays_matches` 以及 `goalcast_calculate_poisson` 等海量工具。

### 5.5 多 Agent 定时运行（实验性）
当前 `agents/` 层提供了可测试的骨架与定时调度入口，适合用作“批处理分析管线”的基础设施。注意：`agents/scheduler.py` 内的 `scheduled_task()` 目前为占位实现，后续可在其中实例化 `Coordinator` 并串起 `DataGatherer → Analyst → Supervisor → Reviewer`。

运行方式（推荐用 module 形式，确保包导入正常）：
```bash
PYTHONPATH=. python -m agents.scheduler
```

仅运行多 Agent 单元测试：
```bash
PYTHONPATH=. pytest tests/agents/ -v
```

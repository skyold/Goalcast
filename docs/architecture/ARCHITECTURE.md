# Goalcast Architecture

> This file is a copy of [Code_Wiki.md](../Code_Wiki.md). Please keep both in sync or remove the original.

## 1. 项目整体架构

Goalcast 是一个基于 Python 的足球赛事数据聚合与量化分析工具包。它的核心定位是作为 **MCP (Model Context Protocol) Server** 运行，为 AI 助手（如 Claude 等）提供无缝的足球数据查询、融合以及量化模型计算能力。

项目采用了清晰的分层架构（Layered Architecture）和"异步优先 (Async-first)"的设计理念，主要分为以下几个层次：

- **Provider 接入层**：负责与外部数据源（FootyStats, Sportmonks, Understat）进行底层 HTTP 交互。
- **生数据缓存层 (Raw Data Cache)**：由 `prewarm_cache.py` 驱动，每日定时拉取原始 JSON 并双写至文件系统 (`data/cache/`) 和 SQLite 数据库。
- **轻量级读取与专属分析层**：取代了旧有的强统一 `DataFusion`。使用 `CacheReader` 直接读取缓存，并挂载 `sportmonks-analyst-v1` 等专属 Skill 直接解析原始 JSON 结构。
- **量化分析层**：纯函数式的确定性数学模型引擎。
- **MCP Server 层**：将底层功能包装为 AI 可直接调用的标准化 Tool。

## 2. 主要模块职责

### 2.1 生数据缓存与轻量级读取 (`data/cache/` & `utils/cache_reader.py`)
- **prewarm_cache.py**: 核心预热引擎，支持 JSON 与 SQLite 双写。
- **cache_reader.py**: 极简读取接口，直接返回原始字典列表。
- **专属技能 (`skills/`)**: 包含 `sportmonks-analyst-v1` 等，指导 LLM 如何解析特定 Provider 的 JSON。

### 2.2 量化分析层 (`analytics/`)
- **poisson.py**: 基础泊松分布 + Dixon-Coles 分布模型。
- **ev_calculator.py**: 单向 EV、凯利公式、风险调整 EV。
- **confidence.py**: 预测和数据的置信度评分。

### 2.3 Provider 层 (`provider/`)
- **base.py**: 带重试和速率限制的异步基类。
- **footystats/**, **sportmonks/**, **understat/**: 具体数据源客户端。

### 2.4 MCP Server 层 (`mcp_server/`)
- **server.py**: MCP 入口，将底层功能注册为工具。

### 2.5 多 Agent 编排层 (`agents/`)
- **core/state.py**: `WorkflowState` 工作流强类型上下文。
- **core/base.py**: `BaseAgent` 抽象基类。
- **core/coordinator.py**: 顺序状态机调度器。
- **roles/**: DataGatherer / Analyst / Supervisor / Reviewer / Trader / Reporter。
- **llm_router.py**: 多模型 LLM 调用封装（litellm）。
- **scheduler.py**: APScheduler 定时调度入口。

## 3. 关键类与函数

- **DataFusion** (`data_strategy/fusion.py`): 并行拉取多维度数据，自动降级。
- **MatchContext** (`data_strategy/models.py`): 不可变数据契约。
- **poisson_distribution / dixon_coles_distribution** (`analytics/poisson.py`): 比分概率矩阵。
- **calculate_ev / calculate_kelly / calculate_risk_adjusted_ev** (`analytics/ev_calculator.py`): 投注数学。
- **BaseProvider._request()** (`provider/base.py`): 带 429 退避的异步请求。
- **goalcast_footystats_resolve_match** (`mcp_server/tools/footystats.py`): 一站式比赛数据包。

## 4. 依赖关系

核心依赖：`httpx[asyncio]`, `loguru`, `python-dotenv`
可选依赖：`aiohttp`, `understatapi`, `beautifulsoup4`, `lxml`, `litellm`, `apscheduler`, `pandas`, `numpy`
开发依赖：`pytest`, `pytest-asyncio`

## 5. 运行方式

### 本地开发
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python mcp_server/server.py
```

### Docker 部署
```bash
docker build -t goalcast-mcp .
docker-compose up -d
```

### AI 客户端集成
```bash
cp mcporter.json.example mcporter.json
# 配置到 Claude Desktop / Cursor 的 MCP Config
```

### 多 Agent 定时运行（实验性）
```bash
PYTHONPATH=. python -m agents.scheduler
PYTHONPATH=. pytest tests/agents/ -v
```

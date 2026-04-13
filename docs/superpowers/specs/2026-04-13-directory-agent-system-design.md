# Directory-Compatible Agent & Team System Design

## 1. Context & Goal
目前在 `agents/roles/` 目录下存在诸如 `analyst`, `backtester`, `reviewer` 等角色的配置文件夹。每个文件夹包含了一套类似 Phoenix Agent 的配置规范，如：
- `IDENTITY.md`, `AGENTS.md`, `MEMORY.md`, `SOUL.md`, `TOOLS.md`, `USER.md` 等 Markdown 文件。
- `tool-registry.jsonc` 等 JSON 配置文件。

而现有的 Python 代理（如 `agents/roles/analyst.py`）中，系统提示词是硬编码的（如 `system_prompt="You are a football analyst."`），并未利用这些丰富的本地文件。

**目标**：开发一个能够兼容这些目录格式的 Agent 与 Team 系统，使得系统可以动态加载这些目录作为 Agent 的知识库和提示词，并使 Coordinator 能够像“团队”一样调度这些基于目录驱动的 Agent。

---

## 2. 架构设计 (Architecture)

### 2.1 Agent 解析层 (`DirectoryAgentLoader`)
职责：负责读取指定路径（如 `agents/roles/analyst`）下的各种配置文件，将其合并转化为 LLM 可用的系统指令。

- **Prompt 合并策略**：
  按顺序加载并拼接以下文件内容作为 System Prompt：
  1. `IDENTITY.md` (核心定位)
  2. `AGENTS.md` (工作指令)
  3. `SOUL.md` (性格与风格)
  4. `MEMORY.md` (记忆与经验)
  5. `TOOLS.md` (工具说明补充)
  6. `USER.md` (用户偏好)
  （忽略不存在的文件）

- **工具注册 (`tool-registry.jsonc`)**：
  读取 JSONC，根据 `builtin.include` 或 `mcp` 字段，动态提取该 Agent 可调用的工具列表，并将工具配置映射到 `llm_router`。

### 2.2 基础 Agent 层 (`DirectoryAgent`)
职责：继承现有的 `BaseAgent`，基于 Loader 加载的配置执行任务。

```python
class DirectoryAgent(BaseAgent):
    def __init__(self, name: str, role_dir: str):
        super().__init__(name)
        self.config = DirectoryAgentLoader.load(role_dir)
        
    async def execute(self, state: WorkflowState) -> WorkflowState:
        # 1. 组装当前状态（如 state.match_contexts）为 User Prompt
        # 2. 将 self.config.system_prompt 和 tools 传给 llm_router
        # 3. 解析 LLM 返回并更新 WorkflowState
        return state
```

### 2.3 Team / Coordinator 调度层 (`TeamCoordinator`)
职责：作为“团队”管理者，提供对多个 `DirectoryAgent` 的组织和编排能力。
现有 `Coordinator` 采用简单的列表顺序执行，为了支持更复杂的团队流转（如在 `agents/roles/team` 目录中可能存在的流程编排），我们可以扩展 `Coordinator`：
- **TeamLoader**：未来若 `team/` 目录中加入 `workflow.json` 等配置，可通过它动态生成流转拓扑（如：GATHER -> ANALYZE -> REVIEW）。目前则保持兼容顺序执行机制，但 Agent 的实例化全部由 `DirectoryAgent` 接管。

---

## 3. 实现步骤 (Implementation Plan)

1. **开发 `utils/config_parser.py`**：
   - 提供 JSONC 解析（支持忽略注释）。
   - 提供 Markdown 读取与拼接功能。

2. **创建 `agents/core/directory_agent.py`**：
   - 实现 `DirectoryAgentLoader`，返回包含 System Prompt 和 Tools 配置的数据类 `AgentConfig`。
   - 实现 `DirectoryAgent` 继承自 `BaseAgent`，内部通过 `llm_router.py`（需扩展支持 Tools Calling）与 LLM 交互。

3. **重构现有 Roles (`analyst`, `supervisor`, `reviewer`)**：
   - 将原先写死的 `Analyst`, `Reviewer` 等类，修改为直接实例化 `DirectoryAgent(name="analyst", role_dir="agents/roles/analyst")`。

4. **更新 `llm_router.py`**：
   - 增加对 Tool Calling 的支持（兼容 LiteLLM 的 `tools` 参数）。

---

## 4. 权衡与优势 (Trade-offs)
- **优势**：极大提高可扩展性。业务人员只需在 `roles/` 目录下修改 Markdown 文件，即可改变 Agent 行为，无需修改 Python 代码；完全兼容现有的 Phoenix 格式。
- **劣势**：随着 Prompt 的增加，Token 消耗会增加。需要确保 `llm_router.py` 使用的模型（如 GPT-4o 或 Claude-3.5）拥有足够的上下文窗口。

请检查上述设计。如果同意，我们将进入实现计划的编写。
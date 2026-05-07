# Provider 抽象化 Fixture 发现设计

**日期**: 2026-05-07  
**状态**: 已批准  
**背景**: 当前系统以 Sportmonks 为唯一 fixture 数据源，OddAlerts fixture ID 通过事后扫描映射，成功率不稳定。本设计将 fixture 发现提升为双（多）provider 并行查询 + 合并，彻底解决 ID 映射问题。

---

## 问题

当前流程：
```
Sportmonks 列表 → 对每场比赛 → 尝试扫描 dropping odds / trends 找到 OA fixture ID → 大概率失败
```

根本原因：OddAlerts fixture ID 与 Sportmonks fixture ID 完全独立，事后用队名模糊搜索覆盖率低。

目标流程：
```
Sportmonks 发现  ─┐
                   ├→ 合并 → UnifiedFixture（含双方 ID）→ 各自取详细数据
OddAlerts 发现  ─┘
```

---

## 数据模型

### `ProviderFixture`

单个 provider 返回的原始 fixture，存放在 `agents/core/models.py`：

```python
@dataclass
class ProviderFixture:
    provider: str          # "sportmonks" | "oddalerts" | ...
    fixture_id: int        # 该 provider 自己的 ID
    home_team: str
    away_team: str
    kickoff_unix: int
    league_name: str | None = None
    raw: dict = field(default_factory=dict)
```

### `UnifiedFixture`

跨 provider 合并后的统一比赛对象，存放在 `agents/core/models.py`：

```python
@dataclass
class UnifiedFixture:
    home_team: str                 # 以优先级最高的 provider 队名为准
    away_team: str
    kickoff_unix: int
    provider_ids: dict[str, int]   # {"sportmonks": 18329, "oddalerts": 54201}
```

`provider_ids` 使用字典，新增 provider 不需要修改数据结构。某 provider 无对应比赛时该 key 不存在，调用方用 `.get("oddalerts")` 安全取值。

---

## BaseProvider 抽象方法

在 `provider/base.py` 的 `BaseProvider` 中新增：

```python
@abstractmethod
async def discover_fixtures(
    self,
    league_ids: list[int],
    dates: list[str],          # ISO 格式，如 ["2026-05-07", "2026-05-08"]
) -> list[ProviderFixture]:
    """
    返回指定联赛和日期范围内的所有 fixture。
    league_ids 为该 provider 自己体系的联赛 ID。
    """
    pass
```

每个 provider 自己维护联赛 ID 体系，Orchestrator 负责将统一联赛名列表转换为各 provider 的 league_ids。

---

## Provider 实现

### Sportmonks

将 `_fetch_and_prepare` 中现有的 `_tool_goalcast_sportmonks_get_matches` 调用封装为 `discover_fixtures`，返回 `list[ProviderFixture]`。改动最小，逻辑不变。

### OddAlerts

两级策略，封装在 provider 内部，对外仅暴露 `discover_fixtures`：

1. **首选**：调用 `/api/fixtures/between`，传入正确的日期范围参数重新验证（历史注释标记为 bug，需实测确认）
2. **兜底**：取 `homeWin` + `awayWin` + `btts` 三个 trends 端点并集（不设 `min_stat` 门槛），覆盖当日绝大多数有赔率的比赛；按 `fixture_id` 去重

### 其他 Provider（未来）

实现 `discover_fixtures` 即可接入，无需改动合并逻辑或 Orchestrator 核心。

---

## 联赛 ID 映射

新增配置文件 `config/oddalerts_leagues.json`，格式与现有 `config/sportmonks_leagues.json` 一致：

```json
{
  "英超": 1,
  "西甲": 2,
  "意甲": 3,
  ...
}
```

Orchestrator 在调用各 provider 的 `discover_fixtures` 前，将统一联赛名列表分别通过各自的映射文件转换为对应的 league_ids。映射文件缺失时降级为传空（provider 返回全量数据）。

---

## FixtureMerger

新建 `agents/core/fixture_merger.py`：

**合并 Key**：

```python
canonical_key = normalize(home) + "|" + normalize(away) + "|" + str(kickoff_unix // 3600)
```

- 队名归一化：移除重音、空格、连字符，全部小写（逻辑从 `fixture_mapper._normalize` 提取到 `utils/normalize.py` 共享）
- 时间取整到小时，允许不同 provider 报的开赛时间有 ±1 小时误差

**合并流程**：

1. 按 provider 优先级顺序（Sportmonks → OddAlerts → 其他）处理 `ProviderFixture`
2. 计算 canonical_key，查已有 `UnifiedFixture` 字典
3. 命中 → 补充 `provider_ids[provider]`，队名以优先级更高的 provider 为准
4. 未命中 → 新建 `UnifiedFixture` 加入字典

复杂度 O(N×M)，N = 总 fixture 数，M = provider 数，实际规模完全够用。

---

## Orchestrator 改动

`_fetch_and_prepare` 重构为：

```
1. 并行获取各 provider 的 league_ids（通过各自映射配置）
2. 并行调用每个 provider 的 discover_fixtures(league_ids, dates)
3. 交给 FixtureMerger 合并，得到 list[UnifiedFixture]
4. 遍历 unified fixtures，调度进 pipeline（传入 provider_ids 字典）
```

原有的 `find_oddalerts_fixture_id` 调用从 Orchestrator 移除。

---

## DataCollector 改动

`collect_all` 签名调整：

```python
async def collect_all(
    executor: Any,
    provider_ids: dict[str, int],   # 替换原来的 fixture_id + oa_fixture_id 分离参数
    home_team: str = "",
    away_team: str = "",
    kickoff_unix: int | None = None,
) -> dict:
```

- `collect_sportmonks` 使用 `provider_ids.get("sportmonks")`
- `collect_oddalerts` 使用 `provider_ids.get("oddalerts")`，ID 已确定，跳过 `fixture_mapper`
- `fixture_mapper.py` 保留但标记为 deprecated，仅极端兜底情况使用

---

## 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `agents/core/models.py` | 新建 | `ProviderFixture`, `UnifiedFixture` |
| `agents/core/fixture_merger.py` | 新建 | 合并逻辑 |
| `utils/normalize.py` | 新建 | 共享队名归一化（从 fixture_mapper 提取） |
| `provider/base.py` | 修改 | 添加 `discover_fixtures` 抽象方法 |
| `provider/sportmonks/client.py` | 修改 | 实现 `discover_fixtures` |
| `provider/oddalerts/client.py` | 修改 | 实现 `discover_fixtures`（两级策略） |
| `config/oddalerts_leagues.json` | 新建 | OddAlerts 联赛名 → competition_id 映射 |
| `agents/core/orchestrator.py` | 修改 | `_fetch_and_prepare` 重构 |
| `agents/core/data_collector.py` | 修改 | 接收 `provider_ids` 字典 |
| `provider/oddalerts/fixture_mapper.py` | 保留 | 标记 deprecated |

---

## 不在此次范围内

- 第三个及以上 provider 的具体实现
- OddAlerts `/fixtures/between` 端点 bug 的根本修复（实现时实测决定）
- Provider 优先级的动态配置（当前硬编码 Sportmonks first）

# Goalcast Skills

本目录包含 Goalcast 项目的所有 skills，每个 skill 都是一个独立的目录，包含详细的使用说明和最佳实践。

## 📁 目录结构

```
skills/
├── README.md                      # 本文件
├── sportmonks-provider/           # SportMonks API 使用技能
│   └── SKILL.md                   # SportMonks 详细文档
├── footystats-provider/           # FootyStats API 使用技能
│   └── SKILL.md                   # FootyStats 详细文档
├── understat-provider/            # Understat API 使用技能
│   └── SKILL.md                   # Understat 详细文档
└── goalcast-*/                    # 其他 Goalcast 相关技能
    └── SKILL.md
```

## 🎯 Skills 列表

### Provider Skills

#### 1. SportMonks Provider
**目录**: `sportmonks-provider/`  
**内容**: SportMonks API v3 完整使用指南
- 免费计划可用端点（6 个）
- 不可用端点（16 个）
- 使用示例和最佳实践
- 常见问题解答

**触发条件**:
- 如何使用 SportMonks API
- SportMonks 免费计划能获取什么数据
- 获取足球比赛数据
- SportMonks API 配置

**核心功能**:
- 比赛数据查询
- 联赛列表
- 球队/球员基础信息
- 日期范围比赛查询

#### 2. FootyStats Provider
**目录**: `footystats-provider/`  
**内容**: FootyStats API 完整使用指南（16 个端点）
- 基础数据端点（3 个）
- 联赛数据端点（6 个）
- 详细数据端点（4 个）
- 统计数据端点（2 个）

**触发条件**:
- 如何使用 FootyStats API
- 获取联赛积分榜
- 获取球队统计数据
- 获取比赛详情
- 查询 BTTS/Over 2.5 统计

**核心功能**:
- 联赛积分榜
- 球队详细统计
- 比赛详情（含 xG）
- BTTS 和 Over 2.5 统计
- 球员/裁判数据

#### 3. Understat Provider
**目录**: `understat-provider/`  
**内容**: Understat API 使用指南（高级统计数据）
- xG, xA 等高级统计
- 球员表现分析
- 射门质量评估

**触发条件**:
- 如何获取 xG 数据
- Understat API 使用
- 期望进球统计
- 获取球员 xG 数据
- 高级足球统计数据

**核心功能**:
- 球员 xG 统计
- xA（期望助攻）
- xG 链和 xGBuildup
- 射门质量分析

## 📊 Provider 对比

| 特性 | SportMonks 免费 | FootyStats | Understat |
|------|---------------|------------|-----------|
| **API Key** | 需要 | 需要 | 不需要 |
| **xG 数据** | ❌ (付费) | ✅ (部分) | ✅ (完整) |
| **积分榜** | ❌ (付费) | ✅ | ⚠️ (需解析) |
| **实时比分** | ❌ (付费) | ❌ | ❌ |
| **球队统计** | ❌ (付费) | ✅ | ⚠️ (需解析) |
| **球员统计** | ✅ (基础) | ✅ (详细) | ✅ (高级) |
| **使用难度** | 中等 | 简单 | 中等 |
| **推荐场景** | 基础数据 | 完整联赛数据 | 高级统计 |

## 🎯 使用建议

### 选择指南

1. **需要基础比赛数据** → 使用 SportMonks
2. **需要完整联赛数据** → 使用 FootyStats
3. **需要 xG 等高级统计** → 使用 Understat
4. **需要实时比分** → 都需要付费升级

### 组合使用

```python
# 示例：组合使用三个 Provider
from provider.sportmonks.client import SportmonksProvider
from provider.footystats.client import FootyStatsProvider
from provider.understat.client import UnderstatProvider

async def get_complete_data():
    """获取完整的足球数据"""
    sportmonks = SportmonksProvider()
    footystats = FootyStatsProvider()
    understat = UnderstatProvider()
    
    # 1. 使用 SportMonks 获取基础数据
    leagues = await sportmonks.get_leagues(page=1)
    
    # 2. 使用 FootyStats 获取联赛详情
    standings = await footystats.get_league_tables(season_id=14968)
    
    # 3. 使用 Understat 获取高级统计
    players_xg = await understat.get_league_players("Bundesliga", "2024")
    
    return leagues, standings, players_xg
```

## 📝 Skill 格式说明

每个 skill 目录包含一个 `SKILL.md` 文件，结构如下：

```markdown
# Skill 名称

## 📋 概述
简要说明 skill 的用途和提供者

## 🎯 触发条件
列出触发此 skill 的用户问题类型

## 🔑 核心知识
- API 端点
- 配置方法
- 数据字段说明

## 💻 使用方法
- 初始化代码
- 使用场景与示例
- 最佳实践

## ⚠️ 注意事项
- API 限制
- 错误处理
- 数据缓存

## 🔍 常见问题解答
Q&A 格式的常见问题

## 📊 数据字段说明
表格形式的字段文档

## 📚 相关文档
链接到相关文档

## 🆘 故障排除
常见问题和解决方案

## 📝 最佳实践
代码示例和推荐做法

## 🔄 更新日志
版本历史和更新内容
```

## 🛠️ 创建新 Skill

要创建新的 skill：

1. 创建目录：`mkdir skills/your-skill-name`
2. 创建 `SKILL.md` 文件
3. 按照上述格式填写内容
4. 更新本 README 文件

## 📖 相关文档

- [SportMonks 测试报告](../docs/SPORTMONKS_TEST_REPORT.md)
- [SportMonks 使用指南](../docs/SPORTMONKS_USAGE.md)
- [Understat 开发总结](../docs/UNDERSTAT_DEVELOPMENT.md)
- [Understat 实现总结](../docs/UNDERSTAT_IMPLEMENTATION_SUMMARY.md)
- [MCP 服务器文档](../mcp_server/README.md)

## 🔄 更新日志

- **2026-04-08**: 
  - 重构 skills 目录结构
  - 将所有 provider 文档转换为独立的 skill 目录
  - 删除旧的 *.skill 文件
  - 创建完整的 provider skills:
    - sportmonks-provider
    - footystats-provider
    - understat-provider

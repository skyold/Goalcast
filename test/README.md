# Goalcast Test Suite

本目录包含所有测试文件和测试脚本。

## 📁 测试文件结构

```
test/
├── __init__.py                 # 测试包初始化
├── README.md                   # 本文件
├── test_sportmonks_api.py      # SportMonks API 基础测试
├── test_sportmonks_endpoints.py # SportMonks API 端点完整测试
├── test_footystats.py          # FootyStats API 测试
├── test_understat_api.py       # Understat API 端点探索
├── test_understat_debug.py     # Understat HTML 调试
├── test_understat_structure.py # Understat 网站结构分析
├── test_api_report.py          # API 综合测试报告
├── test_bundesliga.py          # 德国甲级联赛测试
└── test_debug.py               # 调试脚本
```

## 🧪 运行测试

### 运行所有测试

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行所有测试
pytest test/ -v
```

### 运行特定测试

```bash
# SportMonks API 测试
pytest test/test_sportmonks_endpoints.py -v

# FootyStats API 测试
pytest test/test_footystats.py -v

# Understat API 测试
pytest test/test_understat_*.py -v

# 综合测试报告
python test/test_api_report.py
```

### 运行单个测试脚本

```bash
# 直接运行 Python 测试脚本
python test/test_bundesliga.py

# 带调试信息运行
python -m pytest test/test_sportmonks_endpoints.py -v -s
```

## 📊 测试文件说明

### SportMonks API 测试

#### `test_sportmonks_api.py`
- **用途**: SportMonks API 基础功能测试
- **内容**: 
  - API 连通性检查
  - 基础端点测试
  - 免费计划限制测试

#### `test_sportmonks_endpoints.py`
- **用途**: SportMonks API v3 完整端点测试
- **内容**:
  - 测试 22 个端点
  - 区分可用/不可用端点
  - 生成详细测试报告
- **输出**: `sportmonks_api_report.json`

### FootyStats API 测试

#### `test_footystats.py`
- **用途**: FootyStats API 功能测试
- **内容**:
  - 联赛列表查询
  - 比赛数据查询
  - 球队统计查询

### Understat API 测试

#### `test_understat_api.py`
- **用途**: Understat API 端点探索
- **内容**:
  - 测试可能的 API 端点
  - 查找 AJAX 请求 URLs
  - 分析 JavaScript 文件

#### `test_understat_debug.py`
- **用途**: Understat HTML 数据提取调试
- **内容**:
  - 调试 HTML 解析
  - 查找 JavaScript 变量
  - 保存调试 HTML 文件
- **输出**: `understat_debug.html`

#### `test_understat_structure.py`
- **用途**: Understat 网站结构分析
- **内容**:
  - 分析首页链接
  - 测试不同 URL 格式
  - 查找联赛链接

### 综合测试

#### `test_api_report.py`
- **用途**: SportMonks 和 FootyStats 综合对比测试
- **内容**:
  - 两个 API 的连通性测试
  - 功能对比
  - 获取德国甲级联赛比赛数据

#### `test_bundesliga.py`
- **用途**: 德国甲级联赛特定测试
- **内容**:
  - 使用 FootyStats 获取德甲数据
  - 筛选本周比赛
  - 分析比赛数据

### 调试脚本

#### `test_debug.py`
- **用途**: 通用调试脚本
- **内容**: 根据具体需求临时编写

## 📝 测试报告

### SportMonks API 测试报告

运行 `test_sportmonks_endpoints.py` 后会生成：

```json
{
  "test_time": "2026-04-08T21:00:00",
  "api_key_prefix": "Y4Q4Lr04PZS7WLz",
  "available_endpoints": [...],
  "unavailable_endpoints": [...]
}
```

### 测试覆盖率

| Provider | 测试文件数 | 测试端点数 | 测试状态 |
|----------|-----------|-----------|---------|
| SportMonks | 2 | 22 个 | ✅ 完成 |
| FootyStats | 1 | 16 个 | ✅ 完成 |
| Understat | 3 | 1 个 (JSON) | ⚠️ 部分完成 |

## 🔧 测试配置

### pytest 配置

在 `pytest.ini` 或 `pyproject.toml` 中配置：

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
testpaths = test
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
```

### 环境变量

测试需要配置 API Keys：

```bash
# .env
SPORTMONKS_API_KEY=your_sportmonks_key
FOOTYSTATS_API_KEY=your_footystats_key
```

## 📈 测试结果

### SportMonks API
- ✅ 可用端点：6 个
- ❌ 不可用端点：16 个
- 📊 测试通过率：27%

### FootyStats API
- ✅ 可用端点：16 个（全部）
- 📊 测试通过率：100%

### Understat API
- ✅ 可用端点：1 个（球员统计）
- ⚠️ 需 HTML 解析：5 个
- 📊 测试通过率：部分功能

## 🐛 已知问题

1. **Understat HTML 解析不稳定**
   - 原因：网站结构可能变化
   - 解决：使用 understatapi 库

2. **SportMonks 免费计划限制**
   - 原因：API 订阅计划限制
   - 解决：升级付费计划或使用 FootyStats

3. **会话未关闭警告**
   - 原因：aiohttp 会话管理
   - 解决：确保调用 `close()` 方法

## 📚 相关文档

- [SportMonks 测试报告](../docs/SPORTMONKS_TEST_REPORT.md)
- [SportMonks 使用指南](../docs/SPORTMONKS_USAGE.md)
- [Understat 开发总结](../docs/UNDERSTAT_DEVELOPMENT.md)
- [Understat 实现总结](../docs/UNDERSTAT_IMPLEMENTATION_SUMMARY.md)
- [Skills 重构总结](../docs/SKILLS_REFACTORING_SUMMARY.md)

## 🔄 更新日志

- **2026-04-08**: 
  - 创建 test 目录
  - 移动所有测试文件
  - 添加测试文档
  - 添加 understatapi 依赖

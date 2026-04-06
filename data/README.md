# Data Directory

此目录用于存储项目生成的数据文件。

## 📁 目录结构

```
data/
├── *.json              # API 返回的原始数据文件（已忽略）
├── cache/             # 缓存文件（已忽略）
└── exports/           # 导出的数据文件（已忽略）
```

## 📝 说明

### 存储的文件类型

- **API 原始数据**: `todays_matches.json`, `epl_matches.json`, `epl_standings.json` 等
- **缓存文件**: 临时缓存的 API 响应
- **导出数据**: 处理后的数据导出文件

### Git 追踪规则

- ✅ `data/` 目录本身**会被追踪**（通过 `.gitkeep` 文件）
- ❌ `data/*.json` 文件**不会被提交**（已在 `.gitignore` 中配置）
- ❌ `data/cache/` 和 `data/exports/` 子目录内容**不会被提交**

### 为什么这样配置？

1. **保持目录结构**: `data/` 目录被追踪，确保新克隆的仓库有正确的目录结构
2. **忽略数据文件**: JSON 数据文件可能很大且经常变化，不应该提交到版本控制
3. **便于协作**: 团队成员都有相同的目录结构，但各自生成自己的数据文件

## 🔧 使用方式

### 保存数据

```python
from utils.data_manager import save_json_data

# 保存到 data/ 根目录
file_path = save_json_data(data, "todays_matches")
# 结果：data/todays_matches.json

# 保存到子目录
file_path = save_json_data(data, "epl_standings", subdir="leagues")
# 结果：data/leagues/epl_standings.json
```

### 加载数据

```python
from utils.data_manager import load_json_data

# 从 data/ 根目录加载
data = load_json_data("todays_matches")

# 从子目录加载
data = load_json_data("epl_standings", subdir="leagues")
```

### 获取文件路径

```python
from utils.data_manager import get_data_file_path

# 获取文件路径（不创建文件）
path = get_data_file_path("custom.json")
# 结果：data/custom.json

path = get_data_file_path("report.csv", subdir="reports")
# 结果：data/reports/report.csv
```

## 🧹 清理

定期清理旧数据文件：

```python
from utils.data_manager import cleanup_old_files

# 清理超过 7 天的文件
cleanup_old_files(days=7)
```

## 📦 示例脚本

查看 [`scripts/save_data_example.py`](../scripts/save_data_example.py) 了解完整的使用示例。

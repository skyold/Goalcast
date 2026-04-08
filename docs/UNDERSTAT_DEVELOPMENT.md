# Understat Provider 开发总结

## 📊 进展

### 已完成
1. ✅ 创建了 Understat Provider 基础架构
2. ✅ 实现了 HTML 数据提取功能
3. ✅ 发现了部分 JSON API 端点
4. ✅ 测试了球员统计 API 端点

### 🔍 研究发现

#### Understat 网站结构
Understat.com 使用 JavaScript 动态加载数据，主要通过以下端点：

1. **联赛页面**: `/league/{LEAGUE}/{SEASON}`
   - 数据嵌入在 HTML 的 JavaScript 变量中
   - 需要解析 `teamsData` 等变量

2. **球员统计 API**: `/main/getPlayersStats/{LEAGUE}/{SEASON}`
   - ✅ 返回 JSON 格式数据
   - ✅ 已在测试中验证可用

3. **联赛数据 API**: 实际端点待确认
   - ❌ `/getLeagueData/{LEAGUE}/{SEASON}` 返回 404

#### 可用联赛
- EPL (英格兰超级联赛)
- La Liga (西班牙甲级联赛)
- Bundesliga (德国甲级联赛)
- Serie A (意大利甲级联赛)
- Ligue 1 (法国甲级联赛)
- RFPL (俄罗斯超级联赛)

#### 可用赛季
2014-2025（多个赛季）

## ⚠️ 挑战

### 1. 数据提取困难
Understat 不是传统的 REST API，而是：
- 数据嵌入在 HTML 的 JavaScript 变量中
- 使用 AJAX 动态加载
- 需要模拟浏览器行为

### 2. 正则表达式匹配失败
当前正则表达式无法匹配到数据，原因：
- JavaScript 变量名可能变化
- 数据格式可能不同
- HTML 结构可能更新

### 3. 会话管理问题
测试中出现 "Unclosed client session" 警告，需要改进资源管理。

## 💡 解决方案建议

### 方案 1: 使用现有 Python 库
使用成熟的 `understatapi` 库：

```python
from understat import Understat

async with Understat() as understat:
    # 获取联赛球队
    teams = await understat.get_league_teams("bundesliga", "2024")
    
    # 获取联赛球员
    players = await understat.get_league_players("bundesliga", "2024")
    
    # 获取比赛数据
    matches = await understat.get_league_matches("bundesliga", "2024")
```

**优点：**
- 已经过充分测试
- 处理了所有边缘情况
- 维护活跃

**缺点：**
- 外部依赖
- 可能不稳定

### 方案 2: 改进 HTML 解析
使用 BeautifulSoup 和更智能的解析：

```python
from bs4 import BeautifulSoup
import json
import re

async def get_league_data(self, league, season):
    url = f"https://understat.com/league/{league}/{season}"
    async with session.get(url) as response:
        html = await response.text()
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找所有 script 标签
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'teamsData' in script.string:
                # 提取 JSON
                match = re.search(r'var\s+teamsData\s*=\s*JSON\.parse\((.+?)\)', script.string)
                if match:
                    json_str = match.group(1)
                    # 处理转义
                    data = json.loads(json.loads(json_str))
                    return data
```

### 方案 3: 混合方法（推荐）
结合多种方法：

1. **优先使用已验证的 JSON API**
   - `/main/getPlayersStats/{league}/{season}` - 球员数据
   
2. **对于联赛数据，使用 understatapi 库**
   - 更可靠
   - 处理边缘情况

3. **实现备用方案**
   - 如果 API 失败，尝试 HTML 解析
   - 如果 HTML 解析失败，使用缓存数据

## 📝 下一步行动

### 立即行动
1. 安装并测试 `understatapi` 库
2. 集成到现有 provider 架构
3. 创建完整的测试套件

### 短期目标
1. 实现所有主要端点
2. 添加错误处理
3. 实现数据缓存

### 长期目标
1. 添加更多高级统计（xG, xA, xPTS）
2. 实现射门地图可视化
3. 创建数据分析工具

## 🔧 代码改进建议

### 1. 修复 URL 拼接
```python
# 当前代码
url = f"{self.BASE_URL}{endpoint}"  # 可能导致 double slash

# 改进
if endpoint.startswith('/'):
    url = f"{self.BASE_URL}{endpoint}"
else:
    url = f"{self.BASE_URL}/{endpoint}"
```

### 2. 改进会话管理
```python
async def __aenter__(self):
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
    await self.close()
```

### 3. 添加重试机制
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential())
async def _request(self, endpoint, **kwargs):
    # 请求逻辑
```

## 📦 依赖建议

```txt
# requirements.txt
aiohttp>=3.9.0  # HTTP 客户端
beautifulsoup4>=4.12.0  # HTML 解析
lxml>=4.9.0  # 快速 XML/HTML 解析
tenacity>=8.2.0  # 重试逻辑
```

## 🎯 最终架构建议

```
provider/
├── understat/
│   ├── __init__.py
│   ├── client.py          # 核心 Provider
│   ├── parser.py          # HTML/JSON 解析器
│   ├── models.py          # 数据模型
│   └── test_understat.py  # 测试
└── ...
```

## 📚 参考资料

- Understat API: https://understat.com
- understatapi PyPI: https://pypi.org/project/understatapi/
- soccerdata Understat: https://soccerdata.readthedocs.io/en/stable/datasources/Understat.html

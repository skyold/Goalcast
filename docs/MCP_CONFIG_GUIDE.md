# MCP Server 配置说明

## 📋 `mcporter.json` 的作用

这是 MCP 客户端的配置文件，用于定义如何连接到 Goalcast MCP 服务器。

## ⚠️ 当前问题

原始配置使用了**硬编码的绝对路径**：

```json
{
  "mcpServers": {
    "goalcast": {
      "command": "/Users/zhengningdai/workspace/skyold/Goalcast/.venv/bin/python3",
      "args": ["mcp_server/server.py"],
      "env": {
        "PYTHONPATH": "/Users/zhengningdai/workspace/skyold/Goalcast"
      }
    }
  }
}
```

**问题**：
- ❌ 无法迁移到其他服务器
- ❌ Docker 容器中无法使用
- ❌ 其他开发者需要手动修改路径

---

## ✅ 解决方案

### 方案 1：使用相对路径（推荐本地开发）

创建 `mcporter.json.example` 模板：

```json
{
  "mcpServers": {
    "goalcast": {
      "command": "python3",
      "args": ["mcp_server/server.py"],
      "env": {
        "PYTHONPATH": "."
      },
      "cwd": "."
    }
  }
}
```

**优点**：
- ✅ 可移植，可以在任何位置运行
- ✅ Docker 友好
- ✅ 团队协作无需修改

**使用方式**：
```bash
# 1. 复制模板
cp mcporter.json.example mcporter.json

# 2. 在项目根目录运行 MCP 客户端
cd /path/to/Goalcast
mcp dev
```

---

### 方案 2：使用环境变量（推荐生产环境）

```json
{
  "mcpServers": {
    "goalcast": {
      "command": "python3",
      "args": ["mcp_server/server.py"],
      "env": {
        "PYTHONPATH": "${GOALCAST_PATH}",
        "FOOTYSTATS_API_KEY": "${FOOTYSTATS_API_KEY}",
        "SPORTMONKS_API_KEY": "${SPORTMONKS_API_KEY}"
      }
    }
  }
}
```

**优点**：
- ✅ 敏感信息（API Keys）不硬编码
- ✅ 路径可通过环境变量配置
- ✅ 适合 CI/CD 和自动化部署

---

### 方案 3：Docker 部署（推荐生产环境）

使用 Docker Compose 部署：

```yaml
# docker-compose.yml
services:
  mcp-server:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - HOST=0.0.0.0
      - PORT=8000
    restart: unless-stopped
```

**MCP 客户端配置**（远程连接）：

```json
{
  "mcpServers": {
    "goalcast": {
      "url": "http://localhost:8000/sse",
      "transport": "sse"
    }
  }
}
```

**优点**：
- ✅ 完全隔离，不依赖本地环境
- ✅ 可部署到任何支持 Docker 的服务器
- ✅ 便于扩展和负载均衡

---

## 🔧 实际使用建议

### 本地开发
```bash
# 1. 创建本地配置
cp mcporter.json.example mcporter.json

# 2. 确保虚拟环境激活
source .venv/bin/activate

# 3. 在项目根目录运行
cd /path/to/Goalcast
mcp dev
```

### Docker 部署
```bash
# 1. 构建镜像
docker build -t goalcast-mcp .

# 2. 运行容器
docker run -d --name goalcast \
  -p 8000:8000 \
  --env-file .env \
  goalcast-mcp

# 3. 配置 MCP 客户端连接远程服务器
# 使用 SSE 传输模式
```

### 远程服务器部署
```bash
# 1. 在服务器上运行
docker-compose up -d

# 2. 本地 MCP 客户端配置
{
  "mcpServers": {
    "goalcast": {
      "url": "http://your-server-ip:8000/sse",
      "transport": "sse"
    }
  }
}
```

---

## 📝 最佳实践

### 1. 不要提交 `mcporter.json` 到 Git
```gitignore
# MCP 客户端配置（包含本地路径）
mcporter.json
```

### 2. 提交模板文件
```bash
git add mcporter.json.example
git commit -m "docs: add MCP configuration template"
```

### 3. 使用 `.env` 管理敏感信息
```bash
# .env（不提交）
FOOTYSTATS_API_KEY=your_key_here
SPORTMONKS_API_KEY=your_key_here

# .env.example（提交模板）
FOOTYSTATS_API_KEY=
SPORTMONKS_API_KEY=
```

---

## 🚀 迁移指南

### 从本地迁移到 Docker

1. **构建镜像**
```bash
docker build -t goalcast-mcp .
```

2. **准备环境变量**
```bash
# 复制 .env 文件到服务器
scp .env user@server:/path/to/Goalcast/
```

3. **在服务器上运行**
```bash
docker-compose up -d
```

4. **更新 MCP 客户端配置**
```json
{
  "mcpServers": {
    "goalcast": {
      "url": "http://server-ip:8000/sse",
      "transport": "sse"
    }
  }
}
```

### 从 Docker 迁移到其他服务器

1. **导出镜像**
```bash
docker save goalcast-mcp > goalcast-mcp.tar
```

2. **传输到目标服务器**
```bash
scp goalcast-mcp.tar user@new-server:/path/
```

3. **导入并运行**
```bash
docker load < goalcast-mcp.tar
docker run -d --name goalcast -p 8000:8000 --env-file .env goalcast-mcp
```

---

## 📚 相关文档

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [Docker 部署指南](../Dockerfile)
- [环境变量配置](../.env.example)

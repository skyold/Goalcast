# MCP 服务器配置迁移指南

## ⚠️ 原始问题

`mcporter.json` 文件包含了**硬编码的本地路径**：

```json
{
  "command": "/Users/zhengningdai/workspace/skyold/Goalcast/.venv/bin/python3",
  "args": ["mcp_server/server.py"],
  "env": {
    "PYTHONPATH": "/Users/zhengningdai/workspace/skyold/Goalcast"
  }
}
```

**导致的问题**：
1. ❌ **无法迁移**：路径是绝对的，换服务器就不能用了
2. ❌ **Docker 无法使用**：容器内路径完全不同
3. ❌ **协作困难**：其他开发者需要手动修改路径

---

## ✅ 解决方案总览

| 场景 | 推荐方案 | 配置文件 |
|------|---------|---------|
| 本地开发 | 相对路径 | `mcporter.json.example` |
| Docker 部署 | SSE 远程连接 | `docker-compose.yml` |
| 生产环境 | SSE 远程连接 | 远程服务器配置 |

---

## 🚀 快速开始

### 方案 1：本地开发（推荐）

```bash
# 1. 使用部署脚本自动配置
./scripts/deploy_mcp.sh local

# 2. 或者手动配置
cp mcporter.json.example mcporter.json
```

**配置内容**：
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
- ✅ 使用相对路径，可在任何位置运行
- ✅ 团队协作无需修改
- ✅ Docker 友好

---

### 方案 2：Docker 部署（推荐生产）

```bash
# 1. 使用部署脚本
./scripts/deploy_mcp.sh docker

# 2. 或者手动部署
docker build -t goalcast-mcp .
docker-compose up -d
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

### 方案 3：远程服务器部署

```bash
# 1. 在服务器上运行 Docker
./scripts/deploy_mcp.sh docker

# 2. 本地配置远程连接
./scripts/deploy_mcp.sh remote
# 输入服务器 IP 和端口
```

**生成的配置**：
```json
{
  "mcpServers": {
    "goalcast": {
      "url": "http://your-server-ip:8000/sse",
      "transport": "sse"
    }
  }
}
```

> 💡 **方案 2 vs 方案 3：有什么区别？**
>
> 两个方案都使用了相同的命令 `./scripts/deploy_mcp.sh docker`，但**执行位置和用途不同**：
>
> | 对比项 | 方案 2（本地 Docker） | 方案 3（远程服务器） |
> |--------|---------------------|---------------------|
> | **执行位置** | 本地开发机 | 远程服务器（通过 SSH） |
> | **后续步骤** | 直接使用（本地连接） | 需要配置远程连接 |
> | **连接方式** | `localhost:8000` | `服务器 IP:8000` |
> | **用途** | 开发/测试 | 生产/团队协作 |
>
> **方案 2 使用场景**：
> ```bash
> # 在你的笔记本电脑上运行
> cd Goalcast
> ./scripts/deploy_mcp.sh docker
> # Docker 容器运行在本地，MCP 客户端连接 localhost:8000
> ```
>
> **方案 3 使用场景**：
> ```bash
> # 步骤 1：SSH 到远程服务器
> ssh user@192.168.1.100
> 
> # 步骤 2：在服务器上部署 Docker
> cd Goalcast
> ./scripts/deploy_mcp.sh docker
> # Docker 容器运行在远程服务器
> 
> # 步骤 3：回到本地电脑，配置远程连接
> ./scripts/deploy_mcp.sh remote
> # 输入服务器 IP: 192.168.1.100
> # MCP 客户端连接 http://192.168.1.100:8000/sse
> ```
>
> **简单总结**：
> - **方案 2** = 本地 Docker → 本地连接（一步完成）
> - **方案 3** = 远程 Docker → 远程连接（需要两步：部署 + 配置）

---

## 📁 文件说明

### 已创建的文件

| 文件 | 用途 | 是否提交到 Git |
|------|------|---------------|
| `mcporter.json.example` | 配置模板 | ✅ 是 |
| `mcporter.json` | 实际配置 | ❌ 否（已忽略） |
| `scripts/deploy_mcp.sh` | 部署脚本 | ✅ 是 |
| `MCP_CONFIG_GUIDE.md` | 详细指南 | ✅ 是 |

### Git 配置

已更新 `.gitignore`：
```gitignore
.env
mcporter.json  # 不提交包含本地路径的配置
```

---

## 🔧 使用部署脚本

### 检查配置
```bash
./scripts/deploy_mcp.sh check
```

### 本地开发模式
```bash
./scripts/deploy_mcp.sh local
```

### Docker 部署模式
```bash
./scripts/deploy_mcp.sh docker
```

### 远程连接模式
```bash
./scripts/deploy_mcp.sh remote
```

---

## 📊 迁移场景

### 场景 1：从本地迁移到 Docker

```bash
# 1. 在本地开发完成后
cd /path/to/Goalcast

# 2. 构建 Docker 镜像
docker build -t goalcast-mcp .

# 3. 测试容器
docker run -d -p 8000:8000 --env-file .env goalcast-mcp

# 4. 更新 MCP 客户端配置为 SSE 模式
./scripts/deploy_mcp.sh remote
```

### 场景 2：从 Docker 迁移到远程服务器

```bash
# 1. 导出 Docker 镜像
docker save goalcast-mcp > goalcast-mcp.tar

# 2. 传输到服务器
scp goalcast-mcp.tar user@server:/path/

# 3. 在服务器上导入
ssh user@server
docker load < goalcast-mcp.tar

# 4. 运行容器
docker run -d -p 8000:8000 --env-file .env goalcast-mcp

# 5. 本地配置远程连接
./scripts/deploy_mcp.sh remote
```

### 场景 3：团队协作

```bash
# 1. 提交配置模板（不提交 mcporter.json）
git add mcporter.json.example
git commit -m "docs: add MCP configuration template"

# 2. 团队成员 clone 后
cd Goalcast
./scripts/deploy_mcp.sh local  # 自动生成 mcporter.json
```

---

## 🎯 最佳实践

### ✅ 推荐做法

1. **使用相对路径**
   ```json
   {
     "command": "python3",
     "cwd": "."
   }
   ```

2. **使用环境变量管理敏感信息**
   ```bash
   # .env 文件
   FOOTYSTATS_API_KEY=your_key
   SPORTMONKS_API_KEY=your_key
   ```

3. **使用部署脚本自动化**
   ```bash
   ./scripts/deploy_mcp.sh local
   ```

4. **Docker 化部署**
   ```bash
   docker-compose up -d
   ```

### ❌ 避免的做法

1. **硬编码绝对路径**
   ```json
   // ❌ 不要这样做
   "command": "/Users/xxx/Goalcast/.venv/bin/python3"
   ```

2. **提交包含本地路径的配置文件**
   ```bash
   # ❌ 不要提交
   git add mcporter.json
   ```

3. **在代码中硬编码路径**
   ```python
   # ❌ 不要这样做
   path = "/Users/xxx/Goalcast/data"
   
   # ✅ 使用相对路径
   from config.settings import DATA_DIR
   ```

---

## 📚 相关文档

- [`MCP_CONFIG_GUIDE.md`](MCP_CONFIG_GUIDE.md) - 详细配置指南
- [`scripts/deploy_mcp.sh`](scripts/deploy_mcp.sh) - 部署脚本
- [`Dockerfile`](Dockerfile) - Docker 镜像构建
- [`docker-compose.yml`](docker-compose.yml) - Docker Compose 配置

---

## 🆘 故障排查

### 问题 1：配置不生效

**检查**：
```bash
./scripts/deploy_mcp.sh check
```

**解决**：
```bash
# 重新生成配置
./scripts/deploy_mcp.sh local
```

### 问题 2：Docker 容器无法启动

**检查日志**：
```bash
docker logs goalcast-mcp
```

**常见原因**：
- 缺少 `.env` 文件
- 端口被占用
- API Keys 配置错误

### 问题 3：远程连接失败

**检查**：
```bash
# 测试服务器是否可达
curl http://server-ip:8000/health

# 检查防火墙
telnet server-ip 8000
```

---

## 📞 获取帮助

运行帮助命令：
```bash
./scripts/deploy_mcp.sh help
```

查看详细文档：
- [`MCP_CONFIG_GUIDE.md`](MCP_CONFIG_GUIDE.md)

# 🚀 服务器部署 MCP - 快速指南

## 📋 部署步骤（基于最新代码）

### 1️⃣ 拉取代码

```bash
# SSH 登录服务器
ssh user@your-server-ip

# 进入工作目录
cd /path/to/workspace

# 克隆或更新代码
git clone <repo-url> Goalcast
cd Goalcast
# 或更新已有代码
git pull
```

---

### 2️⃣ 配置环境变量

```bash
# 复制模板
cp .env.example .env

# 编辑配置（填入你的 API Keys）
nano .env
```

**`.env` 文件内容**：
```bash
# Data Sources
FOOTYSTATS_API_KEY=你的_footystats_key
ODDS_API_KEY=你的_odds_key
OPENWEATHER_API_KEY=你的_openweather_key

# AI Analysis
ANTHROPIC_API_KEY=你的_anthropic_key

# Database
DATABASE_URL=sqlite:///data/db/goalcast.db
```

---

### 3️⃣ 一键部署（推荐）

使用快速部署脚本：

```bash
./scripts/quick_deploy.sh
```

脚本会自动：
- ✅ 检查 Docker 安装
- ✅ 创建/检查 .env 配置
- ✅ 构建 Docker 镜像
- ✅ 启动服务
- ✅ 验证服务状态

---

### 4️⃣ 手动部署（可选）

如果不想使用脚本，可以手动执行：

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

---

### 5️⃣ 验证服务

```bash
# 测试本地访问
curl http://localhost:8000/sse

# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs --tail=50
```

**预期结果**：
- 容器状态显示 `Up`
- 可以访问 `http://localhost:8000/sse`

---

### 6️⃣ 配置防火墙（如需远程访问）

```bash
# Ubuntu/Debian
sudo ufw allow 8000/tcp
sudo ufw status

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

---

### 7️⃣ 配置 MCP 客户端

根据你的 MCP 客户端位置选择配置：

#### 本地连接（客户端在服务器）
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

#### 远程连接（客户端在本地）
```json
{
  "mcpServers": {
    "goalcast": {
      "url": "http://服务器IP:8000/sse",
      "transport": "sse"
    }
  }
}
```

---

## 🔧 常用运维命令

### 查看状态
```bash
docker-compose ps
```

### 查看日志
```bash
docker-compose logs -f
```

### 重启服务
```bash
docker-compose restart
```

### 停止服务
```bash
docker-compose down
```

### 更新代码
```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose build --no-cache
docker-compose up -d
```

### 进入容器
```bash
docker-compose exec mcp-server bash
```

---

## 📊 部署架构

```
┌─────────────────────────────────────┐
│         服务器 (Server)              │
│                                     │
│  ┌──────────────────────────────┐   │
│  │   Docker Container           │   │
│  │                              │   │
│  │  Goalcast MCP Server         │   │
│  │  - FootyStats Provider       │   │
│  │  - Sportmonks Provider       │   │
│  │  - SSE Transport             │   │
│  │                              │   │
│  │  端口：8000                  │   │
│  └──────────────────────────────┘   │
│            ↑                        │
│            | http://:8000/sse       │
└────────────┼────────────────────────┘
             │
             ↓
    ┌────────────────┐
    │  MCP Client    │
    │  (Trae/其他)   │
    └────────────────┘
```

---

## ✅ 部署检查清单

完成后逐项检查：

- [ ] Docker 和 Docker Compose 已安装
- [ ] 代码已 pull 到服务器
- [ ] `.env` 文件已配置 API Keys
- [ ] 镜像构建成功
- [ ] 容器正在运行 (`docker-compose ps`)
- [ ] 本地可以访问 `http://localhost:8000/sse`
- [ ] 防火墙已配置（如需远程访问）
- [ ] MCP 客户端配置正确
- [ ] 可以调用 MCP 工具

---

## 🔍 故障排查

### 容器无法启动
```bash
docker-compose logs
```

### 服务无法访问
```bash
# 检查端口
netstat -tlnp | grep 8000

# 检查防火墙
sudo ufw status
```

### API 调用失败
```bash
# 检查 .env 配置
docker-compose exec mcp-server env | grep API_KEY
```

---

## 📚 详细文档

- [完整部署指南](./SERVER_DEPLOYMENT.md) - 详细的部署和运维指南
- [项目 README](../README.md) - 项目说明
- [MCP 配置指南](./MCP_CONFIG_GUIDE.md) - MCP 客户端配置

---

## 🎯 快速参考

### 第一次部署
```bash
git clone <repo> Goalcast
cd Goalcast
cp .env.example .env
nano .env  # 配置 API Keys
./scripts/quick_deploy.sh
```

### 日常更新
```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

### 查看日志
```bash
docker-compose logs -f
```

---

**部署完成！** 🎉

现在你可以在 MCP 客户端中使用 Goalcast 提供的工具了！

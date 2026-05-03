# 服务器部署 MCP - 快速指南

## 部署步骤（基于最新代码）

### 1. 拉取代码

```bash
ssh user@your-server-ip
cd /path/to/workspace
git clone <repo-url> Goalcast
cd Goalcast
# 或更新已有代码
git pull
```

### 2. 配置环境变量

```bash
cp .env.example .env
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

### 3. 一键部署（推荐）

```bash
./scripts/quick_deploy.sh
```

脚本会自动：检查 Docker 安装、创建 .env 配置、构建 Docker 镜像、启动服务、验证服务状态。

### 4. 手动部署（可选）

```bash
docker-compose build
docker-compose up -d
docker-compose ps
docker-compose logs -f
```

### 5. 验证服务

```bash
curl http://localhost:8000/sse
docker-compose ps
docker-compose logs --tail=50
```

### 6. 配置防火墙（如需远程访问）

```bash
# Ubuntu/Debian
sudo ufw allow 8000/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### 7. 配置 MCP 客户端

本地连接：
```json
{"mcpServers": {"goalcast": {"url": "http://localhost:8000/sse", "transport": "sse"}}}
```

远程连接：
```json
{"mcpServers": {"goalcast": {"url": "http://服务器IP:8000/sse", "transport": "sse"}}}
```

## 常用运维命令

```bash
docker-compose ps              # 查看状态
docker-compose logs -f         # 查看日志
docker-compose restart         # 重启服务
docker-compose down            # 停止服务
docker-compose exec mcp-server bash  # 进入容器
```

### 更新代码

```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

## 部署检查清单

- [ ] Docker 和 Docker Compose 已安装
- [ ] 代码已 pull 到服务器
- [ ] `.env` 文件已配置 API Keys
- [ ] 镜像构建成功
- [ ] 容器正在运行
- [ ] 本地可以访问 `http://localhost:8000/sse`
- [ ] 防火墙已配置（如需远程访问）
- [ ] MCP 客户端配置正确

## 故障排查

```bash
docker-compose logs                    # 容器无法启动
netstat -tlnp | grep 8000             # 服务无法访问
docker-compose exec mcp-server env | grep API_KEY  # API 调用失败
```

## 相关文档

- [Docker 完整指南](./DOCKER_GUIDE.md)
- [Docker 构建故障排查](./DOCKER_BUILD_TROUBLESHOOTING.md)
- [Docker 网络超时](./DOCKER_NETWORK_TIMEOUT.md)
- [MCP 配置指南](../MCP_CONFIG_GUIDE.md)

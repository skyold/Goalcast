# 服务器部署 Docker MCP 完整指南

## 部署前准备

- 服务器已安装 Docker 和 Docker Compose
- 有服务器的 SSH 访问权限
- 已获取 API Keys（FootyStats 等）

## 部署步骤

### 1. 克隆代码到服务器
```bash
ssh user@your-server-ip
cd /path/to/your/workspace
git clone <your-repo-url> Goalcast
cd Goalcast
```

### 2. 配置环境变量
```bash
cp .env.example .env
nano .env
```

`.env` 文件内容：
```bash
FOOTYSTATS_API_KEY=你的_footystats_api_key
ODDS_API_KEY=你的_odds_api_key
ANTHROPIC_API_KEY=你的_anthropic_key
DATABASE_URL=sqlite:///data/db/goalcast.db
```

### 3. 构建 Docker 镜像
```bash
docker-compose build
# 或全新构建
docker-compose build --no-cache
```

### 4. 启动 Docker 容器
```bash
docker-compose up -d
```

### 5. 验证服务状态
```bash
docker-compose ps
docker-compose logs -f
curl http://localhost:8000/sse
```

### 6. 配置防火墙（如需远程访问）
```bash
# Ubuntu/Debian
sudo ufw allow 8000/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload

# AWS EC2: 在安全组中添加端口 8000
```

### 7. 配置 MCP 客户端

本地连接：
```json
{"mcpServers": {"goalcast": {"url": "http://localhost:8000/sse", "transport": "sse"}}}
```

远程连接：
```json
{"mcpServers": {"goalcast": {"url": "http://your-server-ip:8000/sse", "transport": "sse"}}}
```

## 常用运维命令

```bash
docker-compose ps                    # 查看状态
docker-compose logs -f               # 实时日志
docker-compose logs --tail=100       # 最近 100 行
docker-compose restart               # 重启
docker-compose down                  # 停止
docker-compose exec mcp-server bash  # 进入容器
docker stats goalcast-mcp-server     # 资源使用
```

### 更新代码
```bash
git pull origin main
docker-compose build --no-cache
docker-compose up -d
docker image prune -f
```

## 故障排查

### 容器无法启动
```bash
docker-compose logs
lsof -i:8000    # 检查端口占用
```

### 服务启动后立即退出
```bash
docker-compose exec mcp-server bash
python --version
pip list | grep mcp
```

### 无法远程连接
```bash
sudo ufw status
netstat -tlnp | grep 8000
curl http://服务器IP:8000/sse
```

### API 调用失败
```bash
docker-compose exec mcp-server env | grep API_KEY
```

## 性能优化

### 资源限制
```yaml
services:
  mcp-server:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### 日志轮转
```yaml
services:
  mcp-server:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 健康检查
```yaml
services:
  mcp-server:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/sse"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## 安全建议

- 使用 `.env` 管理敏感信息，不要硬编码
- 如只需本地访问：`ports: - "127.0.0.1:8000:8000"`
- 定期更新镜像：`docker-compose pull && docker-compose up -d --build`

## 快速恢复

```bash
docker-compose ps
docker-compose logs
docker-compose restart
# 如果不行
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 代码回滚
```bash
git checkout <previous-commit>
docker-compose build --no-cache
docker-compose up -d
```

## 数据备份
```bash
docker cp goalcast-mcp-server:/app/data ./data-backup
```

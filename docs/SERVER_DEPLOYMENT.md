# 服务器部署 Docker MCP 完整指南

## 📋 部署前准备

### 前置条件
- 服务器已安装 Docker 和 Docker Compose
- 有服务器的 SSH 访问权限
- 已获取 API Keys（FootyStats 等）

---

## 🚀 部署步骤

### 步骤 1：克隆代码到服务器

```bash
# SSH 登录到服务器
ssh user@your-server-ip

# 进入合适的工作目录
cd /path/to/your/workspace

# 克隆代码
git clone <your-repo-url> Goalcast
cd Goalcast

# 或者如果是更新已有代码
git pull origin main
```

---

### 步骤 2：配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API Keys
nano .env
# 或者使用 vim/vi
vi .env
```

**编辑 `.env` 文件**：
```bash
# Environment variables
# Data Sources
FOOTYSTATS_API_KEY=你的_footystats_api_key
ODDS_API_KEY=你的_odds_api_key
OPENWEATHER_API_KEY=你的_openweather_api_key

# AI Analysis
ANTHROPIC_API_KEY=你的_anthropic_api_key

# Database
DATABASE_URL=sqlite:///data/db/goalcast.db
```

> ⚠️ **重要**：确保 `.env` 文件不会被提交到 Git（已在 `.gitignore` 中配置）

---

### 步骤 3：构建 Docker 镜像

```bash
# 构建镜像（首次构建可能需要几分钟）
docker-compose build

# 或者使用 --no-cache 确保全新构建
docker-compose build --no-cache
```

**构建过程**：
- 基于 Python 3.13 slim 镜像
- 安装项目依赖（requirements.txt）
- 安装 MCP 和 uvicorn
- 复制应用代码
- 配置运行环境

---

### 步骤 4：启动 Docker 容器

```bash
# 后台启动服务
docker-compose up -d

# 或者前台启动（可以看到实时日志，按 Ctrl+C 停止）
docker-compose up
```

**说明**：
- `-d` 参数表示后台运行（detached mode）
- 容器会在后台持续运行
- 服务会监听 8000 端口

---

### 步骤 5：验证服务状态

```bash
# 查看容器运行状态
docker-compose ps

# 查看服务日志
docker-compose logs -f

# 查看最近 50 行日志
docker-compose logs --tail=50

# 测试服务是否可访问
curl http://localhost:8000/sse

# 或者测试健康检查
curl http://localhost:8000/
```

**预期输出**：
```
NAME                  IMAGE                  COMMAND                  SERVICE      CREATED         STATUS          PORTS
goalcast-mcp-server   goalcast-mcp-server    "python mcp_server/s…"   mcp-server   2 minutes ago   Up 2 minutes    0.0.0.0:8000->8000/tcp
```

---

### 步骤 6：配置防火墙（如果需要远程访问）

如果你的 MCP 客户端不在同一台服务器上，需要开放端口：

```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 8000/tcp
sudo ufw status

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports

# AWS EC2
# 在安全组中添加入站规则：
# 类型：自定义 TCP
# 端口范围：8000
# 源：0.0.0.0/0 或特定 IP
```

---

### 步骤 7：配置 MCP 客户端

根据你的 MCP 客户端位置，选择相应的配置：

#### 场景 A：MCP 客户端在同一台服务器（本地连接）

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

#### 场景 B：MCP 客户端在远程（服务器部署，本地访问）

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

**替换说明**：
- `your-server-ip`：替换为你的服务器公网 IP
- 确保防火墙已开放 8000 端口

---

## 🔧 常用运维命令

### 查看服务状态

```bash
# 查看容器状态
docker-compose ps

# 查看详细信息
docker inspect goalcast-mcp-server

# 查看资源使用
docker stats goalcast-mcp-server
```

### 查看日志

```bash
# 实时日志
docker-compose logs -f

# 最近 100 行
docker-compose logs --tail=100

# 特定时间范围
docker-compose logs --since="2026-04-06"
docker-compose logs --until="2026-04-06T12:00:00"
```

### 重启服务

```bash
# 重启容器
docker-compose restart

# 或者先停止再启动
docker-compose stop
docker-compose start
```

### 停止服务

```bash
# 停止容器（保留数据）
docker-compose down

# 停止并删除容器和网络
docker-compose down

# 停止并删除所有（包括卷）
docker-compose down -v
```

### 更新代码

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建镜像
docker-compose build --no-cache

# 3. 重启容器
docker-compose up -d

# 4. 清理旧镜像
docker image prune -f
```

### 进入容器调试

```bash
# 进入容器的 bash shell
docker-compose exec mcp-server bash

# 在容器内执行命令
docker-compose exec mcp-server python --version
docker-compose exec mcp-server pip list
```

---

## 🔍 故障排查

### 问题 1：容器无法启动

**检查日志**：
```bash
docker-compose logs
```

**常见原因**：
- 端口被占用
- API Keys 配置错误
- 依赖安装失败

**解决方案**：
```bash
# 查看端口占用
lsof -i:8000

# 停止占用进程
kill -9 <PID>

# 重新构建
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

### 问题 2：服务启动后立即退出

**检查**：
```bash
docker-compose logs --tail=100
```

**可能原因**：
- Python 依赖缺失
- API Key 无效
- 代码错误

**解决方案**：
```bash
# 进入容器检查
docker-compose exec mcp-server bash

# 检查 Python 环境
python --version
pip list | grep mcp

# 测试运行
python mcp_server/server.py sse
```

---

### 问题 3：无法远程连接

**检查防火墙**：
```bash
# Ubuntu/Debian
sudo ufw status

# CentOS/RHEL
sudo firewall-cmd --list-all
```

**检查端口监听**：
```bash
# 在服务器上
netstat -tlnp | grep 8000
# 或
ss -tlnp | grep 8000
```

**测试连接**：
```bash
# 在客户端机器上
curl http://服务器IP:8000/sse
telnet 服务器IP 8000
```

---

### 问题 4：API 调用失败

**检查 .env 配置**：
```bash
docker-compose exec mcp-server env | grep API_KEY
```

**重新配置**：
```bash
# 编辑 .env
nano .env

# 重启容器
docker-compose restart
```

---

## 📊 性能优化

### 1. 资源限制

编辑 `docker-compose.yml`，添加：
```yaml
services:
  mcp-server:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 2. 日志轮转

编辑 `docker-compose.yml`，添加：
```yaml
services:
  mcp-server:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 3. 健康检查

编辑 `docker-compose.yml`，添加：
```yaml
services:
  mcp-server:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/sse"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

---

## 🔐 安全建议

### 1. 使用环境变量管理敏感信息

```bash
# ✅ 正确：使用 .env 文件
cp .env.example .env
nano .env

# ❌ 错误：硬编码在代码中
```

### 2. 限制 API 访问

如果只需要本地访问，修改 `docker-compose.yml`：
```yaml
ports:
  - "127.0.0.1:8000:8000"  # 只允许本地访问
```

### 3. 定期更新镜像

```bash
# 每月执行一次
docker-compose pull
docker-compose up -d --build
```

### 4. 监控资源使用

```bash
# 安装 watch 工具
watch -n 5 'docker stats --no-stream'

# 或者使用 docker-compose
docker-compose ps
```

---

## 📝 部署检查清单

部署完成后，逐项检查：

- [ ] 代码已 pull 到服务器
- [ ] `.env` 文件已配置并保存
- [ ] Docker 镜像构建成功
- [ ] 容器正在运行（`docker-compose ps`）
- [ ] 可以访问 `http://localhost:8000/sse`
- [ ] 日志正常（`docker-compose logs`）
- [ ] 防火墙已配置（如需远程访问）
- [ ] MCP 客户端配置正确
- [ ] 可以调用 MCP 工具

---

## 🆘 快速恢复指南

### 服务异常停止

```bash
# 1. 查看状态
docker-compose ps

# 2. 查看日志
docker-compose logs

# 3. 重启服务
docker-compose restart

# 4. 如果不行，重新构建
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 代码更新后回滚

```bash
# 1. 回滚代码
git checkout <previous-commit>

# 2. 重新构建
docker-compose build --no-cache

# 3. 重启
docker-compose up -d
```

### 数据备份

```bash
# 备份数据目录
docker cp goalcast-mcp-server:/app/data ./data-backup

# 或者使用 docker volume
docker run --rm -v goalcast_data:/data -v $(pwd):/backup alpine tar czf /backup/data-backup.tar.gz /data
```

---

## 📚 相关资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [项目 README](../README.md)
- [MCP 配置指南](./MCP_CONFIG_GUIDE.md)

---

## 🎯 部署完成后的下一步

1. **测试 MCP 工具**：在 MCP 客户端中调用工具
2. **监控服务**：设置日志监控和告警
3. **定期更新**：定期 pull 最新代码并重新构建
4. **备份配置**：备份 `.env` 文件和重要配置

---

**祝你部署顺利！** 🎉

如有问题，请查看故障排查部分或联系技术支持。

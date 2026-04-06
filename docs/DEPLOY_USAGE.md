# 部署脚本使用说明

## 🎯 统一部署工具

已将 `deploy_mcp.sh` 和 `quick_deploy.sh` 合并为统一的部署工具：

**脚本位置**: `scripts/goalcast-deploy.sh`

---

## 📋 快速开始

### 查看帮助
```bash
./scripts/goalcast-deploy.sh --help
```

### 检查配置状态
```bash
./scripts/goalcast-deploy.sh check
```

---

## 🚀 部署模式

### 模式 1：本地直接运行（开发环境）

```bash
./scripts/goalcast-deploy.sh deploy
```

**说明**:
- 直接在本地运行 Python 服务
- 绑定到 `0.0.0.0:8000`
- 自动生成 `mcporter.json` 配置
- 适合本地开发测试

**指定端口**:
```bash
./scripts/goalcast-deploy.sh deploy --port 9000
```

---

### 模式 2：Docker 部署（生产环境）

```bash
./scripts/goalcast-deploy.sh deploy --docker
```

**说明**:
- 构建并运行 Docker 容器
- 服务运行在 `http://localhost:8000`
- 自动生成 `mcporter.json` 配置
- 适合服务器部署

**指定端口**:
```bash
./scripts/goalcast-deploy.sh deploy --docker --port 9000
```

---

## 🔧 配置模式

### 场景 1：本地开发配置

```bash
./scripts/goalcast-deploy.sh config --local
```

**生成** `mcporter.json`:
```json
{
  "mcpServers": {
    "goalcast": {
      "command": "python3",
      "args": ["mcp_server/server.py"],
      "env": {"PYTHONPATH": "."},
      "cwd": "."
    }
  }
}
```

---

### 场景 2：远程服务器连接配置

```bash
./scripts/goalcast-deploy.sh config --remote --server 192.168.1.100 --port 8000
```

**生成** `mcporter.json`:
```json
{
  "mcpServers": {
    "goalcast": {
      "url": "http://192.168.1.100:8000/sse",
      "transport": "sse"
    }
  }
}
```

---

## 📊 完整使用场景

### 场景 A：在服务器上部署（Docker）

**步骤 1**: SSH 到服务器
```bash
ssh user@server-ip
```

**步骤 2**: 部署服务
```bash
cd /path/to/Goalcast
./scripts/goalcast-deploy.sh deploy --docker
```

**结果**:
- ✅ Docker 容器运行
- ✅ 服务监听 `http://localhost:8000`
- ✅ 自动生成 `mcporter.json`（本地连接配置）

**步骤 3**: （可选）配置防火墙
```bash
sudo ufw allow 8000/tcp
```

---

### 场景 B：本地电脑连接远程服务器

**在本地电脑上执行**:
```bash
cd /path/to/Goalcast
./scripts/goalcast-deploy.sh config --remote --server <服务器 IP> --port 8000
```

**结果**:
- ✅ 生成 `mcporter.json`
- ✅ 配置连接到远程服务器
- ✅ 可以在 Trae 中使用远程 MCP 服务

---

### 场景 C：本地开发

**方式 1**: 一键部署并配置
```bash
./scripts/goalcast-deploy.sh deploy
```

**方式 2**: 仅生成配置
```bash
./scripts/goalcast-deploy.sh config --local
```

---

## 🔍 参数说明

### 部署模式参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--docker` | 使用 Docker 部署 | 否 |
| `--port <PORT>` | 指定端口 | 8000 |
| `--host <HOST>` | 指定绑定主机 | 0.0.0.0 |

### 配置模式参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--local` | 本地开发配置 | 是 |
| `--remote` | 远程连接配置 | 否 |
| `--server <IP>` | 远程服务器 IP | 必需（--remote 模式） |
| `--port <PORT>` | 远程服务器端口 | 8000 |

---

## 📝 命令对比

### 旧方式（两个脚本）

```bash
# 部署
./scripts/quick_deploy.sh

# 配置
./scripts/deploy_mcp.sh local
./scripts/deploy_mcp.sh remote
```

### 新方式（一个脚本）

```bash
# 部署
./scripts/goalcast-deploy.sh deploy
./scripts/goalcast-deploy.sh deploy --docker

# 配置
./scripts/goalcast-deploy.sh config --local
./scripts/goalcast-deploy.sh config --remote --server 192.168.1.100

# 检查
./scripts/goalcast-deploy.sh check
```

---

## ✅ 优势

### 逻辑统一
- ✅ 部署时自动生成配置
- ✅ 配置与部署保持一致
- ✅ 避免配置和运行不同步

### 使用简单
- ✅ 一个脚本完成所有操作
- ✅ 清晰的命令结构
- ✅ 完善的帮助信息

### 灵活配置
- ✅ 支持本地和 Docker 部署
- ✅ 支持本地和远程配置
- ✅ 可自定义端口和主机

---

## 🆘 故障排查

### 服务无法启动

```bash
# 检查配置
./scripts/goalcast-deploy.sh check

# 查看详细日志
docker-compose logs -f
```

### 配置不生效

```bash
# 重新生成配置
./scripts/goalcast-deploy.sh config --local
# 或
./scripts/goalcast-deploy.sh config --remote --server <IP>
```

---

## 📚 相关文档

- [服务器部署指南](./SERVER_DEPLOYMENT.md)
- [快速入门](./DEPLOY_QUICK_START.md)
- [MCP 配置指南](./MCP_CONFIG_GUIDE.md)

---

**现在只需一个脚本，完成所有部署和配置工作！** 🎉

# 部署脚本使用说明

## 统一部署工具

已将 `deploy_mcp.sh` 和 `quick_deploy.sh` 合并为统一的部署工具：

**脚本位置**: `scripts/goalcast-deploy.sh`

## 快速开始

```bash
./scripts/goalcast-deploy.sh --help
./scripts/goalcast-deploy.sh check
```

## 部署模式

### 本地直接运行（开发环境）
```bash
./scripts/goalcast-deploy.sh deploy
./scripts/goalcast-deploy.sh deploy --port 9000
```

### Docker 部署（生产环境）
```bash
./scripts/goalcast-deploy.sh deploy --docker
./scripts/goalcast-deploy.sh deploy --docker --port 9000
```

## 配置模式

### 本地开发配置
```bash
./scripts/goalcast-deploy.sh config --local
```

### 远程服务器连接配置
```bash
./scripts/goalcast-deploy.sh config --remote --server 192.168.1.100 --port 8000
```

## 参数说明

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

## 命令映射

| 旧命令 | 新命令 |
|--------|--------|
| `./scripts/quick_deploy.sh` | `./scripts/goalcast-deploy.sh deploy --docker` |
| `./scripts/deploy_mcp.sh local` | `./scripts/goalcast-deploy.sh deploy` |
| `./scripts/deploy_mcp.sh docker` | `./scripts/goalcast-deploy.sh deploy --docker` |
| `./scripts/deploy_mcp.sh remote` | `./scripts/goalcast-deploy.sh config --remote --server <IP>` |

## 使用场景

### 服务器部署（Docker）
```bash
ssh user@server-ip
cd /path/to/Goalcast
./scripts/goalcast-deploy.sh deploy --docker
```

### 本地连接远程服务器
```bash
./scripts/goalcast-deploy.sh config --remote --server <服务器 IP> --port 8000
```

### 本地开发
```bash
./scripts/goalcast-deploy.sh deploy
```

## 故障排查
```bash
./scripts/goalcast-deploy.sh check
docker-compose logs -f
./scripts/goalcast-deploy.sh config --local
```

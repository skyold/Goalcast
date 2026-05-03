# Deploy Documentation

Goalcast 部署和运维文档。

## Quick Start

- [Quick Start Guide](QUICK_START.md) - 服务器部署 MCP 快速指南（5 步完成）

## Docker

- [Docker Complete Guide](DOCKER_GUIDE.md) - Docker 部署完整指南（运维、安全、性能优化）
- [Docker Build Troubleshooting](DOCKER_BUILD_TROUBLESHOOTING.md) - 构建故障排查（Python/依赖版本问题）
- [Docker Network Timeout](DOCKER_NETWORK_TIMEOUT.md) - 中国大陆 pip 镜像源配置

## Tools

- [Deploy Tool Usage](USAGE.md) - `goalcast-deploy.sh` 统一部署工具使用说明

## Quick Reference

### 本地开发
```bash
./scripts/goalcast-deploy.sh deploy
```

### Docker 部署
```bash
./scripts/goalcast-deploy.sh deploy --docker
```

### 远程连接配置
```bash
./scripts/goalcast-deploy.sh config --remote --server <IP> --port 8000
```

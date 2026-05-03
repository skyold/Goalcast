# 部署脚本合并说明

## 合并原因

### 原有问题

之前使用两个脚本：
- `scripts/deploy_mcp.sh` - 生成配置
- `scripts/quick_deploy.sh` - 部署服务

**存在的问题**:
1. 配置与运行分离 - 可能生成本地配置但部署到服务器
2. 逻辑不连贯 - 不运行服务却生成配置
3. 容易混淆 - 两个脚本功能重叠，用户不知道用哪个
4. 同步问题 - 配置修改后忘记重新部署

## 统一解决方案

### 新脚本：`scripts/goalcast-deploy.sh`

**设计理念**:
- 配置跟随部署 - 部署时自动生成相应配置
- 逻辑统一 - 一个脚本完成所有操作
- 清晰分离 - 通过模式参数区分不同场景

## 功能对比

### 旧方式（两个脚本）

```bash
# 部署脚本
./scripts/quick_deploy.sh
# → 构建 Docker
# → 启动容器
# → 验证服务

# 配置脚本（需要单独运行）
./scripts/deploy_mcp.sh local
# → 生成 mcporter.json
```

**问题**: 部署和配置可能不一致

### 新方式（一个脚本）

```bash
# 部署并自动生成配置
./scripts/goalcast-deploy.sh deploy --docker
# → 检查依赖
# → 构建 Docker
# → 启动容器
# → 验证服务
# → 自动生成匹配的 mcporter.json
```

**优势**: 配置与部署自动同步

## 使用方式

### 场景 1：在服务器上部署（Docker）

**旧方式**:
```bash
# 步骤 1：部署
./scripts/quick_deploy.sh

# 步骤 2：配置（容易忘记或混淆）
./scripts/deploy_mcp.sh local
```

**新方式**:
```bash
./scripts/goalcast-deploy.sh deploy --docker
# 自动完成部署 + 配置
```

### 场景 2：本地开发

**旧方式**:
```bash
./scripts/deploy_mcp.sh local
# 然后手动启动服务...
```

**新方式**:
```bash
./scripts/goalcast-deploy.sh deploy
# 自动启动服务 + 生成配置
```

### 场景 3：仅生成配置（不部署）

**旧方式**:
```bash
./scripts/deploy_mcp.sh remote --server 192.168.1.100
```

**新方式**:
```bash
./scripts/goalcast-deploy.sh config --remote --server 192.168.1.100
# 保持独立配置功能
```

## 命令映射

| 旧命令 | 新命令 |
|--------|--------|
| `./scripts/quick_deploy.sh` | `./scripts/goalcast-deploy.sh deploy --docker` |
| `./scripts/deploy_mcp.sh local` | `./scripts/goalcast-deploy.sh deploy` 或 `config --local` |
| `./scripts/deploy_mcp.sh docker` | `./scripts/goalcast-deploy.sh deploy --docker` |
| `./scripts/deploy_mcp.sh remote` | `./scripts/goalcast-deploy.sh config --remote --server <IP>` |
| `./scripts/deploy_mcp.sh check` | `./scripts/goalcast-deploy.sh check` |

## 核心改进

### 1. 自动配置同步

**部署时自动生成匹配的配置**:
```bash
./scripts/goalcast-deploy.sh deploy --docker --port 9000
# 生成的 mcporter.json 自动使用 localhost:9000
```

### 2. 逻辑一致性

**配置模式与部署模式匹配**:
- `deploy` → 自动调用 `config --local`
- `deploy --docker` → 自动调用 `config --local`
- 可以独立使用 `config` 命令

### 3. 清晰的参数系统

```bash
# 部署模式
deploy [--docker] [--port PORT] [--host HOST]

# 配置模式
config [--local|--remote --server IP] [--port PORT]

# 检查模式
check
```

## 实际使用示例

### 示例 1：服务器部署完整流程

```bash
# 1. SSH 到服务器
ssh user@server-ip

# 2. 部署服务（自动配置）
cd /path/to/Goalcast
./scripts/goalcast-deploy.sh deploy --docker

# 结果:
# - Docker 容器运行
# - 服务监听 http://localhost:8000
# - mcporter.json 配置为本地连接
```

### 示例 2：本地连接远程服务器

```bash
# 1. 在服务器上部署
# （服务器执行）
./scripts/goalcast-deploy.sh deploy --docker --port 8000

# 2. 在本地电脑上配置远程连接
# （本地电脑执行）
./scripts/goalcast-deploy.sh config --remote --server <服务器 IP> --port 8000

# 结果:
# - mcporter.json 配置为连接远程服务器
# - Trae 可以连接并使用远程 MCP 服务
```

### 示例 3：本地开发

```bash
# 一键完成
./scripts/goalcast-deploy.sh deploy

# 或分开执行
./scripts/goalcast-deploy.sh config --local
# 然后手动启动服务...
```

## 优势总结

| 方面 | 旧方式 | 新方式 |
|------|--------|--------|
| **脚本数量** | 2 个 | 1 个 |
| **配置同步** | 手动 | 自动 |
| **学习成本** | 需要理解两个脚本 | 一个脚本多个模式 |
| **出错概率** | 高（容易忘记配置） | 低（自动配置） |
| **逻辑一致性** | 分离 | 统一 |
| **灵活性** | 一般 | 更高 |

## 迁移指南

### 保留旧脚本（向后兼容）

旧的脚本仍然保留，但建议迁移到新脚本：

```bash
# 旧脚本（保留但不再推荐）
./scripts/quick_deploy.sh
./scripts/deploy_mcp.sh

# 新脚本（推荐）
./scripts/goalcast-deploy.sh
```

### 迁移步骤

1. **更新文档** - 使用新脚本命令
2. **团队培训** - 说明新脚本的优势
3. **逐步替换** - 在 CI/CD 中使用新脚本

## 相关文档

- [使用指南](../deploy/USAGE.md) - 详细使用说明
- 帮助信息 - `./scripts/goalcast-deploy.sh --help`

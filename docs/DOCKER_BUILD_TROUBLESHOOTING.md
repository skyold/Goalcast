# Docker 构建故障排查

## ❌ 问题描述

在 Ubuntu 服务器上构建 Docker 镜像时失败：

```bash
ERROR: No matching distribution found for sqlalchemy==2.0.35
```

## 🔍 根本原因

1. **SQLAlchemy 版本问题** - `sqlalchemy==2.0.35` 在 PyPI 上不存在
2. **Python 版本过新** - Python 3.13 可能导致某些包兼容性差

## ✅ 解决方案

### 修复 1：更新 requirements.txt

**问题**：
```txt
sqlalchemy==2.0.35  # ❌ 此版本不存在
```

**修复**：
```txt
sqlalchemy>=2.0.0   # ✅ 使用版本范围
```

**说明**：
- 使用 `>=` 允许 pip 安装最新兼容版本
- 避免硬编码具体版本号（除非绝对必要）

---

### 修复 2：降级 Python 版本

**问题**：
```dockerfile
FROM python:3.13-slim  # ❌ Python 3.13 太新，包兼容性差
```

**修复**：
```dockerfile
FROM python:3.11-slim  # ✅ Python 3.11 稳定，兼容性好
```

**说明**：
- Python 3.11 是当前最稳定的生产版本
- 大多数包对 Python 3.11 支持最好
- Python 3.13 可能还没有完整的包支持

---

## 🚀 重新构建

修复后，在服务器上重新构建：

```bash
# 1. 拉取最新代码
cd ~/goalcast
git pull

# 2. 清理旧镜像（可选）
docker-compose down
docker rmi goalcast-mcp-server 2>/dev/null || true

# 3. 重新构建
docker-compose build --no-cache

# 4. 启动服务
docker-compose up -d

# 5. 查看状态
docker-compose ps
docker-compose logs -f
```

---

## 📝 最佳实践

### 1. requirements.txt 版本管理

**❌ 不推荐**：
```txt
package==1.2.3  # 硬编码具体版本
```

**✅ 推荐**：
```txt
package>=1.2.0  # 使用最小版本要求
package~=1.2.0  # 或兼容版本
```

### 2. Docker Python 版本选择

| Python 版本 | 推荐度 | 说明 |
|------------|--------|------|
| 3.11 | ✅ 强烈推荐 | 稳定，兼容性好 |
| 3.10 | ✅ 推荐 | 稳定，广泛使用 |
| 3.12 | ⚠️ 可用 | 较新，部分包可能不兼容 |
| 3.13 | ❌ 不推荐 | 太新，包支持不完善 |

### 3. 构建优化

```dockerfile
# 分开安装依赖和复制代码
# 利用 Docker 层缓存

# 步骤 1：安装依赖（变化少）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 步骤 2：复制代码（变化多）
COPY . .
```

---

## 🔧 常见构建错误及解决方案

### 错误 1：包版本不存在

```bash
ERROR: No matching distribution found for package==x.y.z
```

**解决**：
```txt
# 使用版本范围
package>=x.y.0
```

---

### 错误 2：连接超时

```bash
WARNING: Connection timed out while downloading.
```

**解决**：
```dockerfile
# 使用国内镜像（如果在海外服务器）
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

### 错误 3：权限问题

```bash
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```

**解决**：
```dockerfile
# 使用 --user 或升级 pip
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
```

---

### 错误 4：内存不足

```bash
Killed
```

**解决**：
```bash
# 增加服务器内存或添加 swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📊 完整构建流程

```bash
# 1. 准备环境
cd ~/goalcast

# 2. 停止旧服务
docker-compose down

# 3. 清理旧镜像
docker system prune -f

# 4. 构建新镜像
docker-compose build --no-cache

# 5. 启动服务
docker-compose up -d

# 6. 验证
docker-compose ps
docker-compose logs --tail=50

# 7. 测试连接
curl http://localhost:8000/sse
```

---

## ✅ 验证清单

构建完成后检查：

- [ ] Docker 镜像构建成功
- [ ] 容器正在运行
- [ ] 服务监听 8000 端口
- [ ] 可以访问 `http://localhost:8000/sse`
- [ ] 日志没有错误
- [ ] MCP 工具可以调用

---

## 📚 相关资源

- [SQLAlchemy 版本历史](https://pypi.org/project/SQLAlchemy/#history)
- [Docker 最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Python 版本选择](https://devguide.python.org/versions/)

---

**修复完成！现在应该可以成功构建了！** 🎉

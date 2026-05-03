# Docker 构建故障排查

## 问题描述

在 Ubuntu 服务器上构建 Docker 镜像时失败：

```bash
ERROR: No matching distribution found for sqlalchemy==2.0.35
```

## 根本原因

1. **SQLAlchemy 版本问题** - `sqlalchemy==2.0.35` 在 PyPI 上不存在
2. **Python 版本过新** - Python 3.13 可能导致某些包兼容性差

## 解决方案

### 修复 1：更新 requirements.txt

```txt
# 问题
sqlalchemy==2.0.35  # 此版本不存在

# 修复
sqlalchemy>=2.0.0   # 使用版本范围
```

### 修复 2：降级 Python 版本

```dockerfile
# 问题
FROM python:3.13-slim  # Python 3.13 太新

# 修复
FROM python:3.11-slim  # Python 3.11 稳定，兼容性好
```

## Python 版本推荐

| Python 版本 | 推荐度 | 说明 |
|------------|--------|------|
| 3.11 | 强烈推荐 | 稳定，兼容性好 |
| 3.10 | 推荐 | 稳定，广泛使用 |
| 3.12 | 可用 | 较新，部分包可能不兼容 |
| 3.13 | 不推荐 | 太新，包支持不完善 |

## 常见构建错误

### 包版本不存在
```txt
# 使用版本范围
package>=x.y.0
```

### 连接超时
```dockerfile
# 使用国内镜像
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 权限问题
```dockerfile
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
```

### 内存不足
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 重新构建

```bash
cd ~/goalcast
docker-compose down
docker system prune -f
docker-compose build --no-cache
docker-compose up -d
docker-compose ps
docker-compose logs --tail=50
curl http://localhost:8000/sse
```

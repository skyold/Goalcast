# Docker 网络超时故障排查

## ❌ 问题描述

在中国大陆的服务器上构建 Docker 镜像时，pip 安装依赖超时：

```bash
TimeoutError: The read operation timed out
```

## 🔍 根本原因

**PyPI 官方源在国外** - `pypi.org` 服务器在海外，中国大陆访问速度慢且不稳定。

## ✅ 解决方案

### 方案 1：使用清华大学镜像源（推荐）

**修改 Dockerfile**：
```dockerfile
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    httpx[asyncio]==0.27.0 \
    loguru==0.7.2 \
    python-dotenv==1.0.1 \
    mcp \
    uvicorn
```

**优势**：
- ✅ 国内访问速度快
- ✅ 镜像源稳定可靠
- ✅ 清华大学维护

---

### 方案 2：使用其他国内镜像源

如果清华源不可用，可以切换到其他镜像源：

| 镜像源 | 地址 |
|--------|------|
| 清华大学 | `https://pypi.tuna.tsinghua.edu.cn/simple` |
| 中国科学技术大学 | `https://pypi.mirrors.ustc.edu.cn/simple/` |
| 阿里云 | `https://mirrors.aliyun.com/pypi/simple/` |
| 豆瓣 | `https://pypi.douban.com/simple/` |

**切换方法**：
```dockerfile
RUN pip install --no-cache-dir \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    httpx[asyncio]==0.27.0 \
    loguru==0.7.2 \
    python-dotenv==1.0.1 \
    mcp \
    uvicorn
```

---

### 方案 3：配置 pip 全局镜像源

在 Dockerfile 中创建 pip 配置文件：

```dockerfile
# 创建 pip 配置
RUN mkdir -p /root/.pip && \
    echo "[global]" > /root/.pip/pip.conf && \
    echo "index-url = https://pypi.tuna.tsinghua.edu.cn/simple" >> /root/.pip/pip.conf

# 然后正常安装
RUN pip install --no-cache-dir \
    httpx[asyncio]==0.27.0 \
    loguru==0.7.2 \
    python-dotenv==1.0.1 \
    mcp \
    uvicorn
```

---

## 🚀 重新构建步骤

### 1. 拉取最新代码

```bash
cd ~/goalcast
git pull
```

### 2. 清理旧镜像

```bash
docker-compose down
docker rmi goalcast-mcp-server 2>/dev/null || true
```

### 3. 重新构建（使用国内镜像源）

```bash
docker-compose build --no-cache
```

**预期输出**：
```bash
[+] Building 15.2s (13/13) FINISHED
 => [internal] load build definition from Dockerfile
 => [1/5] FROM docker.io/library/python:3.11-slim
 => [2/5] WORKDIR /app
 => [3/5] COPY requirements.txt .
 => [4/5] RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple ...
 => => Downloading httpx-0.27.0... (快速)
 => => Downloading loguru-0.7.2... (快速)
 => => Downloading python-dotenv-1.0.1... (快速)
 => [5/5] COPY . .
 => exporting to image
```

### 4. 启动服务

```bash
docker-compose up -d
```

### 5. 验证

```bash
docker-compose ps
docker-compose logs -f
```

---

## 📊 速度对比

| 镜像源 | 下载速度 | 稳定性 |
|--------|---------|--------|
| PyPI 官方 | ~50 KB/s | ❌ 经常超时 |
| 清华大学 | ~5 MB/s | ✅ 非常稳定 |
| 阿里云 | ~3 MB/s | ✅ 稳定 |
| 豆瓣 | ~2 MB/s | ✅ 稳定 |

**构建时间对比**：
- PyPI 官方：5-10 分钟（可能失败）
- 清华大学：1-2 分钟（稳定）

---

## 🔧 其他优化建议

### 1. 使用 --no-cache-dir

已经在 Dockerfile 中使用，避免缓存占用空间。

### 2. 合并 pip 安装命令

```dockerfile
# ❌ 不推荐：多次调用 pip
RUN pip install httpx
RUN pip install loguru
RUN pip install python-dotenv

# ✅ 推荐：一次安装所有
RUN pip install httpx loguru python-dotenv
```

### 3. 指定版本范围

```dockerfile
# ❌ 太严格：可能下载慢
RUN pip install httpx==0.27.0

# ✅ 更灵活：允许小版本更新
RUN pip install "httpx>=0.27.0,<1.0.0"
```

---

## 🆘 常见问题

### Q1: 镜像源不可用怎么办？

**解决**：切换到其他镜像源
```dockerfile
# 清华源不可用时，切换到阿里云
-i https://mirrors.aliyun.com/pypi/simple/
```

### Q2: 还是超时怎么办？

**解决**：增加 pip 超时时间
```dockerfile
RUN pip install --default-timeout=100 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    httpx[asyncio]==0.27.0 \
    loguru==0.7.2 \
    python-dotenv==1.0.1 \
    mcp \
    uvicorn
```

### Q3: 如何在本地测试 Dockerfile？

**解决**：在本地构建测试
```bash
# 本地构建
docker build -t goalcast-test .

# 查看构建日志
docker build -t goalcast-test . --progress=plain
```

---

## 📝 完整 Dockerfile（已优化）

```dockerfile
# Use Python 3.11 for better package compatibility
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies using Tsinghua mirror for better speed in China
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    httpx[asyncio]==0.27.0 \
    loguru==0.7.2 \
    python-dotenv==1.0.1 \
    mcp \
    uvicorn

# Copy the rest of the application code into the container
COPY . .

# Set environment variables
ENV PYTHONPATH=/app

# Expose the port the app runs on
EXPOSE 8000

# Run the MCP server using SSE (Server-Sent Events) transport
CMD ["python", "mcp_server/server.py", "sse"]
```

---

## ✅ 验证清单

构建完成后检查：

- [ ] 使用国内镜像源
- [ ] 构建过程无超时错误
- [ ] 镜像成功创建
- [ ] 容器正常启动
- [ ] 服务可以访问
- [ ] 日志无错误

---

## 📚 相关资源

- [清华大学开源软件镜像站](https://mirrors.tuna.tsinghua.edu.cn/)
- [PyPI 镜像使用指南](https://help.mirrors.tuna.tsinghua.edu.cn/pypi/)
- [Docker 最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

---

**已修复！现在应该可以快速成功构建了！** 🎉

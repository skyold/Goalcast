# Docker 网络超时故障排查

## 问题描述

在中国大陆的服务器上构建 Docker 镜像时，pip 安装依赖超时：

```bash
TimeoutError: The read operation timed out
```

## 根本原因

PyPI 官方源在国外，中国大陆访问速度慢且不稳定。

## 解决方案

### 方案 1：使用清华大学镜像源（推荐）

```dockerfile
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    httpx[asyncio]==0.27.0 \
    loguru==0.7.2 \
    python-dotenv==1.0.1 \
    mcp \
    uvicorn
```

### 方案 2：其他国内镜像源

| 镜像源 | 地址 |
|--------|------|
| 清华大学 | `https://pypi.tuna.tsinghua.edu.cn/simple` |
| 中国科学技术大学 | `https://pypi.mirrors.ustc.edu.cn/simple/` |
| 阿里云 | `https://mirrors.aliyun.com/pypi/simple/` |
| 豆瓣 | `https://pypi.douban.com/simple/` |

### 方案 3：配置 pip 全局镜像源

```dockerfile
RUN mkdir -p /root/.pip && \
    echo "[global]" > /root/.pip/pip.conf && \
    echo "index-url = https://pypi.tuna.tsinghua.edu.cn/simple" >> /root/.pip/pip.conf
```

## 速度对比

| 镜像源 | 下载速度 | 稳定性 |
|--------|---------|--------|
| PyPI 官方 | ~50 KB/s | 经常超时 |
| 清华大学 | ~5 MB/s | 非常稳定 |
| 阿里云 | ~3 MB/s | 稳定 |

## 完整优化后的 Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    httpx[asyncio]==0.27.0 \
    loguru==0.7.2 \
    python-dotenv==1.0.1 \
    mcp \
    uvicorn
COPY . .
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["python", "mcp_server/server.py", "sse"]
```

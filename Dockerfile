# ─────────────────────────────────────────────────────────────────────────────
# Goalcast Backend Dockerfile
# ─────────────────────────────────────────────────────────────────────────────
#
# 默认运行：无限循环分析模式（每小时自动获取并分析比赛）
#   docker run goalcast/backend:latest
#
# 单次运行：
#   docker run goalcast/backend:latest run --leagues 英超 --date 2026-05-03
#
# 查看所有命令：
#   docker run goalcast/backend:latest --help
#
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt \
    mcp \
    uvicorn

COPY backend/ .

ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "-m", "main", "run", "--infinite", "--cooldown", "3600"]

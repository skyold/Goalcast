FROM python:3.12-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    "fastapi>=0.111" \
    "uvicorn[standard]>=0.30" \
    "aiosqlite>=0.20" \
    "httpx>=0.27" \
    "apscheduler>=3.10" \
    "pydantic-settings>=2.3"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

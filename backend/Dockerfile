FROM python:3.12-slim
WORKDIR /app

# Keep this list aligned with pyproject.toml `[project] dependencies`.
# A `pip install .` from pyproject.toml is cleaner in theory but hatchling
# fails on the current flat-layout source (no proper package dir), so we list
# deps explicitly here.
RUN pip install --no-cache-dir \
    "fastapi>=0.111" \
    "uvicorn[standard]>=0.30" \
    "aiosqlite>=0.20" \
    "httpx>=0.27" \
    "apscheduler>=3.10" \
    "pydantic-settings>=2.3" \
    "python-jose[cryptography]>=3.3" \
    "passlib[bcrypt]>=1.7" \
    "bcrypt>=4.0,<5.0" \
    "python-multipart>=0.0.9" \
    "email-validator>=2.0"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

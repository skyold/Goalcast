# Use Python 3.11 for better package compatibility
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies using Tsinghua mirror for better speed in China
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt \
    mcp \
    uvicorn

# Copy the rest of the application code into the container
COPY . .

# Set environment variables
ENV PYTHONPATH=/app

# Expose the port the app runs on
EXPOSE 8000

# Run the FastAPI Web Server with WebSocket support
CMD ["uvicorn", "agents.web.server:app", "--host", "0.0.0.0", "--port", "8000"]

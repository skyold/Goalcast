# Use Python 3.11 for better package compatibility
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install only core dependencies (skip optional ones)
# Core: httpx, loguru, python-dotenv
RUN pip install --no-cache-dir \
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

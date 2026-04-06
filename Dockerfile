# Use Python 3.11 for better package compatibility
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt mcp uvicorn

# Copy the rest of the application code into the container
COPY . .

# Set environment variables
ENV PYTHONPATH=/app

# Expose the port the app runs on
EXPOSE 8000

# Run the MCP server using SSE (Server-Sent Events) transport
CMD ["python", "mcp_server/server.py", "sse"]

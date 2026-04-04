# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt mcp uvicorn

# Copy the rest of the application code into the container
COPY . .

# Set environment variables
ENV PYTHONPATH=/app

# Expose the port the app runs on
EXPOSE 8000

# Run the MCP server using SSE (Server-Sent Events) transport
# Default to running as a web server on port 8000
CMD ["python", "mcp_server/server.py", "sse"]

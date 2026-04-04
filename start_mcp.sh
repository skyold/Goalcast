#!/bin/bash
# 快速启动 MCP 服务器（SSE 模式）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 激活虚拟环境
source .venv/bin/activate

# 设置 PYTHONPATH
export PYTHONPATH="$SCRIPT_DIR"

# 启动服务器
echo "🚀 Starting MCP Server in SSE mode..."
echo "📍 URL: http://localhost:8000/sse"
echo "💡 Press CTRL+C to stop"
echo ""

python mcp_server/server.py sse

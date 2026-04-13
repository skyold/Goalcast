#!/usr/bin/env bash
# 本地 MCP Server 启动脚本（stdio 模式，供 Claude Code 调用）
# 自动加载 .env，确保 API Key 可用

set -a
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 加载 .env
if [ -f "$PROJECT_DIR/.env" ]; then
  source "$PROJECT_DIR/.env"
fi
set +a

# 设置 PYTHONPATH
export PYTHONPATH="$PROJECT_DIR:$PROJECT_DIR/mcp_server:${PYTHONPATH}"

# 启动 MCP server（stdio 模式）
exec "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/mcp_server/server.py"

#!/usr/bin/env bash
# goalcast.sh — Goalcast 统一管理脚本
#
# 用法:
#   scripts/goalcast.sh start                        # stdio 模式（.mcp.json 自动调用）
#   scripts/goalcast.sh deploy [--port N]            # SSE 前台运行（调试）
#   scripts/goalcast.sh deploy --docker [--port N]   # Docker 后台部署
#   scripts/goalcast.sh config                       # 客户端：stdio 配置（.mcp.json）
#   scripts/goalcast.sh config --server <IP> [--port N]  # 客户端：SSE 配置（mcporter.json）
#   scripts/goalcast.sh check                        # 检查环境和服务状态
#   scripts/goalcast.sh help                         # 显示帮助

set -euo pipefail

# ── 路径 ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
SERVER_ENTRY="$PROJECT_ROOT/mcp_server/server.py"
ENV_FILE="$PROJECT_ROOT/.env"
WATCHLIST="$PROJECT_ROOT/config/watchlist.yaml"

# ── 颜色 ──────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()      { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
err()     { echo -e "${RED}[✗]${NC} $*" >&2; }
section() { echo -e "\n${BOLD}$*${NC}"; }

# ── 帮助 ──────────────────────────────────────────────────────────────
show_help() {
    cat << EOF
${BOLD}Goalcast 统一管理脚本${NC}

${BLUE}用法:${NC}
  $(basename "$0") <命令> [选项]

${BLUE}命令:${NC}
  ${BOLD}start${NC}                   stdio 模式（.mcp.json 专用，Claude Code 自动调用）
  ${BOLD}deploy${NC}                  SSE 前台启动（调试用，Ctrl+C 停止）
  ${BOLD}deploy --docker${NC}         Docker 后台部署（自动生成 mcporter.json）
  ${BOLD}config${NC}                  生成客户端 stdio 配置（.mcp.json）
  ${BOLD}config --server <IP>${NC}    生成客户端 SSE 配置（mcporter.json）
  ${BOLD}check${NC}                   检查环境、Docker、服务状态
  ${BOLD}help${NC}                    显示此帮助

${BLUE}deploy 选项:${NC}
  --docker              Docker Compose 后台部署
  --port <PORT>         绑定端口（默认：8000）
  --host <HOST>         绑定主机（默认：0.0.0.0）

${BLUE}config 选项:${NC}
  （无）                stdio 配置，生成 .mcp.json（无网络直连）
  --server <IP>         SSE 配置，生成 mcporter.json，连接 http://<IP>:PORT/sse
  --port <PORT>         SSE 端口（默认：8000）

${BLUE}config --server 的 IP 填什么:${NC}
  127.0.0.1 / localhost   Docker 和 Claude Code 在同一台机器
  <服务器公网 IP>          Docker 在远端服务器，Claude Code 在本地 Mac

${BLUE}部署场景速查:${NC}

  ${BOLD}场景 A — 本地开发（stdio，无 Docker）${NC}
    .mcp.json 已配置好，Claude Code 自动调用，无需手动操作
    手动测试：$(basename "$0") start

  ${BOLD}场景 B — 本地 Docker + 本地 Claude Code${NC}
    $(basename "$0") deploy --docker               # 启动 Docker
    $(basename "$0") config --server 127.0.0.1    # 生成 mcporter.json

  ${BOLD}场景 C — 远端 Docker + 本地 Claude Code${NC}
    # 在远端服务器上：
    $(basename "$0") deploy --docker
    # 在本地 Mac 上：
    $(basename "$0") config --server 81.70.207.129

  $(basename "$0") check                           # 任何场景下检查状态
EOF
}

# ── 公共：加载环境 ─────────────────────────────────────────────────────
load_env() {
    # 以 set -a 方式加载 .env，让所有变量自动导出
    if [ -f "$ENV_FILE" ]; then
        set -a
        # shellcheck disable=SC1090
        source "$ENV_FILE"
        set +a
    else
        warn ".env 不存在，API Key 可能未配置"
    fi
}

# ── 公共：设置 PYTHONPATH ─────────────────────────────────────────────
setup_pythonpath() {
    export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/mcp_server${PYTHONPATH:+:$PYTHONPATH}"
}

# ── 公共：选择 Python 解释器 ──────────────────────────────────────────
pick_python() {
    if [ -x "$VENV_PYTHON" ]; then
        echo "$VENV_PYTHON"
    elif command -v python3 &>/dev/null; then
        echo "python3"
    else
        err "找不到 Python。请先创建 venv：python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
        exit 1
    fi
}

# ── 命令：start（stdio 模式，.mcp.json 专用）─────────────────────────
cmd_start() {
    load_env
    setup_pythonpath
    PYTHON="$(pick_python)"
    # exec 替换当前进程（保持 stdio 管道干净，FastMCP stdio 要求）
    exec "$PYTHON" "$SERVER_ENTRY"
}

# ── 命令：deploy（SSE 模式本地运行）─────────────────────────────────
cmd_deploy_native() {
    local port="${1:-8000}" host="${2:-0.0.0.0}"

    section "本地 SSE 部署"
    _check_env_file
    load_env
    setup_pythonpath

    PYTHON="$(pick_python)"
    ok "Python: $($PYTHON --version)"
    info "启动地址：http://${host}:${port}/sse"
    warn "按 Ctrl+C 停止"
    echo ""

    export FASTMCP_HOST="$host"
    export FASTMCP_PORT="$port"
    "$PYTHON" "$SERVER_ENTRY" sse
}

# ── 命令：deploy --docker ────────────────────────────────────────────
cmd_deploy_docker() {
    local port="${1:-8000}" host="${2:-0.0.0.0}"

    section "Docker 部署"
    _check_env_file
    _check_docker

    cd "$PROJECT_ROOT"

    info "构建 Docker 镜像..."
    docker-compose build
    ok "镜像构建完成"

    info "启动容器..."
    FASTMCP_HOST="$host" FASTMCP_PORT="$port" docker-compose up -d

    info "等待服务就绪..."
    local attempts=0
    until curl -s --max-time 2 "http://localhost:${port}/sse" >/dev/null 2>&1 || [ $attempts -ge 10 ]; do
        sleep 2; attempts=$((attempts + 1))
    done

    docker-compose ps
    echo ""

    if curl -s --max-time 3 "http://localhost:${port}/sse" >/dev/null 2>&1; then
        ok "服务可访问：http://localhost:${port}/sse"
    else
        warn "服务未响应，查看日志：docker-compose logs -f"
    fi

    local server_ip
    server_ip="$(hostname -I 2>/dev/null | awk '{print $1}' || echo '<服务器IP>')"

    # 自动生成 SSE localhost 配置（场景 B：Docker 与 Claude Code 同机）
    _gen_sse_config "localhost" "$port"
    ok "已生成 mcporter.json → http://localhost:${port}/sse"

    section "部署完成"
    info "本地访问：http://localhost:${port}/sse"
    info "外网访问：http://${server_ip}:${port}/sse"
    echo ""
    info "如需从其他机器连接，在那台机器上执行："
    echo "  $(basename "$0") config --remote --server ${server_ip} --port ${port}"
    echo ""
    info "常用命令："
    echo "  docker-compose ps          # 查看状态"
    echo "  docker-compose logs -f     # 查看日志"
    echo "  docker-compose restart     # 重启"
    echo "  docker-compose down        # 停止"
}

# ── 命令：config ─────────────────────────────────────────────────────
# 只有两种：无 --server（stdio），有 --server（SSE）
# SSE 的 IP 填什么由调用者决定：127.0.0.1 = 本机 Docker，公网 IP = 远端服务器
cmd_config() {
    local server_ip="${1:-}" port="${2:-8000}"

    section "生成 MCP 客户端配置"
    cd "$PROJECT_ROOT"

    if [ -z "$server_ip" ]; then
        # stdio 模式：无网络，server.py 与 Claude Code 同机直连
        cat > .mcp.json << EOF
{
  "mcpServers": {
    "goalcast-local": {
      "type": "stdio",
      "command": "$PROJECT_ROOT/scripts/goalcast.sh",
      "args": ["start"]
    }
  }
}
EOF
        ok "已生成 .mcp.json（stdio 配置）"
        info "Claude Code / Cowork 重启后自动加载"

    else
        # SSE 模式：通过网络连接，IP 可以是 127.0.0.1 或公网地址
        cat > mcporter.json << EOF
{
  "mcpServers": {
    "goalcast": {
      "url": "http://${server_ip}:${port}/sse",
      "transport": "sse"
    }
  }
}
EOF
        ok "已生成 mcporter.json → http://${server_ip}:${port}/sse"
        [ "$server_ip" = "127.0.0.1" ] || [ "$server_ip" = "localhost" ] \
            && info "场景：本地 Docker + 本地 Claude Code" \
            || { info "场景：远端 Docker + 本地 Claude Code"; warn "确认服务器防火墙已放行端口 ${port}"; }
    fi
}

# ── 命令：check ──────────────────────────────────────────────────────
cmd_check() {
    section "环境检查"
    cd "$PROJECT_ROOT"

    # Python
    if [ -x "$VENV_PYTHON" ]; then
        ok "venv Python: $($VENV_PYTHON --version)"
    elif command -v python3 &>/dev/null; then
        warn "未找到 .venv，使用系统 Python: $(python3 --version)"
    else
        err "Python 未安装"
    fi

    # .env
    if [ -f "$ENV_FILE" ]; then
        ok ".env 存在"
        # 检查关键 Key 是否设置（不打印值）
        local missing=()
        grep -q "SPORTMONKS_API_KEY=.\+" "$ENV_FILE" || missing+=("SPORTMONKS_API_KEY")
        grep -q "FOOTYSTATS_API_KEY=.\+" "$ENV_FILE"  || missing+=("FOOTYSTATS_API_KEY")
        [ ${#missing[@]} -eq 0 ] && ok "API Keys 已配置" || warn "未配置：${missing[*]}"
    else
        err ".env 不存在（cp .env.example .env 创建）"
    fi

    # .mcp.json
    if [ -f ".mcp.json" ]; then
        ok ".mcp.json 存在"
    else
        warn ".mcp.json 不存在（运行 config 生成）"
    fi

    # Docker
    section "Docker 状态"
    if command -v docker &>/dev/null; then
        ok "Docker: $(docker --version)"
        if docker-compose ps 2>/dev/null | grep -q "Up"; then
            ok "容器运行中"
            docker-compose ps
        else
            info "无运行中的容器"
        fi
    else
        info "Docker 未安装（仅本地模式需忽略此项）"
    fi

    # 服务连通性
    section "服务连通性"
    if curl -s --max-time 2 "http://localhost:8000/sse" >/dev/null 2>&1; then
        ok "SSE 服务运行中：http://localhost:8000/sse"
    else
        info "SSE 服务未运行（stdio 模式不需要，属正常）"
    fi

    # mcp 包
    section "依赖检查"
    PYTHON="$(pick_python)"
    if "$PYTHON" -c "import mcp; print('mcp', mcp.__version__)" 2>/dev/null; then
        ok "mcp 包已安装"
    else
        err "mcp 包未安装（运行：.venv/bin/pip install mcp）"
    fi
}

# ── 内部：检查 .env 文件 ──────────────────────────────────────────────
_check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        warn ".env 不存在，从模板创建..."
        cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
        info "请编辑 $ENV_FILE 配置 API Keys"
        read -r -p "配置完成后按 Enter 继续..."
    fi
}

# ── 内部：检查 Docker ─────────────────────────────────────────────────
_check_docker() {
    command -v docker &>/dev/null || {
        err "Docker 未安装"
        info "macOS: 安装 Docker Desktop"
        info "Linux: curl -fsSL https://get.docker.com | sh"
        exit 1
    }
    # 支持 docker compose（v2）和 docker-compose（v1）
    if ! command -v docker-compose &>/dev/null; then
        if docker compose version &>/dev/null 2>&1; then
            # 创建 shim
            docker-compose() { docker compose "$@"; }
            export -f docker-compose
        else
            err "docker-compose / docker compose 未找到"
            exit 1
        fi
    fi
    ok "Docker: $(docker --version)"
}

# ── 主入口 ────────────────────────────────────────────────────────────
main() {
    local cmd="${1:-help}"
    shift || true

    # 解析选项
    local docker_mode=false server_ip="" port="8000" host="0.0.0.0"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --docker)  docker_mode=true; shift ;;
            --server)  server_ip="$2";   shift 2 ;;
            --port)    port="$2";        shift 2 ;;
            --host)    host="$2";        shift 2 ;;
            --help|-h) show_help; exit 0 ;;
            *) err "未知选项：$1"; echo ""; show_help; exit 1 ;;
        esac
    done

    case "$cmd" in
        start)          cmd_start ;;
        deploy)
            $docker_mode \
                && cmd_deploy_docker "$port" "$host" \
                || cmd_deploy_native "$port" "$host" ;;
        config)         cmd_config "$server_ip" "$port" ;;
        check)          cmd_check ;;
        help|--help|-h) show_help ;;
        *)  err "未知命令：$cmd"; echo ""; show_help; exit 1 ;;
    esac
}

main "$@"

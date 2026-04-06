#!/bin/bash
# Goalcast MCP 统一部署工具
# 集配置生成、服务部署、连接配置于一体

set -e

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 打印消息
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

# 显示帮助信息
show_help() {
    cat << EOF
${GREEN}Goalcast MCP 统一部署工具${NC}

${BLUE}用法:${NC} $0 <模式> [选项]

${BLUE}部署模式:${NC}
  deploy          部署 MCP 服务（本地运行或 Docker）
  config          仅生成 MCP 客户端配置
  check           检查配置状态

${BLUE}部署模式选项:${NC}
  --docker        使用 Docker 部署（默认：直接运行）
  --port <PORT>   指定端口（默认：8000）
  --host <HOST>   指定绑定主机（默认：0.0.0.0）

${BLUE}配置模式选项:${NC}
  --local         本地开发配置（默认）
  --remote        远程服务器连接配置
  --server <IP>   远程服务器 IP（--remote 模式下必需）
  --port <PORT>   远程服务器端口（默认：8000）

${BLUE}示例:${NC}
  # 部署服务
  $0 deploy                    # 本地直接运行
  $0 deploy --docker          # Docker 部署
  $0 deploy --port 9000       # 指定端口

  # 生成配置
  $0 config                   # 本地开发配置
  $0 config --remote --server 192.168.1.100  # 远程连接配置

  # 检查配置
  $0 check

${BLUE}完整流程示例:${NC}
  # 场景 1：在服务器上部署并配置本地连接
  $0 deploy --docker
  # 服务运行在 http://localhost:8000
  # 自动生成 mcporter.json 连接到 localhost:8000

  # 场景 2：在服务器上部署，在本地配置远程连接
  # 在服务器上：
  $0 deploy --docker --port 8000
  # 在本地电脑上：
  $0 config --remote --server <服务器 IP> --port 8000

  # 场景 3：本地开发
  $0 deploy
  # 或
  $0 config --local

EOF
}

# 检查依赖
check_dependencies() {
    print_info "检查环境依赖..."
    
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装"
        exit 1
    fi
    print_success "Python3: $(python3 --version)"
    
    # 检查 .env 文件
    if [ ! -f ".env" ]; then
        print_warning ".env 文件不存在"
        print_info "从模板创建 .env 文件..."
        cp .env.example .env
        print_info "请编辑 .env 文件并配置 API Keys"
        print_info "使用命令：nano .env 或 vi .env"
        echo ""
        read -p "配置完成后按回车继续..."
    else
        print_success ".env 文件已存在"
    fi
    echo ""
}

# 检查 Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装"
        echo ""
        print_info "安装 Docker:"
        echo "  Ubuntu/Debian: curl -fsSL https://get.docker.com | sh"
        echo "  macOS:         下载 Docker Desktop"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_warning "docker-compose 未安装，尝试安装..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
    
    print_success "Docker: $(docker --version)"
    print_success "Docker Compose: $(docker-compose --version)"
    echo ""
}

# 生成 MCP 客户端配置
generate_mcp_config() {
    local mode="$1"
    local server_ip="$2"
    local port="$3"
    
    print_info "生成 MCP 客户端配置..."
    
    if [ "$mode" = "local" ]; then
        # 本地开发配置
        cat > mcporter.json << 'EOF'
{
  "mcpServers": {
    "goalcast": {
      "command": "python3",
      "args": ["mcp_server/server.py"],
      "env": {
        "PYTHONPATH": "."
      },
      "cwd": "."
    }
  }
}
EOF
        print_success "已生成本地开发配置"
        print_info "配置文件：mcporter.json"
        echo ""
        print_info "下一步:"
        echo "  1. 部署服务：$0 deploy"
        echo "  2. 或在 Trae 中加载配置"
        
    elif [ "$mode" = "remote" ]; then
        if [ -z "$server_ip" ]; then
            print_error "远程模式需要指定服务器 IP"
            echo ""
            echo "用法：$0 config --remote --server <IP> [--port <PORT>]"
            exit 1
        fi
        
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
        print_success "已生成远程连接配置"
        print_info "服务器地址：http://${server_ip}:${port}/sse"
        print_info "配置文件：mcporter.json"
    fi
    
    echo ""
}

# 部署服务（直接运行）
deploy_native() {
    local port="${1:-8000}"
    local host="${2:-0.0.0.0}"
    
    print_info "准备本地部署 MCP 服务..."
    echo ""
    
    check_dependencies
    
    print_info "启动 MCP 服务..."
    print_info "绑定地址：http://${host}:${port}"
    echo ""
    print_warning "按 Ctrl+C 停止服务"
    echo ""
    
    # 设置环境变量
    export PYTHONPATH="$PROJECT_ROOT"
    export FASTMCP_HOST="$host"
    export FASTMCP_PORT="$port"
    
    # 启动服务
    python3 mcp_server/server.py sse
}

# Docker 部署
deploy_docker() {
    local port="${1:-8000}"
    local host="${2:-0.0.0.0}"
    
    print_info "准备 Docker 部署..."
    echo ""
    
    check_dependencies
    check_docker
    
    # 构建镜像
    print_info "构建 Docker 镜像..."
    docker-compose build
    
    print_success "镜像构建完成"
    echo ""
    
    # 启动容器
    print_info "启动 Docker 容器..."
    docker-compose up -d
    
    # 等待启动
    print_info "等待服务启动..."
    sleep 5
    
    echo ""
    print_success "服务已启动"
    echo ""
    
    # 验证服务
    print_info "验证服务状态..."
    docker-compose ps
    echo ""
    
    # 测试连接
    if curl -s --max-time 5 http://localhost:${port}/sse > /dev/null 2>&1; then
        print_success "✓ 服务可以访问：http://localhost:${port}/sse"
    else
        print_warning "⚠ 服务响应超时"
        print_info "查看日志：docker-compose logs -f"
    fi
    echo ""
    
    # 生成配置
    print_info "生成 MCP 客户端配置..."
    generate_mcp_config "local" "" "$port"
    
    echo ""
    print_success "=========================================="
    print_success "    Docker 部署完成！"
    print_success "=========================================="
    echo ""
    print_info "服务信息:"
    echo "  - 本地访问：http://localhost:${port}/sse"
    echo "  - 远程访问：http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '<服务器 IP>'):${port}/sse"
    echo ""
    print_info "常用命令:"
    echo "  查看状态：docker-compose ps"
    echo "  查看日志：docker-compose logs -f"
    echo "  重启服务：docker-compose restart"
    echo "  停止服务：docker-compose down"
    echo ""
    print_info "如需远程访问，请确保防火墙开放 ${port} 端口"
    echo ""
}

# 检查配置状态
check_status() {
    print_info "检查配置状态..."
    echo ""
    
    # 检查 Python
    if command -v python3 &> /dev/null; then
        print_success "Python3: $(python3 --version)"
    else
        print_error "Python3 未安装"
    fi
    
    # 检查 .env
    if [ -f ".env" ]; then
        print_success ".env 文件：存在"
    else
        print_warning ".env 文件：不存在"
    fi
    
    # 检查 mcporter.json
    if [ -f "mcporter.json" ]; then
        print_success "mcporter.json：存在"
        echo ""
        print_info "配置内容:"
        cat mcporter.json | sed 's/^/  /'
    else
        print_warning "mcporter.json：不存在"
    fi
    echo ""
    
    # 检查 Docker
    if command -v docker &> /dev/null; then
        print_success "Docker: 已安装"
        if docker-compose ps 2>/dev/null | grep -q "goalcast"; then
            print_success "Docker 容器：运行中"
            docker-compose ps
        fi
    else
        print_warning "Docker: 未安装"
    fi
    echo ""
    
    # 检查服务状态
    if curl -s --max-time 2 http://localhost:8000/sse > /dev/null 2>&1; then
        print_success "MCP 服务：运行中 (http://localhost:8000/sse)"
    else
        print_warning "MCP 服务：未运行"
    fi
    echo ""
    
    print_success "检查完成"
}

# 主函数
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi
    
    local mode="$1"
    shift
    
    # 解析参数
    local docker_mode=false
    local config_mode="local"
    local server_ip=""
    local port="8000"
    local host="0.0.0.0"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --docker)
                docker_mode=true
                shift
                ;;
            --local)
                config_mode="local"
                shift
                ;;
            --remote)
                config_mode="remote"
                shift
                ;;
            --server)
                server_ip="$2"
                shift 2
                ;;
            --host)
                host="$2"
                shift 2
                ;;
            --port)
                port="$2"
                shift 2
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "未知参数：$1"
                echo ""
                show_help
                exit 1
                ;;
        esac
    done
    
    case $mode in
        deploy)
            if [ "$docker_mode" = true ]; then
                deploy_docker "$port" "$host"
            else
                deploy_native "$port" "$host"
            fi
            ;;
        config)
            generate_mcp_config "$config_mode" "$server_ip" "$port"
            ;;
        check)
            check_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知模式：$mode"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"

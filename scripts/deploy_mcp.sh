#!/bin/bash
# MCP Server 部署脚本
# 支持本地开发、Docker 部署和远程服务器部署

set -e

# 获取项目根目录（scripts 的父目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印帮助信息
print_help() {
    cat << EOF
MCP Server 部署脚本

用法：$0 [选项]

选项:
    local       本地开发模式（使用相对路径）
    docker      Docker 容器模式
    remote      远程服务器模式（SSE 传输）
    check       检查配置
    help        显示此帮助信息

示例:
    $0 local          # 本地开发
    $0 docker         # Docker 部署
    $0 remote         # 远程 SSE 模式
    $0 check          # 检查配置是否正确

EOF
}

# 检查环境变量
check_env() {
    echo -e "${YELLOW}检查环境变量...${NC}"
    
    if [ ! -f ".env" ]; then
        echo -e "${RED}警告：.env 文件不存在${NC}"
        echo "建议：复制 .env.example 并配置 API Keys"
        echo "命令：cp .env.example .env"
        echo ""
    else
        echo -e "${GREEN}✓ .env 文件存在${NC}"
    fi
    
    if [ ! -f "mcporter.json" ]; then
        echo -e "${YELLOW}提示：mcporter.json 不存在，将使用模板${NC}"
        cp mcporter.json.example mcporter.json
    else
        echo -e "${GREEN}✓ mcporter.json 存在${NC}"
    fi
    
    echo ""
}

# 本地开发模式
deploy_local() {
    echo -e "${GREEN}=== 本地开发模式 ===${NC}"
    echo ""
    
    check_env
    
    # 创建使用相对路径的配置
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
    
    echo -e "${GREEN}✓ 已创建本地开发配置${NC}"
    echo ""
    echo "下一步："
    echo "  1. 激活虚拟环境：source .venv/bin/activate"
    echo "  2. 运行 MCP 客户端：mcp dev"
    echo "  3. 或者在 Claude Desktop 中配置使用此 MCP 服务器"
    echo ""
}

# Docker 部署模式
deploy_docker() {
    echo -e "${GREEN}=== Docker 部署模式 ===${NC}"
    echo ""
    
    check_env
    
    # 检查 Docker 是否安装
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误：Docker 未安装${NC}"
        exit 1
    fi
    
    # 检查 docker-compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${YELLOW}提示：docker-compose 未安装，将使用 docker 命令${NC}"
    fi
    
    # 构建镜像
    echo -e "${YELLOW}构建 Docker 镜像...${NC}"
    docker build -t goalcast-mcp .
    
    echo ""
    echo -e "${GREEN}✓ 镜像构建完成${NC}"
    echo ""
    
    # 创建 docker-compose 配置
    cat > docker-compose.deploy.yml << 'EOF'
services:
  mcp-server:
    image: goalcast-mcp
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - FASTMCP_TRANSPORT=sse
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
EOF
    
    echo "下一步："
    echo "  启动服务：docker-compose -f docker-compose.deploy.yml up -d"
    echo "  查看日志：docker-compose -f docker-compose.deploy.yml logs -f"
    echo "  停止服务：docker-compose -f docker-compose.deploy.yml down"
    echo ""
    echo "远程连接配置（mcporter.json）："
    cat << 'EOF'
{
  "mcpServers": {
    "goalcast": {
      "url": "http://localhost:8000/sse",
      "transport": "sse"
    }
  }
}
EOF
    echo ""
    echo "💡 注意："
    echo "  - 如果 MCP 服务器在 Docker 中，客户端在宿主机，使用："
    echo "    http://host.docker.internal:8000/sse"
    echo ""
    echo ""
}

# 远程服务器模式（生成 SSE 配置）
deploy_remote() {
    echo -e "${GREEN}=== 远程服务器模式 ===${NC}"
    echo ""
    
    read -p "请输入服务器 IP 地址或主机名 [localhost]: " SERVER_IP
    SERVER_IP=${SERVER_IP:-localhost}
    
    read -p "请输入端口号 [8000]: " PORT
    PORT=${PORT:-8000}
    
    # 创建远程连接配置
    cat > mcporter.json << EOF
{
  "mcpServers": {
    "goalcast": {
      "url": "http://${SERVER_IP}:${PORT}/sse",
      "transport": "sse"
    }
  }
}
EOF
    
    echo ""
    echo -e "${GREEN}✓ 已创建远程连接配置${NC}"
    echo ""
    echo "配置信息："
    echo "  服务器地址：http://${SERVER_IP}:${PORT}/sse"
    echo "  传输模式：SSE (Server-Sent Events)"
    echo ""
    echo "下一步："
    echo "  1. 确保远程服务器已运行 MCP 服务"
    echo "  2. 在 Claude Desktop 或其他 MCP 客户端中加载此配置"
    echo "  3. 测试连接是否正常"
    echo ""
}

# 检查配置
check_config() {
    echo -e "${GREEN}=== 检查配置 ===${NC}"
    echo ""
    
    # 检查 Python
    if command -v python3 &> /dev/null; then
        echo -e "${GREEN}✓ Python3: $(python3 --version)${NC}"
    else
        echo -e "${RED}✗ Python3 未安装${NC}"
    fi
    
    # 检查依赖
    if [ -f "requirements.txt" ]; then
        echo -e "${GREEN}✓ requirements.txt 存在${NC}"
    else
        echo -e "${RED}✗ requirements.txt 不存在${NC}"
    fi
    
    # 检查 MCP 服务器代码
    if [ -f "mcp_server/server.py" ]; then
        echo -e "${GREEN}✓ MCP 服务器代码存在${NC}"
    else
        echo -e "${RED}✗ mcp_server/server.py 不存在${NC}"
    fi
    
    # 检查配置文件
    if [ -f "mcporter.json" ]; then
        echo -e "${GREEN}✓ mcporter.json 存在${NC}"
        echo "  配置内容："
        cat mcporter.json | sed 's/^/    /'
    else
        echo -e "${YELLOW}⚠ mcporter.json 不存在${NC}"
    fi
    
    # 检查环境变量
    if [ -f ".env" ]; then
        echo -e "${GREEN}✓ .env 文件存在${NC}"
    else
        echo -e "${YELLOW}⚠ .env 文件不存在${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}配置检查完成${NC}"
    echo ""
}

# 主函数
main() {
    case "${1:-help}" in
        local)
            deploy_local
            ;;
        docker)
            deploy_docker
            ;;
        remote)
            deploy_remote
            ;;
        check)
            check_config
            ;;
        help|--help|-h)
            print_help
            ;;
        *)
            echo -e "${RED}未知选项：$1${NC}"
            print_help
            exit 1
            ;;
    esac
}

main "$@"

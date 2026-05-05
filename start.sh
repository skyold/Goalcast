#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start.sh — Goalcast 足球量化分析系统 统一管理脚本
# ─────────────────────────────────────────────────────────────────────────────
#
# 用法：
#   ./start.sh <命令> [目标] [选项]
#
# 目标（不指定则默认 all）：
#   (默认)              backend + frontend（全部服务）
#   backend             仅后端服务（无限循环分析引擎）
#   frontend            仅前端服务
#
# 命令速查：
#   build   [目标]           构建 Docker 镜像（默认全部）
#   push    [目标]           推送镜像到 registry（不重新构建）
#   pull    [目标]           从 registry 拉取最新镜像（部署服务器用）
#   start   [目标]           启动服务（默认全部）
#   stop    [目标]           优雅停止（等当前分析完成）
#   restart [目标]            重启服务
#   upgrade [目标]            重建镜像 + 滚动重启
#   logs    [目标]            查看日志（实时跟踪）
#   status                   查看容器状态 + 健康检查
#   check                    运行环境配置检查
#   ps                       简洁的容器列表
#   stats                    实时资源用量（CPU/内存）
#   shell   [目标]           进入容器 shell（调试，默认 backend）
#
# 选项：
#   --tag <version>    镜像版本标签（默认 dev）
#   --push             构建后同时推送到 registry
#   --no-cache         构建时不使用缓存
#   --tail <n>         日志显示最近 n 行（默认 100）
#
# 示例：
#   ./start.sh start --build                   # 构建并启动全部服务
#   ./start.sh start backend --build          # 构建并启动 backend
#   ./start.sh stop                            # 停止全部服务
#   ./start.sh logs                            # 查看实时日志
#   ./start.sh status                          # 查看服务状态
#   ./start.sh check                           # 检查环境配置
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DOCKERFILE="${REPO_ROOT}/Dockerfile"
FRONTEND_DOCKERFILE="${REPO_ROOT}/frontend/Dockerfile"
COMPOSE_FILE="${REPO_ROOT}/docker/docker-compose.yml"
BACKEND_IMAGE="goalcast/backend"
FRONTEND_IMAGE="goalcast/frontend"

if [[ -t 1 ]]; then
    RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'
    BLUE=$'\033[0;34m'; CYAN=$'\033[0;36m'; BOLD=$'\033[1m'; RESET=$'\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; CYAN=''; BOLD=''; RESET=''
fi

info()    { echo -e "${CYAN}▶${RESET} $*"; }
success() { echo -e "${GREEN}✓${RESET} $*"; }
warn()    { echo -e "${YELLOW}⚠${RESET} $*"; }
error()   { echo -e "${RED}✗${RESET} $*" >&2; }
header()  { echo -e "\n${BOLD}${BLUE}══ $* ══${RESET}"; }

die() { error "$*"; exit 1; }

check_docker() {
    command -v docker &>/dev/null || die "未找到 docker，请先安装 Docker Desktop"
    docker info &>/dev/null       || die "Docker daemon 未运行，请启动 Docker"
}

_platform() {
    local native
    native="$(docker info --format '{{.OSType}}/{{.Architecture}}' 2>/dev/null)"
    echo "${PLATFORM:-${native}}"
}

CMD="${1:-help}"; shift || true
TARGET=""
TAG="dev"
PUSH=false
BUILD=false
NO_CACHE=""
TAIL_LINES=100
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        backend|frontend|all) TARGET="$1"; shift ;;
        --tag)      TAG="$2";        shift 2 ;;
        --push)     PUSH=true;       shift   ;;
        --build)    BUILD=true;      shift   ;;
        --no-cache) NO_CACHE="--no-cache"; shift ;;
        --tail)     TAIL_LINES="$2"; shift 2 ;;
        --)         shift; EXTRA_ARGS+=("$@"); break ;;
        *)          EXTRA_ARGS+=("$1"); shift ;;
    esac
done

[[ -z "${TARGET}" ]] && TARGET="all"

_build_backend() {
    header "构建 goalcast/backend 镜像"
    [[ -f "${BACKEND_DOCKERFILE}" ]] || die "未找到 ${BACKEND_DOCKERFILE}"

    docker build \
        ${NO_CACHE} \
        --platform "$(_platform)" \
        -t "${BACKEND_IMAGE}:${TAG}" \
        -t "${BACKEND_IMAGE}:latest" \
        -f "${BACKEND_DOCKERFILE}" \
        "${REPO_ROOT}"
    success "${BACKEND_IMAGE}:${TAG} 构建完成"

    if $PUSH; then
        docker push "${BACKEND_IMAGE}:${TAG}"
        docker push "${BACKEND_IMAGE}:latest"
        success "已推送 ${BACKEND_IMAGE}:${TAG}"
    fi
}

_build_frontend() {
    header "构建 goalcast/frontend 镜像"
    [[ -f "${FRONTEND_DOCKERFILE}" ]] || die "未找到 ${FRONTEND_DOCKERFILE}"

    docker build \
        ${NO_CACHE} \
        --platform "$(_platform)" \
        -t "${FRONTEND_IMAGE}:${TAG}" \
        -t "${FRONTEND_IMAGE}:latest" \
        -f "${FRONTEND_DOCKERFILE}" \
        "${REPO_ROOT}/frontend"
    success "${FRONTEND_IMAGE}:${TAG} 构建完成"

    if $PUSH; then
        docker push "${FRONTEND_IMAGE}:${TAG}"
        docker push "${FRONTEND_IMAGE}:latest"
        success "已推送 ${FRONTEND_IMAGE}:${TAG}"
    fi
}

cmd_build() {
    check_docker
    case "${TARGET}" in
        backend)   _build_backend ;;
        frontend)  _build_frontend ;;
        all)
            _build_backend
            _build_frontend
            ;;
        *) die "build 目标须为 backend / frontend / all" ;;
    esac
}

_push_backend() {
    header "推送 ${BACKEND_IMAGE} 到 registry"
    docker image inspect "${BACKEND_IMAGE}:${TAG}" &>/dev/null \
        || die "${BACKEND_IMAGE}:${TAG} 本地不存在，请先运行：./start.sh build backend --tag ${TAG}"
    docker push "${BACKEND_IMAGE}:${TAG}"
    docker push "${BACKEND_IMAGE}:latest"
    success "已推送 ${BACKEND_IMAGE}:${TAG}"
}

_push_frontend() {
    header "推送 ${FRONTEND_IMAGE} 到 registry"
    docker image inspect "${FRONTEND_IMAGE}:${TAG}" &>/dev/null \
        || die "${FRONTEND_IMAGE}:${TAG} 本地不存在，请先运行：./start.sh build frontend --tag ${TAG}"
    docker push "${FRONTEND_IMAGE}:${TAG}"
    docker push "${FRONTEND_IMAGE}:latest"
    success "已推送 ${FRONTEND_IMAGE}:${TAG}"
}

cmd_push() {
    check_docker
    case "${TARGET}" in
        backend)   _push_backend ;;
        frontend)  _push_frontend ;;
        all)
            _push_backend
            _push_frontend
            ;;
        *) die "push 目标须为 backend / frontend / all" ;;
    esac
}

_pull_backend() {
    header "拉取 ${BACKEND_IMAGE}:${TAG}"
    docker pull "${BACKEND_IMAGE}:${TAG}"
    [[ "${TAG}" != "latest" ]] && docker tag "${BACKEND_IMAGE}:${TAG}" "${BACKEND_IMAGE}:latest"
    success "${BACKEND_IMAGE}:${TAG} 拉取完成"
}

_pull_frontend() {
    header "拉取 ${FRONTEND_IMAGE}:${TAG}"
    docker pull "${FRONTEND_IMAGE}:${TAG}"
    [[ "${TAG}" != "latest" ]] && docker tag "${FRONTEND_IMAGE}:${TAG}" "${FRONTEND_IMAGE}:latest"
    success "${FRONTEND_IMAGE}:${TAG} 拉取完成"
}

cmd_pull() {
    check_docker
    case "${TARGET}" in
        backend)   _pull_backend ;;
        frontend)  _pull_frontend ;;
        all)
            _pull_backend
            _pull_frontend
            ;;
        *) die "pull 目标须为 backend / frontend / all" ;;
    esac
}

_start_backend() {
    header "启动 Goalcast 后端服务（无限循环分析引擎）"
    local env_file="${REPO_ROOT}/backend/.env"
    if [[ ! -f "${env_file}" ]]; then
        warn "backend/.env 不存在，从 backend/.env.example 复制..."
        cp "${REPO_ROOT}/backend/.env.example" "${env_file}"
        warn "请编辑 ${env_file} 填入真实密钥后重新运行"
        exit 1
    fi

    docker compose -f "${COMPOSE_FILE}" up -d backend
    success "后端服务已启动"
    info "后端 API：  http://localhost:8000"
    info "分析模式：  无限循环（每小时自动获取并分析比赛）"
    info "查看日志：  ./start.sh logs backend"
    info "优雅停止：  ./start.sh stop backend"
}

_start_frontend() {
    header "启动 Goalcast 前端服务"

    docker compose -f "${COMPOSE_FILE}" up -d frontend
    success "前端服务已启动"
    info "访问地址：  http://localhost"
    info "查看日志：  ./start.sh logs frontend"
}

cmd_start() {
    check_docker
    case "${TARGET}" in
        backend)
            if $BUILD; then _build_backend; fi
            _start_backend
            ;;
        frontend)
            if $BUILD; then _build_frontend; fi
            _start_frontend
            ;;
        all)
            if $BUILD; then
                _build_backend
                _build_frontend
            fi
            _start_backend
            _start_frontend
            echo ""
            info "访问地址：  http://localhost"
            info "后端 API：  http://localhost:8000"
            ;;
        *) die "start 目标须为 backend / frontend / all" ;;
    esac
}

cmd_stop() {
    check_docker
    case "${TARGET}" in
        backend)
            header "优雅停止后端服务（等待当前分析完成，最多 30s）"
            docker compose -f "${COMPOSE_FILE}" stop backend
            success "后端服务已停止"
            ;;
        frontend)
            header "停止前端服务"
            docker compose -f "${COMPOSE_FILE}" stop frontend
            success "前端服务已停止"
            ;;
        all)
            header "优雅停止所有服务"
            docker compose -f "${COMPOSE_FILE}" stop
            success "所有服务已停止"
            ;;
        *) die "stop 目标须为 backend / frontend / all" ;;
    esac
}

cmd_restart() {
    check_docker
    case "${TARGET}" in
        backend)
            header "重启后端服务"
            docker compose -f "${COMPOSE_FILE}" restart backend
            success "后端服务已重启"
            ;;
        frontend)
            header "重启前端服务"
            docker compose -f "${COMPOSE_FILE}" restart frontend
            success "前端服务已重启"
            ;;
        all)
            header "重启所有服务"
            docker compose -f "${COMPOSE_FILE}" restart
            success "所有服务已重启"
            ;;
        *) die "restart 目标须为 backend / frontend / all" ;;
    esac
}

cmd_upgrade() {
    check_docker
    case "${TARGET}" in
        backend)
            _build_backend
            header "滚动重启后端服务"
            docker compose -f "${COMPOSE_FILE}" up -d --force-recreate backend
            success "后端服务升级完成"
            ;;
        frontend)
            _build_frontend
            header "滚动重启前端服务"
            docker compose -f "${COMPOSE_FILE}" up -d --force-recreate frontend
            success "前端服务升级完成"
            ;;
        all)
            _build_backend
            _build_frontend
            header "滚动重启所有服务"
            docker compose -f "${COMPOSE_FILE}" up -d --force-recreate
            success "所有服务升级完成"
            ;;
        *) die "upgrade 目标须为 backend / frontend / all" ;;
    esac
}

cmd_logs() {
    check_docker
    case "${TARGET}" in
        backend)
            header "后端日志（最近 ${TAIL_LINES} 行，实时跟踪）"
            docker compose -f "${COMPOSE_FILE}" logs -f --tail "${TAIL_LINES}" backend
            ;;
        frontend)
            header "前端日志（最近 ${TAIL_LINES} 行，实时跟踪）"
            docker compose -f "${COMPOSE_FILE}" logs -f --tail "${TAIL_LINES}" frontend
            ;;
        all)
            header "所有服务日志（实时跟踪）"
            docker compose -f "${COMPOSE_FILE}" logs -f --tail "${TAIL_LINES}"
            ;;
        *) die "logs 目标须为 backend / frontend / all" ;;
    esac
}

cmd_status() {
    check_docker
    header "服务状态"

    echo ""
    echo -e "${BOLD}─── 后端服务 (backend) ───${RESET}"
    docker compose -f "${COMPOSE_FILE}" ps backend 2>/dev/null || echo "  （未运行）"

    echo ""
    echo -e "${BOLD}─── 前端服务 (frontend) ───${RESET}"
    docker compose -f "${COMPOSE_FILE}" ps frontend 2>/dev/null || echo "  （未运行）"

    echo ""
    echo -e "${BOLD}─── 比赛数据统计 ───${RESET}"
    local matches_dir="${REPO_ROOT}/backend/data/matches"
    if [[ -d "${matches_dir}" ]]; then
        local total
        total=$(find "${matches_dir}" -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
        echo "  已处理比赛 : ${GREEN}${total} 场${RESET}"
    else
        echo "  已处理比赛 : 0 场"
    fi

    local reports_dir="${REPO_ROOT}/backend/data/reports"
    if [[ -d "${reports_dir}" ]]; then
        local report_count
        report_count=$(find "${reports_dir}" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
        echo "  生成报告   : ${report_count} 份"
    fi

    echo ""
}

cmd_ps() {
    check_docker
    docker compose -f "${COMPOSE_FILE}" ps
}

cmd_stats() {
    check_docker
    header "实时资源用量（Ctrl+C 退出）"
    docker stats goalcast-backend goalcast-frontend 2>/dev/null || \
    docker stats $(docker ps --filter "name=goalcast" -q) 2>/dev/null || \
    warn "没有正在运行的容器"
}

cmd_shell() {
    check_docker
    local container="${TARGET}"
    case "${container}" in
        backend)   container="goalcast-backend" ;;
        frontend)  container="goalcast-frontend" ;;
        all)       container="goalcast-backend" ;;
    esac
    header "进入容器 ${container}（exit 退出）"
    docker exec -it "${container}" /bin/bash 2>/dev/null || \
    docker exec -it "${container}" /bin/sh
}

cmd_check() {
    check_docker
    header "环境检查"

    local env_file="${REPO_ROOT}/backend/.env"
    if [[ -f "${env_file}" ]]; then
        success "backend/.env 存在"
    else
        warn "backend/.env 不存在（请从 backend/.env.example 复制并填写）"
    fi

    if docker image inspect "${BACKEND_IMAGE}:latest" &>/dev/null; then
        local built_at
        built_at=$(docker image inspect "${BACKEND_IMAGE}:latest" --format '{{.Created}}' | cut -dT -f1)
        success "backend 镜像存在（创建于 ${built_at}）"
    else
        warn "backend 镜像不存在，请先运行：./start.sh build backend"
    fi

    if docker image inspect "${FRONTEND_IMAGE}:latest" &>/dev/null; then
        local built_at
        built_at=$(docker image inspect "${FRONTEND_IMAGE}:latest" --format '{{.Created}}' | cut -dT -f1)
        success "frontend 镜像存在（创建于 ${built_at}）"
    else
        warn "frontend 镜像不存在，请先运行：./start.sh build frontend"
    fi

    echo ""
    info "运行容器内环境检查..."
    if docker image inspect "${BACKEND_IMAGE}:latest" &>/dev/null && [[ -f "${env_file}" ]]; then
        docker run --rm \
            --env-file "${env_file}" \
            "${BACKEND_IMAGE}:latest" \
            check 2>/dev/null || warn "容器内 check 命令失败"
    fi
}

cmd_help() {
    cat <<EOF

${BOLD}start.sh${RESET} — Goalcast 足球量化分析系统 统一管理脚本

${BOLD}用法：${RESET}
  ./start.sh <命令> [目标] [选项]

${BOLD}目标：${RESET}
  ${CYAN}(默认)${RESET}   backend + frontend（全部服务）
  ${CYAN}backend${RESET}  仅后端服务（无限循环分析引擎）
  ${CYAN}frontend${RESET} 仅前端服务

${BOLD}命令：${RESET}
  ${CYAN}build${RESET}   [目标]             构建 Docker 镜像
  ${CYAN}push${RESET}    [目标]             推送镜像到 registry（不重新构建）
  ${CYAN}pull${RESET}    [目标]             从 registry 拉取最新镜像（部署服务器用）
  ${CYAN}start${RESET}   [目标]             启动服务（默认全部）
  ${CYAN}stop${RESET}    [目标]             优雅停止（等当前分析完成）
  ${CYAN}restart${RESET} [目标]             重启服务
  ${CYAN}upgrade${RESET} [目标]             重建镜像 + 重启（代码更新后使用）
  ${CYAN}logs${RESET}    [目标]             查看实时日志
  ${CYAN}status${RESET}                      服务状态 + 数据统计
  ${CYAN}ps${RESET}                          容器列表
  ${CYAN}stats${RESET}                       实时 CPU/内存用量
  ${CYAN}shell${RESET}   [目标]             进入容器 shell（调试，默认 backend）
  ${CYAN}check${RESET}                       环境配置检查

${BOLD}选项：${RESET}
  --tag <version>    镜像版本标签（默认 dev）
  --push             构建后推送到 registry
  --build            启动前先构建对应镜像
  --no-cache         构建时禁用缓存
  --tail <n>         日志显示最近 n 行（默认 100）

${BOLD}常用工作流：${RESET}
  ${GREEN}# 首次部署${RESET}
  cp backend/.env.example backend/.env
  vim backend/.env                  # 填入 API_KEY 等
  ./start.sh start --build         # 构建并启动全部服务
  # 打开 http://localhost

  ${GREEN}# 代码更新后升级${RESET}
  git pull
  ./start.sh upgrade                # 重建并重启所有服务

  ${GREEN}# 日常运维${RESET}
  ./start.sh logs                   # 查看实时日志
  ./start.sh status                 # 查看状态
  ./start.sh stop                   # 停止服务（优雅退出）

EOF
}

case "${CMD}" in
    build)    cmd_build    ;;
    push)     cmd_push     ;;
    pull)     cmd_pull     ;;
    start)    cmd_start    ;;
    stop)     cmd_stop     ;;
    restart)  cmd_restart  ;;
    upgrade)  cmd_upgrade  ;;
    logs|log) cmd_logs     ;;
    status)   cmd_status   ;;
    ps)       cmd_ps       ;;
    stats)    cmd_stats    ;;
    shell)    cmd_shell    ;;
    check)    cmd_check    ;;
    help|-h|--help) cmd_help ;;
    *) error "未知命令：${CMD}"; cmd_help; exit 1 ;;
esac

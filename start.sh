#!/bin/bash

# Goalcast Startup Script
# Usage: 
#   ./start.sh start           # Starts the docker containers
#   ./start.sh start --build   # Rebuilds the images and starts the containers
#   ./start.sh stop            # Stops the docker containers
#   ./start.sh restart         # Restarts the docker containers
#   ./start.sh logs            # Follows the logs of the containers

COMMAND=$1
BUILD_FLAG=$2

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function show_help {
    echo -e "${YELLOW}Usage:${NC}"
    echo -e "  $0 start           - Start Goalcast services"
    echo -e "  $0 start --build   - Rebuild images and start services"
    echo -e "  $0 stop            - Stop all services"
    echo -e "  $0 restart         - Restart all services"
    echo -e "  $0 logs            - View realtime logs"
}

case "$COMMAND" in
    start)
        if [ "$BUILD_FLAG" == "--build" ]; then
            echo -e "${GREEN}Building and starting Goalcast services...${NC}"
            docker-compose up --build -d
        else
            echo -e "${GREEN}Starting Goalcast services...${NC}"
            docker-compose up -d
        fi
        echo -e "${GREEN}Goalcast is running!${NC}"
        echo -e "Frontend: ${YELLOW}http://localhost${NC}"
        echo -e "Backend API: ${YELLOW}http://localhost:8000${NC}"
        ;;
    stop)
        echo -e "${YELLOW}Stopping Goalcast services...${NC}"
        docker-compose down
        echo -e "${GREEN}Services stopped.${NC}"
        ;;
    restart)
        echo -e "${YELLOW}Restarting Goalcast services...${NC}"
        docker-compose restart
        echo -e "${GREEN}Services restarted.${NC}"
        ;;
    logs)
        docker-compose logs -f
        ;;
    *)
        show_help
        exit 1
        ;;
esac

exit 0

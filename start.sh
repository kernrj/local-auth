#!/bin/bash
# Secure startup script for Local Auth System

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}       Local Auth System - Secure Start        ${NC}"
echo -e "${BLUE}===============================================${NC}"
echo ""

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check for docker compose (new or old syntax)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
fi

# Check if already initialized
if [ -f "./config/.initialized" ]; then
    echo -e "${GREEN}System already initialized${NC}"
    echo ""
    echo "Starting services..."
    $DOCKER_COMPOSE up -d

    echo ""
    echo -e "${GREEN}✓ Services started${NC}"
    echo ""
    echo "Access points:"
    echo "  - Authentik:     http://localhost:9000"
    echo "  - phpLDAPadmin:  http://localhost:8080"
    echo "  - Init/Mgmt UI:  http://localhost:8000"
    echo ""
    echo "Manage passwords with:"
    echo "  - ./scripts/reset-admin-password.sh"
    echo "  - ./scripts/reset-ldap-password.sh"
    echo "  - ./scripts/reset-database-password.sh"
else
    echo -e "${YELLOW}First-time setup detected${NC}"
    echo ""
    echo "Starting initialization process..."

    # Create necessary directories
    mkdir -p config media custom-templates geoip

    echo -e "${BLUE}Note: Default configurations will be created automatically${NC}"

    # Start only the init service first
    $DOCKER_COMPOSE up -d init

    echo ""
    echo -e "${GREEN}✓ Initialization service started${NC}"
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}     IMPORTANT: Complete Setup          ${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "1. Open your web browser to:"
    echo -e "   ${GREEN}http://localhost:8000${NC}"
    echo ""
    echo "2. Complete the secure setup form"
    echo ""
    echo "3. The system will automatically initialize"
    echo ""
    echo "4. Once complete, all services will start"
    echo ""
    echo -e "${YELLOW}Waiting for you to complete web setup...${NC}"

    # Monitor initialization
    while [ ! -f "./config/.initialized" ]; do
        sleep 5
    done

    echo ""
    echo -e "${GREEN}✓ Web setup completed!${NC}"
    echo "Starting all services..."

    # Start all services
    $DOCKER_COMPOSE up -d

    echo ""
    echo -e "${GREEN}✓ All services started successfully!${NC}"
fi

# Show service status
echo ""
echo "Service status:"
$DOCKER_COMPOSE ps

echo ""
echo -e "${BLUE}===============================================${NC}"
echo -e "${GREEN}System is ready!${NC}"
echo -e "${BLUE}===============================================${NC}"

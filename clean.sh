#!/bin/bash
# Clean script for Local Auth System

set -e

echo "Cleaning Local Auth System..."
echo "============================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Confirm with user
read -p "This will stop all containers and remove volumes. Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

echo -e "${YELLOW}Stopping containers...${NC}"
docker-compose down

echo -e "${YELLOW}Removing volumes...${NC}"
docker-compose down -v

echo -e "${YELLOW}Removing configuration...${NC}"
if [ -d "./config" ]; then
    read -p "Remove config directory? This will delete all settings! (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf ./config
        echo -e "${GREEN}✓ Config directory removed${NC}"
    else
        echo "Config directory preserved"
    fi
fi

echo -e "${YELLOW}Removing generated files...${NC}"
rm -f ./media/* 2>/dev/null || true
rm -f ./geoip/* 2>/dev/null || true
rm -f ./custom-templates/* 2>/dev/null || true

echo ""
echo -e "${GREEN}Cleanup complete!${NC}"
echo ""
echo "To start fresh:"
echo "1. Run: ./build.sh"
echo "2. Configure .env file"
echo "3. Run: docker-compose up -d"
echo ""

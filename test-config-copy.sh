#!/bin/bash
# Test script to verify default configuration copying works correctly

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Testing Configuration Copy Mechanism${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Test 1: Empty config directory
echo -e "${YELLOW}Test 1: Empty config directory${NC}"
rm -rf test-config
mkdir -p test-config

docker run --rm \
    -v "$PWD/test-config:/config" \
    -e SERVICE_TYPE=init \
    kernrj/authentik-init:latest \
    /defaults/copy-defaults.sh

if [ -f "test-config/defaults.json" ]; then
    echo -e "${GREEN}✓ Default config copied successfully${NC}"
else
    echo -e "${RED}✗ Default config not copied${NC}"
    exit 1
fi

# Test 2: Existing config should not be overwritten
echo ""
echo -e "${YELLOW}Test 2: Existing config preservation${NC}"
echo '{"test": "data"}' > test-config/defaults.json

docker run --rm \
    -v "$PWD/test-config:/config" \
    -e SERVICE_TYPE=init \
    kernrj/authentik-init:latest \
    /defaults/copy-defaults.sh

if grep -q '"test": "data"' test-config/defaults.json; then
    echo -e "${GREEN}✓ Existing config preserved${NC}"
else
    echo -e "${RED}✗ Existing config was overwritten${NC}"
    exit 1
fi

# Test 3: RADIUS specific configs
echo ""
echo -e "${YELLOW}Test 3: RADIUS configuration${NC}"
rm -rf test-config
mkdir -p test-config

docker run --rm \
    -v "$PWD/test-config:/etc/freeradius" \
    -e SERVICE_TYPE=radius \
    kernrj/authentik-freeradius:latest \
    /defaults/copy-defaults.sh

if [ -f "test-config/clients.conf" ]; then
    echo -e "${GREEN}✓ RADIUS config copied successfully${NC}"
else
    echo -e "${RED}✗ RADIUS config not copied${NC}"
    exit 1
fi

# Cleanup
rm -rf test-config

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All tests passed!${NC}"
echo -e "${GREEN}========================================${NC}"

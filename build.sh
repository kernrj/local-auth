#!/bin/bash
# Build script for Local Auth System

set -e

# Parse arguments
PUSH_IMAGES=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            PUSH_IMAGES=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--push]"
            echo "  --push    Push images to Docker Hub after building"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Building Local Auth System Docker images..."
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to build an image
build_image() {
    local context=$1
    local image=$2
    local name=$3
    local dockerfile_flag=$4

    echo -e "${YELLOW}Building $name...${NC}"
    if docker build -t "$image" $dockerfile_flag "$context"; then
        echo -e "${GREEN}✓ $name built successfully${NC}"
    else
        echo -e "${RED}✗ Failed to build $name${NC}"
        exit 1
    fi
}

# Build FreeRADIUS image (using parent context for initial-config)
build_image "." "kernrj/authentik-freeradius:latest" "FreeRADIUS" "-f ./docker/Dockerfile-radius"

# Build Initialization image (using parent context for initial-config)
build_image "." "kernrj/authentik-init:latest" "Initialization Service" "-f ./docker/Dockerfile-init"

echo ""
echo -e "${GREEN}All images built successfully!${NC}"

# Push images if requested
if [ "$PUSH_IMAGES" = true ]; then
    echo ""
    echo "Pushing images to Docker Hub..."
    echo "=============================="

    push_image() {
        local image=$1
        local name=$2

        echo -e "${YELLOW}Pushing $name...${NC}"
        if docker push "$image"; then
            echo -e "${GREEN}✓ $name pushed successfully${NC}"
        else
            echo -e "${RED}✗ Failed to push $name${NC}"
            exit 1
        fi
    }

    # Push images
    push_image "kernrj/authentik-freeradius:latest" "FreeRADIUS"
    push_image "kernrj/authentik-init:latest" "Initialization Service"

    echo ""
    echo -e "${GREEN}All images pushed successfully!${NC}"
fi

echo ""
echo "Next steps:"
if [ "$PUSH_IMAGES" = true ]; then
    echo "Images have been pushed to Docker Hub."
    echo "Users can now use docker-compose.yml directly without building."
else
    echo "1. Copy .env.example to .env and configure your settings"
    echo "2. Run: docker compose up -d"
    echo "3. Monitor initialization: docker logs -f authentik-init"
    echo "4. Access Authentik at: http://localhost:9000"
    echo ""
    echo "To push images to Docker Hub, run: $0 --push"
fi
echo ""

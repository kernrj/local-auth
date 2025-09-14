#!/bin/bash
# Script to copy default configurations to mounted volumes if they don't exist
# This ensures containers have proper configs even with empty volume mounts

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to copy default configs
copy_if_not_exists() {
    local src="$1"
    local dst="$2"
    local desc="$3"

    if [ ! -f "$dst" ]; then
        echo -e "${YELLOW}Creating default $desc${NC}"
        cp "$src" "$dst"
        echo -e "${GREEN}✓ Created $dst${NC}"
    else
        echo -e "${BLUE}✓ $desc already exists${NC}"
    fi
}

# Function to copy directory if not exists
copy_dir_if_not_exists() {
    local src="$1"
    local dst="$2"
    local desc="$3"

    if [ ! -d "$dst" ]; then
        echo -e "${YELLOW}Creating default $desc directory${NC}"
        cp -r "$src" "$dst"
        echo -e "${GREEN}✓ Created $dst${NC}"
    else
        echo -e "${BLUE}✓ $desc directory already exists${NC}"
    fi
}

# Main configuration check
echo "Checking for required configuration files..."

# Check which service we're running in
SERVICE_TYPE="${SERVICE_TYPE:-generic}"

case "$SERVICE_TYPE" in
    "radius")
        echo "Configuring FreeRADIUS defaults..."
        copy_if_not_exists "/defaults/radius/clients.conf.default" "/etc/freeradius/clients.conf" "RADIUS clients configuration"
        ;;

    "ldap")
        echo "Configuring OpenLDAP defaults..."
        # LDAP configuration is handled by the OpenLDAP container itself
        # We just ensure the organization structure is available
        copy_if_not_exists "/defaults/ldap/organization.ldif" "/config/organization.ldif" "LDAP organization structure"
        ;;

    "authentik")
        echo "Configuring Authentik defaults..."
        copy_if_not_exists "/defaults/authentik/authentik.yaml" "/config/authentik.yaml" "Authentik configuration"
        ;;

    "postgres")
        echo "Configuring PostgreSQL defaults..."
        # PostgreSQL init scripts are handled by the postgres image
        if [ ! -f "/docker-entrypoint-initdb.d/init.sql" ]; then
            cp "/defaults/postgres/init.sql" "/docker-entrypoint-initdb.d/"
            echo -e "${GREEN}✓ Created PostgreSQL init script${NC}"
        fi
        ;;

    "init")
        echo "Configuring initialization defaults..."
        copy_if_not_exists "/defaults/defaults.json" "/config/defaults.json" "system defaults"

        # Create required directories
        mkdir -p /config/{radius,ldap,authentik,postgres}
        echo -e "${GREEN}✓ Created configuration directories${NC}"
        ;;

    *)
        echo "Unknown service type: $SERVICE_TYPE"
        ;;
esac

# Copy global defaults if not exists
if [ -f "/defaults/defaults.json" ] && [ ! -f "/config/defaults.json" ]; then
    cp "/defaults/defaults.json" "/config/defaults.json"
    echo -e "${GREEN}✓ Created global defaults${NC}"
fi

echo -e "${GREEN}Configuration check complete${NC}"

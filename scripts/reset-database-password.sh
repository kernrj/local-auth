#!/bin/bash
# Reset PostgreSQL database password for Local Auth System

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

CONFIG_DIR="./config"
CONFIG_FILE="$CONFIG_DIR/system_config.json"

echo "=========================================="
echo "Local Auth System - Database Password Reset"
echo "=========================================="

# Check if system is initialized
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: System not initialized. Please run docker-compose up first.${NC}"
    exit 1
fi

# Get database info from config
DB_INFO=$(docker run --rm -v "$PWD/config:/config:ro" python:3.11-slim python -c "
import json
with open('/config/system_config.json', 'r') as f:
    config = json.load(f)
    db = config['database']
    print(f\"{db['username']}|{db['database']}\")
")

DB_USER=$(echo $DB_INFO | cut -d'|' -f1)
DB_NAME=$(echo $DB_INFO | cut -d'|' -f2)

echo -e "Resetting password for database user: ${GREEN}$DB_USER${NC}"
echo -e "Database: ${GREEN}$DB_NAME${NC}"
echo ""

# Prompt for new password
read -s -p "Enter new password: " NEW_PASSWORD
echo ""
read -s -p "Confirm new password: " NEW_PASSWORD_CONFIRM
echo ""

# Validate passwords match
if [ "$NEW_PASSWORD" != "$NEW_PASSWORD_CONFIRM" ]; then
    echo -e "${RED}Error: Passwords do not match${NC}"
    exit 1
fi

echo -e "${YELLOW}Stopping services that use the database...${NC}"
docker-compose stop authentik-server authentik-worker

echo -e "${YELLOW}Updating password...${NC}"

# Update password in config file (hashed)
docker run --rm -v "$PWD/config:/config" python:3.11-slim /bin/bash -c "
pip install argon2-cffi >/dev/null 2>&1
python3 << 'EOF'
import json
from argon2 import PasswordHasher

# Load config
with open('/config/system_config.json', 'r') as f:
    config = json.load(f)

# Hash new password
ph = PasswordHasher(memory_cost=65536, time_cost=3, parallelism=4)
new_hash = ph.hash('$NEW_PASSWORD')

# Update config
config['database']['password_hash'] = new_hash

# Save config
with open('/config/system_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print('Password hash updated in configuration')
EOF
"

# Update password in PostgreSQL
echo -e "${YELLOW}Updating password in PostgreSQL...${NC}"
docker exec -i authentik-postgresql psql -U postgres << EOF
ALTER USER $DB_USER WITH PASSWORD '$NEW_PASSWORD';
EOF

# Update docker-compose environment
echo -e "${YELLOW}Updating Docker environment...${NC}"
cat > "$CONFIG_DIR/.env.database" << EOF
PG_PASS=$NEW_PASSWORD
EOF
chmod 600 "$CONFIG_DIR/.env.database"

# Restart services
echo -e "${YELLOW}Restarting services...${NC}"
docker-compose start authentik-server authentik-worker

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

echo ""
echo -e "${GREEN}✓ Database password reset successfully!${NC}"
echo ""
echo "The following services have been restarted with the new password:"
echo "  - authentik-server"
echo "  - authentik-worker"
echo ""
echo "Note: You may need to update any external applications that connect to this database."

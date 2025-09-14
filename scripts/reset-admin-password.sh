#!/bin/bash
# Reset admin password for Local Auth System
# This script follows security best practices by hashing passwords with Argon2

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

CONFIG_DIR="./config"
CONFIG_FILE="$CONFIG_DIR/system_config.json"

echo "=========================================="
echo "Local Auth System - Admin Password Reset"
echo "=========================================="

# Check if system is initialized
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: System not initialized. Please run docker-compose up first.${NC}"
    exit 1
fi

# Get admin email from config
ADMIN_EMAIL=$(docker run --rm -v "$PWD/config:/config:ro" python:3.11-slim python -c "
import json
with open('/config/system_config.json', 'r') as f:
    config = json.load(f)
    print(config['admin']['email'])
")

echo -e "Resetting password for admin user: ${GREEN}$ADMIN_EMAIL${NC}"
echo ""

# Prompt for new password
read -s -p "Enter new password (min 12 characters): " NEW_PASSWORD
echo ""
read -s -p "Confirm new password: " NEW_PASSWORD_CONFIRM
echo ""

# Validate passwords match
if [ "$NEW_PASSWORD" != "$NEW_PASSWORD_CONFIRM" ]; then
    echo -e "${RED}Error: Passwords do not match${NC}"
    exit 1
fi

# Validate password length
if [ ${#NEW_PASSWORD} -lt 12 ]; then
    echo -e "${RED}Error: Password must be at least 12 characters${NC}"
    exit 1
fi

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
config['admin']['password_hash'] = new_hash

# Save config
with open('/config/system_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print('Password hash updated in configuration')
EOF
"

# Update password in Authentik
echo -e "${YELLOW}Updating password in Authentik...${NC}"

# Use Authentik's password reset feature
docker exec authentik-server python -m lifecycle.migrate
docker exec authentik-server ak change_password "$ADMIN_EMAIL" --password "$NEW_PASSWORD" 2>/dev/null || {
    # If the above fails, try the alternative method
    docker exec -it authentik-server python << EOF
from authentik.core.models import User
from django.contrib.auth.hashers import make_password

try:
    user = User.objects.get(email='$ADMIN_EMAIL')
    user.set_password('$NEW_PASSWORD')
    user.save()
    print("Password updated successfully")
except Exception as e:
    print(f"Error: {e}")
EOF
}

echo ""
echo -e "${GREEN}✓ Admin password reset successfully!${NC}"
echo ""
echo "You can now log in to Authentik with:"
echo "  Email: $ADMIN_EMAIL"
echo "  Password: [your new password]"
echo "  URL: http://localhost:9000"
echo ""

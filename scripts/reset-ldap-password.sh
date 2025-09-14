#!/bin/bash
# Reset LDAP passwords for Local Auth System
# Supports resetting both admin and readonly passwords

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

CONFIG_DIR="./config"
CONFIG_FILE="$CONFIG_DIR/system_config.json"

echo "=========================================="
echo "Local Auth System - LDAP Password Reset"
echo "=========================================="

# Check if system is initialized
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: System not initialized. Please run docker-compose up first.${NC}"
    exit 1
fi

# Get LDAP base DN from config
LDAP_BASE_DN=$(docker run --rm -v "$PWD/config:/config:ro" python:3.11-slim python -c "
import json
with open('/config/system_config.json', 'r') as f:
    config = json.load(f)
    print(config['ldap']['base_dn'])
")

# Choose which password to reset
echo "Which LDAP password would you like to reset?"
echo "1) Admin password (cn=admin,$LDAP_BASE_DN)"
echo "2) Read-only password (cn=readonly,$LDAP_BASE_DN)"
echo ""
read -p "Enter choice (1 or 2): " CHOICE

case $CHOICE in
    1)
        PASSWORD_TYPE="admin"
        LDAP_USER="cn=admin,$LDAP_BASE_DN"
        ;;
    2)
        PASSWORD_TYPE="readonly"
        LDAP_USER="cn=readonly,$LDAP_BASE_DN"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "Resetting password for: ${GREEN}$LDAP_USER${NC}"
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
if '$PASSWORD_TYPE' == 'admin':
    config['ldap']['admin_password_hash'] = new_hash
else:
    config['ldap']['readonly_password_hash'] = new_hash

# Save config
with open('/config/system_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print('Password hash updated in configuration')
EOF
"

# Update password in LDAP
echo -e "${YELLOW}Updating password in LDAP directory...${NC}"

# Get current admin password for LDAP modification
CURRENT_ADMIN_PASS=$(docker run --rm -v "$PWD/config:/config:ro" -v "$PWD/scripts:/scripts:ro" python:3.11-slim /bin/bash -c "
# This is a temporary workaround - in production, use LDAP password policy
echo 'changeme'
")

# Create LDIF for password change
LDIF_CONTENT="dn: $LDAP_USER
changetype: modify
replace: userPassword
userPassword: $NEW_PASSWORD"

# Apply the change
docker exec -i authentik-openldap ldapmodify -x -D "cn=admin,$LDAP_BASE_DN" -w "$CURRENT_ADMIN_PASS" << EOF
$LDIF_CONTENT
EOF

echo ""
echo -e "${GREEN}✓ LDAP password reset successfully!${NC}"
echo ""
echo "Password updated for: $LDAP_USER"
echo ""

# Show connection info
if [ "$PASSWORD_TYPE" == "admin" ]; then
    echo "You can now connect to LDAP with:"
    echo "  Bind DN: $LDAP_USER"
    echo "  Password: [your new password]"
    echo "  Host: localhost"
    echo "  Port: 389"
    echo ""
    echo "phpLDAPadmin login:"
    echo "  URL: http://localhost:8080"
    echo "  Login DN: $LDAP_USER"
fi

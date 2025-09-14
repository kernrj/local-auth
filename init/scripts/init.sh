#!/bin/bash
set -e

CONFIG_DIR="/config"
CONFIG_FILE="$CONFIG_DIR/system_config.json"
INIT_FLAG="$CONFIG_DIR/.initialized"

echo "Starting Local Auth System initialization process..."

# Create config directory if it doesn't exist
mkdir -p "$CONFIG_DIR"

# Copy default configurations if needed
echo "Checking default configurations..."
/defaults/copy-defaults.sh

# Check if already initialized
if [ -f "$INIT_FLAG" ]; then
    echo "System already initialized."
    echo "Starting web interface for management..."
    cd /webapp
    exec gunicorn -b 0.0.0.0:8000 --workers 2 --timeout 120 app:app
fi

echo "First-time setup detected. Starting configuration interface..."
echo "=========================================================="
echo "Please open your web browser and navigate to:"
echo "  http://localhost:8000"
echo "to complete the initial setup."
echo "=========================================================="

# Start the web interface
cd /webapp
gunicorn -b 0.0.0.0:8000 --workers 2 --timeout 120 app:app &
WEB_PID=$!

# Wait for configuration to be completed
echo "Waiting for configuration to be completed..."
while [ ! -f "$CONFIG_FILE" ]; do
    sleep 5
done

echo "Configuration detected! Proceeding with system initialization..."

# Kill the web server
kill $WEB_PID 2>/dev/null || true

# Load configuration and initialization passwords
export CONFIG_FILE
source "$CONFIG_DIR/init_passwords.sh" 2>/dev/null || true

# Create PostgreSQL environment file
echo "Creating PostgreSQL environment file..."
echo "POSTGRES_PASSWORD=$DB_INIT_PASSWORD" > "$CONFIG_DIR/.env.postgres"
chmod 600 "$CONFIG_DIR/.env.postgres"

# Create environment files for other services
echo "LDAP_ADMIN_PASSWORD=$LDAP_ADMIN_INIT_PASSWORD" > "$CONFIG_DIR/.env.ldap"
echo "LDAP_READONLY_PASSWORD=$LDAP_READONLY_INIT_PASSWORD" >> "$CONFIG_DIR/.env.ldap"
chmod 600 "$CONFIG_DIR/.env.ldap"

# Function to wait for a service to be ready
wait_for_service() {
    local service=$1
    local port=$2
    local max_attempts=60
    local attempt=0

    echo "Waiting for $service to be ready..."
    while ! nc -z "$service" "$port" 2>/dev/null; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            echo "ERROR: $service failed to start after $max_attempts attempts"
            exit 1
        fi
        echo "Waiting for $service... (attempt $attempt/$max_attempts)"
        sleep 5
    done
    echo "$service is ready!"
}

# Function to wait for PostgreSQL to be ready
wait_for_postgres() {
    echo "Waiting for PostgreSQL to be ready..."
    until PGPASSWORD="$PG_PASS" psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" -c '\q' 2>/dev/null; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 5
    done
    echo "PostgreSQL is ready!"
}

# Load secure configuration
echo "Loading secure configuration..."
python3 /scripts/prepare_environment.py

# Wait for services
wait_for_postgres
wait_for_service "$LDAP_HOST" 389
wait_for_service "$AUTHENTIK_HOST" "$AUTHENTIK_PORT"

# Additional wait for Authentik to fully initialize
echo "Waiting for Authentik to fully initialize..."
sleep 30

# Run Python initialization script with temporary admin password
echo "Running Authentik configuration..."
export TEMP_ADMIN_PASSWORD="$ADMIN_INIT_PASSWORD"
python3 /scripts/configure_authentik.py

# Configure LDAP integration with passwords
echo "Configuring LDAP integration..."
export LDAP_ADMIN_PASSWORD="$LDAP_ADMIN_INIT_PASSWORD"
export LDAP_READONLY_PASSWORD="$LDAP_READONLY_INIT_PASSWORD"
python3 /scripts/configure_ldap.py

# Configure RADIUS
echo "Configuring RADIUS..."
python3 /scripts/configure_radius.py

# Create initialization flag
touch "$INIT_FLAG"

# Clean up temporary password files
echo "Cleaning up temporary files..."
rm -f "$CONFIG_DIR/init_passwords.sh" 2>/dev/null || true

echo "==========================================="
echo "Initialization complete!"
echo "==========================================="
echo "System has been securely configured."
echo "Authentik URL: http://localhost:9000"
echo "phpLDAPadmin URL: http://localhost:8080"
echo ""
echo "To manage passwords, use the scripts in the /scripts directory:"
echo "  - reset-admin-password.sh"
echo "  - reset-ldap-password.sh"
echo "  - reset-database-password.sh"
echo ""
echo "Default RADIUS clients can be configured via RADIUS_CLIENTS environment variable"
echo "Format: CLIENT_NAME:CLIENT_IP:CLIENT_SECRET;CLIENT_NAME2:CLIENT_IP2:CLIENT_SECRET2"
echo "==========================================="

# Keep container running if needed for debugging
if [ "$DEBUG_MODE" = "true" ]; then
    echo "Debug mode enabled. Container will stay running..."
    tail -f /dev/null
fi

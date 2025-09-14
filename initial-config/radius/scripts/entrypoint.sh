#!/bin/bash
set -e

# Set service type for config initialization
export SERVICE_TYPE=radius

# Function to copy default config if not exists
copy_default_config() {
    local src="$1"
    local dst="$2"
    local desc="$3"

    if [ ! -f "$dst" ]; then
        echo "Creating default $desc..."
        cp "$src" "$dst"
        echo "✓ Created $dst"
    else
        echo "✓ $desc already exists"
    fi
}

# Function to copy directory if not exists
copy_default_dir() {
    local src="$1"
    local dst="$2"
    local desc="$3"

    if [ ! -d "$dst" ]; then
        echo "Creating default $desc directory..."
        mkdir -p "$(dirname "$dst")"
        cp -r "$src" "$dst"
        echo "✓ Created $dst"
    else
        echo "✓ $desc directory already exists"
    fi
}

# Copy default configurations from image to mounted volume if needed
echo "Checking RADIUS configurations..."

# Copy main config files
copy_default_config "/defaults/radiusd.conf" "/etc/freeradius/radiusd.conf" "radiusd.conf"
copy_default_config "/defaults/clients.conf.default" "/etc/freeradius/clients.conf.default" "default clients.conf"

# Auto-discover and copy all directories from defaults
echo "Auto-copying missing configuration directories..."
rsync -av --ignore-existing /defaults/ /etc/freeradius/

# Ensure critical directories exist
mkdir -p /etc/freeradius/{mods-enabled,sites-enabled,policy.d,certs}

# Enable necessary modules if not already enabled
if [ ! -L "/etc/freeradius/mods-enabled/rest" ]; then
    ln -sf /etc/freeradius/mods-available/rest /etc/freeradius/mods-enabled/rest
    echo "✓ Enabled REST module"
fi

if [ ! -L "/etc/freeradius/mods-enabled/eap" ]; then
    ln -sf /etc/freeradius/mods-available/eap /etc/freeradius/mods-enabled/eap
    echo "✓ Enabled EAP module"
fi

# Generate clients.conf from environment variable if provided
if [ -n "$RADIUS_CLIENTS" ]; then
    echo "# Auto-generated RADIUS clients" > /etc/freeradius/clients.conf
    echo "" >> /etc/freeradius/clients.conf

    # Format: CLIENT_NAME:CLIENT_IP:CLIENT_SECRET;CLIENT_NAME2:CLIENT_IP2:CLIENT_SECRET2
    IFS=';' read -ra CLIENTS <<< "$RADIUS_CLIENTS"
    for client in "${CLIENTS[@]}"; do
        IFS=':' read -ra CLIENT_INFO <<< "$client"
        CLIENT_NAME="${CLIENT_INFO[0]}"
        CLIENT_IP="${CLIENT_INFO[1]}"
        CLIENT_SECRET="${CLIENT_INFO[2]}"

        cat >> /etc/freeradius/clients.conf <<EOF
client $CLIENT_NAME {
    ipaddr = $CLIENT_IP
    secret = $CLIENT_SECRET
    require_message_authenticator = no
    nas_type = other
}

EOF
    done
else
    # Use default clients.conf
    cp /etc/freeradius/clients.conf.default /etc/freeradius/clients.conf 2>/dev/null || true
fi

# Update Authentik configuration in the Python script
if [ -n "$AUTHENTIK_HOST" ] && [ -n "$AUTHENTIK_TOKEN" ]; then
    sed -i "s|AUTHENTIK_HOST = .*|AUTHENTIK_HOST = '$AUTHENTIK_HOST'|g" /usr/local/bin/authentik_auth.py
    sed -i "s|AUTHENTIK_PORT = .*|AUTHENTIK_PORT = '$AUTHENTIK_PORT'|g" /usr/local/bin/authentik_auth.py
    sed -i "s|AUTHENTIK_TOKEN = .*|AUTHENTIK_TOKEN = '$AUTHENTIK_TOKEN'|g" /usr/local/bin/authentik_auth.py
fi

# Start FreeRADIUS
exec "$@"

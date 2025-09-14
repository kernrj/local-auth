#!/bin/bash
set -e

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

# Copy default PostgreSQL init script if needed
echo "Checking PostgreSQL initialization scripts..."
if [ -d "/docker-entrypoint-initdb.d" ]; then
    copy_default_config "/defaults/postgres/init.sql" "/docker-entrypoint-initdb.d/init.sql" "PostgreSQL init script"
fi

# Call the original PostgreSQL entrypoint
exec docker-entrypoint.sh "$@"

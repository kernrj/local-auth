#!/bin/bash
# Wrapper script to ensure default configs are copied before running the main entrypoint
# This can be used by any service that needs config initialization

set -e

# Run the copy-defaults script if it exists
if [ -f "/defaults/copy-defaults.sh" ]; then
    echo "Initializing default configurations..."
    /defaults/copy-defaults.sh
else
    echo "Warning: No default configurations found"
fi

# Execute the original entrypoint
echo "Starting service..."
exec "$@"

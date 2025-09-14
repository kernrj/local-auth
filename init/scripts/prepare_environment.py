#!/usr/bin/env python3
"""
Prepare environment variables from secure configuration.
This script bridges the gap between secure storage and Docker environment needs.
"""

import os
import json
import sys
from pathlib import Path

def load_config():
    """Load the secure configuration."""
    config_file = Path("/config/system_config.json")
    if not config_file.exists():
        return None

    with open(config_file, 'r') as f:
        return json.load(f)

def generate_env_file(config):
    """Generate environment file for Docker services."""
    # Generate a temporary password for services that need plain text
    # This is only used during initialization

    env_lines = []

    # Database configuration
    env_lines.append(f"PG_USER={config['database']['username']}")
    env_lines.append(f"PG_DB={config['database']['database']}")

    # Admin configuration
    env_lines.append(f"ADMIN_EMAIL={config['admin']['email']}")

    # LDAP configuration
    env_lines.append(f"LDAP_BASE_DN={config['ldap']['base_dn']}")

    # Security keys
    env_lines.append(f"AUTHENTIK_SECRET_KEY={config['security']['authentik_secret_key']}")

    # Write to secure env file
    env_path = Path("/config/.env.runtime")
    with open(env_path, 'w') as f:
        f.write('\n'.join(env_lines))

    os.chmod(env_path, 0o600)

    print("Runtime environment prepared")

def main():
    """Main entry point."""
    config = load_config()
    if not config:
        print("No configuration found")
        sys.exit(1)

    generate_env_file(config)

if __name__ == "__main__":
    main()

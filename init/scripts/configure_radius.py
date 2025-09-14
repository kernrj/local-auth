#!/usr/bin/env python3
"""
Configure RADIUS integration with Authentik.
"""

import os
import sys
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RADIUSConfigurator:
    """Handles RADIUS configuration for Authentik integration."""

    def __init__(self):
        """Initialize RADIUS configurator."""
        self.config_dir = "/config"

    def save_radius_token(self) -> bool:
        """
        Save Authentik API token for RADIUS authentication.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Configuring RADIUS authentication token...")

        # Read the token saved by Authentik configurator
        token_file = f"{self.config_dir}/authentik_token.txt"
        if not os.path.exists(token_file):
            logger.error("Authentik token not found!")
            return False

        with open(token_file, 'r') as f:
            token = f.read().strip()

        # Update RADIUS environment file
        radius_env_file = f"{self.config_dir}/radius.env"
        with open(radius_env_file, 'w') as f:
            f.write(f"AUTHENTIK_TOKEN={token}\n")
            f.write(f"AUTHENTIK_HOST=authentik-server\n")
            f.write(f"AUTHENTIK_PORT=9000\n")

        logger.info("RADIUS authentication token configured")
        return True

    def generate_radius_clients(self) -> bool:
        """
        Generate default RADIUS client configurations.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Generating RADIUS client configurations...")

        # Default RADIUS clients for common network devices
        default_clients = [
            {
                "name": "home-router",
                "ip": "192.168.1.1",
                "secret": "router-secret-123"
            },
            {
                "name": "wifi-ap",
                "ip": "192.168.1.2",
                "secret": "wifi-secret-456"
            },
            {
                "name": "vpn-server",
                "ip": "192.168.1.3",
                "secret": "vpn-secret-789"
            },
            {
                "name": "local-network",
                "ip": "192.168.1.0/24",
                "secret": "network-secret-000"
            }
        ]

        # Generate RADIUS_CLIENTS environment variable format
        radius_clients = []
        for client in default_clients:
            radius_clients.append(f"{client['name']}:{client['ip']}:{client['secret']}")

        radius_clients_str = ";".join(radius_clients)

        # Save to configuration file
        clients_file = f"{self.config_dir}/radius_clients.conf"
        with open(clients_file, 'w') as f:
            f.write("# RADIUS Client Configuration\n")
            f.write("# Format: CLIENT_NAME:CLIENT_IP:CLIENT_SECRET\n")
            f.write("# Multiple clients separated by semicolon\n\n")
            f.write(f"RADIUS_CLIENTS={radius_clients_str}\n\n")
            f.write("# Individual client details:\n")
            for client in default_clients:
                f.write(f"# {client['name']}: {client['ip']} (secret: {client['secret']})\n")

        logger.info(f"RADIUS client configurations saved to {clients_file}")
        return True

    def create_radius_test_script(self) -> bool:
        """
        Create a test script for RADIUS authentication.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Creating RADIUS test script...")

        test_script = """#!/bin/bash
# RADIUS Authentication Test Script

echo "RADIUS Authentication Test"
echo "=========================="

# Default values
RADIUS_HOST="${1:-localhost}"
RADIUS_SECRET="${2:-testing123}"
USERNAME="${3:-jdoe}"
PASSWORD="${4:-password123}"

echo "Testing RADIUS authentication:"
echo "  Host: $RADIUS_HOST"
echo "  Secret: $RADIUS_SECRET"
echo "  Username: $USERNAME"
echo ""

# Test authentication
radtest "$USERNAME" "$PASSWORD" "$RADIUS_HOST" 1812 "$RADIUS_SECRET"

echo ""
echo "Usage: $0 [radius_host] [radius_secret] [username] [password]"
echo "Example: $0 localhost testing123 jdoe password123"
"""

        test_script_path = f"{self.config_dir}/test_radius.sh"
        with open(test_script_path, 'w') as f:
            f.write(test_script)

        # Make executable
        os.chmod(test_script_path, 0o755)

        logger.info(f"RADIUS test script created at {test_script_path}")
        return True

    def create_documentation(self) -> bool:
        """
        Create RADIUS-specific documentation.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Creating RADIUS documentation...")

        radius_doc = f"""# RADIUS Configuration Guide

## Overview
This authentication system includes a FreeRADIUS server integrated with Authentik for centralized authentication.

## RADIUS Clients Configuration

### Default Clients
The following RADIUS clients are pre-configured:
- **home-router** (192.168.1.1): Router authentication
- **wifi-ap** (192.168.1.2): WiFi access point
- **vpn-server** (192.168.1.3): VPN server authentication
- **local-network** (192.168.1.0/24): Entire local network

### Adding New Clients
To add new RADIUS clients, update the `RADIUS_CLIENTS` environment variable in docker-compose.yml:

```
RADIUS_CLIENTS=CLIENT_NAME:CLIENT_IP:CLIENT_SECRET;CLIENT_NAME2:CLIENT_IP2:CLIENT_SECRET2
```

Example:
```
RADIUS_CLIENTS=switch1:192.168.1.10:switch-secret-123;firewall:192.168.1.20:firewall-secret-456
```

## Testing RADIUS Authentication

### Using the Test Script
A test script is provided at `{self.config_dir}/test_radius.sh`:

```bash
# Test with default settings
./config/test_radius.sh

# Test with custom parameters
./config/test_radius.sh localhost testing123 jdoe password123
```

### Using radtest Directly
```bash
# Install freeradius-utils if not already installed
sudo apt-get install freeradius-utils

# Test authentication
radtest username password localhost 1812 testing123
```

## Network Device Configuration

### Cisco IOS Example
```
aaa new-model
aaa authentication login default group radius local
aaa authorization exec default group radius local

radius server authentik
 address ipv4 YOUR_DOCKER_HOST_IP auth-port 1812 acct-port 1813
 key YOUR_RADIUS_SECRET
```

### UniFi Controller
1. Go to Settings > Profiles > RADIUS
2. Create new RADIUS profile:
   - Name: Authentik RADIUS
   - IP Address: YOUR_DOCKER_HOST_IP
   - Port: 1812
   - Password: YOUR_RADIUS_SECRET

### pfSense
1. System > User Manager > Authentication Servers
2. Add new server:
   - Type: RADIUS
   - Hostname: YOUR_DOCKER_HOST_IP
   - Shared Secret: YOUR_RADIUS_SECRET
   - Port: 1812

## Troubleshooting

### View RADIUS Logs
```bash
docker logs authentik-freeradius -f
```

### Check RADIUS Service
```bash
docker exec authentik-freeradius radtest testuser testpass localhost 0 testing123
```

### Common Issues
1. **Authentication failures**: Check Authentik user exists and is active
2. **Connection refused**: Ensure firewall allows UDP port 1812
3. **Shared secret mismatch**: Verify RADIUS_CLIENTS configuration
"""

        doc_path = f"{self.config_dir}/RADIUS_GUIDE.md"
        with open(doc_path, 'w') as f:
            f.write(radius_doc)

        logger.info(f"RADIUS documentation created at {doc_path}")
        return True

    def run(self) -> bool:
        """
        Run the RADIUS configuration process.

        Returns:
            True if successful, False otherwise
        """
        # Save RADIUS token
        if not self.save_radius_token():
            return False

        # Generate RADIUS clients
        if not self.generate_radius_clients():
            logger.warning("Failed to generate RADIUS clients")

        # Create test script
        if not self.create_radius_test_script():
            logger.warning("Failed to create test script")

        # Create documentation
        if not self.create_documentation():
            logger.warning("Failed to create documentation")

        logger.info("RADIUS configuration completed!")
        return True


def main():
    """Main entry point."""
    configurator = RADIUSConfigurator()
    if not configurator.run():
        logger.error("RADIUS configuration failed!")
        sys.exit(1)

    logger.info("RADIUS configuration completed successfully!")


if __name__ == "__main__":
    main()

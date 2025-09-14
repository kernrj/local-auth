#!/usr/bin/env python3
"""
FreeRADIUS authentication script for Authentik integration.
This script authenticates users against Authentik's API.
"""

import sys
import json
import requests
import logging
from typing import Dict, Optional, Tuple

# Configuration
AUTHENTIK_HOST = 'authentik-server'
AUTHENTIK_PORT = '9000'
AUTHENTIK_TOKEN = ''

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/var/log/freeradius/authentik_auth.log')]
)
logger = logging.getLogger(__name__)


class AuthentikAuthenticator:
    """Handles authentication requests against Authentik API."""

    def __init__(self, host: str, port: str, token: str):
        """
        Initialize the authenticator with Authentik connection details.

        Args:
            host: Authentik server hostname
            port: Authentik server port
            token: API token for authentication
        """
        self.base_url = f"http://{host}:{port}/api/v3"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Authenticate a user against Authentik.

        Args:
            username: Username to authenticate
            password: User's password

        Returns:
            Tuple of (success: bool, user_attributes: dict or None)
        """
        try:
            # First, try to authenticate the user
            auth_url = f"{self.base_url}/flows/executor/default-authentication-flow/"

            # Initial flow request
            response = requests.post(
                auth_url,
                json={
                    "component": "ak-stage-identification",
                    "uid_field": username
                },
                headers=self.headers
            )

            if response.status_code != 200:
                logger.error(f"Authentication flow failed: {response.status_code}")
                return False, None

            # Password stage
            response = requests.post(
                auth_url,
                json={
                    "component": "ak-stage-password",
                    "password": password
                },
                headers=self.headers
            )

            if response.status_code == 200:
                # Get user details
                user_data = self._get_user_details(username)
                return True, user_data
            else:
                logger.warning(f"Authentication failed for user {username}")
                return False, None

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False, None

    def _get_user_details(self, username: str) -> Optional[Dict]:
        """
        Retrieve user details from Authentik.

        Args:
            username: Username to look up

        Returns:
            User attributes dictionary or None
        """
        try:
            users_url = f"{self.base_url}/core/users/"
            response = requests.get(
                users_url,
                params={"username": username},
                headers=self.headers
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("results"):
                    user = data["results"][0]
                    return {
                        "username": user.get("username"),
                        "email": user.get("email"),
                        "groups": [g.get("name") for g in user.get("groups", [])],
                        "is_active": user.get("is_active", True),
                        "attributes": user.get("attributes", {})
                    }
            return None
        except Exception as e:
            logger.error(f"Failed to get user details: {str(e)}")
            return None


def main():
    """Main entry point for FreeRADIUS authentication."""
    # Read attributes from stdin
    attributes = {}
    for line in sys.stdin:
        if '=' in line:
            key, value = line.strip().split('=', 1)
            attributes[key] = value

    # Extract username and password
    username = attributes.get('User-Name', '').strip('"')
    password = attributes.get('User-Password', '').strip('"')

    if not username or not password:
        logger.error("Missing username or password")
        sys.exit(1)

    # Authenticate against Authentik
    authenticator = AuthentikAuthenticator(AUTHENTIK_HOST, AUTHENTIK_PORT, AUTHENTIK_TOKEN)
    success, user_data = authenticator.authenticate(username, password)

    if success:
        logger.info(f"Authentication successful for user {username}")
        # Return attributes to FreeRADIUS
        if user_data:
            print(f"Reply-Message = \"Welcome {username}\"")
            if user_data.get('groups'):
                print(f"Class = \"{','.join(user_data['groups'])}\"")
        sys.exit(0)
    else:
        logger.warning(f"Authentication failed for user {username}")
        print("Reply-Message = \"Authentication failed\"")
        sys.exit(1)


if __name__ == "__main__":
    main()

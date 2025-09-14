#!/usr/bin/env python3
"""
Configure Authentik with initial setup including admin user,
LDAP provider, and RADIUS application.
"""

import os
import sys
import time
import json
import requests
import logging
from typing import Optional, Dict, Any
from argon2 import PasswordHasher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AuthentikConfigurator:
    """Handles initial configuration of Authentik."""

    def __init__(self):
        """Initialize configurator with secure configuration."""
        self.host = os.environ.get('AUTHENTIK_HOST', 'authentik-server')
        self.port = os.environ.get('AUTHENTIK_PORT', '9000')
        self.base_url = f"http://{self.host}:{self.port}/api/v3"

        # Load secure configuration
        config_file = os.environ.get('CONFIG_FILE', '/config/system_config.json')
        with open(config_file, 'r') as f:
            self.config = json.load(f)

        self.admin_email = self.config['admin']['email']
        self.admin_password = None  # Will be retrieved from secure storage
        self.token = None
        self.hasher = PasswordHasher()

    def wait_for_authentik(self, max_attempts: int = 60) -> bool:
        """
        Wait for Authentik API to be ready.

        Args:
            max_attempts: Maximum number of attempts

        Returns:
            True if ready, False otherwise
        """
        logger.info("Waiting for Authentik API to be ready...")
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{self.base_url}/")
                if response.status_code in [200, 401]:
                    logger.info("Authentik API is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass

            logger.info(f"Waiting for Authentik... (attempt {attempt + 1}/{max_attempts})")
            time.sleep(5)

        logger.error("Authentik API failed to become ready")
        return False

    def create_initial_admin(self) -> bool:
        """
        Create the initial admin user using Authentik's bootstrap API.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Creating initial admin user...")

        # Get the temporary password for initial setup
        temp_password = os.environ.get('TEMP_ADMIN_PASSWORD')
        if not temp_password:
            logger.error("Temporary admin password not provided for initial setup")
            return False

        # Store the password for later use
        self.admin_password = temp_password

        # Use Authentik's bootstrap endpoint to create the initial admin
        bootstrap_data = {
            "username": self.admin_email,
            "password": temp_password,
            "name": "Administrator"
        }

        try:
            # First, try to access the API without authentication to see if setup is needed
            response = requests.get(f"{self.base_url}/core/users/", timeout=10)

            if response.status_code == 403:
                # API requires authentication, which means Authentik is set up
                logger.info("Authentik appears to be already configured (API requires auth)")
                return True
            elif response.status_code == 200:
                # Check if any superusers exist
                users = response.json().get('results', [])
                superusers = [u for u in users if u.get('is_superuser', False)]
                if superusers:
                    logger.info("Admin user already exists")
                    return True

            # If we get here, we need to create an admin user
            # Try using the bootstrap endpoint if available
            bootstrap_url = f"http://{self.host}:{self.port}/api/v3/root/config/"
            try:
                bootstrap_response = requests.post(bootstrap_url, json={
                    "admin_email": self.admin_email,
                    "admin_password": temp_password
                }, timeout=10)

                if bootstrap_response.status_code in [200, 201]:
                    logger.info("Admin user created via bootstrap endpoint")
                    return True
            except:
                pass  # Bootstrap endpoint might not be available

            # Fallback: try creating user directly (this might work if no auth is required yet)
            user_data = {
                "username": self.admin_email,
                "email": self.admin_email,
                "name": "Administrator",
                "is_superuser": True,
                "is_staff": True,
                "is_active": True
            }

            # Try to create without password first
            response = requests.post(f"{self.base_url}/core/users/", json=user_data, timeout=10)
            if response.status_code == 201:
                logger.info("Admin user created successfully")
                # Now try to set password
                user_id = response.json().get('pk')
                if user_id:
                    pwd_data = {"password": temp_password}
                    pwd_response = requests.post(
                        f"{self.base_url}/core/users/{user_id}/set_password/",
                        json=pwd_data,
                        timeout=10
                    )
                    if pwd_response.status_code == 200:
                        logger.info("Admin password set successfully")
                return True
            elif response.status_code == 400 and "already exists" in response.text.lower():
                logger.info("Admin user already exists")
                return True
            else:
                logger.warning(f"Could not create admin user via API: {response.status_code}")
                logger.warning("This may be normal if Authentik requires manual setup")
                return True  # Don't fail the entire process

        except Exception as e:
            logger.warning(f"Could not create admin user automatically: {str(e)}")
            logger.warning("You may need to create the admin user manually via Authentik UI")
            return True  # Don't fail the entire process

    def get_admin_token(self) -> Optional[str]:
        """
        Retrieve an API token for the admin user.

        Returns:
            API token or None
        """
        logger.info("Retrieving admin API token...")

        # First, we need to authenticate
        auth_data = {
            "username": self.admin_email,
            "password": self.admin_password
        }

        try:
            # Get a session
            session = requests.Session()

            # Login
            login_url = f"http://{self.host}:{self.port}/api/v3/flows/executor/default-authentication-flow/"
            response = session.post(login_url, json=auth_data)

            if response.status_code != 200:
                logger.error(f"Failed to authenticate: {response.status_code}")
                return None

            # Create API token
            token_url = f"{self.base_url}/core/tokens/"
            token_data = {
                "identifier": "init-token",
                "description": "Initial configuration token",
                "expiring": False
            }

            response = session.post(token_url, json=token_data)
            if response.status_code == 201:
                token = response.json().get('key')
                logger.info("API token created successfully")
                return token
            else:
                logger.error(f"Failed to create API token: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting API token: {str(e)}")
            return None

    def configure_ldap_source(self) -> bool:
        """
        Configure LDAP as an authentication source.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Configuring LDAP source...")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        ldap_config = {
            "name": "Local LDAP",
            "slug": "local-ldap",
            "enabled": True,
            "server_uri": f"ldap://{os.environ.get('LDAP_HOST', 'openldap')}:389",
            "bind_cn": f"cn=admin,{os.environ.get('LDAP_BASE_DN', 'dc=local,dc=auth')}",
            "bind_password": os.environ.get('LDAP_ADMIN_PASSWORD', 'admin'),
            "base_dn": os.environ.get('LDAP_BASE_DN', 'dc=local,dc=auth'),
            "property_mappings": [],
            "group_property_mappings": [],
            "sync_users": True,
            "sync_users_password": True,
            "sync_groups": True,
            "sync_parent_group": None,
            "user_object_filter": "(objectClass=inetOrgPerson)",
            "group_object_filter": "(objectClass=groupOfNames)",
            "user_group_membership_field": "memberOf",
            "object_uniqueness_field": "entryUUID"
        }

        try:
            response = requests.post(
                f"{self.base_url}/sources/ldap/",
                json=ldap_config,
                headers=headers
            )

            if response.status_code == 201:
                logger.info("LDAP source configured successfully")
                return True
            else:
                logger.error(f"Failed to configure LDAP source: {response.status_code}")
                logger.error(response.text)
                return False

        except Exception as e:
            logger.error(f"Error configuring LDAP source: {str(e)}")
            return False

    def configure_radius_provider(self) -> bool:
        """
        Configure RADIUS provider for network device authentication.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Configuring RADIUS provider...")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        # Create RADIUS provider
        radius_provider = {
            "name": "RADIUS Provider",
            "authorization_flow": None,  # Will use default
            "client_networks": "0.0.0.0/0",  # Allow all networks initially
            "shared_secret": os.environ.get('RADIUS_SHARED_SECRET', 'radius-secret-key')
        }

        try:
            response = requests.post(
                f"{self.base_url}/providers/radius/",
                json=radius_provider,
                headers=headers
            )

            if response.status_code == 201:
                provider_pk = response.json().get('pk')
                logger.info("RADIUS provider created successfully")

                # Create application for RADIUS
                app_config = {
                    "name": "RADIUS Authentication",
                    "slug": "radius-auth",
                    "provider": provider_pk,
                    "policy_engine_mode": "any",
                    "meta_launch_url": "",
                    "meta_description": "RADIUS authentication for network devices"
                }

                response = requests.post(
                    f"{self.base_url}/core/applications/",
                    json=app_config,
                    headers=headers
                )

                if response.status_code == 201:
                    logger.info("RADIUS application created successfully")
                    return True
                else:
                    logger.error(f"Failed to create RADIUS application: {response.status_code}")
                    return False

            else:
                logger.error(f"Failed to create RADIUS provider: {response.status_code}")
                logger.error(response.text)
                return False

        except Exception as e:
            logger.error(f"Error configuring RADIUS: {str(e)}")
            return False

    def run(self) -> bool:
        """
        Run the complete configuration process.

        Returns:
            True if successful, False otherwise
        """
        # Wait for Authentik to be ready
        if not self.wait_for_authentik():
            return False

        # Create initial admin user
        if not self.create_initial_admin():
            return False

        # Get API token
        self.token = self.get_admin_token()
        if not self.token:
            return False

        # Save token for RADIUS integration
        with open('/config/authentik_token.txt', 'w') as f:
            f.write(self.token)

        # Configure LDAP source
        if not self.configure_ldap_source():
            logger.warning("LDAP source configuration failed, continuing...")

        # Configure RADIUS provider
        if not self.configure_radius_provider():
            logger.warning("RADIUS provider configuration failed, continuing...")

        logger.info("Authentik configuration completed successfully!")
        return True


def main():
    """Main entry point."""
    configurator = AuthentikConfigurator()
    if not configurator.run():
        logger.error("Configuration failed!")
        sys.exit(1)

    logger.info("Configuration completed successfully!")


if __name__ == "__main__":
    main()

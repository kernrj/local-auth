#!/usr/bin/env python3
"""
Configure OpenLDAP with initial structure and sample users.
"""

import os
import subprocess
import logging
import time
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LDAPConfigurator:
    """Handles initial configuration of OpenLDAP."""

    def __init__(self):
        """Initialize LDAP configurator with environment variables."""
        self.ldap_host = os.environ.get('LDAP_HOST', 'openldap')
        self.ldap_base_dn = os.environ.get('LDAP_BASE_DN', 'dc=local,dc=auth')
        self.ldap_admin_password = os.environ.get('LDAP_ADMIN_PASSWORD', 'admin')
        self.ldap_organisation = os.environ.get('LDAP_ORGANISATION', 'Local Auth')

    def wait_for_ldap(self, max_attempts: int = 30) -> bool:
        """
        Wait for LDAP server to be ready.

        Args:
            max_attempts: Maximum number of attempts

        Returns:
            True if ready, False otherwise
        """
        logger.info("Waiting for LDAP server to be ready...")

        for attempt in range(max_attempts):
            try:
                # Try to bind to LDAP
                cmd = [
                    'ldapsearch',
                    '-x',
                    '-H', f'ldap://{self.ldap_host}:389',
                    '-D', f'cn=admin,{self.ldap_base_dn}',
                    '-w', self.ldap_admin_password,
                    '-b', self.ldap_base_dn,
                    '-s', 'base',
                    '(objectClass=*)'
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("LDAP server is ready!")
                    return True

            except Exception as e:
                logger.debug(f"LDAP not ready: {str(e)}")

            logger.info(f"Waiting for LDAP... (attempt {attempt + 1}/{max_attempts})")
            time.sleep(2)

        logger.error("LDAP server failed to become ready")
        return False

    def create_organizational_units(self) -> bool:
        """
        Create organizational units for users and groups.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Creating organizational units...")

        # Create OUs LDIF
        ou_ldif = f"""
# Users OU
dn: ou=users,{self.ldap_base_dn}
objectClass: organizationalUnit
ou: users
description: User accounts

# Groups OU
dn: ou=groups,{self.ldap_base_dn}
objectClass: organizationalUnit
ou: groups
description: User groups

# Services OU
dn: ou=services,{self.ldap_base_dn}
objectClass: organizationalUnit
ou: services
description: Service accounts
"""

        return self._apply_ldif(ou_ldif, "organizational_units.ldif")

    def create_groups(self) -> bool:
        """
        Create initial groups.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Creating initial groups...")

        groups_ldif = f"""
# Administrators group
dn: cn=admins,ou=groups,{self.ldap_base_dn}
objectClass: groupOfNames
cn: admins
description: System administrators
member: cn=admin,{self.ldap_base_dn}

# Users group
dn: cn=users,ou=groups,{self.ldap_base_dn}
objectClass: groupOfNames
cn: users
description: Regular users
member: cn=admin,{self.ldap_base_dn}

# Network admins group
dn: cn=network-admins,ou=groups,{self.ldap_base_dn}
objectClass: groupOfNames
cn: network-admins
description: Network device administrators
member: cn=admin,{self.ldap_base_dn}

# VPN users group
dn: cn=vpn-users,ou=groups,{self.ldap_base_dn}
objectClass: groupOfNames
cn: vpn-users
description: VPN access users
member: cn=admin,{self.ldap_base_dn}
"""

        return self._apply_ldif(groups_ldif, "groups.ldif")

    def create_sample_users(self) -> bool:
        """
        Create sample users for testing.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Creating sample users...")

        # Generate sample users
        sample_users = [
            {
                "uid": "jdoe",
                "cn": "John Doe",
                "sn": "Doe",
                "givenName": "John",
                "mail": "jdoe@local.auth",
                "password": "password123",
                "groups": ["users", "vpn-users"]
            },
            {
                "uid": "asmith",
                "cn": "Alice Smith",
                "sn": "Smith",
                "givenName": "Alice",
                "mail": "asmith@local.auth",
                "password": "password123",
                "groups": ["users", "network-admins"]
            },
            {
                "uid": "bwilson",
                "cn": "Bob Wilson",
                "sn": "Wilson",
                "givenName": "Bob",
                "mail": "bwilson@local.auth",
                "password": "password123",
                "groups": ["users"]
            }
        ]

        users_ldif = ""
        group_updates_ldif = ""

        for user in sample_users:
            # Create user entry
            users_ldif += f"""
# User: {user['cn']}
dn: uid={user['uid']},ou=users,{self.ldap_base_dn}
objectClass: inetOrgPerson
objectClass: posixAccount
objectClass: shadowAccount
uid: {user['uid']}
cn: {user['cn']}
sn: {user['sn']}
givenName: {user['givenName']}
mail: {user['mail']}
userPassword: {user['password']}
uidNumber: {1000 + len(users_ldif.split('dn:'))}
gidNumber: 1000
homeDirectory: /home/{user['uid']}
loginShell: /bin/bash

"""

            # Add user to groups
            for group in user['groups']:
                group_updates_ldif += f"""
# Add {user['uid']} to {group}
dn: cn={group},ou=groups,{self.ldap_base_dn}
changetype: modify
add: member
member: uid={user['uid']},ou=users,{self.ldap_base_dn}

"""

        # Apply user creation
        if not self._apply_ldif(users_ldif, "users.ldif"):
            return False

        # Apply group membership updates
        return self._apply_ldif(group_updates_ldif, "group_updates.ldif", modify=True)

    def create_service_accounts(self) -> bool:
        """
        Create service accounts for applications.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Creating service accounts...")

        services_ldif = f"""
# Authentik service account
dn: cn=authentik,ou=services,{self.ldap_base_dn}
objectClass: applicationProcess
objectClass: simpleSecurityObject
cn: authentik
userPassword: authentik-service-password
description: Authentik LDAP integration service account

# RADIUS service account
dn: cn=radius,ou=services,{self.ldap_base_dn}
objectClass: applicationProcess
objectClass: simpleSecurityObject
cn: radius
userPassword: radius-service-password
description: RADIUS LDAP integration service account
"""

        return self._apply_ldif(services_ldif, "services.ldif")

    def _apply_ldif(self, ldif_content: str, filename: str, modify: bool = False) -> bool:
        """
        Apply LDIF content to LDAP server.

        Args:
            ldif_content: LDIF content to apply
            filename: Filename for temporary LDIF file
            modify: Use ldapmodify instead of ldapadd

        Returns:
            True if successful, False otherwise
        """
        # Write LDIF to temporary file
        ldif_path = f"/tmp/{filename}"
        with open(ldif_path, 'w') as f:
            f.write(ldif_content)

        # Apply LDIF
        cmd = [
            'ldapmodify' if modify else 'ldapadd',
            '-x',
            '-H', f'ldap://{self.ldap_host}:389',
            '-D', f'cn=admin,{self.ldap_base_dn}',
            '-w', self.ldap_admin_password,
            '-f', ldif_path
        ]

        if not modify:
            cmd.append('-c')  # Continue on errors for ldapadd

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Successfully applied {filename}")
                return True
            else:
                # Check if it's just "already exists" error
                if "Already exists" in result.stderr:
                    logger.info(f"{filename} entries already exist, skipping...")
                    return True
                else:
                    logger.error(f"Failed to apply {filename}: {result.stderr}")
                    return False
        except Exception as e:
            logger.error(f"Error applying {filename}: {str(e)}")
            return False
        finally:
            # Clean up temporary file
            if os.path.exists(ldif_path):
                os.remove(ldif_path)

    def run(self) -> bool:
        """
        Run the complete LDAP configuration process.

        Returns:
            True if successful, False otherwise
        """
        # Wait for LDAP to be ready
        if not self.wait_for_ldap():
            return False

        # Create organizational units
        if not self.create_organizational_units():
            logger.warning("Failed to create OUs, they may already exist")

        # Create groups
        if not self.create_groups():
            logger.warning("Failed to create groups, they may already exist")

        # Create service accounts
        if not self.create_service_accounts():
            logger.warning("Failed to create service accounts, they may already exist")

        # Create sample users
        if not self.create_sample_users():
            logger.warning("Failed to create sample users, they may already exist")

        logger.info("LDAP configuration completed!")
        return True


def main():
    """Main entry point."""
    configurator = LDAPConfigurator()
    if not configurator.run():
        logger.error("LDAP configuration failed!")
        sys.exit(1)

    logger.info("LDAP configuration completed successfully!")


if __name__ == "__main__":
    main()

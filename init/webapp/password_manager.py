#!/usr/bin/env python3
"""
Secure password manager for Local Auth System.
Implements Repository pattern for password storage and retrieval.
"""

import os
import json
import secrets
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

logger = logging.getLogger(__name__)


class PasswordRepositoryInterface(ABC):
    """Interface for password repository following Interface Segregation Principle."""

    @abstractmethod
    def store_password(self, service: str, username: str, password_hash: str) -> None:
        """Store a hashed password for a service."""
        pass

    @abstractmethod
    def verify_password(self, service: str, username: str, password: str) -> bool:
        """Verify a password against stored hash."""
        pass

    @abstractmethod
    def update_password(self, service: str, username: str, new_password_hash: str) -> None:
        """Update a password hash."""
        pass

    @abstractmethod
    def get_temporary_password(self, service: str, username: str) -> Optional[str]:
        """Get a temporary password for initial setup (if available)."""
        pass


class SecurePasswordRepository(PasswordRepositoryInterface):
    """
    Concrete implementation of password repository with secure storage.
    Uses a temporary in-memory cache for initial setup passwords.
    """

    def __init__(self, config_path: Path):
        """Initialize repository with configuration path."""
        self.config_path = config_path
        self.hasher = PasswordHasher(
            memory_cost=65536,  # 64 MB
            time_cost=3,
            parallelism=4
        )
        # Temporary password cache for initial setup only
        self._temp_passwords: Dict[str, Dict[str, str]] = {}

    def store_password(self, service: str, username: str, password_hash: str) -> None:
        """Store a hashed password in configuration."""
        config = self._load_config()

        if service not in config:
            config[service] = {}

        config[service][f"{username}_password_hash"] = password_hash
        self._save_config(config)

    def verify_password(self, service: str, username: str, password: str) -> bool:
        """Verify a password against stored hash."""
        config = self._load_config()

        if service not in config:
            return False

        hash_key = f"{username}_password_hash"
        if hash_key not in config[service]:
            return False

        try:
            self.hasher.verify(config[service][hash_key], password)
            return True
        except VerifyMismatchError:
            return False

    def update_password(self, service: str, username: str, new_password_hash: str) -> None:
        """Update a password hash."""
        self.store_password(service, username, new_password_hash)

        # Clear any temporary password
        if service in self._temp_passwords:
            if username in self._temp_passwords[service]:
                del self._temp_passwords[service][username]

    def set_temporary_password(self, service: str, username: str, password: str) -> None:
        """
        Set a temporary password for initial setup.
        This is only stored in memory and cleared after use.
        """
        if service not in self._temp_passwords:
            self._temp_passwords[service] = {}

        self._temp_passwords[service][username] = password
        logger.info(f"Temporary password set for {service}/{username}")

    def get_temporary_password(self, service: str, username: str) -> Optional[str]:
        """
        Get a temporary password for initial setup.
        This is used only during the initialization phase.
        """
        if service in self._temp_passwords:
            if username in self._temp_passwords[service]:
                password = self._temp_passwords[service][username]
                # Clear after retrieval for security
                del self._temp_passwords[service][username]
                return password
        return None

    def generate_initialization_script(self) -> str:
        """
        Generate a script with temporary passwords for service initialization.
        This is used only during first-time setup.
        """
        script_lines = ["#!/bin/bash", "# Temporary passwords for initialization"]

        for service, users in self._temp_passwords.items():
            for username, password in users.items():
                # Export as environment variable
                env_var = f"{service.upper()}_{username.upper()}_TEMP_PASS"
                script_lines.append(f"export {env_var}='{password}'")

        return '\n'.join(script_lines)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not self.config_path.exists():
            return {}

        with open(self.config_path, 'r') as f:
            return json.load(f)

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)

        # Set restrictive permissions
        os.chmod(self.config_path, 0o600)


class PasswordManagerService:
    """
    Service class for managing passwords across the system.
    Uses Dependency Injection with the repository pattern.
    """

    def __init__(self, repository: PasswordRepositoryInterface):
        """Initialize service with password repository."""
        self.repository = repository

    def initialize_service_password(self, service: str, username: str, password: str) -> None:
        """
        Initialize a password for a service.
        Stores both the hash and a temporary copy for initial setup.
        """
        # Generate hash
        hasher = PasswordHasher()
        password_hash = hasher.hash(password)

        # Store hash
        self.repository.store_password(service, username, password_hash)

        # Store temporary password for initialization
        if hasattr(self.repository, 'set_temporary_password'):
            self.repository.set_temporary_password(service, username, password)

    def verify_service_password(self, service: str, username: str, password: str) -> bool:
        """Verify a service password."""
        return self.repository.verify_password(service, username, password)

    def update_service_password(self, service: str, username: str, new_password: str) -> None:
        """Update a service password."""
        hasher = PasswordHasher()
        new_hash = hasher.hash(new_password)
        self.repository.update_password(service, username, new_hash)

    def get_initialization_passwords(self) -> Dict[str, Dict[str, str]]:
        """
        Get temporary passwords for initialization.
        Returns a dictionary of service -> username -> password mappings.
        """
        if hasattr(self.repository, '_temp_passwords'):
            return self.repository._temp_passwords.copy()
        return {}


# Example usage for initialization
if __name__ == "__main__":
    # This would be called during the web setup process
    config_path = Path("/config/system_config.json")
    repository = SecurePasswordRepository(config_path)
    manager = PasswordManagerService(repository)

    # Example: Initialize database password
    db_password = secrets.token_urlsafe(16)
    manager.initialize_service_password("database", "authentik", db_password)

    # The temporary password can be retrieved once for initialization
    temp_pass = repository.get_temporary_password("database", "authentik")
    print(f"Temporary password for database setup: {temp_pass}")

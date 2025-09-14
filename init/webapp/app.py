#!/usr/bin/env python3
"""
Secure web-based initialization interface for Local Auth System.
Implements Factory pattern for configuration builders and Strategy pattern for password hashing.
"""

import os
import json
import secrets
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import yaml
from password_manager import SecurePasswordRepository, PasswordManagerService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration paths
CONFIG_DIR = Path("/config")
CONFIG_FILE = CONFIG_DIR / "system_config.json"
INIT_FLAG = CONFIG_DIR / ".initialized"


class PasswordHasherInterface(ABC):
    """Interface for password hashing strategies following Interface Segregation Principle."""

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash a password with salt."""
        pass

    @abstractmethod
    def verify_password(self, password: str, hash: str) -> bool:
        """Verify a password against its hash."""
        pass


class Argon2PasswordHasher(PasswordHasherInterface):
    """Concrete implementation using Argon2 hashing algorithm."""

    def __init__(self):
        """Initialize Argon2 hasher with secure parameters."""
        self.ph = PasswordHasher(
            memory_cost=65536,  # 64 MB
            time_cost=3,
            parallelism=4
        )

    def hash_password(self, password: str) -> str:
        """Hash password using Argon2id."""
        return self.ph.hash(password)

    def verify_password(self, password: str, hash: str) -> bool:
        """Verify password against Argon2 hash."""
        try:
            self.ph.verify(hash, password)
            # Check if rehashing is needed (parameters changed)
            if self.ph.check_needs_rehash(hash):
                return True  # Still valid but needs rehash
            return True
        except VerifyMismatchError:
            return False


class ConfigurationBuilder:
    """Builder pattern for creating system configuration."""

    def __init__(self, hasher: PasswordHasherInterface):
        """Initialize builder with password hasher dependency injection."""
        self.hasher = hasher
        self.config = {
            "version": "1.0",
            "security": {},
            "services": {},
            "initialized": False
        }

    def set_admin_credentials(self, email: str, password: str) -> 'ConfigurationBuilder':
        """Set admin credentials with hashed password."""
        self.config["admin"] = {
            "email": email,
            "password_hash": self.hasher.hash_password(password)
        }
        return self

    def set_database_credentials(self, username: str, password: str, database: str) -> 'ConfigurationBuilder':
        """Set database credentials with hashed password."""
        self.config["database"] = {
            "username": username,
            "password_hash": self.hasher.hash_password(password),
            "database": database,
            "host": "postgresql",
            "port": 5432
        }
        return self

    def set_ldap_configuration(self, base_dn: str, admin_password: str,
                              readonly_password: str) -> 'ConfigurationBuilder':
        """Set LDAP configuration with hashed passwords."""
        self.config["ldap"] = {
            "base_dn": base_dn,
            "admin_password_hash": self.hasher.hash_password(admin_password),
            "readonly_password_hash": self.hasher.hash_password(readonly_password),
            "host": "openldap",
            "port": 389
        }
        return self

    def set_radius_configuration(self, shared_secret: str, clients: list) -> 'ConfigurationBuilder':
        """Set RADIUS configuration with hashed secrets."""
        self.config["radius"] = {
            "shared_secret_hash": self.hasher.hash_password(shared_secret),
            "clients": clients  # Client secrets will be hashed individually
        }
        return self

    def set_security_keys(self, authentik_secret: str) -> 'ConfigurationBuilder':
        """Set security keys."""
        self.config["security"] = {
            "authentik_secret_key": authentik_secret,
            "api_token": secrets.token_urlsafe(32)
        }
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the configuration."""
        self.config["initialized"] = True
        return self.config


class ConfigurationManager:
    """Manages system configuration with secure storage."""

    def __init__(self, hasher: PasswordHasherInterface):
        """Initialize configuration manager."""
        self.hasher = hasher
        self.config_path = CONFIG_FILE
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def save_configuration(self, config: Dict[str, Any]) -> None:
        """Save configuration to secure storage."""
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
        # Set restrictive permissions
        os.chmod(self.config_path, 0o600)
        logger.info("Configuration saved securely")

    def load_configuration(self) -> Optional[Dict[str, Any]]:
        """Load configuration from storage."""
        if not self.config_path.exists():
            return None

        with open(self.config_path, 'r') as f:
            return json.load(f)

    def is_initialized(self) -> bool:
        """Check if system is already initialized."""
        return INIT_FLAG.exists()

    def mark_initialized(self) -> None:
        """Mark system as initialized."""
        INIT_FLAG.touch()

    def generate_environment_file(self, config: Dict[str, Any]) -> None:
        """Generate Docker environment file from configuration."""
        env_content = f"""# Auto-generated secure configuration
# DO NOT EDIT DIRECTLY - Use password reset scripts or web UI

# Database
PG_USER={config['database']['username']}
PG_DB={config['database']['database']}

# Admin
ADMIN_EMAIL={config['admin']['email']}

# LDAP
LDAP_BASE_DN={config['ldap']['base_dn']}

# Security
AUTHENTIK_SECRET_KEY={config['security']['authentik_secret_key']}

# Note: Passwords are stored hashed in /config/system_config.json
"""
        env_path = CONFIG_DIR / ".env.secure"
        with open(env_path, 'w') as f:
            f.write(env_content)
        os.chmod(env_path, 0o600)

    def save_initialization_passwords(self, passwords: Dict[str, str]) -> None:
        """Save temporary passwords for service initialization."""
        # Create a temporary script with passwords for initialization
        init_script = "#!/bin/bash\n# Temporary passwords for initialization\n\n"

        for key, value in passwords.items():
            init_script += f"export {key}='{value}'\n"

        script_path = CONFIG_DIR / "init_passwords.sh"
        with open(script_path, 'w') as f:
            f.write(init_script)
        os.chmod(script_path, 0o600)
        logger.info("Initialization passwords saved temporarily")


# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_urlsafe(32)
CORS(app)

# Initialize components
password_hasher = Argon2PasswordHasher()
config_manager = ConfigurationManager(password_hasher)
password_repository = SecurePasswordRepository(CONFIG_FILE)
password_service = PasswordManagerService(password_repository)


@app.route('/')
def index():
    """Serve the initialization page."""
    if config_manager.is_initialized():
        return render_template('already_initialized.html')
    return render_template('setup.html')


@app.route('/api/check-status')
def check_status():
    """Check initialization status."""
    return jsonify({
        'initialized': config_manager.is_initialized(),
        'config_exists': config_manager.load_configuration() is not None
    })


@app.route('/api/initialize', methods=['POST'])
def initialize():
    """Handle initialization form submission."""
    if config_manager.is_initialized():
        return jsonify({'error': 'System already initialized'}), 400

    try:
        data = request.json

        # Validate required fields
        required_fields = [
            'admin_email', 'admin_password', 'admin_password_confirm',
            'db_password', 'ldap_admin_password', 'ldap_readonly_password'
        ]

        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Validate password confirmation
        if data['admin_password'] != data['admin_password_confirm']:
            return jsonify({'error': 'Admin passwords do not match'}), 400

        # Validate password strength
        if len(data['admin_password']) < 12:
            return jsonify({'error': 'Admin password must be at least 12 characters'}), 400

        # Build configuration using Builder pattern
        builder = ConfigurationBuilder(password_hasher)

        # Generate secure keys
        authentik_secret = secrets.token_urlsafe(50)

        config = (builder
                 .set_admin_credentials(data['admin_email'], data['admin_password'])
                 .set_database_credentials(
                     data.get('db_username', 'authentik'),
                     data['db_password'],
                     data.get('db_name', 'authentik')
                 )
                 .set_ldap_configuration(
                     data.get('ldap_base_dn', 'dc=local,dc=auth'),
                     data['ldap_admin_password'],
                     data['ldap_readonly_password']
                 )
                 .set_radius_configuration(
                     data.get('radius_secret', secrets.token_urlsafe(16)),
                     []  # Clients will be added later
                 )
                 .set_security_keys(authentik_secret)
                 .build())

        # Save configuration
        config_manager.save_configuration(config)
        config_manager.generate_environment_file(config)

        # Store temporary passwords for service initialization
        init_passwords = {
            'DB_INIT_PASSWORD': data['db_password'],
            'LDAP_ADMIN_INIT_PASSWORD': data['ldap_admin_password'],
            'LDAP_READONLY_INIT_PASSWORD': data['ldap_readonly_password'],
            'ADMIN_INIT_PASSWORD': data['admin_password']
        }
        config_manager.save_initialization_passwords(init_passwords)

        # Also store in password manager for proper initialization
        password_service.initialize_service_password('database', 'authentik', data['db_password'])
        password_service.initialize_service_password('ldap', 'admin', data['ldap_admin_password'])
        password_service.initialize_service_password('ldap', 'readonly', data['ldap_readonly_password'])
        password_service.initialize_service_password('authentik', 'admin', data['admin_password'])

        config_manager.mark_initialized()

        # Return success with next steps
        return jsonify({
            'success': True,
            'message': 'System initialized successfully',
            'next_steps': [
                'System will now complete initialization',
                'Access Authentik at http://localhost:9000',
                'Use the admin credentials you just configured'
            ]
        })

    except Exception as e:
        logger.error(f"Initialization error: {str(e)}")
        return jsonify({'error': f'Initialization failed: {str(e)}'}), 500


@app.route('/api/generate-password')
def generate_password():
    """Generate a secure random password."""
    # Generate password with good entropy
    length = 16
    password = secrets.token_urlsafe(length)[:length]
    return jsonify({'password': password})


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    # Run with Gunicorn in production, Flask dev server for testing
    if os.environ.get('FLASK_ENV') == 'production':
        # Gunicorn will handle this
        pass
    else:
        app.run(host='0.0.0.0', port=8000, debug=True)

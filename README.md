# Local Auth System - SSO & RADIUS Authentication

A comprehensive authentication system for home networks that provides Single Sign-On (SSO) and RADIUS authentication backed by LDAP, powered by Authentik.

## Features

- **Single Sign-On (SSO)**: SAML, OAuth2/OIDC support for web applications
- **RADIUS Authentication**: For network devices (routers, switches, VPN, WiFi)
- **LDAP Backend**: Centralized user directory with OpenLDAP
- **Web GUI**: Modern interface via Authentik for user and policy management
- **RBAC**: Role-Based Access Control with groups and permissions
- **Docker-based**: Easy deployment with Docker Compose
- **Secure Setup**: Web-based initialization with Argon2 password hashing
- **Password Management**: Secure password reset scripts included

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Basic understanding of authentication concepts
- Network access to configure your devices

### Configuration Management

The system uses a smart configuration system:
- **Default Configs**: Built into Docker images from `initial-config/`
- **User Configs**: Stored in `./config/` (created automatically)
- **Auto-population**: Empty config directories are populated with defaults
- **Override**: User configs always override defaults

### Installation

1. **Clone and prepare the environment:**
   ```bash
   git clone <repository-url>
   cd local-auth
   ```

2. **Build the Docker images:**
   ```bash
   ./build.sh
   ```

3. **Start the system:**
   ```bash
   ./start.sh
   ```

4. **Complete secure web setup (first time only):**
   - Open your browser to: **http://localhost:8000**
   - Fill out the secure configuration form:
     - Set admin email and strong password (min 12 chars)
     - Configure database password
     - Set LDAP admin and readonly passwords
   - Click "Initialize System"
   - Wait for automatic initialization to complete

5. **Access the services:**
   - Authentik Web UI: **http://localhost:9000**
   - phpLDAPadmin: **http://localhost:8080**
   - Password changes: Use Authentik UI or provided scripts

## Services Overview

### Authentik (Core Authentication)
- **Port**: 9000 (HTTP), 9443 (HTTPS)
- **Purpose**: Identity Provider with SSO capabilities
- **Features**: SAML, OAuth2/OIDC, LDAP sync, policy engine

### OpenLDAP (User Directory)
- **Port**: 389 (LDAP), 636 (LDAPS)
- **Purpose**: Centralized user and group storage
- **Default Base DN**: `dc=local,dc=auth`

### FreeRADIUS (Network Authentication)
- **Port**: 1812 (Auth), 1813 (Accounting)
- **Purpose**: Network device authentication
- **Integration**: Authenticates against Authentik API

### PostgreSQL (Database)
- **Internal only**
- **Purpose**: Authentik data storage

### Redis (Cache)
- **Internal only**
- **Purpose**: Session and cache storage

## Default Users

The system creates sample users for testing:

| Username | Groups                  | Email              |
|----------|------------------------|-------------------|
| admin    | admins, all groups     | (configured during setup) |
| jdoe     | users, vpn-users       | jdoe@local.auth   |
| asmith   | users, network-admins  | asmith@local.auth |
| bwilson  | users                  | bwilson@local.auth|

**Note**: All passwords are configured securely during initial setup

## Configuration Guide

### Adding RADIUS Clients

1. **Via Environment Variable:**
   Edit `.env` file:
   ```
   RADIUS_CLIENTS=router:192.168.1.1:secret123;switch:192.168.1.10:secret456
   ```

2. **Format:**
   ```
   CLIENT_NAME:CLIENT_IP:CLIENT_SECRET;CLIENT_NAME2:CLIENT_IP2:CLIENT_SECRET2
   ```

### Configuring Network Devices

#### Cisco IOS
```cisco
aaa new-model
aaa authentication login default group radius local
aaa authorization exec default group radius local

radius server authentik
 address ipv4 YOUR_DOCKER_HOST_IP auth-port 1812 acct-port 1813
 key YOUR_RADIUS_SECRET
```

#### UniFi Controller
1. Settings → Profiles → RADIUS
2. Create profile with your Docker host IP and secret

#### pfSense
1. System → User Manager → Authentication Servers
2. Add RADIUS server with your configuration

### Adding SSO Applications

1. Login to Authentik (http://localhost:9000)
2. Navigate to Applications → Create
3. Choose provider type (SAML, OAuth2, etc.)
4. Configure according to your application's requirements

## Testing

### Test RADIUS Authentication
```bash
# Using provided test script
./config/test_radius.sh

# Or manually with radtest
radtest jdoe password123 localhost 1812 testing123
```

### Test LDAP Connection
```bash
# Search for users
ldapsearch -x -H ldap://localhost -D "cn=admin,dc=local,dc=auth" -w admin -b "dc=local,dc=auth" "(objectClass=person)"
```

## Management

### Backup
```bash
# Backup all data
docker-compose exec postgresql pg_dump -U authentik authentik > backup.sql
```

### User Management
- **Via Authentik**: http://localhost:9000 → Directory → Users
- **Via LDAP**: http://localhost:8080 (phpLDAPadmin)
- **Password Reset Scripts**:
  - `./scripts/reset-admin-password.sh` - Reset Authentik admin password
  - `./scripts/reset-ldap-password.sh` - Reset LDAP passwords
  - `./scripts/reset-database-password.sh` - Reset database password

### Monitoring
```bash
# View logs
docker-compose logs -f authentik-server
docker-compose logs -f freeradius

# Check service status
docker-compose ps
```

## Troubleshooting

### Common Issues

1. **RADIUS authentication fails**
   - Check user exists and is active in Authentik
   - Verify RADIUS client configuration matches
   - Review logs: `docker logs authentik-freeradius`

2. **LDAP connection refused**
   - Ensure LDAP service is running: `docker-compose ps openldap`
   - Check firewall rules for port 389

3. **Authentik won't start**
   - Verify PostgreSQL is running
   - Check `AUTHENTIK_SECRET_KEY` is set in `.env`
   - Review logs: `docker logs authentik-server`

### Reset Everything
```bash
# Complete cleanup and fresh start
./clean.sh
./build.sh
docker-compose up -d
```

## Security Considerations

1. **Secure Password Storage**: All passwords are hashed using Argon2id
2. **Web-based Setup**: Initial configuration through secure web interface
3. **No Plain-text Passwords**: Passwords never stored in configuration files
4. **Use strong secrets** for RADIUS clients
5. **Enable HTTPS** for production use
6. **Restrict network access** to authentication services
7. **Regular backups** of PostgreSQL database and config directory
8. **Monitor logs** for authentication failures

### Password Security
- Minimum 12 characters enforced for admin password
- Argon2id hashing with secure parameters (64MB memory, 3 iterations)
- Password strength indicator in web interface
- Secure random password generator available

## Advanced Configuration

### Custom LDAP Schema
Place custom schema files in `ldap_config` volume

### Custom Authentik Flows
1. Create flows in Authentik UI
2. Export and save to `custom-templates/`

### High Availability
For production use, consider:
- PostgreSQL replication
- Redis Sentinel
- Multiple Authentik instances
- LDAP multi-master replication

## License

This project is provided as-is for home/lab use. Please review individual component licenses:
- Authentik: MIT License
- OpenLDAP: OpenLDAP Public License
- FreeRADIUS: GPLv2
- PostgreSQL: PostgreSQL License
- Redis: BSD License

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review service logs
3. Consult component documentation:
   - [Authentik Docs](https://goauthentik.io/docs/)
   - [FreeRADIUS Wiki](https://wiki.freeradius.org/)
   - [OpenLDAP Admin Guide](https://www.openldap.org/doc/admin25/)

---

**Note**: This system is designed for home/lab environments. For production use, additional security hardening and high availability configurations are recommended.

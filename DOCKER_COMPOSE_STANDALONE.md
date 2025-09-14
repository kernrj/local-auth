# Using Local Auth System with Docker Compose (Standalone)

This guide explains how to use the Local Auth System with just the `docker-compose.yml` file, without needing to build images locally.

## Prerequisites

- Docker and Docker Compose installed
- Port availability: 389, 636, 1812/udp, 1813/udp, 8000, 8080, 9000, 9443

## Quick Start

1. **Download docker-compose.yml**
   ```bash
   wget https://raw.githubusercontent.com/your-repo/local-auth/main/docker-compose.yml
   ```

2. **Create required directories**
   ```bash
   mkdir -p postgres/{data,config}
   mkdir -p authentik/{media,custom-templates,geoip,config}
   mkdir -p ldap/{data,config}
   mkdir -p radius/{config,data}
   ```

3. **(Optional) Set environment variables**
   ```bash
   # Set secure passwords - IMPORTANT for production!
   export PG_PASS="your-secure-postgres-password"
   export AUTHENTIK_SECRET_KEY="your-secure-50-character-authentik-secret-key"
   export LDAP_ADMIN_PASSWORD="your-secure-ldap-admin-password"
   export LDAP_CONFIG_PASSWORD="your-secure-ldap-config-password"
   export LDAP_READONLY_PASSWORD="your-secure-ldap-readonly-password"

   # Optional: customize other settings
   export LDAP_ORGANISATION="Your Organization"
   export LDAP_DOMAIN="your.domain"
   export RADIUS_CLIENTS="switch1:192.168.1.10:switch-secret;router1:192.168.1.1:router-secret"
   ```

4. **Start the initialization service**
   ```bash
   docker compose up -d init
   ```

5. **Complete web-based setup**
   - Open http://localhost:8000
   - Fill in the secure setup form
   - Wait for initialization to complete

6. **Start all services**
   ```bash
   docker compose up -d
   ```

## What Happens During Initialization

When containers start with empty volumes, they automatically:

1. **FreeRADIUS**: Copies default configuration files to `/etc/freeradius`
   - radiusd.conf
   - clients.conf.default
   - mods-available/
   - sites-available/

2. **PostgreSQL**: Standard PostgreSQL initialization

3. **OpenLDAP**: Standard OpenLDAP initialization

4. **Authentik**: Uses official Authentik configuration

## Access Points

After initialization:
- **Authentik**: http://localhost:9000
- **phpLDAPadmin**: http://localhost:8080
- **Management UI**: http://localhost:8000
- **LDAP**: localhost:389 (non-TLS), localhost:636 (TLS)
- **RADIUS**: localhost:1812/udp (auth), localhost:1813/udp (accounting)

## Volume Structure

The system creates the following volume structure:
```
./
├── postgres/
│   ├── data/           # PostgreSQL data
│   └── config/         # PostgreSQL init scripts
├── authentik/
│   ├── media/          # Authentik media files
│   ├── custom-templates/   # Custom templates
│   ├── geoip/          # GeoIP data
│   └── config/         # Authentik configuration
├── ldap/
│   ├── data/           # LDAP database
│   └── config/         # LDAP configuration
└── radius/
    ├── config/         # FreeRADIUS configuration
    └── data/           # FreeRADIUS logs
```

## Environment Variables

Key variables in `.env`:
- `PG_USER`: PostgreSQL username (default: authentik)
- `PG_DB`: PostgreSQL database name (default: authentik)
- `LDAP_ORGANISATION`: LDAP organization name
- `LDAP_DOMAIN`: LDAP domain
- `LDAP_BASE_DN`: LDAP base DN
- `RADIUS_CLIENTS`: RADIUS client configuration

## Password Management

After initialization, use the provided scripts:
- Reset admin password: `./scripts/reset-admin-password.sh`
- Reset LDAP password: `./scripts/reset-ldap-password.sh`
- Reset database password: `./scripts/reset-database-password.sh`

## Troubleshooting

1. **Check container logs**
   ```bash
   docker compose logs -f [service-name]
   ```

2. **Verify all services are running**
   ```bash
   docker compose ps
   ```

3. **Reset and start fresh**
   ```bash
   docker compose down -v
   rm -rf postgres/ authentik/ ldap/ radius/
   # Then start from step 3 above
   ```

## Security Notes

- All passwords are securely hashed using Argon2
- Configuration files contain sensitive data - protect with appropriate permissions
- Use HTTPS/TLS in production environments
- Regularly update container images for security patches

# Default Configuration Files

This directory contains default configuration files that are built into the Docker images. These defaults ensure the system can start even with empty volume mounts.

## How It Works

1. **Build Time**: Default configs are copied into Docker images during build
2. **Runtime**: On container start, the `copy-defaults.sh` script checks if configs exist
3. **Copy if Missing**: If configs don't exist in the mounted volume, defaults are copied
4. **User Override**: Users can modify configs in their mounted `./config` directory

## Directory Structure

```
initial-config/
├── defaults.json          # System-wide default settings
├── copy-defaults.sh       # Script to copy defaults to volumes
├── radius/               # FreeRADIUS defaults
│   └── clients.conf.default
├── ldap/                 # OpenLDAP defaults
│   └── organization.ldif
├── authentik/            # Authentik defaults
│   └── authentik.yaml
└── postgres/             # PostgreSQL defaults
    └── init.sql
```

## Configuration Files

### defaults.json
- System-wide default values
- Service endpoints and ports
- Security settings
- Used by initialization web interface

### radius/clients.conf.default
- Default RADIUS client configurations
- Includes localhost for testing
- Template for adding network devices

### ldap/organization.ldif
- Default LDAP organizational structure
- Standard OUs (users, groups, services)
- Default groups (admins, users, network-admins)

### authentik/authentik.yaml
- Authentik service configuration
- Database and cache settings
- Default flows and policies
- Branding configuration

### postgres/init.sql
- PostgreSQL initialization script
- Performance tuning settings
- Extension creation

## Adding New Defaults

1. Add files to appropriate subdirectory
2. Update `copy-defaults.sh` to handle new files
3. Update service Dockerfile to set `SERVICE_TYPE`
4. Rebuild images with `./build.sh`

## Security Notes

- Default configs use secure defaults
- Passwords are never stored in default configs
- Secrets are generated during initialization
- Production configs should override defaults

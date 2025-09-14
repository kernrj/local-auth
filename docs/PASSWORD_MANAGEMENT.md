# Password Management Guide

This guide explains how passwords are securely managed in the Local Auth System.

## Security Architecture

### Password Storage
- **Argon2id Hashing**: All passwords are hashed using Argon2id with secure parameters
  - Memory cost: 64MB
  - Time cost: 3 iterations
  - Parallelism: 4 threads
- **No Plain Text**: Passwords are never stored in plain text in configuration files
- **Secure Configuration**: Passwords stored in `/config/system_config.json` with 0600 permissions

### Initial Setup
1. Passwords are configured through a secure web interface at http://localhost:8000
2. During initialization, temporary environment files are created for services that require passwords
3. These temporary files are automatically deleted after initialization

## Changing Passwords

### Through Authentik Web UI (Recommended)

#### Admin Password
1. Log in to Authentik at http://localhost:9000
2. Click on your username in the top right
3. Select "User Settings"
4. Click "Change Password"
5. Enter current password and new password
6. Click "Update"

#### User Passwords
1. Log in to Authentik as admin
2. Navigate to Directory → Users
3. Click on the user to edit
4. Click "Set Password"
5. Enter new password
6. Click "Update"

### Using Command Line Scripts

#### Reset Admin Password
```bash
cd /path/to/local-auth
./scripts/reset-admin-password.sh
```
- Prompts for new password (minimum 12 characters)
- Updates both configuration file and Authentik database
- No service restart required

#### Reset LDAP Passwords
```bash
cd /path/to/local-auth
./scripts/reset-ldap-password.sh
```
- Choose between admin or readonly password
- Updates configuration and LDAP directory
- Used for phpLDAPadmin access

#### Reset Database Password
```bash
cd /path/to/local-auth
./scripts/reset-database-password.sh
```
- Updates PostgreSQL password
- Automatically restarts affected services
- Updates configuration files

## Password Policies

### Authentik Password Policies
1. Navigate to Flows & Stages → Policies
2. Create a new "Password Policy"
3. Configure requirements:
   - Minimum length
   - Character requirements
   - Password history
   - Expiration settings

### LDAP Password Policies
LDAP passwords are managed through Authentik when users are synced. Configure policies in Authentik to enforce LDAP password requirements.

## RBAC and Password Permissions

### Who Can Change Passwords

| Role | Can Change Own Password | Can Change Others' Passwords |
|------|------------------------|------------------------------|
| Admin | Yes | Yes (all users) |
| Users | Yes | No |
| Service Accounts | No | No |

### Granting Password Change Permissions
1. In Authentik, create a new group (e.g., "Password Managers")
2. Assign the `authentik.change_user` permission
3. Add users to this group who need to reset others' passwords

## Security Best Practices

### Password Requirements
- **Minimum Length**: 12 characters for admin, 8 for users
- **Complexity**: Mix of uppercase, lowercase, numbers, and symbols
- **Uniqueness**: Don't reuse passwords across accounts
- **Regular Updates**: Change passwords every 90 days

### Secure Password Generation
The web interface includes a password generator that creates cryptographically secure passwords:
- Uses `secrets.token_urlsafe()` for randomness
- Generates 16-character passwords by default
- Includes mixed case, numbers, and symbols

### Audit Trail
All password changes are logged:
- Authentik logs: `/var/log/authentik/`
- System logs: Check docker logs
- Who changed what and when

## Troubleshooting

### Forgotten Admin Password
If you've forgotten the admin password:
1. Access the server with SSH/console
2. Run: `./scripts/reset-admin-password.sh`
3. Follow prompts to set new password

### Password Not Working After Reset
1. Ensure services have restarted:
   ```bash
   docker-compose restart authentik-server authentik-worker
   ```
2. Clear browser cache and cookies
3. Check logs for authentication errors

### LDAP Bind Failures
After changing LDAP password:
1. Update any applications using LDAP bind
2. Restart services that connect to LDAP
3. Test with ldapsearch:
   ```bash
   ldapsearch -x -H ldap://localhost -D "cn=admin,dc=local,dc=auth" -W
   ```

## Integration with External Systems

### RADIUS Clients
RADIUS clients authenticate through Authentik's API, so user password changes in Authentik automatically apply to RADIUS authentication.

### SSO Applications
Applications using SSO (SAML/OAuth2) automatically use updated passwords since authentication happens through Authentik.

### Direct LDAP Integration
Applications binding directly to LDAP need configuration updates when LDAP passwords change:
1. Update application's LDAP configuration
2. Use the readonly account for applications that only need to search
3. Use admin account only when necessary

## Emergency Access

### Break-Glass Procedure
In case of complete lockout:
1. Stop the authentik-server container
2. Use PostgreSQL direct access to reset admin
3. Restart services
4. Document the incident

### Backup and Recovery
Always backup before major password changes:
```bash
# Backup configuration
cp -r ./config ./config.backup.$(date +%Y%m%d)

# Backup database
docker-compose exec postgresql pg_dump -U authentik authentik > backup.sql
```

## Compliance and Auditing

### Password History
Authentik maintains password history to prevent reuse. Configure in password policies.

### Regular Audits
1. Review user accounts quarterly
2. Check for inactive accounts
3. Verify service account usage
4. Update passwords for departing users

### Compliance Requirements
The system supports common compliance requirements:
- NIST 800-63B password guidelines
- PCI-DSS password requirements
- HIPAA security rules
- SOC 2 password controls

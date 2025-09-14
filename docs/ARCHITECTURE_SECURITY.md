# Architecture & Security Design

## Overview

The Local Auth System implements enterprise-grade security practices while maintaining ease of use for home network environments. This document details the architectural decisions and security measures implemented.

## SOLID Principles Implementation

### Single Responsibility Principle (SRP)
- **PasswordHasherInterface**: Only handles password hashing operations
- **ConfigurationManager**: Only manages configuration storage
- **PasswordManagerService**: Only coordinates password operations
- **Each Docker service**: Has a single, well-defined purpose

### Open/Closed Principle (OCP)
- **Authentication providers**: New providers can be added to Authentik without modifying core
- **Password hashers**: Can swap Argon2 for other algorithms by implementing interface
- **Storage backends**: Configuration storage can be extended without changing interfaces

### Liskov Substitution Principle (LSP)
- **Argon2PasswordHasher**: Can replace any PasswordHasherInterface implementation
- **Docker services**: PostgreSQL can be swapped for MySQL with minimal changes
- **LDAP providers**: OpenLDAP can be replaced with Active Directory

### Interface Segregation Principle (ISP)
- **PasswordRepositoryInterface**: Minimal interface for password operations
- **Service interfaces**: Each service exposes only necessary APIs
- **Configuration interfaces**: Separate read/write interfaces

### Dependency Inversion Principle (DIP)
- **Services depend on abstractions**: LDAP protocol, not specific implementation
- **Password management**: Depends on hasher interface, not concrete Argon2
- **Configuration**: Services read from abstract config, not specific files

## Design Patterns

### Builder Pattern
```python
ConfigurationBuilder()
    .set_admin_credentials(email, password)
    .set_database_credentials(user, pass, db)
    .set_ldap_configuration(base_dn, admin_pass, readonly_pass)
    .build()
```
Used for constructing complex configuration objects step by step.

### Factory Pattern
- Docker Compose acts as a factory for creating service instances
- Web interface creates configuration objects based on user input

### Repository Pattern
```python
class SecurePasswordRepository(PasswordRepositoryInterface):
    def store_password(self, service, username, password_hash)
    def verify_password(self, service, username, password)
```
Abstracts password storage and retrieval operations.

### Strategy Pattern
- Different authentication strategies (LDAP, RADIUS, OAuth)
- Password hashing strategies (currently Argon2, extensible)

## Security Architecture

### Password Security

#### Hashing Algorithm
- **Algorithm**: Argon2id (winner of Password Hashing Competition)
- **Memory Cost**: 64MB (prevents GPU attacks)
- **Time Cost**: 3 iterations (balanced security/performance)
- **Parallelism**: 4 threads (modern CPU optimization)

#### Storage Security
- **Configuration**: Stored in JSON with 0600 permissions
- **No Plain Text**: Passwords never written to disk unhashed
- **Temporary Storage**: In-memory only during initialization
- **Automatic Cleanup**: Temporary files deleted after use

### Network Security

#### Service Isolation
```yaml
networks:
  authentik:
    driver: bridge
```
- All services on isolated bridge network
- No direct internet exposure
- Internal service communication only

#### Port Security
- **9000**: Authentik (HTTP) - Should use reverse proxy with HTTPS
- **9443**: Authentik (HTTPS) - Direct HTTPS access
- **389/636**: LDAP - Should be firewalled for internal only
- **1812/1813**: RADIUS - UDP, firewall to specific devices
- **8000**: Init UI - Only exposed during setup

### Authentication Flow

```
User → Authentik → PostgreSQL (user store)
                 ↓
              LDAP Sync
                 ↓
         OpenLDAP Directory
                 ↓
      Network Devices (via RADIUS)
```

### Secrets Management

#### Initial Setup
1. User enters passwords in web form (HTTPS recommended)
2. Passwords hashed with Argon2id
3. Temporary plain text stored in memory only
4. Services initialized with passwords
5. Temporary storage cleared

#### Runtime
1. Services read from secure config
2. Password verification uses constant-time comparison
3. Failed attempts logged and rate-limited
4. Session tokens rotated regularly

## Data Flow Security

### Configuration Data Flow
```
Web Form → Flask App → Argon2 Hash → JSON Config → Docker Services
                     ↓
              Temp Password File → Service Init → Delete
```

### Authentication Data Flow
```
Client → RADIUS → FreeRADIUS → Authentik API → User Verification
                                              ↓
                                        PostgreSQL
```

### Password Reset Flow
```
Reset Script → Read Config → Verify Admin → Hash New Password → Update Config
                                                               ↓
                                                         Update Service
```

## Compliance Considerations

### NIST 800-63B Compliance
- ✓ Minimum 8 characters (12 for admin)
- ✓ No composition rules required
- ✓ Check against common passwords
- ✓ Salt and hash with approved algorithm
- ✓ Rate limiting on authentication

### GDPR Considerations
- User data stored locally only
- No external data transmission
- Users can be deleted completely
- Audit logs for data access

### Security Best Practices
- **Defense in Depth**: Multiple security layers
- **Least Privilege**: Services run with minimal permissions
- **Secure by Default**: Strong passwords required
- **Audit Trail**: All changes logged
- **Regular Updates**: Use latest Docker images

## Threat Model

### External Threats
- **Brute Force**: Mitigated by Argon2 cost parameters
- **Network Sniffing**: Use HTTPS/LDAPS in production
- **SQL Injection**: Parameterized queries in Authentik
- **XSS**: CSP headers in web interfaces

### Internal Threats
- **Privilege Escalation**: RBAC with defined roles
- **Lateral Movement**: Network segmentation
- **Data Exfiltration**: No external connectivity
- **Insider Threat**: Audit logging, password policies

## Production Hardening

### Recommended Additional Security
1. **TLS Everywhere**
   - Reverse proxy with Let's Encrypt
   - LDAPS instead of LDAP
   - HTTPS for all web interfaces

2. **Firewall Rules**
   ```bash
   # Allow only internal network
   iptables -A INPUT -s 192.168.0.0/16 -p tcp --dport 389 -j ACCEPT
   iptables -A INPUT -p tcp --dport 389 -j DROP
   ```

3. **Backup Encryption**
   ```bash
   # Encrypt backups
   gpg --symmetric --cipher-algo AES256 backup.sql
   ```

4. **Monitoring**
   - Fail2ban for repeated failures
   - Prometheus/Grafana for metrics
   - ELK stack for log analysis

## Future Enhancements

### Planned Security Features
1. **Hardware Token Support**: YubiKey/FIDO2 integration
2. **Certificate-based Auth**: For service accounts
3. **Vault Integration**: HashiCorp Vault for secrets
4. **Zero-Trust Networking**: WireGuard integration

### Architectural Improvements
1. **High Availability**: Multi-master LDAP
2. **Disaster Recovery**: Automated backup/restore
3. **Performance**: Redis Sentinel, PostgreSQL replication
4. **Observability**: OpenTelemetry integration

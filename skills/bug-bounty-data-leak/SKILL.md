---
name: bug-bounty-data-leak
description: Use for sensitive data exposure testing: PII leaks, credential exposure, API key leaks, debug information, verbose errors, and unintended data access.
---

# Bug Bounty Data Leak Testing

Use this skill for finding sensitive data exposure vulnerabilities.

## PII Discovery

```bash
target="example.com"
slug="$(printf '%s' "$target" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/_/g')"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"

# Search for PII patterns in responses
pii_patterns=(
    "ssn|social.security"
    "credit.card|card.number"
    "passport"
    "driver.license"
    "date.of.birth|dob"
    "phone.number|mobile"
    "address|street|city|zip"
    "email.*list|subscriber"
)

# Search through collected responses
for pattern in "${pii_patterns[@]}"; do
    grep -riE "$pattern" "$BB_ROOT" 2>/dev/null | \
        head -20 >> "$BB_ROOT/vulns/pii-leads.txt"
done
```

## API Key/Secret Discovery

```bash
# Search for API keys in JS files
api_key_patterns=(
    "api[_-]?key['\"]?\\s*[:=]\\s*['\"][a-zA-Z0-9]{20,}['\"]"
    "api[_-]?secret['\"]?\\s*[:=]\\s*['\"][a-zA-Z0-9]{20,}['\"]"
    "access[_-]?token['\"]?\\s*[:=]\\s*['\"][a-zA-Z0-9]{20,}['\"]"
    "secret[_-]?key['\"]?\\s*[:=]\\s*['\"][a-zA-Z0-9]{20,}['\"]"
    "AKIA[0-9A-Z]{16}"  # AWS Access Key
    "AIza[0-9A-Za-z\\-_]{35}"  # Google API Key
    "ghp_[0-9a-zA-Z]{36}"  # GitHub PAT
    "xox[baprs]-[0-9]{10,12}-[0-9]{10,12}-[a-zA-Z0-9]{24}"  # Slack Token
)

for pattern in "${api_key_patterns[@]}"; do
    grep -roPE "$pattern" "$BB_ROOT/content/js/" 2>/dev/null | \
        sort -u >> "$BB_ROOT/vulns/api-keys-found.txt"
done
```

## Debug Information Exposure

```bash
# Search for debug endpoints
debug_paths=(
    "/debug"
    "/debug/pprof"
    "/debug/vars"
    "/actuator"
    "/actuator/health"
    "/actuator/env"
    "/metrics"
    "/prometheus"
    "/server-status"
    "/phpinfo.php"
    "/info.php"
    "/test.php"
    "/elmah.axd"
)

for path in "${debug_paths[@]}"; do
    curl -sk "https://$target$path" | \
        grep -iE "debug|stack|trace|error|exception" && \
        echo "Debug endpoint: $path" >> "$BB_ROOT/vulns/debug-endpoints.txt"
done
```

## Verbose Error Messages

```bash
# Trigger errors with malformed requests
# SQL error
curl -sk "https://$target/search?q=' OR 1=1--" | \
    grep -iE "sql|syntax|mysql|postgres|oracle" >> "$BB_ROOT/vulns/sql-errors.txt"

# Path traversal error
curl -sk "https://$target/page?file=../../etc/passwd" | \
    grep -iE "path|file|directory|permission" >> "$BB_ROOT/vulns/path-errors.txt"

# Type mismatch errors
curl -sk "https://$target/api/users/invalid_json" | \
    grep -iE "json|parse|type|exception" >> "$BB_ROOT/vulns/type-errors.txt"
```

## .git Exposure

```bash
# Check for .git directory
curl -sk "https://$target/.git/" | \
    grep -i "index of\|directory" && \
    echo ".git directory exposed!" >> "$BB_ROOT/vulns/git-exposure.txt"

# Check for .git/config
curl -sk "https://$target/.git/config" | \
    grep -i "repositoryformatversion" && \
    echo ".git/config exposed!" >> "$BB_ROOT/vulns/git-exposure.txt"

# Check for .git/HEAD
curl -sk "https://$target/.git/HEAD" | \
    grep -i "ref:" && \
    echo ".git/HEAD exposed!" >> "$BB_ROOT/vulns/git-exposure.txt"
```

## .env Exposure

```bash
# Check for .env files
env_paths=("/.env" "/.env.local" "/.env.production" "/.env.dev" "/api/.env" "/app/.env")

for path in "${env_paths[@]}"; do
    curl -sk "https://$target$path" | \
        grep -iE "db_|database_|mysql_|postgres_|redis_|aws_|secret_|api_" && \
        echo ".env exposed: $path" >> "$BB_ROOT/vulns/env-exposure.txt"
done
```

## Backup File Discovery

```bash
# Check for backup files
backup_extensions=(
    ".bak" ".backup" ".old" ".orig" ".save"
    ".sql" ".db" ".sqlite"
    ".tar" ".tar.gz" ".zip"
    ".swp" ".swo"
    "~" "#"
)

for ext in "${backup_extensions[@]}"; do
    curl -skI "https://$target/config$ext" | \
        grep -i "200\|ok" && \
        echo "Backup found: config$ext" >> "$BB_ROOT/vulns/backup-files.txt"
done
```

## Directory Listing

```bash
# Check for directory listing
dirs=("/uploads/" "/files/" "/images/" "/backup/" "/config/" "/admin/" "/api/")

for dir in "${dirs[@]}"; do
    curl -sk "https://$target$dir" | \
        grep -iE "index of|directory|parent directory" && \
        echo "Directory listing: $dir" >> "$BB_ROOT/vulns/dir-listing.txt"
done
```

## S3 Bucket Discovery

```bash
# Search for S3 references
grep -roE "s3[.-]amazonaws[.]com/[a-zA-Z0-9.-]+" "$BB_ROOT" 2>/dev/null | \
    sort -u > "$BB_ROOT/cloud/s3-references.txt"

# Check if buckets are accessible
while read -r bucket; do
    curl -sI "https://$bucket" | \
        grep -i "200\|403" && \
        echo "S3 bucket: $bucket" >> "$BB_ROOT/cloud/s3-status.txt"
done < "$BB_ROOT/cloud/s3-references.txt"
```

## Database Dump Discovery

```bash
# Search for database dumps
db_dumps=("dump.sql" "db.sql" "database.sql" "backup.sql" "data.sql" "export.sql")

for dump in "${db_dumps[@]}"; do
    curl -skI "https://$target/$dump" | \
        grep -i "200\|ok" && \
        echo "Database dump found: $dump" >> "$BB_ROOT/vulns/db-dumps.txt"
done
```

## Data Leak Checklist

- [ ] PII in responses (SSN, credit cards, etc.)
- [ ] API keys/secrets in JS files
- [ ] AWS credentials exposed
- [ ] Debug endpoints accessible
- [ ] Verbose error messages
- [ ] Stack traces exposed
- [ ] .git directory exposed
- [ ] .env files accessible
- [ ] Backup files discoverable
- [ ] Directory listing enabled
- [ ] S3 buckets open
- [ ] Database dumps accessible
- [ ] Log files exposed
- [ ] Config files readable
- [ ] User data accessible via IDOR

## Data Leak Tools

- `trufflehog` - Secret scanning
- `gitleaks` - Git secret scanning
- `shhgit` - GitHub secret monitoring
- `nuclei` - Exposure templates
- `grep`/`rg` - Pattern matching
- `curl` - Manual testing

## Reporting Data Leaks

```markdown
## Sensitive Data Exposure

**Type:** API Key Exposure / PII Leak / Config File / etc.
**Location:** https://target.com/js/app.js
**Data Type:** AWS Access Keys / User PII / Database Credentials

**Evidence:**
- File: `vulns/api-keys-found.txt`
- Pattern: `AKIA...`
- Count: 3 keys found

**Impact:**
- AWS account compromise
- Data breach
- Lateral movement
- Financial loss

**Remediation:**
- Remove hardcoded credentials
- Use environment variables
- Implement secret management
- Rotate exposed keys immediately
```

## Severity Classification

| Data Type | Severity |
|-----------|----------|
| AWS/Cloud credentials | Critical |
| Database credentials | Critical |
| PII (SSN, credit cards) | Critical/High |
| API keys (internal) | High |
| User emails/passwords | High |
| Internal docs | Medium |
| Stack traces | Medium |
| Directory listing | Low/Medium |
| Version info | Low |

## Safety Rules

- Only test within authorized scope boundaries.
- Use self-owned test accounts exclusively. Never test on real user accounts.
- No destructive operations: no data deletion, no DoS, no real data exfiltration.
- Require explicit approval before active scanning, brute-force, or high-volume requests.
- All findings must be manually validated before reporting.

## Output Convention

All commands must save output to organized paths:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
# stdout -> $BB_ROOT/<phase>/<tool>-$ts.txt
# stderr -> $BB_ROOT/logs/<tool>-$ts.err
```

Never dump raw tool output into chat context. Save to files, then read targeted excerpts.
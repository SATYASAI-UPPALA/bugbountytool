---
name: bug-bounty-api-security
description: Use for REST API, SOAP, gRPC security testing: authentication flaws, rate limiting, mass assignment, batch requests, pagination abuse, and API-specific injection.
---

# Bug Bounty API Security Testing

Use this skill for modern API testing (REST, GraphQL, gRPC, SOAP).

## API Discovery

```bash
target="example.com"
slug="$(printf '%s' "$target" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/_/g')"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"

# Find API endpoints
## OpenAPI/Swagger
curl -sk "https://$target/swagger.json" | jq '.' > "$BB_ROOT/api/swagger.json" 2>/dev/null
curl -sk "https://$target/openapi.json" | jq '.' > "$BB_ROOT/api/openapi.json" 2>/dev/null
curl -sk "https://$target/v1/swagger.json" | jq '.' > "$BB_ROOT/api/swagger-v1.json" 2>/dev/null

## API endpoints from historical URLs
gau "$target" | grep -iE "/api/|/v[0-9]/|graphql|rest" | sort -u > "$BB_ROOT/api/endpoints.txt"

## Common API paths
api_paths=("/api" "/api/v1" "/api/v2" "/api/v3" "/v1" "/v2" "/v3" "/rest" "/graphql" "/gql" "/webservice")
for path in "${api_paths[@]}"; do
    curl -sk -o /dev/null -w "%{http_code} $path\n" "https://$target$path" >> "$BB_ROOT/api/probe-results.txt"
done
```

## Authentication Testing

```bash
# Test missing auth
curl -sk "https://$target/api/v1/users" -H "Accept: application/json"

# Test weak auth (Bearer token manipulation)
curl -sk "https://$target/api/v1/users" \
    -H "Authorization: Bearer invalid_token" \
    -H "Accept: application/json"

# Test token reuse across endpoints
# Capture token from one request, test on others
```

## Rate Limiting Testing

```bash
# Test rate limits (only if ROE allows)
for i in {1..50}; do
    curl -sk -X POST "https://$target/api/v1/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@example.com","password":"wrongpass"}' \
        -o /dev/null -w "%{http_code} " &
done
wait
# Check for 429 Too Many Requests responses
```

## Mass Assignment Testing

```bash
# Test if you can set admin/role fields
curl -sk -X PUT "https://$target/api/v1/users/me" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -d '{"name":"Test","email":"test@example.com","role":"admin","is_admin":true}'

# Check if role/privilege fields are accepted
```

## Batch Request Abuse

```bash
# Test batch endpoints
curl -sk -X POST "https://$target/api/v1/batch" \
    -H "Content-Type: application/json" \
    -d '{"requests":[{"endpoint":"/users/1"},{"endpoint":"/users/2"},{"endpoint":"/users/3"}]}'

# Test if you can access other users' data via batch
```

## Pagination Abuse

```bash
# Test pagination limits
curl -sk "https://$target/api/v1/users?limit=10000&offset=0"
curl -sk "https://$target/api/v1/users?page=1&pageSize=10000"

# Check if excessive data is returned
```

## gRPC Testing

```bash
# Enumerate gRPC services (requires grpcurl)
grpcurl -plaintext $target:port list

# Call gRPC methods
grpcurl -plaintext -d '{"id":"123"}' $target:port package.Service/Method

# gRPC fuzzing
grpcfuzz -target $target:port -method package.Service/Method
```

## API Security Checklist

- [ ] Authentication required on all endpoints
- [ ] Rate limiting implemented
- [ ] Input validation on all parameters
- [ ] No mass assignment vulnerabilities
- [ ] Proper authorization checks (IDOR testing)
- [ ] No verbose error messages
- [ ] Pagination limits enforced
- [ ] Batch request limits in place
- [ ] No sensitive data in responses
- [ ] Proper CORS configuration
- [ ] API versioning secure (old versions deprecated)

## API Tools

- `postman` - API testing
- `insomnia` - API client
- `grpcurl` - gRPC testing
- `burpsuite` - API scanning
- `nuclei` - API templates
- `ffuf` - API fuzzing
- `arjun` - Parameter discovery
- `paramspider` - Parameter extraction

## Reporting API Findings

| Severity | Finding |
|----------|---------|
| **Critical** | Auth bypass on sensitive endpoints |
| **High** | IDOR allowing access to other users' data |
| **High** | Mass assignment leading to privilege escalation |
| **High** | No rate limiting on auth/password reset |
| **Medium** | Verbose error messages |
| **Medium** | Missing pagination limits |
| **Low** | Deprecated API versions still accessible |

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

## Approval Checkpoints

Require explicit approval before:
- Rate limiting tests (concurrent/high-volume requests)
- Brute-force or enumeration attempts
- Any active scanning against production endpoints
- Mass assignment or privilege escalation attempts
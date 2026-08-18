---
name: bug-bounty-auth-session
description: Use for authentication, OAuth/OIDC, JWT, password reset, MFA, session management, rate limiting, account recovery, invite flows, and credential attack boundary analysis.
---

# Bug Bounty Auth And Session

Use this skill for auth and session workflows after the orchestrator confirms scope, allowed test accounts, and forbidden actions.

## Safety Rules

- Use only self-owned or program-provided test accounts.
- Do not brute force, password spray, or credential stuff unless explicitly authorized.
- Never bypass MFA on real users or test live customer accounts.
- Save requests and responses to files with tokens redacted in reports.

## Workflow

1. Map auth surfaces: register, login, logout, refresh, reset, MFA, magic link, invite, OAuth/OIDC, SSO, API tokens.
2. Identify tokens: session cookies, JWTs, refresh tokens, CSRF tokens, device IDs.
3. Test workflow state: replay, expiration, invalidation, token rotation, downgrade, role changes, callback URLs.
4. Test rate limits only within ROE.
5. Validate impact with self-owned accounts.

## Browser-Based Auth Capture

If the target has a manifest in `~/Desktop/opencode-bugbounty-browser/targets/`, use the browser tools for auth:

1. `auth_check` — check if a saved session already exists.
2. `auth_start` — opens a visible Chromium at the target's login page.
3. User logs in manually (agent never enters credentials).
4. `auth_complete` — saves cookies/localStorage securely (mode 600).
5. `bb_browser_crawl` or `bb_browser_use` — automatically load the saved session for authenticated page inventory.

This is the preferred method when the target needs authenticated browser analysis (vs. curl/Burp token-based testing).

## Commands

JWT triage:

```bash
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
mkdir -p "$BB_ROOT"/{vulns,logs,tmp}
token="PASTE_JWT_HERE"
ts="$(date +%Y%m%d-%H%M%S)"
printf '%s' "$token" | cut -d. -f1 | base64 -d 2> "$BB_ROOT/logs/jwt-header-$ts.err" | jq '.' > "$BB_ROOT/vulns/jwt-header-$ts.json" 2>> "$BB_ROOT/logs/jwt-header-$ts.err"
printf '%s' "$token" | cut -d. -f2 | base64 -d 2> "$BB_ROOT/logs/jwt-body-$ts.err" | jq '.' > "$BB_ROOT/vulns/jwt-body-$ts.json" 2>> "$BB_ROOT/logs/jwt-body-$ts.err"
jq '{alg, typ, kid}' "$BB_ROOT/vulns/jwt-header-$ts.json"
jq '{iss, aud, exp, iat, sub, role, scope}' "$BB_ROOT/vulns/jwt-body-$ts.json"
```

Cookie flag triage:

```bash
url="https://example.com/login"
ts="$(date +%Y%m%d-%H%M%S)"
curl -sk -D "$BB_ROOT/vulns/auth-headers-$ts.txt" -o "$BB_ROOT/vulns/auth-body-$ts.txt" "$url" > "$BB_ROOT/logs/auth-$ts.out" 2> "$BB_ROOT/logs/auth-$ts.err"
rg -n "set-cookie|secure|httponly|samesite|location|csrf|state|nonce" "$BB_ROOT/vulns/auth-headers-$ts.txt" "$BB_ROOT/vulns/auth-body-$ts.txt"
```

## Tool Map

- Manual workflow testing: Burp Suite, `curl`, browser devtools.
- JWT review: `jq`, `base64`, `jwt_tool` when available.
- Rate-limit evidence: `ffuf`, `wfuzz`, `hydra` only if explicitly authorized and low-rate.
- Password/reset logic: manual replay, timing, token reuse, redirect checks.
- OAuth/OIDC: redirect URI, state, nonce, PKCE, token audience, issuer, callback confusion.

## Evidence Criteria

Valid auth findings need:

- Affected flow and preconditions.
- Self-owned account proof.
- Token/session state before and after.
- Clear business impact.
- No unauthorized account access.

## Output Convention

All commands must save output to organized paths:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
# stdout -> $BB_ROOT/<phase>/<tool>-$ts.txt
# stderr -> $BB_ROOT/logs/<tool>-$ts.err
```

Never dump raw tool output into chat context. Save to files, then read targeted excerpts.

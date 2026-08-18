---
name: bug-bounty-csrf-ssrf-advanced
description: Use for advanced CSRF and SSRF testing: CSRF token bypass, SameSite cookie issues, SSRF with protocol smuggling, DNS rebinding, and advanced redirect chains.
---

# CSRF & SSRF Advanced Testing

This skill covers advanced Cross-Site Request Forgery and Server-Side Request Forgery techniques.

## Safety Rules

- Only test within authorized scope boundaries.
- Use self-owned test accounts exclusively. Never test on real user accounts.
- No destructive operations: no data deletion, no DoS, no real data exfiltration.
- Require explicit approval before active scanning or high-volume requests.
- All findings must be manually validated before reporting.

## CSRF Testing

### Token Bypass
- Remove CSRF token entirely
- Use empty token value
- Reuse old/expired tokens
- Test cross-origin token sharing
- Check if token is tied to session

### SameSite Cookie Testing
```bash
# Check SameSite cookie attributes
curl -sI "$url" | grep -i "set-cookie" | grep -i "samesite"
# Test cross-origin form submission
```

### CSRF PoC Generation
```bash
# Generate auto-submit form PoC (use only for authorized testing)
cat > "$BB_ROOT/vulns/csrf-poc.html" << 'POCEOF'
<html><body>
<form id="csrf" action="TARGET_URL" method="POST">
  <input type="hidden" name="param" value="value">
</form>
<script>document.getElementById('csrf').submit();</script>
</body></html>
POCEOF
```

## Advanced SSRF Techniques

### DNS Rebinding
- Use rebinding services (e.g., rbndr.us) to bypass allowlists
- Monitor DNS TTL and time-of-check to time-of-use gaps

### Protocol Smuggling
- Test gopher://, dict://, file:// protocol handlers
- Test URL encoding bypass (double encoding, Unicode normalization)

### Redirect Chain SSRF
```bash
# Test open redirect chaining to internal resources
curl -sL "$url/redirect?url=http://127.0.0.1:8080/admin" -o "$BB_ROOT/vulns/ssrf-redirect-test.txt" 2>/dev/null
```

## CSRF/SSRF Checklist

- [ ] CSRF token present on all state-changing requests
- [ ] Token tied to user session
- [ ] SameSite cookie attribute set properly
- [ ] Referer/Origin header validation
- [ ] SSRF: internal IP/hostname blocked
- [ ] SSRF: redirect following disabled or validated
- [ ] SSRF: protocol allowlist enforced
- [ ] DNS rebinding protection

## Output Convention

All commands must save output to organized paths:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
# stdout -> $BB_ROOT/<phase>/<tool>-$ts.txt
# stderr -> $BB_ROOT/logs/<tool>-$ts.err
```

Never dump raw tool output into chat context. Save to files, then read targeted excerpts.

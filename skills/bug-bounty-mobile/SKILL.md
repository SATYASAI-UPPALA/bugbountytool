---
name: bug-bounty-mobile
description: Use for mobile application security testing: APK/IPA analysis, mobile API testing, certificate pinning bypass, local storage analysis, and mobile-specific vulnerability testing.
---

# Mobile Application Security Testing

This skill covers Android and iOS application security testing.

## Safety Rules

- Only test within authorized scope boundaries.
- Use self-owned test accounts and devices exclusively.
- No destructive operations or data exfiltration.
- Require explicit approval before active testing.
- All findings must be manually validated before reporting.

## Android APK Analysis

```bash
target="example.com"
slug=$(echo "$target" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/_/g')
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
mkdir -p "$BB_ROOT"/{mobile/{apk,api,secrets},vulns/{critical,high,medium},logs}

# Decompile APK
apktool d app.apk -o "$BB_ROOT/mobile/apk/decompiled/"

# Extract strings and secrets
grep -rn "api_key\|secret\|password\|token\|http://\|https://" \
    "$BB_ROOT/mobile/apk/decompiled/" > "$BB_ROOT/mobile/secrets/strings-found.txt"

# Check for hardcoded URLs
grep -rnoP 'https?://[^"'\''\\s]+' "$BB_ROOT/mobile/apk/decompiled/" | \
    sort -u > "$BB_ROOT/mobile/api/endpoints.txt"
```

## Mobile API Testing

```bash
# Test mobile API endpoints found in APK
while read -r ENDPOINT; do
    curl -s -o /dev/null -w "%{http_code} $ENDPOINT\n" "$ENDPOINT" >> "$BB_ROOT/mobile/api/api-probe.txt"
done < "$BB_ROOT/mobile/api/endpoints.txt"
```

## Certificate Pinning Check

- Use Frida/Objection to bypass certificate pinning
- Proxy traffic through Burp Suite
- Check for improper TLS validation

## Mobile Security Checklist

- [ ] APK/IPA decompilation and static analysis
- [ ] Hardcoded secrets and API keys
- [ ] Insecure data storage (SharedPreferences, Keychain)
- [ ] Certificate pinning implementation
- [ ] Mobile API endpoint security
- [ ] WebView vulnerabilities
- [ ] Intent/deep link handling
- [ ] Root/jailbreak detection bypass
- [ ] Clipboard data exposure
- [ ] Debug mode enabled in production

## Tools

- apktool, jadx, dex2jar — APK decompilation
- frida, objection — Runtime hooking
- mobsf — Automated mobile security framework
- Burp Suite — API traffic interception

## Output Convention

All commands must save output to organized paths:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
# stdout -> $BB_ROOT/<phase>/<tool>-$ts.txt
# stderr -> $BB_ROOT/logs/<tool>-$ts.err
```

Never dump raw tool output into chat context. Save to files, then read targeted excerpts.

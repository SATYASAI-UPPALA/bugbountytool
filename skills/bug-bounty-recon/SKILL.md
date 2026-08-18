---
name: bug-bounty-recon
description: Use for bug bounty reconnaissance: passive subdomain discovery, DNS validation, HTTP probing, port mapping, technology fingerprinting, recon output analysis, and adaptive wordlist selection based on tech stack.
---

# Bug Bounty Recon

Use passive recon first. Move to active recon only after scope and authorization are clear.

**Note:** For the full recon flow (passive → merge → active, with adaptive widening/WAF handling), follow the Adaptive Execution Loop in `bug-bounty-orchestrator/SKILL.md` — same commands, run by you one at a time rather than by a script.

## Adaptive Wordlist Selection

Pick the wordlist yourself based on what httpx's `-tech-detect` output shows for a host, before you fuzz it:

| Tech Detected | Wordlist | Purpose |
|---------------|----------|---------|
| Spring Boot / Java | `spring-boot.txt` | Actuator endpoints, Spring paths |
| PHP / Laravel | `php-pages.txt` + `common.txt` | PHP files, LFI paths |
| API / GraphQL | `api-endpoints.txt` + `graphql.txt` | REST routes, GraphQL ops |
| SPA (React/Vue/Angular) | Client-side routes | `/login`, `/dashboard`, `/admin` |
| Default | `common.txt` → `raft-medium.txt` → `big.txt` | Escalating coverage |

## Passive Recon Commands

Set the target and output root first:

```bash
target="example.com"
slug="$(printf '%s' "$target" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/_/g')"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
mkdir -p "$BB_ROOT"/{scope,passive,active,content,params,js,vulns,reports,logs,tmp}
```

Run passive sources into files:

```bash
ts="$(date +%Y%m%d-%H%M%S)"; subfinder -silent -all -d "$target" > "$BB_ROOT/passive/subfinder-$ts.txt" 2> "$BB_ROOT/logs/subfinder-$ts.err"
ts="$(date +%Y%m%d-%H%M%S)"; amass enum -passive -d "$target" > "$BB_ROOT/passive/amass-passive-$ts.txt" 2> "$BB_ROOT/logs/amass-passive-$ts.err"
ts="$(date +%Y%m%d-%H%M%S)"; assetfinder --subs-only "$target" > "$BB_ROOT/passive/assetfinder-$ts.txt" 2> "$BB_ROOT/logs/assetfinder-$ts.err"
```

Merge and normalize:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
find "$BB_ROOT/passive" -type f -name '*.txt' -exec sed 's/^\*\.//' {} + | tr '[:upper:]' '[:lower:]' | sed '/^$/d' | sort -u > "$BB_ROOT/passive/subdomains-merged-$ts.txt" 2> "$BB_ROOT/logs/subdomains-merged-$ts.err"
latest_subs="$(ls -t "$BB_ROOT"/passive/subdomains-merged-*.txt | sed -n '1p')"
wc -l "$latest_subs"
sed -n '1,80p' "$latest_subs"
```

## Active Recon Commands

Ask for approval before these. Keep rates conservative unless the rules of engagement allow more.

```bash
latest_subs="$(ls -t "$BB_ROOT"/passive/subdomains-merged-*.txt | sed -n '1p')"
ts="$(date +%Y%m%d-%H%M%S)"; dnsx -silent -a -aaaa -cname -resp -l "$latest_subs" > "$BB_ROOT/active/dnsx-$ts.txt" 2> "$BB_ROOT/logs/dnsx-$ts.err"
ts="$(date +%Y%m%d-%H%M%S)"; httpx -silent -json -title -tech-detect -status-code -content-length -follow-host-redirects -rate-limit 25 -l "$latest_subs" > "$BB_ROOT/active/httpx-$ts.jsonl" 2> "$BB_ROOT/logs/httpx-$ts.err"
ts="$(date +%Y%m%d-%H%M%S)"; naabu -silent -rate 50 -top-ports 100 -l "$latest_subs" > "$BB_ROOT/active/naabu-top100-$ts.txt" 2> "$BB_ROOT/logs/naabu-top100-$ts.err"
```

Only use `nmap` on confirmed in-scope hosts and small host sets:

```bash
hosts_file="$BB_ROOT/active/nmap-hosts.txt"
ts="$(date +%Y%m%d-%H%M%S)"; nmap -sV -sC -Pn --top-ports 100 --max-rate 50 -iL "$hosts_file" -oA "$BB_ROOT/active/nmap-top100-$ts" > "$BB_ROOT/logs/nmap-top100-$ts.out" 2> "$BB_ROOT/logs/nmap-top100-$ts.err"
```

Avoid `masscan` unless explicitly authorized with rate limits.

## Recon Analysis with Adaptive Intelligence

Use narrow reads and look for adaptive signals:

```bash
latest_httpx="$(ls -t "$BB_ROOT"/active/httpx-*.jsonl | sed -n '1p')"
jq -r '[.url, .status_code, .title, (.tech // [] | join(","))] | @tsv' "$latest_httpx" | sort -u | sed -n '1,120p'
jq -r 'select(.status_code == 200 or .status_code == 401 or .status_code == 403) | .url' "$latest_httpx" | sort -u > "$BB_ROOT/active/live-interesting-$(date +%Y%m%d-%H%M%S).txt"
rg -n "swagger|openapi|graphql|actuator|admin|debug|metrics|prometheus|jenkins|gitlab|jira|confluence" "$latest_httpx"
```

### Adaptive Signals to Watch For

After recon, check for these signals that trigger adaptive behavior:

```bash
# GraphQL detected?
if grep -qi "graphql" "$BB_ROOT/active/httpx-*.jsonl"; then
    echo "[!] GraphQL detected - enable GraphQL introspection testing"
fi

# Spring Boot actuator?
if grep -qi "actuator\|spring" "$BB_ROOT/active/httpx-*.jsonl"; then
    echo "[!] Spring Boot detected - use spring-boot.txt wordlist"
fi

# API framework?
if grep -qi "express\|fastapi\|flask\|django\|rails" "$BB_ROOT/active/httpx-*.jsonl"; then
    echo "[!] API framework detected - prioritize API fuzzing"
fi

# SPA detected?
if grep -qi "react\|angular\|vue\|next\|nuxt" "$BB_ROOT/active/httpx-*.jsonl"; then
    echo "[!] SPA detected - probe client-side routes"
fi

# WAF/CDN detected?
if grep -qi "cloudflare\|cloudfront\|akamai\|fastly" "$BB_ROOT/active/waf-*.txt"; then
    echo "[!] WAF/CDN detected - use stealth rates, probe origin IP"
fi
```

### Subdomain Widening Logic

If fewer than 10 subdomains found, widen the search:

```bash
sub_count=$(wc -l < "$BB_ROOT/passive/subdomains-merged-*.txt" | tail -1 | awk '{print $1}')
if [ "$sub_count" -lt 10 ]; then
    echo "[*] Few subdomains found - widening search..."
    curl -s "https://api.hackertarget.com/hostsearch/?q=$target" | cut -d, -f1 >> "$BB_ROOT/passive/all-subs.txt"
    curl -s "https://api.sublist3r.com/search.php?domain=$target" | jq -r '.[]' >> "$BB_ROOT/passive/all-subs.txt" 2>/dev/null || true
    sort -u "$BB_ROOT/passive/all-subs.txt" -o "$BB_ROOT/passive/all-subs.txt"
fi
```

## Priority Assets

Prioritize assets with:
- Authentication boundaries (401/403 responses)
- Admin panels, exposed docs, debug endpoints
- Cloud storage keywords (S3, CloudFront, blob.core)
- Unusual status codes (500, 502, 503 - potential edge cases)
- Modern JS-heavy applications (React, Vue, Angular)
- API endpoints with parameters (SSRF, IDOR potential)
- GraphQL endpoints (introspection, complex queries)
- Cloud metadata paths (169.254.169.254 probes if SSRF confirmed)

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

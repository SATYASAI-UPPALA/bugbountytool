---
name: bug-bounty-network-infra
description: Use for authorized network and infrastructure bug bounty testing: service discovery, nmap/naabu triage, TLS checks, WAF/CDN fingerprinting, default exposures, and infrastructure misconfiguration review.
---

# Bug Bounty Network And Infrastructure

Use this skill when the orchestrator needs service-level visibility or infrastructure misconfiguration checks. Active network scanning always requires clear scope and approval.

## Safety Rules

- Confirm CIDRs, IPs, hostnames, ports, and rate limits before scanning.
- Avoid high-rate scanning unless explicitly authorized.
- Do not run exploit modules, default credential checks, or brute force without explicit written permission.
- Save outputs with `-oA`, JSON, or text files and read back only key lines.

## Low-Noise Service Discovery

```bash
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
mkdir -p "$BB_ROOT"/{active,vulns,logs,tmp}
hosts_file="$BB_ROOT/active/hosts-in-scope.txt"
ts="$(date +%Y%m%d-%H%M%S)"
naabu -silent -rate 50 -top-ports 100 -l "$hosts_file" > "$BB_ROOT/active/naabu-top100-$ts.txt" 2> "$BB_ROOT/logs/naabu-top100-$ts.err"
nmap -sV -sC -Pn --top-ports 100 --max-rate 50 -iL "$hosts_file" -oA "$BB_ROOT/active/nmap-top100-$ts" > "$BB_ROOT/logs/nmap-top100-$ts.out" 2> "$BB_ROOT/logs/nmap-top100-$ts.err"
rg -n "open|http|ssl|ssh|ftp|rdp|smb|vnc|redis|mongo|elastic|kibana|jenkins|grafana|prometheus" "$BB_ROOT/active/nmap-top100-$ts.nmap" "$BB_ROOT/active/naabu-top100-$ts.txt"
```

## HTTP/TLS/WAF Triage

```bash
url="https://example.com"
ts="$(date +%Y%m%d-%H%M%S)"
whatweb "$url" > "$BB_ROOT/active/whatweb-$ts.txt" 2> "$BB_ROOT/logs/whatweb-$ts.err"
wafw00f "$url" > "$BB_ROOT/active/wafw00f-$ts.txt" 2> "$BB_ROOT/logs/wafw00f-$ts.err"
curl -skI "$url" > "$BB_ROOT/active/headers-$ts.txt" 2> "$BB_ROOT/logs/headers-$ts.err"
rg -n "Server:|X-Powered-By|Set-Cookie|Strict-Transport|Content-Security|Access-Control|WAF|Cloudflare|Akamai|Fastly" "$BB_ROOT/active" | sed -n '1,120p'
```

## Tool Map

- Discovery: `dnsx`, `httpx`, `naabu`, `nmap`.
- High-rate discovery: `masscan` only when explicitly allowed with rate limits.
- Web stack fingerprinting: `whatweb`, `wafw00f`, `nikto`, `curl`.
- Vulnerability triage: `nuclei`, `searchsploit`, `metasploit` only for safe checks or explicitly authorized modules.
- Credentials: `hydra`, `john`, `hashcat` only for authorized test credentials, hashes, or lab artifacts.
- TLS: `openssl s_client`, `nmap --script ssl-*`, `testssl.sh` if installed.

## Candidate Findings

Prioritize:

- Public admin panels.
- Exposed metrics, debug, actuator, Prometheus, Grafana, Jenkins, Kibana.
- Unauthenticated databases or queues.
- Sensitive headers or weak TLS.
- Default credentials only when testing is explicitly authorized.
- Services outside expected exposure.

## Output Convention

All commands must save output to organized paths:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
# stdout -> $BB_ROOT/<phase>/<tool>-$ts.txt
# stderr -> $BB_ROOT/logs/<tool>-$ts.err
```

Never dump raw tool output into chat context. Save to files, then read targeted excerpts.

## Network Testing Checklist

- [ ] Port scan (naabu quick + nmap targeted)
- [ ] Service version identification
- [ ] TLS certificate and configuration check
- [ ] WAF/CDN detection and fingerprinting
- [ ] Default credentials check on exposed services
- [ ] DNS misconfiguration (zone transfer, dangling CNAME)
- [ ] Exposed admin panels (Jenkins, Grafana, phpMyAdmin)
- [ ] SNMP community string check
- [ ] SSH weak algorithms check

## Reporting Template

- **Type:** [Service exposure / Misconfiguration / Weak TLS / Default credentials]
- **Severity:** [Critical / High / Medium / Low]
- **Host:Port:**
- **Service:**
- **Evidence:**
- **Impact:**
- **Remediation:**

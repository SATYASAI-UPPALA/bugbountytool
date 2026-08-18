---
name: bug-bounty-injection
description: Use for SQL injection, NoSQL injection, command injection, SSTI, XXE, path traversal, unsafe deserialization, template injection, and parser confusion testing.
---

# Bug Bounty Injection

Use this skill when the orchestrator identifies parameters, request bodies, headers, file parsers, templates, or backend integrations that may process attacker-controlled input.

## Safety Rules

- Do not dump databases, files, environment variables, or secrets.
- Use boolean, error, timing, harmless arithmetic, or canary proofs.
- Ask for approval before scanner runs, time-based payloads, out-of-band callbacks, or exploit modules.
- Keep all raw responses in files and summarize only the relevant evidence.

## Triage Flow

1. Identify injectable inputs from URLs, forms, APIs, headers, cookies, JSON, XML, GraphQL, file upload metadata, and template fields.
2. Send safe control and test payloads.
3. Compare status, length, timing, reflected errors, and server behavior.
4. Escalate scanner use only after a manual signal.
5. Validate with minimal impact and route to `bug-bounty-validation`.

## Manual Comparison Pattern

```bash
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
mkdir -p "$BB_ROOT"/{vulns,logs,tmp}
base_url="https://example.com/search?q=test"
test_url="https://example.com/search?q=test%27"
ts="$(date +%Y%m%d-%H%M%S)"
curl -sk -w '\nHTTP:%{http_code} TIME:%{time_total} SIZE:%{size_download}\n' -D "$BB_ROOT/vulns/inj-control-headers-$ts.txt" -o "$BB_ROOT/vulns/inj-control-body-$ts.txt" "$base_url" > "$BB_ROOT/logs/inj-control-$ts.out" 2> "$BB_ROOT/logs/inj-control-$ts.err"
curl -sk -w '\nHTTP:%{http_code} TIME:%{time_total} SIZE:%{size_download}\n' -D "$BB_ROOT/vulns/inj-test-headers-$ts.txt" -o "$BB_ROOT/vulns/inj-test-body-$ts.txt" "$test_url" > "$BB_ROOT/logs/inj-test-$ts.out" 2> "$BB_ROOT/logs/inj-test-$ts.err"
cat "$BB_ROOT/logs/inj-control-$ts.out" "$BB_ROOT/logs/inj-test-$ts.out"
rg -n "SQL|syntax|ODBC|PostgreSQL|MySQL|ORA-|SQLite|Mongo|template|Traceback|Exception|stack" "$BB_ROOT/vulns" "$BB_ROOT/logs"
```

## Tool Map

- SQLi: `sqlmap`, `ghauri`, manual `curl`, Burp Suite. Use `--risk 1 --level 1` first and never use dumping options unless explicitly authorized.
- Command injection: `commix`, manual harmless commands, out-of-band canaries only when allowed.
- SSTI: manual arithmetic and safe template probes; avoid file reads or RCE payloads unless explicitly authorized.
- XXE: safe entity behavior tests; no sensitive local file reads.
- Path traversal: benign known files only when permitted; prefer application-owned sample files.
- Deserialization: fingerprint libraries and errors; do not run weaponized gadget chains without explicit authorization.
- NoSQLi: boolean response differences and auth bypass checks against self-owned test accounts.

## Evidence Criteria

Valid injection evidence should show:

- The vulnerable input and request.
- A control response.
- A test response with clear behavioral difference.
- Minimal impact proof.
- No unauthorized data extraction.

## Output Convention

All commands must save output to organized paths:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
# stdout -> $BB_ROOT/<phase>/<tool>-$ts.txt
# stderr -> $BB_ROOT/logs/<tool>-$ts.err
```

Never dump raw tool output into chat context. Save to files, then read targeted excerpts.

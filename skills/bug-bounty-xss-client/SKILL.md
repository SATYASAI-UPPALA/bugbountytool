---
name: bug-bounty-xss-client
description: Use for reflected XSS, stored XSS, DOM XSS, open redirects, CSP weaknesses, JavaScript endpoint extraction, source maps, and client-side secret triage.
---

# Bug Bounty XSS And Client-Side

Use this skill when the orchestrator finds reflected input, rich text, file names, profile fields, markdown, redirects, DOM sinks, JavaScript-heavy apps, or client-side routes.

## Safety Rules

- Use harmless proof strings and self-owned accounts.
- Do not target real users or steal cookies, tokens, or PII.
- Avoid persistence outside self-owned test objects unless the program allows it.
- Capture screenshots or response snippets only after sanitizing sensitive data.

## Workflow

1. Collect URLs and parameters from `gau`, `waybackurls`, `katana`, `hakrawler`, and app crawling.
2. Identify reflection, DOM sinks, redirect parameters, and upload-render paths.
3. Run low-noise scanner triage after approval.
4. Manually validate in a browser or Burp.
5. Document context, payload, sink, exploitability, and impact.

## Commands

Parameter and reflection triage:

```bash
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
mkdir -p "$BB_ROOT"/{params,js,vulns,logs,tmp}
latest_urls="$(ls -t "$BB_ROOT"/params/urls-merged-*.txt 2>/dev/null | sed -n '1p')"
ts="$(date +%Y%m%d-%H%M%S)"
rg -n "\?|redirect=|return=|next=|callback=|q=|search=|url=|continue=" "$latest_urls" > "$BB_ROOT/vulns/xss-params-$ts.txt" 2> "$BB_ROOT/logs/xss-params-$ts.err"
sed -n '1,120p' "$BB_ROOT/vulns/xss-params-$ts.txt"
```

Scanner triage after approval:

```bash
target_url="https://example.com/search?q=test"
ts="$(date +%Y%m%d-%H%M%S)"; dalfox url "$target_url" --silence --output "$BB_ROOT/vulns/dalfox-xss-$ts.txt" > "$BB_ROOT/logs/dalfox-xss-$ts.out" 2> "$BB_ROOT/logs/dalfox-xss-$ts.err"
ts="$(date +%Y%m%d-%H%M%S)"; xsstrike -u "$target_url" --crawl --skip-dom > "$BB_ROOT/vulns/xsstrike-$ts.txt" 2> "$BB_ROOT/logs/xsstrike-$ts.err"
```

JS endpoint and secret triage:

```bash
rg -n "innerHTML|outerHTML|document\.write|eval\(|setTimeout\(|location\.hash|postMessage|localStorage|sessionStorage|api_key|token|secret|sourceMappingURL" "$BB_ROOT/js" "$BB_ROOT/content" | sed -n '1,160p'
```

## Evidence Criteria

A valid XSS/client-side finding needs:

- Affected URL or feature.
- Payload and execution context.
- Browser or response proof.
- User interaction requirement.
- CSP or sanitizer behavior.
- Realistic impact without stealing data.

## Output Convention

All commands must save output to organized paths:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
# stdout -> $BB_ROOT/<phase>/<tool>-$ts.txt
# stderr -> $BB_ROOT/logs/<tool>-$ts.err
```

Never dump raw tool output into chat context. Save to files, then read targeted excerpts.

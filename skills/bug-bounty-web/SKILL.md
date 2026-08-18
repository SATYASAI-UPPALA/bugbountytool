---
name: bug-bounty-web
description: Use for web and API bug bounty testing: content discovery, parameter discovery, JS endpoint extraction, API route analysis, and low-noise vulnerability scanner triage.
---

# Bug Bounty Web And API Testing

Use this skill after scope is confirmed and live HTTP services are identified.

## Content Discovery

Ask for approval before fuzzing. Keep wordlists and rates appropriate for the program.

```bash
url="https://example.com"
slug="$(printf '%s' "$url" | sed 's#https\?://##; s#[/:?&=]#_#g' | tr '[:upper:]' '[:lower:]')"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
mkdir -p "$BB_ROOT"/{scope,passive,active,content,params,js,vulns,reports,logs,tmp}
ts="$(date +%Y%m%d-%H%M%S)"; feroxbuster -u "$url" -w /usr/share/wordlists/dirb/common.txt -x php,aspx,js,json,txt,bak,zip -k -r --rate-limit 20 --silent > "$BB_ROOT/content/feroxbuster-$ts.txt" 2> "$BB_ROOT/logs/feroxbuster-$ts.err"
ts="$(date +%Y%m%d-%H%M%S)"; ffuf -u "$url/FUZZ" -w /usr/share/seclists/Discovery/Web-Content/raft-small-words.txt -mc all -fc 404 -rate 20 -of json -o "$BB_ROOT/content/ffuf-$ts.json" > "$BB_ROOT/logs/ffuf-$ts.out" 2> "$BB_ROOT/logs/ffuf-$ts.err"
```

Analyze outputs:

```bash
latest_ffuf="$(ls -t "$BB_ROOT"/content/ffuf-*.json | sed -n '1p')"
jq -r '.results[]? | [.status, .length, .url] | @tsv' "$latest_ffuf" | sort -u | sed -n '1,120p'
rg -n "200|204|301|302|307|308|401|403|500|swagger|openapi|graphql|admin|backup|debug|config" "$BB_ROOT/content"
```

## Parameter Discovery

Prefer passive URL sources first:

```bash
ts="$(date +%Y%m%d-%H%M%S)"; gau "$target" > "$BB_ROOT/params/gau-$ts.txt" 2> "$BB_ROOT/logs/gau-$ts.err"
ts="$(date +%Y%m%d-%H%M%S)"; waybackurls "$target" > "$BB_ROOT/params/waybackurls-$ts.txt" 2> "$BB_ROOT/logs/waybackurls-$ts.err"
ts="$(date +%Y%m%d-%H%M%S)"; find "$BB_ROOT/params" -type f -name '*.txt' -exec cat {} + | sort -u > "$BB_ROOT/params/urls-merged-$ts.txt" 2> "$BB_ROOT/logs/urls-merged-$ts.err"
latest_urls="$(ls -t "$BB_ROOT"/params/urls-merged-*.txt | sed -n '1p')"
rg -n "\?|redirect=|url=|next=|file=|path=|id=|user=|account=|token=|debug=|callback=|return=" "$latest_urls" | sed -n '1,160p'
```

For active parameter discovery, ask for approval:

```bash
ts="$(date +%Y%m%d-%H%M%S)"; arjun -u "$url" -oJ "$BB_ROOT/params/arjun-$ts.json" > "$BB_ROOT/logs/arjun-$ts.out" 2> "$BB_ROOT/logs/arjun-$ts.err"
```

## JavaScript And API Analysis

```bash
ts="$(date +%Y%m%d-%H%M%S)"; katana -u "$url" -silent -jc -kf all -d 3 -rate-limit 20 > "$BB_ROOT/js/katana-js-$ts.txt" 2> "$BB_ROOT/logs/katana-js-$ts.err"
latest_js="$(ls -t "$BB_ROOT"/js/katana-js-*.txt | sed -n '1p')"
rg -n "\.js($|\?)|api/|graphql|swagger|openapi|token|secret|client_id|apikey|api_key|bearer" "$latest_js" | sed -n '1,160p'
```

When reviewing JS, look for:

- API base URLs and hidden routes.
- Feature flags and role names.
- Source maps.
- Hardcoded keys, tokens, client secrets, or private endpoints.
- IDOR-prone identifiers and tenant/account parameters.

## Scanner Triage

Ask for approval before running scanners. Keep output file-based.

```bash
ts="$(date +%Y%m%d-%H%M%S)"; nuclei -u "$url" -severity medium,high,critical -rate-limit 5 -retries 1 -timeout 8 -jsonl -o "$BB_ROOT/vulns/nuclei-$ts.jsonl" > "$BB_ROOT/logs/nuclei-$ts.out" 2> "$BB_ROOT/logs/nuclei-$ts.err"
ts="$(date +%Y%m%d-%H%M%S)"; dalfox url "$url" --silence --output "$BB_ROOT/vulns/dalfox-$ts.txt" > "$BB_ROOT/logs/dalfox-$ts.out" 2> "$BB_ROOT/logs/dalfox-$ts.err"
```

Treat scanner results as leads. Validate manually before reporting.

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

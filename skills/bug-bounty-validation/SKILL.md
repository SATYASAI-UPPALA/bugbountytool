---
name: bug-bounty-validation
description: Use for validating candidate bug bounty vulnerabilities, building safe PoCs, chaining impact, collecting evidence, estimating CVSS, and writing final reports.
---

# Bug Bounty Validation And Reporting

Use this skill when a candidate vulnerability needs proof, impact analysis, or a report.

## Validation Rules

- Confirm the asset is in scope before touching it.
- Use the minimum number of requests needed to prove the issue.
- Do not access, change, delete, or export real user data.
- Prefer harmless markers, self-owned accounts, canary callbacks, and metadata-only evidence.
- Redact tokens, cookies, PII, and secrets in chat and report drafts.
- Document exact commands, timestamps, request IDs, and output files.

## Evidence Capture

Capture headers and bodies separately:

```bash
url="https://example.com/path"
slug="$(printf '%s' "$url" | sed 's#https\?://##; s#[/:?&=]#_#g' | tr '[:upper:]' '[:lower:]')"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
mkdir -p "$BB_ROOT"/{scope,passive,active,content,params,js,vulns,reports,logs,tmp}
ts="$(date +%Y%m%d-%H%M%S)"
curl -sk --path-as-is -D "$BB_ROOT/vulns/curl-headers-$ts.txt" -o "$BB_ROOT/vulns/curl-body-$ts.txt" "$url" > "$BB_ROOT/logs/curl-$ts.out" 2> "$BB_ROOT/logs/curl-$ts.err"
sed -n '1,80p' "$BB_ROOT/vulns/curl-headers-$ts.txt"
wc -c "$BB_ROOT/vulns/curl-body-$ts.txt"
```

For JSON APIs:

```bash
jq '.' "$BB_ROOT/vulns/curl-body-$ts.txt" > "$BB_ROOT/vulns/curl-body-$ts.pretty.json" 2> "$BB_ROOT/logs/jq-$ts.err"
rg -n "id|user|tenant|role|admin|token|error|debug|stack|trace" "$BB_ROOT/vulns/curl-body-$ts.pretty.json"
```

## Manual Checks

Prioritize:

- IDOR and tenant isolation: compare two authorized self-owned accounts.
- Broken access control: direct object access, role changes, missing server-side checks.
- SSRF: use safe canary endpoints and metadata probes only if allowed.
- SQLi and command injection: non-destructive boolean/time/error validation.
- XSS: harmless markers and self-owned contexts.
- File disclosure: request only benign system files or known public files when permitted.
- Auth flaws: password reset, MFA bypass, token confusion, session fixation, OAuth redirect issues.
- Business logic: payment, coupon, quota, invitation, workflow, and state machine abuse.

## Chaining Impact

When chaining, document each link:

1. Initial primitive.
2. Required privileges or preconditions.
3. Data or control gained at each step.
4. Final business impact.
5. Why the chain is realistic.

Do not escalate beyond the minimum safe proof.

## Report Format

Use this exact structure:

- **Title**: [Clear vulnerability name]
- **Severity**: [Critical / High / Medium / Low / Informational]
- **Endpoint / Asset**: [URL / IP / description]
- **Description**: [What it is and why it matters]
- **Steps to Reproduce**: [Numbered steps, including exact commands]
- **Impact**: [Business + technical impact]
- **Remediation**: [Recommended fix]
- **CVSS Score**: [Estimate + vector if possible]
- **PoC**: [If applicable, attach or describe]

Save drafts here:

```bash
report="$BB_ROOT/reports/finding-$(date +%Y%m%d-%H%M%S).md"
printf '%s\n' '# Finding Draft' > "$report"
printf 'Report path: %s\n' "$report"
```

Before pasting captured requests/responses into the draft, redact tokens and cookies yourself — don't rely on remembering to do it later:

```bash
sed -E 's/(Authorization: Bearer) [A-Za-z0-9._-]+/\1 [REDACTED]/I; s/(Cookie: )[^\r\n]+/\1[REDACTED]/I' \
  "$BB_ROOT/vulns/curl-headers-<ts>.txt" >> "$report"
```

Still re-read the draft end to end before submitting — that pattern catches the common cases (bearer tokens, session cookies), not every form a secret can take.

## False Positive Reduction

Before finalizing:

- Reproduce from a clean shell or fresh session.
- Verify the issue is not intended behavior or documented public data.
- Check whether auth state changes the behavior.
- Check whether a WAF, cache, redirect, or client-side control explains the result.
- Keep raw evidence in files and only include sanitized snippets in chat.

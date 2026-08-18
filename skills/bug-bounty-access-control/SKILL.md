---
name: bug-bounty-access-control
description: Use for IDOR, BOLA, BFLA, tenant isolation, object ownership, privilege escalation, role bypass, and broken access control validation in bug bounty targets.
---

# Bug Bounty Access Control

Use this skill only after the orchestrator confirms scope and authorization. Access-control testing needs self-owned accounts or explicitly provided test accounts.

## Test Requirements

- Use at least two authorized roles or accounts when possible.
- Never access real user data. Use self-owned records, test tenants, or harmless metadata.
- Save each request and response to files.
- Track the expected authorization decision before testing.

## Workflow

1. Identify object identifiers: `id`, `user_id`, `account_id`, `tenant_id`, `org_id`, `invoice_id`, `order_id`, UUIDs, slugs.
2. Map roles and privileges: unauthenticated, user, admin, manager, tenant owner, support user.
3. Build a request matrix: account A owns object A; account B attempts access to object A.
4. Test read, create, update, delete, export, invite, role-change, and workflow-state actions.
5. Validate impact without modifying or exposing real data.

## Commands

Capture baseline requests:

```bash
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
mkdir -p "$BB_ROOT"/{vulns,logs,reports,tmp}
ts="$(date +%Y%m%d-%H%M%S)"
curl -sk -D "$BB_ROOT/vulns/access-a-headers-$ts.txt" -o "$BB_ROOT/vulns/access-a-body-$ts.txt" \
  -H "Authorization: Bearer TOKEN_A" \
  "https://example.com/api/resource/OBJECT_A" \
  > "$BB_ROOT/logs/access-a-$ts.out" 2> "$BB_ROOT/logs/access-a-$ts.err"
curl -sk -D "$BB_ROOT/vulns/access-b-headers-$ts.txt" -o "$BB_ROOT/vulns/access-b-body-$ts.txt" \
  -H "Authorization: Bearer TOKEN_B" \
  "https://example.com/api/resource/OBJECT_A" \
  > "$BB_ROOT/logs/access-b-$ts.out" 2> "$BB_ROOT/logs/access-b-$ts.err"
```

Compare safely:

```bash
wc -c "$BB_ROOT"/vulns/access-*-body-"$ts".txt
rg -n "200|401|403|owner|tenant|role|forbidden|unauthorized|OBJECT_A" "$BB_ROOT"/vulns/access-*-headers-"$ts".txt "$BB_ROOT"/vulns/access-*-body-"$ts".txt
```

## Tooling

- `curl` for exact request replay.
- Burp Suite for request manipulation and repeater comparisons.
- `jq` for JSON diff-friendly inspection.
- `ffuf` for low-rate identifier or method discovery only when allowed.
- `arjun`, `gau`, `waybackurls`, and `katana` to find ID-bearing endpoints.
- `nuclei` templates only as triage, never as final proof.

## Report Criteria

A valid access-control finding needs:

- Expected access rule.
- Actual bypass behavior.
- Two-account or two-role proof.
- Minimal evidence showing unauthorized access or action.
- Business impact tied to the object or workflow.

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

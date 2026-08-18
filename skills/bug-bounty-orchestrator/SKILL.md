---
name: bug-bounty-orchestrator
description: Use for all bug bounty control-plane work: scope gating, master plans, todo lists, phase routing, adaptive tool mapping, specialist skill delegation, evidence tracking, P0 alerting, and final reporting.
---

# Bug Bounty Orchestrator

This is the boss skill for bug bounty operations. Use it before every bug bounty workflow and whenever the work crosses phases, tools, or vulnerability classes. It controls planning, todo lists, skill selection, tool selection, evidence paths, approval checkpoints, and report handoff.

## Boss Rules

- **Own the plan (Autonomously).** Start by creating a concise plan. As tool responses come back, automatically update the todo list with new leads without asking the user.
- **Chain safe tools automatically.** Do not pause for permission between safe, non-destructive phases (like passive recon -> browser crawl -> parameter discovery -> manual error-based checks).
- **Own scope.** No specialist skill or tool run can bypass the scope gate.
- **Own approvals (The Hard Stop).** Pause and ask the user before active, risky, high-volume, exploitative (e.g., sqlmap), brute-force, or cloud metadata commands.
- **Own routing.** Load only the specialist skills needed for the current phase or vulnerability hypothesis.
- **Own output discipline.** Every command writes stdout and stderr to files, then only targeted excerpts are read back.
- **Own evidence.** Track output paths, request IDs, timestamps, payloads, and sanitized proof in the hunt summary.
- **Own final quality.** A finding is not valid until manually reproduced and impact is documented.

## Scope Gate

Before active testing, confirm:

- Program or client authorization exists.
- In-scope domains, IPs, mobile apps, APIs, cloud assets, or repositories are explicit.
- Out-of-scope assets and forbidden test types are known.
- Rate limits, test windows, auth requirements, and reporting expectations are known.

If any item is missing, ask for it. Passive recon can be prepared, but do not run active probes, fuzzers, exploit checks, credential attacks, cloud metadata probes, brute-force checks, or scanners until scope is clear.

## Master Plan And Todo List

Maintain this control loop:

1. Define the objective and target scope.
2. Create `"$BB_ROOT/reports/orchestrator-plan-$(date +%Y%m%d-%H%M%S).md"`.
3. Create `"$BB_ROOT/reports/todo-$(date +%Y%m%d-%H%M%S).md"`.
4. Route each todo item to one phase skill or vulnerability skill.
5. Map each todo item to tools, expected output files, approval needs, and validation criteria.
6. Execute or propose commands in phase order.
7. **Auto-Update:** After each result, automatically mark status (`done`, `blocked`, `candidate-finding`) and instantly insert new tasks based on what was found (e.g., if a parameter is found, immediately queue a manual validation check).
8. **Auto-Chain:** If the next queued task is non-destructive and low-noise, execute it immediately without asking the user.
9. Promote only manually validated items into report drafts.

Use this file format:

```markdown
# Orchestrator Plan

- Target:
- Scope source:
- ROE notes:
- Current objective:
- Boss decision:

## Todo

| Status | Phase | Skill | Tool(s) | Output file | Validation |
| --- | --- | --- | --- | --- | --- |
| pending | passive recon | bug-bounty-recon | subfinder, amass | passive/*.txt | unique in-scope hosts |

## Approval Queue

| Needed for | Why approval is needed | Command file |
| --- | --- | --- |

## Evidence Index

| Finding/lead | Evidence file | Notes |
| --- | --- | --- |
```

## Workspace Contract

Use one workspace per target:

```bash
target="example.com"
slug="$(printf '%s' "$target" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/_/g')"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
mkdir -p "$BB_ROOT"/{recon/{passive,active},content/{dirs,files,js},vulns/{critical,high,medium,low},cloud,reports,logs,wordlists}
printf 'Target: %s\nCreated: %s\n' "$target" "$(date -Is)" > "$BB_ROOT/recon/session-$(date +%Y%m%d-%H%M%S).txt"
```

Do not dump raw command output into the chat. Save stdout and stderr:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
out="$BB_ROOT/<phase>/<tool>-$ts.txt"
err="$BB_ROOT/logs/<tool>-$ts.err"
<command> > "$out" 2> "$err"
wc -l "$out" "$err"
sed -n '1,80p' "$err"
```

After tool execution, read back only targeted evidence:

```bash
rg -n "critical|high|vulnerable|exposed|swagger|openapi|graphql|admin|debug|token|secret" "$out"
sed -n '1,120p' "$out"
jq -r '.url? // .host? // empty' "$out" 2>/dev/null | sort -u | sed -n '1,80p'
```

## Adaptive Execution Loop

There is no standalone script to shell out to. You (the agent) run each phase yourself, one command at a time, read the output file, and decide the next command based on what's actually there. That loop is the point — it's why an agent runs this instead of a fixed script.

### Phase 0: Tool check + target classification

Check what's installed before planning around it. Install anything missing via the normal package manager rather than skipping the phase silently:

```bash
for t in subfinder httpx dnsx naabu nuclei ffuf jq amass assetfinder katana gau waybackurls nmap wafw00f; do
  command -v "$t" >/dev/null 2>&1 && echo "[ok] $t" || echo "[missing] $t"
done
```

For anything missing: `go install -v <module>@latest` for the Go-based recon tools (subfinder, httpx, dnsx, naabu, nuclei, ffuf, assetfinder, katana, gau, waybackurls all install this way), `sudo apt-get install -y <pkg>` for amass/nmap/wafw00f/jq. Re-check with `command -v` after installing; if it still fails, note it and move on rather than blocking the whole run on one tool.

If nuclei is present and you're heading into `--deep`-style triage later, refresh templates now rather than at triage time — stale templates are the biggest source of both false positives (matchers for since-patched issues) and false negatives (missing recent CVE templates):

```bash
nuclei -update-templates -silent
```

### Phase 1-2: Recon (see bug-bounty-recon for the actual commands)

Run passive recon, merge subdomains, then active recon (dnsx/httpx/naabu). After httpx finishes, read the JSON yourself and decide what it implies — don't just move to the next scripted step:

- **Subdomains under ~10?** Widen with an alternate source (HackerTarget, crt.sh) before moving on.
- **WAF detected** (`wafw00f` against the first live host, or repeated 403s with a vendor-looking body)? Drop your own rate limits for every phase after this — pass a lower `-rate-limit`/`-rate` to whatever you run next.
- **Spring/actuator, PHP, API framework, or SPA signals in httpx `-tech-detect` output?** Pick the matching wordlist and skill before fuzzing rather than fuzzing blind.
- **No live hosts at all?** Stop here and say so — don't run content discovery or vuln triage against nothing.

### Phase 3: P0 signal confirmation

A string match ("graphql" appearing in a URL or JS filename) is not a finding — confirm it with one harmless, read-only request before treating it as P0:

```bash
# GraphQL: does introspection actually respond?
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"query":"{__schema{queryType{name}}}"}' "https://example.com/graphql" | grep -q '"queryType"' \
  && echo "[P0][confirmed] introspection enabled"

# Swagger/OpenAPI: is the doc actually live and valid JSON?
curl -sk "https://example.com/swagger.json" | jq -e '.swagger // .openapi' >/dev/null \
  && echo "[P0][confirmed] OpenAPI doc live"
```

Same principle for secrets: a regex hit on `AKIA[0-9A-Z]{16}` or a PEM header in already-fetched JS/recon output is a lead worth flagging immediately (P0), but still gets verified manually before it goes in a report — never test whether a found key actually works.

### Phase 4 (deep dives only): reducing false positives before you triage

- **Soft-404 baseline before content discovery.** Request a near-certainly-nonexistent path first and note its response size; when you fuzz with ffuf/feroxbuster, filter that exact size (`-fs <n>`) so a custom "not found" page that returns HTTP 200 doesn't flood your results.
- **Dedupe and re-check nuclei output.** Nuclei can fire the same template against the same host multiple times across different paths — dedupe by `(template-id, matched-at)` before reading through it. Then re-request each unique match once more; a hit that only fired once and doesn't reproduce on a clean second request is a much weaker lead than one that does.
- **Everything here is still a lead, not a finding.** A reproducible nuclei match is a template match, not a manually verified bug. Route every candidate through `bug-bounty-validation` before it goes anywhere near a report.

### P0 Alert System

Immediately flag and escalate (after the confirmation step above, not before):
- GraphQL introspection enabled
- OpenAPI/Swagger docs exposed
- Secrets/keys in JS files
- Open S3 buckets
- SSRF to cloud metadata confirmed
- Critical/high nuclei findings that reproduced on re-check
- Cloud credentials in historical URLs

### Smart Skipping
- No JS files → Skip JS analysis
- No historical URLs → Skip param extraction
- No cloud signal → Skip cloud enum (unless doing a deep dive)
- No live hosts → Skip active phases entirely and say so
- No subdomains → Widen the intel phase instead of moving on

## Phase Routing - Complete Skill Matrix

Load specialist skills based on target type and findings:

### Core Phase Skills
- `bug-bounty-recon` - Passive recon, DNS, HTTP probing, ports, technology fingerprinting
- `browser-bounty-recon` - Authenticated/JS-rendered recon via Playwright: real API endpoint inventory from actual browsing, human-driven login, read-only by design
- `bug-bounty-web` - Content discovery, parameters, JS/API analysis, scanner triage
- `bug-bounty-validation` - Proof, exploit safety, impact analysis, chaining, final reports

### Vulnerability-Specific Skills
- `bug-bounty-access-control` - IDOR, BOLA/BFLA, tenant isolation, role bypass, object ownership, privilege escalation
- `bug-bounty-injection` - SQLi, NoSQLi, command injection, SSTI, XXE, path traversal, unsafe deserialization
- `bug-bounty-ssrf-cloud` - SSRF, cloud metadata risk, object storage exposure, cloud IAM clues
- `bug-bounty-xss-client` - Reflected, stored, DOM XSS, open redirect, CSP, client-side routes, JS secrets
- `bug-bounty-auth-session` - Login, logout, password reset, MFA, OAuth/OIDC, JWT, session, rate limiting
- `bug-bounty-rce` - Remote code execution, command injection, unsafe deserialization, template injection
- `bug-bounty-file-upload` - Upload bypasses, extension validation, MIME type, malicious file processing
- `bug-bounty-graphql` - GraphQL introspection, query complexity, batch DoS, injection, authorization bypass
- `bug-bounty-logic-bugs` - Price manipulation, quantity abuse, coupon bypass, workflow state, race conditions
- `bug-bounty-auth-bypass` - JWT manipulation, session fixation, OAuth flaws, MFA bypass, password reset poisoning
- `bug-bounty-data-leak` - PII exposure, credential leaks, API key discovery, debug info, verbose errors

### Infrastructure Skills
- `bug-bounty-network-infra` - nmap/naabu service triage, TLS, WAF/CDN behavior, exposed admin services
- `bug-bounty-api-security` - REST API, SOAP, gRPC testing, authentication flaws, rate limiting, mass assignment
- `bug-bounty-mobile` - Mobile app testing (iOS/Android), APK/IPA analysis, mobile API testing
- `bug-bounty-devsecops` - CI/CD pipeline testing, Git exposure, container security, cloud misconfigurations

### Post-Exploitation
- `bug-bounty-privesc` - Privilege escalation after initial access: Linux/Windows/Cloud privesc, sudo exploits, cron abuse

Load skills contextually based on what the orchestrator discovers during automated phases.

## Kali Tool Map

Map tools to hypotheses instead of running everything blindly:

### Reconnaissance

* Passive: `subfinder`, `amass`, `assetfinder`, `findomain`, `theHarvester`, `recon-ng`, `crtsh` via `curl`, `waybackurls`, `gau`, `github-subdomains`
* DNS/HTTP: `dnsx`, `puredns`, `shuffledns`, `massdns`, `httpx`, `httprobe`, `wafw00f`, `whatweb`, `curl`, `openssl`
* ASN/IP Discovery: `asnmap`, `whois`, `dig`, `host`, `nslookup`
* Ports: `naabu`, `nmap`, `rustscan`; use `masscan` only if ROE explicitly allows high-rate scanning
* TLS: `testssl.sh`, `sslyze`, `openssl`

### Content Discovery

* Directories: `ffuf`, `feroxbuster`, `gobuster`, `dirsearch`, `dirb`, `wfuzz`, SecLists
* Crawling: `katana`, `hakrawler`, `gospider`, `cariddi`, `gau`, `waybackurls`
* Parameters: `arjun`, `paramspider`, `x8`, `Param Miner`, `ffuf`
* URL Processing: `uro`, `unfurl`, `anew`, `qsreplace`, `sort`, `grep`
* JS/Endpoints: `katana`, `LinkFinder`, `xnLinkFinder`, `subjs`, `getJS`, `curl`
* Secrets: `SecretFinder`, `trufflehog`, `gitleaks`, `detect-secrets`, `rg`, `jq`

### API Security

* REST: `Burp Suite`, `Postman`, `Insomnia`, `curl`, `httpie`, `mitmproxy`
* Endpoint Discovery: `kiterunner`, `arjun`, `ffuf`, `katana`
* JWT: `jwt_tool`, `JWT Editor`, `openssl`
* GraphQL: `InQL`, `graphql-cop`, `Clairvoyance`, `GraphQL Voyager`
* gRPC: `grpcurl`, `grpcui`, `protoc`, `Burp Suite`
* WebSockets: `websocat`, `wscat`, `Burp WebSocket Repeater`, Python `websocket-client`

### Access Control

* IDOR/BOLA: `Burp Repeater`, `Autorize`, `AuthMatrix`, `Comparer`, `curl`, `Postman`
* Role Testing: separate User A, User B, admin, low-privilege and unauthenticated sessions
* Object Discovery: `arjun`, `Param Miner`, `gau`, `waybackurls`, `jq`
* Response Comparison: `Burp Comparer`, `diff`, `jq`, Python scripts

### Vulnerability Scanning

* Template Triage: `nuclei`, `nikto`, `searchsploit`, `wappalyzer`, `whatweb`
* XSS: `dalfox`, `xsstrike`, `kxss`, `DOM Invader`, browser/Burp validation
* SQLi: `sqlmap`, `ghauri`, manual `curl` and Burp comparisons; never dump tables or real data
* Command Injection: `commix`, manual safe markers, canary callbacks only when explicitly allowed
* SSTI: `tplmap`, Burp Repeater, harmless mathematical expressions
* Path Traversal/LFI: Burp Repeater, `curl`, safe local-file indicators only
* Open Redirect: `OpenRedireX`, Burp Repeater, browser validation
* CORS: `CORScanner`, `Corsy`, Burp Repeater, `curl`
* Host Header: `Param Miner`, Burp Repeater, `curl`
* Request Smuggling: `HTTP Request Smuggler`, `smuggler.py`, Burp Repeater; test slowly
* Cache Issues: `Param Miner`, Web Cache Vulnerability Scanner, Burp Repeater
* Race Conditions: `Turbo Intruder`, `Race The Web`, Python `asyncio`; keep request counts low
* Network Auth: `hydra`, `medusa`, `ncrack`, `john`, `hashcat`, Metasploit only when explicitly authorized

### Authentication and Session Testing

* Session Analysis: Burp Sequencer, Repeater, browser developer tools
* Password Reset: Burp Repeater, `curl`, separate test accounts
* MFA: Burp Repeater, Authenticator test accounts, controlled replay testing
* OAuth/OIDC: Burp Suite, browser developer tools, `curl`, `jwt_tool`
* JWT: `jwt_tool`, `JWT Editor`, `openssl`, `base64`
* Rate Limits: Burp Intruder, Turbo Intruder, `ffuf`; use low request rates

### File Upload Testing

* Interception: Burp Suite, `curl`, Postman
* File Inspection: `file`, `xxd`, `strings`, `exiftool`, `binwalk`
* Image Validation: `identify`, ImageMagick, `exiftool`
* Upload Checks: MIME type, extension, filename, storage path, authorization and signed URLs
* Safety: avoid persistent web shells unless ROE explicitly permits them

### SSRF and Out-of-Band Testing

* OAST: Burp Collaborator, `interactsh-client`, Canarytokens
* SSRF: `ssrfmap`, `gopherus`, `ssrf-sheriff`, Burp Repeater, manual canary URLs
* URL Parsing: `curl`, `httpie`, Burp Decoder
* DNS Callbacks: `interactsh-client`, Burp Collaborator
* Safety: start with harmless external callbacks before testing internal services

### Cloud Security

* Bucket Enumeration: `cloud_enum`, `S3Scanner`, `awscli`, Azure CLI, `gcloud`
* Public Exposure: `curl`, `dig`, `openssl`, browser validation
* AWS Review: `Prowler`, `ScoutSuite`, `CloudFox`, `Pacu` only with authorized credentials
* Azure Review: `ScoutSuite`, `ROADtools`, `AzureHound` only with authorization
* GCP Review: `gcloud`, `ScoutSuite`, manual IAM review
* Metadata: `curl` probes to `169.254.169.254` and `metadata.google.internal` only when explicitly allowed
* IAM: role checks, policy review, trust relationships and excessive permissions
* Secrets: credential files, environment variables and CI/CD variables only within authorized assets

### Source Code and Repository Review

* Static Analysis: `semgrep`, `CodeQL`, `bandit`, `gosec`, `brakeman`
* Secrets: `gitleaks`, `trufflehog`, `detect-secrets`
* Dependencies: `npm audit`, `pip-audit`, `osv-scanner`, `grype`
* SBOM: `syft`
* Manual Search: `rg`, `grep`, `git log`, `git diff`
* Focus Areas: authentication, authorization, tenant filtering, SSRF sinks, SQL construction, file handling and command execution

### Network and TLS Testing

* Services: `nmap`, `naabu`, `rustscan`, `netcat`
* TLS: `testssl.sh`, `sslyze`, `openssl`
* DNS: `dig`, `dnsx`, `host`, `nslookup`
* Packet Analysis: `Wireshark`, `tcpdump`
* HTTP Debugging: `curl`, `httpie`, `mitmproxy`

### Privilege Escalation (Post-Access)

* Linux: `linpeas.sh`, `pspy64`, `pspy32`, `getcap`, `find`, `sudo -l`, `systemctl`
* Windows: `winpeas.exe`, `winpeas.bat`, `Watson`, `Seatbelt`, `wmic`, `icacls`, PowerShell
* Active Directory: `BloodHound`, `SharpHound`, `ldapsearch` only when explicitly authorized
* Cloud: metadata probes, IAM role checks, token inspection and credential file searches
* Safety: perform post-access testing only when the program explicitly allows exploitation and privilege escalation

### Evidence and Reporting

* Screenshots: `Flameshot`, `ShareX`, `gowitness`, `EyeWitness`, `Aquatone`
* Traffic Evidence: Burp Organizer, Logger++, Repeater
* Notes: Obsidian, CherryTree, Markdown
* Video: OBS Studio
* Reports: Markdown, Pandoc, PDF generation
* Preserve: original request, modified request, response, account role, timestamps and minimal impact evidence

### Essential Wordlists

* General: SecLists
* Directories: `raft-medium-directories.txt`, `common.txt`
* Files: `raft-medium-files.txt`
* APIs: `Discovery/Web-Content/api`
* Parameters: `burp-parameter-names.txt`
* DNS: `subdomains-top1million-5000.txt`
* Fuzzing: `Fuzzing/` directory in SecLists

### High-Risk Tools

* Scanning: `masscan` only when high-rate scanning is permitted
* Credential Attacks: `hydra`, `medusa`, `ncrack`, `john`, `hashcat` only when explicitly authorized
* Exploitation: Metasploit, `commix`, `Pacu`, post-exploitation tools only within approved ROE
* Data Access: never dump databases, download bulk records or access unrelated user data
* Persistence: never install shells, scheduled tasks, services or backdoors
* Availability: never perform denial-of-service, resource exhaustion or destructive tests

### Burp Suite

* Core: Proxy, HTTP History, Repeater, Intruder, Comparer, Decoder, Sequencer, Organizer, Collaborator
* Access Control: `Autorize`, `AuthMatrix`, `Logger++`
* Authentication: `JWT Editor`, `JSON Web Tokens`, `Param Miner`
* Advanced Testing: `Turbo Intruder`, `Backslash Powered Scanner`, `HTTP Request Smuggler`
* API Testing: `InQL`, `Content Type Converter`
* File Uploads: `Upload Scanner`
* Out-of-Band: `Collaborator Everywhere`

### Burp and Manual
- Burp Suite, repeater-style `curl`, saved requests, self-owned test accounts

If a useful Kali tool is installed and fits the hypothesis, the orchestrator may add it to the plan, but it must still pass scope, approval, rate-limit, and output-file rules.

## Privilege Escalation Integration

When initial access is gained (via any vulnerability), the orchestrator:

1. **Detects target OS** from tech fingerprint (whatweb, nuclei, headers)
2. **Generates OS-specific checklist** at `$BB_ROOT/vulns/privesc-checklist.md`
3. **Maps available tools** from `~/bugbounty/tools/privesc/`:
   - `linpeas.sh` - Linux comprehensive enumeration
   - `winpeas.exe` / `winpeas.bat` - Windows enumeration
   - `pspy64` / `pspy32` - Process monitoring (cron jobs, hidden tasks)
   - `sudo-cve-2021-3156` - Baron Samedit sudo exploit
   - `sudo-cve-2019-14287.py` - Sudo bypass exploit
4. **Routes to appropriate skill** for validation if cloud metadata or credentials found

## Operating Pattern

1. Restate the authorized scope in one concise line.
2. Build or reuse the `BB_ROOT` directory.
3. Create or update the orchestrator plan and todo list.
4. **Run the recon + active phases yourself**, following the Adaptive Execution Loop above — passive recon, merge, active recon, P0 confirmation, then (only if going deep) content discovery and nuclei triage. Read each output file as it lands and let it steer the next command; don't queue up every command in advance.
5. **Browser recon** (if target has web UI, SPA, or auth requirements):
   - Load `browser-bounty-recon` skill.
   - If auth needed: run `bb_auth_capture.py`, let the human log in by hand, session saves to `$BB_ROOT/active/storage_state.json`.
   - Run `bb_browser_crawl.py` against the authenticated start page to build the real API endpoint inventory.
   - Review `$BB_ROOT/active/browser-crawl/summary.json` and `endpoints.json` before deciding what to load next.
6. **Auto-Update & Chain:** Immediately update the todo list based on the findings. Pick the next todo based on impact and P0 alerts. If the next step is safe (e.g., manual validation of a parameter with a single quote), run it automatically.
7. Load the required specialist skill for deep-dive validation.
8. Ask for approval **only** before active, risky, exploitative (sqlmap/commix), or high-volume commands.
9. Save tool output to files.
10. Analyze the files with narrow reads.
11. Mark todo status and update `"$BB_ROOT/reports/hunt-summary-$(date +%Y%m%d).md"`.
12. Route validated candidates to `bug-bounty-validation` for proof and reporting.

## Summary Note Template

```markdown
# Hunt Summary

- Target:
- Scope source:
- Date:
- Current phase:
- Commands run:
- Output files:
- Candidate findings:
- P0 alerts (if any):
- Next actions:
- Blockers:
```

## Report Handoff

When a finding is validated, create a report draft:

```markdown
# Vulnerability Report

## Summary
- **Type:**
- **Severity:** (Critical/High/Medium/Low)
- **Location:**
- **Affected Component:**

## Steps to Reproduce
1.
2.
3.

## Evidence
- Request/Response files:
- Screenshots:
- Timestamps:

## Impact
What can an attacker do? What data or systems are at risk?

## Remediation
What should be fixed?

## References
- CVSS vector:
- CWE ID:
- Related advisories:
```

Route all final reports through `bug-bounty-validation` for impact verification and CVSS estimation before submission.

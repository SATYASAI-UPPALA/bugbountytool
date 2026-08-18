---
name: browser-bounty-recon
description: Use for authenticated or JS-rendered recon — SPAs, client-side routing, XHR/fetch-only API calls, and anything that only appears after login. Builds a live API endpoint inventory by browsing the app, not by guessing paths.
---

# Browser Bounty Recon

Static recon (`bug-bounty-recon`, `httpx`, `nuclei`) only sees what a plain HTTP request returns. Most modern apps render content and call APIs from JavaScript after the page loads, and plenty of the interesting attack surface (IDOR targets, internal APIs, admin panels) only exists once you're logged in. This skill uses Playwright to actually browse the app — the same thing a human hunter does with Burp/ZAP's browser proxy — and records what it sees.

**This skill is read-only by design.** It navigates, it observes, it never submits.

## Safety Rules

- **You log in, not the agent.** Credentials never pass through the agent or get typed by a script. `bb_auth_capture.py` opens a real, visible browser window and waits for a human to complete login (including 2FA/SSO/CAPTCHA) before saving the session.
- **Never auto-submit forms, click buttons, or issue POST/PUT/PATCH/DELETE requests.** The crawler only follows `<a href>` navigation and lets the page's own passive load-time network activity happen. Every form and every mutating request it *observes* gets logged as a candidate for manual review — never executed automatically. If you want to actually test a specific form or button, do that by hand or through the relevant specialist skill (`bug-bounty-injection`, `bug-bounty-access-control`, etc.) with explicit approval per action.
- **Same-origin only.** The crawler will not follow links off the authorized target's domain.
- **Rate limit yourself.** Default is one page every ~300ms with a page cap (`--max-pages`, default 25). Don't raise this past what the program's scope/ROE allows.
- **Treat `storage_state.json` as a credential.** It contains live session cookies/tokens. Keep it inside `$BB_ROOT`, never commit it, never paste its contents into a report, and delete it when you're done with the engagement.
- **No CAPTCHA/anti-bot bypass.** If the app puts up a CAPTCHA, that's you solving it during the manual login step — this skill does not attempt to defeat bot detection.

## Setup

```bash
pip install playwright --break-system-packages
playwright install chromium
```

## Phase A: Capture an authenticated session (human does the login)

```bash
python3 bb_auth_capture.py "https://example.com/login" --out "$BB_ROOT/active/storage_state.json"
```

```python
#!/usr/bin/env python3
"""
bb_auth_capture.py -- opens a VISIBLE browser window and waits for the human
to log in by hand. The agent never sees or handles credentials. Once you're
logged in, press Enter in the terminal and the session (cookies +
localStorage) is saved to storage_state.json for later authenticated crawls.
"""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright


def capture(login_url: str, out_path: Path):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(login_url)

        print(f"\nBrowser window opened at {login_url}")
        print("Log in by hand in that window (2FA, SSO, CAPTCHA -- all fine, it's you doing it).")
        input("Once you're logged in and see the authenticated app, press Enter here to save the session... ")

        context.storage_state(path=str(out_path))
        print(f"Session saved to {out_path}")
        browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("login_url")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    capture(args.login_url, Path(args.out))
```

This needs a display (run it on the Kali desktop session, not over a headless SSH-only connection). If you're fully headless, do the login with `playwright codegen --save-storage=storage_state.json https://example.com` instead, which gives you the same result via Playwright's own recorder.

## Phase B: Authenticated crawl — build the real endpoint inventory

```bash
python3 bb_browser_crawl.py "https://example.com/dashboard" \
  --storage-state "$BB_ROOT/active/storage_state.json" \
  --max-pages 25 \
  --out "$BB_ROOT/active/browser-crawl"
```

```python
#!/usr/bin/env python3
"""
bb_browser_crawl.py -- authenticated, read-only recon crawl.

Loads a saved session, walks same-origin pages up to a depth/page limit, and
logs every network request the page actually makes (including XHR/fetch
calls JS-only apps issue after load) to build a real API endpoint inventory.

This script NEVER submits a form, clicks a button, or issues a
POST/PUT/PATCH/DELETE. It only follows <a href> navigation and lets the
page's own passive network activity happen. Anything state-changing it
observes (a form action, a mutating-looking request) gets logged as a
candidate for manual follow-up, not executed.
"""
import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
ID_PATTERN = re.compile(r"/\d+(?=/|$|\?)")


def normalize_path(path: str) -> str:
    """Collapse numeric IDs so /orders/123 and /orders/456 count as one endpoint."""
    return ID_PATTERN.sub("/{id}", path)


def same_origin(url: str, origin: str) -> bool:
    try:
        return urlparse(url).netloc == urlparse(origin).netloc
    except Exception:
        return False


def crawl(start_url, storage_state, max_pages, out_dir: Path, headless=True):
    out_dir.mkdir(parents=True, exist_ok=True)
    origin = start_url
    visited, queue = set(), [start_url]
    pages_report, endpoints, mutating_candidates, forms_found = [], {}, [], []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx_kwargs = {}
        if storage_state and Path(storage_state).exists():
            ctx_kwargs["storage_state"] = storage_state
        context = browser.new_context(**ctx_kwargs)
        page = context.new_page()

        def on_request(req):
            url = req.url
            if not same_origin(url, origin):
                return
            method = req.method
            norm = normalize_path(urlparse(url).path or "/")
            key = f"{method} {norm}"
            entry = endpoints.setdefault(key, {"method": method, "path": norm, "sample_urls": [], "count": 0})
            entry["count"] += 1
            if url not in entry["sample_urls"] and len(entry["sample_urls"]) < 5:
                entry["sample_urls"].append(url)
            if method in MUTATING_METHODS:
                mutating_candidates.append({"method": method, "url": url})

        page.on("request", on_request)

        while queue and len(visited) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                page.goto(url, wait_until="networkidle", timeout=15000)
            except Exception as e:
                pages_report.append({"url": url, "error": str(e)})
                continue

            pages_report.append({"url": url, "title": page.title(), "status": "ok"})

            for form in page.query_selector_all("form"):
                action = form.get_attribute("action") or url
                fmethod = (form.get_attribute("method") or "GET").upper()
                forms_found.append({"page": url, "action": urljoin(url, action), "method": fmethod})

            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            for href in hrefs:
                if same_origin(href, origin) and href not in visited:
                    queue.append(href)

            time.sleep(0.3)  # be polite; this is recon, not a load test

        context.close()
        browser.close()

    (out_dir / "pages.json").write_text(json.dumps(pages_report, indent=2))
    (out_dir / "endpoints.json").write_text(json.dumps(sorted(endpoints.values(), key=lambda e: -e["count"]), indent=2))
    (out_dir / "forms.json").write_text(json.dumps(forms_found, indent=2))
    (out_dir / "mutating-candidates.json").write_text(json.dumps(mutating_candidates, indent=2))
    summary = {
        "pages_visited": len(visited),
        "unique_endpoints": len(endpoints),
        "forms_found": len(forms_found),
        "mutating_requests_observed_passively": len(mutating_candidates),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("start_url")
    ap.add_argument("--storage-state", default=None)
    ap.add_argument("--max-pages", type=int, default=25)
    ap.add_argument("--out", required=True)
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    crawl(args.start_url, args.storage_state, args.max_pages, Path(args.out), headless=not args.headed)
```

Tested against a local fixture app: it correctly picked up `fetch()`-only API calls a curl-based crawl would never see (`GET /api/v1/orders`, `GET /api/v1/users/me`), followed same-origin links, and logged a `<form method="POST" action="/api/v1/delete-account">` into `forms.json` **without ever clicking it** — `mutating-candidates.json` stayed empty because nothing was submitted.

## Reading the output

- **`endpoints.json`** — every unique `METHOD + normalized-path` the app called while you browsed it, sorted by frequency, with sample URLs. This is your real API surface — feed the interesting ones (auth-adjacent, ID-bearing, admin-looking) into `bug-bounty-access-control`, `bug-bounty-api-security`, or `bug-bounty-injection`.
- **`forms.json`** — every form found, with its action/method. Anything `POST`/`PUT`/`PATCH`/`DELETE` here is a candidate for manual testing, not something already tried.
- **`mutating-candidates.json`** — any state-changing request the *page itself* fired on load (rare, but some apps do this) — review these specifically, since they happened without you clicking anything.
- **`pages.json`** — crawl coverage and any pages that errored out (auth expired, 404, timeout).

## Phase C: Targeted JS/SPA analysis

For a specific page where you want to see exactly what changes when you interact with one element (not a full crawl), drive it manually and read `page.request`/`page.response` events for that single action — write a short one-off Playwright script for that specific interaction rather than trying to generalize a crawler to "click everything." A crawler that clicks every button on a live app *will* trigger real actions (password resets, emails, purchases, account changes) — that's the line between recon and testing, and it's a manual, approved step on purpose.

## Handoff

After a crawl, route findings the same way as any other recon phase:
- Interesting endpoint in `endpoints.json` → load the matching vulnerability-class skill and test it manually with real approval for anything mutating.
- Form in `forms.json` you want to test → test that specific form by hand, or with a short single-purpose script you write for that one interaction, not the crawler.
- `storage_state.json` → delete it when the engagement is done; it's a live session, not a report artifact.

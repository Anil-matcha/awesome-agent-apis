#!/usr/bin/env python3
"""Validate one or more catalog entries.

Two entry kinds, opposite disclosure rules:

- providers/<provider>.yaml — a community-submitted third-party tool, called with
  the CONTRIBUTOR'S OWN key. Must fully disclose base_url/auth/endpoints.
- models/<name>.yaml — one of muapi's own hosted models/APIs, called through your
  muapi key. Must NEVER disclose the internal routing vendor muapi uses to serve
  it (base_url, auth details, or a known vendor name) — see INTERNAL_VENDOR_NAMES.

Usage:
    python3 scripts/catalog_validate.py providers/hunter.yaml
    python3 scripts/catalog_validate.py models/some-model.yaml
    python3 scripts/catalog_validate.py providers/*.yaml models/*.yaml
"""
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency: pip install pyyaml")

# ---- shared ----

VALID_STATUS_PROVIDER = {"draft", "verified"}
VALID_STATUS_MODEL = {"live"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Secrets that look like real keys, not placeholder text. Tuned loosely on purpose —
# false positives here just mean re-checking a file by hand, false negatives ship a leak.
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),  # JWT-shaped
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
]
PLACEHOLDER_HINTS = {"{key}", "your-key", "your_api_key", "xxxx", "example", "changeme", "<key>"}

# muapi's internal routing/infra vendors. These must NEVER appear in a models/*.yaml
# entry (or anywhere else in this repo) — that's muapi's own procurement layer, not
# part of any model's public identity. Hard CI failure, no exceptions.
INTERNAL_VENDOR_NAMES = re.compile(
    r"(?i)\brunware\b|\bwavespeed\b|\bkie\b|kie\.ai|\bpoyo\b|\bkinovi\b|\bapimart\b|"
    r"\bpiapi\b|\bseegen\b|\btoapis?\b|\bfal\.(ai|run|media)\b"
)


def fail(errors, msg):
    errors.append(msg)


def check_secrets(raw_text, errors):
    for pat in SECRET_PATTERNS:
        for m in pat.finditer(raw_text):
            token = m.group(0)
            if any(h in token.lower() for h in PLACEHOLDER_HINTS):
                continue
            fail(errors, f"possible real secret matched pattern {pat.pattern!r}: {token[:12]}...")


# ---- providers/*.yaml (community third-party tools, full disclosure) ----

REQUIRED_TOP_PROVIDER = ["provider", "docs_url", "status", "auth", "pricing", "endpoints", "base_url"]
REQUIRED_AUTH = ["location", "format", "bad_key_behavior"]
REQUIRED_PRICING = ["model", "source_url", "checked"]
REQUIRED_ENDPOINT = ["id", "method", "path", "summary"]
VALID_AUTH_LOCATION = {"header", "query", "path"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.[a-z0-9][a-z0-9-]*$")


def validate_provider(path, data, errors):
    for field in REQUIRED_TOP_PROVIDER:
        if field not in data:
            fail(errors, f"missing required top-level field: {field}")

    if data.get("provider") and path.stem != "_TEMPLATE":
        expected = data["provider"]
        if path.stem != expected:
            fail(errors, f"filename {path.stem}.yaml does not match provider: {expected}")

    if "status" in data and data.get("status") not in VALID_STATUS_PROVIDER:
        fail(errors, f"status must be one of {VALID_STATUS_PROVIDER}, got {data.get('status')!r}")

    auth = data.get("auth") or {}
    for field in REQUIRED_AUTH:
        if not auth.get(field):
            fail(errors, f"auth.{field} is required and must be non-empty")
    if auth.get("location") and auth["location"] not in VALID_AUTH_LOCATION:
        fail(errors, f"auth.location must be one of {VALID_AUTH_LOCATION}")

    pricing = data.get("pricing") or {}
    for field in REQUIRED_PRICING:
        if not pricing.get(field):
            fail(errors, f"pricing.{field} is required and must be non-empty")
    checked = pricing.get("checked")
    if checked and not DATE_RE.match(str(checked)):
        fail(errors, f"pricing.checked must be YYYY-MM-DD, got {checked!r}")

    endpoints = data.get("endpoints") or []
    if not endpoints:
        fail(errors, "at least one endpoint is required")
    seen_ids = set()
    for i, ep in enumerate(endpoints):
        for field in REQUIRED_ENDPOINT:
            if not ep.get(field):
                fail(errors, f"endpoints[{i}].{field} is required and must be non-empty")
        eid = ep.get("id")
        if eid:
            if not ID_RE.match(eid):
                fail(errors, f"endpoints[{i}].id {eid!r} must look like <provider>.<action>")
            if eid in seen_ids:
                fail(errors, f"duplicate endpoint id: {eid}")
            seen_ids.add(eid)

    if data.get("status") == "verified":
        example_path = path.parent.parent / "examples" / f"{data.get('provider', path.stem)}.json"
        if not example_path.exists():
            fail(errors, f"status: verified requires a captured example at {example_path}")


# ---- models/*.yaml (muapi's own hosted models, routing vendor never disclosed) ----

REQUIRED_TOP_MODEL = ["id", "capability", "via", "title", "description", "docs_url", "status"]
FORBIDDEN_MODEL_FIELDS = ["base_url", "auth", "provider_name", "query_task_url", "adapter", "field_map", "endpoints"]
MODEL_ID_RE = re.compile(r"^muapi\.[a-z0-9][a-z0-9.-]*$")


def validate_model(path, data, errors):
    for field in REQUIRED_TOP_MODEL:
        if field not in data:
            fail(errors, f"missing required top-level field: {field}")

    for field in FORBIDDEN_MODEL_FIELDS:
        if field in data:
            fail(errors, f"models/*.yaml must never include {field!r} — that's internal routing detail")

    mid = data.get("id")
    if mid and not MODEL_ID_RE.match(mid):
        fail(errors, f"id {mid!r} must look like muapi.<name>")

    if data.get("via") and data["via"] != "muapi":
        fail(errors, "via must be 'muapi' for models/*.yaml (called through your own muapi key)")

    if "status" in data and data.get("status") not in VALID_STATUS_MODEL:
        fail(errors, f"models/*.yaml status must be one of {VALID_STATUS_MODEL}, got {data.get('status')!r}")

    docs_url = data.get("docs_url") or ""
    if docs_url and "muapi.ai" not in docs_url:
        fail(errors, f"docs_url for a models/*.yaml entry should point at muapi.ai, got {docs_url!r}")


# ---- shared entry point ----

def validate_entry(path):
    errors = []
    raw_text = path.read_text()
    check_secrets(raw_text, errors)

    leak = INTERNAL_VENDOR_NAMES.search(raw_text)
    if leak:
        fail(errors, f"internal routing-vendor name leaked: {leak.group(0)!r} — this must never appear in this repo")

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as e:
        return [f"invalid YAML: {e}"]

    if not isinstance(data, dict):
        return ["top-level document must be a mapping"]

    if path.parent.name == "providers":
        validate_provider(path, data, errors)
    elif path.parent.name == "models":
        validate_model(path, data, errors)
    else:
        fail(errors, f"unrecognized entry location: {path} (expected providers/ or models/)")

    return errors


def main(argv):
    if not argv:
        print("usage: catalog_validate.py providers/<file>.yaml [more files...]")
        return 2

    any_failed = False
    for arg in argv:
        path = Path(arg)
        if path.name in ("_TEMPLATE.yaml", ".gitkeep"):
            continue
        if not path.exists():
            print(f"SKIP {arg}: not found")
            continue
        errors = validate_entry(path)
        if errors:
            any_failed = True
            print(f"FAIL {path}")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"OK   {path}")

    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

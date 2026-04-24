#!/usr/bin/env python3
"""
Optional: offload plate extraction to a deepskyai.com server endpoint.

This script is a THIN CLIENT. It does not do any vision work itself — it POSTs
the plate image/PDF to a server endpoint and returns the briefing JSON.

The server endpoint is a future deployment. Today this script will simply
fail with a helpful message if you run it without the endpoint being live.
Use the hosting agent's native vision (per SKILL.md) in the meantime.

Usage:
    export DEEPSKY_API_KEY=sk-...
    python3 deepsky_brief.py /path/to/plate.png
    python3 deepsky_brief.py /path/to/plate.pdf --endpoint https://custom/api
    python3 deepsky_brief.py https://example.com/plate.png --url

Response (on success):
    Prints the JSON conforming to references/briefing-schema.json to stdout.

Exit codes:
    0   Success — JSON on stdout
    1   Missing DEEPSKY_API_KEY
    2   Input file not found / unreadable
    3   Endpoint not reachable or returned non-2xx
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

DEFAULT_ENDPOINT = "https://deepskyai.com/api/v1/briefing/plate"


def build_request(src: str, is_url: bool, endpoint: str, api_key: str) -> urllib.request.Request:
    """Build the POST request. Image/PDF is sent as base64 in a JSON body."""
    if is_url:
        body = {"plate_url": src}
    else:
        if not os.path.isfile(src):
            print(f"ERROR: file not found: {src}", file=sys.stderr)
            sys.exit(2)
        mime, _ = mimetypes.guess_type(src)
        with open(src, "rb") as f:
            raw = f.read()
        body = {
            "plate_b64": base64.b64encode(raw).decode("ascii"),
            "mime_type": mime or "application/octet-stream",
            "filename": os.path.basename(src),
        }

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "approach-briefing-skill/0.1 (+https://github.com/deepskyai/agent-tools)",
        },
    )
    return req


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Send an approach plate to the deepskyai.com briefing endpoint.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("src", help="Path to plate image/PDF, or URL with --url")
    p.add_argument("--url", action="store_true", help="Treat src as a URL instead of a file path")
    p.add_argument("--endpoint", default=DEFAULT_ENDPOINT,
                   help=f"Override endpoint (default {DEFAULT_ENDPOINT})")
    p.add_argument("--timeout", type=float, default=60.0, help="Seconds (default 60)")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    api_key = os.environ.get("DEEPSKY_API_KEY")
    if not api_key:
        print(
            "ERROR: DEEPSKY_API_KEY not set.\n"
            "The server endpoint is not live yet anyway — fall back to the\n"
            "hosting agent's native vision (see SKILL.md).",
            file=sys.stderr,
        )
        return 1

    req = build_request(args.src, args.url, args.endpoint, api_key)
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            payload = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR {e.code} from {args.endpoint}:\n{body}", file=sys.stderr)
        return 3
    except urllib.error.URLError as e:
        print(f"ERROR: cannot reach {args.endpoint}: {e.reason}", file=sys.stderr)
        return 3

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        print(payload)
        return 0

    print(json.dumps(parsed, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

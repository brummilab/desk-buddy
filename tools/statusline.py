"""Claude Code status line for Desk Buddy on Windows (statusline.sh's twin: Git for Windows has no jq).

Claude Code runs this after each reply with session JSON on stdin; it includes your plan's usage
limits (rate_limits.five_hour / seven_day: used_percentage, resets_at). This forwards that JSON
to the bridge (which turns it into Lump's usage-gauge colour) and prints a short status line.
Standard library only, so plain `py` runs it. Installed copy: ~/.desk-buddy/statusline.py
(referenced from ~/.claude/settings.json by tools/install_hooks.py).
"""
import json, math, sys, threading, urllib.request

BRIDGE = "http://127.0.0.1:47823/usage"


def forward(raw):
    try:
        req = urllib.request.Request(BRIDGE, data=raw, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=1).read()
    except Exception:
        pass                                   # no bridge: the status line still shows


def line(data):
    model = (data.get("model") or {}).get("display_name")
    limits = data.get("rate_limits") or {}
    parts = [model] if model else []
    for key, label in (("five_hour", "5h"), ("seven_day", "week")):
        pct = (limits.get(key) or {}).get("used_percentage")
        if isinstance(pct, (int, float)):
            parts.append(f"{label} {math.floor(pct)}%")
    return " · ".join(parts)


def main():
    raw = sys.stdin.buffer.read()
    t = threading.Thread(target=forward, args=(raw,), daemon=True)
    t.start()
    try:
        text = line(json.loads(raw or b"{}"))
    except Exception:
        text = ""
    if text:
        sys.stdout.buffer.write(text.encode("utf-8") + b"\n")   # not the console's code page: "·"
    t.join(1.2)                                # the POST is local: let it finish, but never hang


if __name__ == "__main__":
    main()

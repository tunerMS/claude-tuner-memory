#!/usr/bin/env python3
"""
Безопасный захват наблюдения для continuous-learning-v2.
Читает JSON хука из STDIN (как данные, не как код — без инъекции),
режет по денилисту cwd, дописывает наблюдение в observations.jsonl.

env: EVENT=pre|post  STORE=<path>  EXCLUDE=<path>  MAX_MB=<int>
"""
import json, os, sys, datetime

raw = sys.stdin.read()
try:
    d = json.loads(raw)
except Exception:
    sys.exit(0)

cwd = d.get("cwd", "") or ""

excl = os.environ.get("EXCLUDE", "")
if cwd and excl and os.path.exists(excl):
    with open(excl, encoding="utf-8") as fh:
        for line in fh:
            p = line.strip()
            if not p or p.startswith("#"):
                continue
            if cwd == p or cwd.startswith(p.rstrip("/") + "/"):
                sys.exit(0)

event = "tool_start" if os.environ.get("EVENT", "pre") == "pre" else "tool_complete"
tool = d.get("tool_name") or d.get("tool") or "unknown"
session = d.get("session_id") or d.get("session") or "unknown"


def clip(v, n):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s[:n]


obs = {
    "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "event": event,
    "tool": tool,
    "session": session,
}
if event == "tool_start":
    inp = d.get("tool_input", d.get("input"))
    if inp is not None:
        obs["input"] = clip(inp, 2000)
else:
    out = d.get("tool_response", d.get("tool_output", d.get("output")))
    if out is not None:
        obs["output"] = clip(out, 1000)

store = os.environ.get("STORE", os.path.expanduser("~/.claude/homunculus/observations.jsonl"))
try:
    max_b = int(os.environ.get("MAX_MB", "10")) * 1024 * 1024
    if os.path.exists(store) and os.path.getsize(store) >= max_b:
        adir = os.path.join(os.path.dirname(store), "observations.archive")
        os.makedirs(adir, exist_ok=True)
        os.replace(store, os.path.join(adir, "observations-" + obs["timestamp"].replace(":", "") + ".jsonl"))
except Exception:
    pass

with open(store, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(obs, ensure_ascii=False) + "\n")

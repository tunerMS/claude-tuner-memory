#!/usr/bin/env python3
"""
Прототип жнеца задач (read-side).
Берёт один транскрипт Claude Code (.jsonl) и сжимает его в компактный
дайджест задачи: юзер-промпты целиком, реплики ассистента и tool-вызовы
кратко, thinking + сырые tool-результаты отбрасываются.

Назначение: проверить КАЧЕСТВО восстановления задачи из лога ДО того,
как вешать хуки и писать в канон. Ничего не пишет в память/Obsidian.

usage: harvest.py <path-to-transcript.jsonl>
"""
import json, sys, os, datetime

MAX_ASSIST_TEXT = 400      # обрезка текста ассистента
MAX_TOOL_ARG = 140         # обрезка аргумента тула
MAX_TOOL_RESULT = 0        # сырые результаты тулов не тащим (0 = выкинуть)

# какое ключевое поле инпута показывать для каждого тула
TOOL_KEY = {
    "Bash": "command", "Read": "file_path", "Edit": "file_path",
    "Write": "file_path", "Grep": "pattern", "Glob": "pattern",
    "Task": "description", "WebFetch": "url", "WebSearch": "query",
    "TodoWrite": None, "Skill": "skill",
}

def clip(s, n):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:n] + "…"

def is_real_user_text(content):
    """str-контент юзера, который НЕ служебный (не вывод локальной команды/caveat)."""
    if not isinstance(content, str):
        return None
    t = content.strip()
    if not t:
        return None
    for marker in ("<local-command", "<command-", "<bash-", "Caveat:"):
        if t.startswith(marker):
            return None
    return t

def tool_oneliner(block):
    name = block.get("name", "tool")
    inp = block.get("input", {}) or {}
    key = TOOL_KEY.get(name, "_")
    if key is None:
        return name
    val = inp.get(key) if isinstance(inp, dict) else None
    if val is None and isinstance(inp, dict) and inp:
        # взять первое короткое поле
        k = next(iter(inp))
        val = f"{k}={inp[k]}"
    return f"{name}({clip(val, MAX_TOOL_ARG)})" if val else name

def parse(path):
    meta = {}
    events = []          # хронология: (ts, kind, text)
    counts = {"user_prompts": 0, "assistant_texts": 0, "tool_calls": 0,
              "thinking": 0, "tool_results": 0}
    tools_used = {}
    first_ts = last_ts = None

    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            typ = d.get("type")
            ts = d.get("timestamp")
            if ts:
                first_ts = first_ts or ts
                last_ts = ts
            # метаданные сессии — из первой полноценной записи
            if typ in ("user", "assistant") and not meta.get("cwd"):
                for k in ("cwd", "gitBranch", "version", "sessionId"):
                    if d.get(k):
                        meta[k] = d[k]

            msg = d.get("message")
            if typ == "user" and isinstance(msg, dict):
                if d.get("isMeta"):
                    continue
                content = msg.get("content")
                txt = is_real_user_text(content)
                if txt:
                    counts["user_prompts"] += 1
                    events.append((ts, "USER", txt))
                elif isinstance(content, list):
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "tool_result":
                            counts["tool_results"] += 1
                            if MAX_TOOL_RESULT:
                                events.append((ts, "RESULT", clip(b.get("content", ""), MAX_TOOL_RESULT)))

            elif typ == "assistant" and isinstance(msg, dict):
                content = msg.get("content", [])
                if isinstance(content, list):
                    for b in content:
                        if not isinstance(b, dict):
                            continue
                        bt = b.get("type")
                        if bt == "thinking":
                            counts["thinking"] += 1
                        elif bt == "text":
                            t = clip(b.get("text", ""), MAX_ASSIST_TEXT)
                            if t:
                                counts["assistant_texts"] += 1
                                events.append((ts, "CLAUDE", t))
                        elif bt == "tool_use":
                            counts["tool_calls"] += 1
                            nm = b.get("name", "tool")
                            tools_used[nm] = tools_used.get(nm, 0) + 1
                            events.append((ts, "TOOL", tool_oneliner(b)))
    return meta, events, counts, tools_used, first_ts, last_ts

def fmt_dur(a, b):
    try:
        fa = datetime.datetime.fromisoformat(a.replace("Z", "+00:00"))
        fb = datetime.datetime.fromisoformat(b.replace("Z", "+00:00"))
        m = int((fb - fa).total_seconds() // 60)
        return f"{m//60}ч {m%60}м" if m >= 60 else f"{m}м"
    except Exception:
        return "?"

def render(meta, events, counts, tools_used, first_ts, last_ts):
    out = []
    out.append("# ДАЙДЖЕСТ СЕССИИ (прототип жнеца)")
    out.append("")
    out.append(f"- session: `{meta.get('sessionId','?')}`")
    out.append(f"- cwd: `{meta.get('cwd','?')}`  |  branch: `{meta.get('gitBranch','-')}`")
    out.append(f"- период: {first_ts} → {last_ts}  (~{fmt_dur(first_ts, last_ts)})")
    out.append(f"- объём: промптов={counts['user_prompts']}, реплик={counts['assistant_texts']}, "
               f"tool-вызовов={counts['tool_calls']}, thinking-блоков выкинуто={counts['thinking']}, "
               f"tool-результатов выкинуто={counts['tool_results']}")
    top = sorted(tools_used.items(), key=lambda x: -x[1])
    out.append(f"- инструменты: " + ", ".join(f"{k}×{v}" for k, v in top))
    out.append("")
    out.append("## Хронология (сжатая)")
    out.append("")
    for ts, kind, text in events:
        prefix = {"USER": "🧑 ЮЗЕР", "CLAUDE": "🤖", "TOOL": "  ↳", "RESULT": "  ="}[kind]
        out.append(f"{prefix}: {text}")
    return "\n".join(out)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: harvest.py <transcript.jsonl>", file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    meta, events, counts, tools_used, first_ts, last_ts = parse(path)
    digest = render(meta, events, counts, tools_used, first_ts, last_ts)
    # оценим экономию
    raw = os.path.getsize(path)
    dig = len(digest.encode("utf-8"))
    print(digest)
    print("\n---")
    print(f"[сжатие: транскрипт {raw//1024} КБ → дайджест {dig//1024} КБ "
          f"= {100*dig//max(raw,1)}% от исходного]", file=sys.stderr)

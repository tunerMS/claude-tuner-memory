#!/usr/bin/env python3
"""
Жнец задач — ядро: один транскрипт → сжатое саммари → upsert в память.
Канон: <memory>/sessions/<project>.md
Спроектировано под recall ассистента (не для чтения глазами).

usage: harvester.py <transcript.jsonl>   # одна сессия (для теста/ручного прогона)
import: harvest_transcript(path) -> dict
env:    CTM_MEMORY_DIR — каталог памяти (по умолчанию вычисляется из $HOME)
"""
import sys, os, re, json, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harvest as H  # переиспользуем парсер дайджеста


def _default_mem_dir():
    # ~/.claude/projects/<slug>/memory, где slug = $HOME со слэшами-в-дефисы
    home = os.path.expanduser("~")
    slug = home.replace("/", "-")
    return os.path.join(home, ".claude", "projects", slug, "memory")


MEM = os.environ.get("CTM_MEMORY_DIR", _default_mem_dir())
SESS_DIR = os.path.join(MEM, "sessions")
ARCH_DIR = os.path.join(SESS_DIR, "archive")
MODEL = "sonnet"          # шаг качества; дёшево — на вход маленький дайджест
MAX_JOURNAL = 15          # сколько сессий держать в основном файле
MIN_PROMPTS = 2           # < 2 юзер-промптов = служебная/тривиальная, не жнём
SENTINEL = "HARVEST_INTERNAL_v1"   # метит наши собственные саммари-сессии (свипер их пропускает)


def known_projects():
    names = set()
    if os.path.isdir(SESS_DIR):
        for f in os.listdir(SESS_DIR):
            if f.endswith(".md"):
                names.add(f[:-3])
    for f in os.listdir(MEM):
        m = re.match(r'project_(.+)\.md$', f)
        if m:
            names.add(m.group(1).replace("_", "-"))
    return sorted(names)


def summarize(digest, hint):
    prompt = f"""{SENTINEL}
Ты — компонент памяти ассистента Claude. Ниже ДАЙДЖЕСТ одной рабочей сессии Claude Code (сжатый лог).
Верни СТРОГО один JSON-объект и больше ничего (без ``` и пояснений). Поля:
- "project": короткий стабильный слаг латиницей (kebab-case). Сопоставь с известными слагами: [{hint}]. Если ни один не подходит — придумай свой по сути работы.
- "current_state": 3-6 строк markdown — где проект СЕЙЧАС после этой сессии: точка возврата (коммит/состояние/ветка), что осталось/дальше. Плотно, для будущего себя, без воды.
- "session_summary": markdown 6-15 строк — что сделано в ЭТОЙ сессии: задачи, ключевые файлы/правки, коммиты (хэши), важные решения и их причины, фидбэк пользователя. ТОЛЬКО факты из дайджеста — ничего не выдумывай.

ДАЙДЖЕСТ:
{digest}
"""
    out = subprocess.run(
        ["claude", "--model", MODEL, "--print", "--max-turns", "1", prompt],
        capture_output=True, text=True, timeout=240,
    )
    txt = (out.stdout or "").strip()
    m = re.search(r'\{.*\}', txt, re.S)
    if not m:
        raise ValueError("в выводе LLM нет JSON: " + (txt[:400] or out.stderr[:400]))
    data = json.loads(m.group(0))
    for k in ("project", "current_state", "session_summary"):
        data.setdefault(k, "")
    data["project"] = re.sub(r'[^a-z0-9-]', '-', data["project"].strip().lower()) or "misc"
    return data


def _parse_journal(path):
    """Возвращает (order:list[sid], entries:{sid:(headerline, body)})."""
    order, entries = [], {}
    if not os.path.exists(path):
        return order, entries
    txt = open(path, encoding="utf-8").read()
    parts = txt.split("## Журнал", 1)
    if len(parts) < 2:
        return order, entries
    for chunk in parts[1].split("\n### ")[1:]:
        line, _, rest = chunk.partition("\n")
        toks = [t.strip() for t in line.split("·")]
        sid = toks[1] if len(toks) > 1 else line.strip()
        entries[sid] = ("### " + line.strip(), rest.rstrip())
        order.append(sid)
    return order, entries


def upsert(project, current_state, session_summary, sid, date_str, dur):
    os.makedirs(SESS_DIR, exist_ok=True)
    path = os.path.join(SESS_DIR, project + ".md")
    order, entries = _parse_journal(path)

    entries[sid] = (f"### {date_str} · {sid} · {dur}", session_summary.strip())
    order = [s for s in order if s != sid]
    order.insert(0, sid)  # новые сверху

    keep, overflow = order[:MAX_JOURNAL], order[MAX_JOURNAL:]

    out = [
        f"# Сессии: {project}",
        "<!-- AUTO-HARVEST (launchd-свипер). Канон recall. Руками не править — перезапишется. -->",
        "",
        "## 🔖 Текущее состояние",
        current_state.strip(),
        "",
        "## Журнал",
    ]
    for s in keep:
        h, b = entries[s]
        out += ["", h] + ([b] if b else [])
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")

    if overflow:
        os.makedirs(ARCH_DIR, exist_ok=True)
        with open(os.path.join(ARCH_DIR, project + ".md"), "a", encoding="utf-8") as fh:
            for s in overflow:
                h, b = entries[s]
                fh.write("\n" + h + "\n" + (b or "") + "\n")
    return path


def harvest_transcript(path):
    meta, events, counts, tools, first, last = H.parse(path)
    if counts["user_prompts"] < MIN_PROMPTS:
        return {"skipped": "too few prompts", "prompts": counts["user_prompts"]}
    digest = H.render(meta, events, counts, tools, first, last)
    res = summarize(digest, ", ".join(known_projects()) or "нет")
    sid = (meta.get("sessionId") or os.path.basename(path)[:8])[:8]
    date_str = (first or "")[:10] or "?"
    dur = H.fmt_dur(first, last) if (first and last) else "?"
    p = upsert(res["project"], res["current_state"], res["session_summary"], sid, date_str, dur)
    return {"project": res["project"], "path": p, "sid": sid}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: harvester.py <transcript.jsonl>", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(harvest_transcript(sys.argv[1]), ensure_ascii=False, indent=2))

#!/usr/bin/env python3
"""
Пишет/мёржит инстинкты из JSON (stdin) в instincts/personal/.
claude их только ВОЗВРАЩАЕТ текстом — файлы пишет этот скрипт → headless-безопасно
(не нужны разрешения на запись в фоновом `claude --print`).

stdin: {"instincts":[{id,title,trigger,confidence,domain,action,evidence}, ...]}
"""
import sys, os, re, json, datetime

INST = os.path.expanduser("~/.claude/homunculus/instincts/personal")


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def slug(s):
    s = re.sub(r'[^a-z0-9]+', '-', (s or '').strip().lower()).strip('-')
    return s or 'instinct'


def read_conf(path):
    try:
        m = re.search(r'confidence:\s*([0-9.]+)', open(path, encoding="utf-8").read())
        return float(m.group(1)) if m else None
    except Exception:
        return None


def bump_existing(path, conf, today):
    """Матч существующего инстинкта (модель вернула только id): повышаем
    confidence и last_observed, НЕ трогая текст — там вручную слитые
    триггеры/действия после дедупликации, их нельзя перезатирать."""
    txt = open(path, encoding="utf-8").read()
    txt = re.sub(r'(?m)^confidence:\s*[0-9.]+', f'confidence: {conf:.2f}', txt, count=1)
    txt = re.sub(r'(?m)^last_observed:\s*.+', f'last_observed: {today}', txt, count=1)
    open(path, "w", encoding="utf-8").write(txt)


def main():
    raw = sys.stdin.read()
    m = re.search(r'\{.*\}', raw, re.S)
    if not m:
        print("  writer: в выводе нет JSON")
        return
    try:
        data = json.loads(m.group(0))
    except Exception as e:
        print("  writer: битый JSON:", e)
        return

    items = data.get("instincts") or []
    if not items:
        print("  writer: чётких паттернов нет (0 инстинктов)")
        return

    os.makedirs(INST, exist_ok=True)
    today = datetime.date.today().isoformat()
    written = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        iid = slug(it.get("id") or it.get("title"))
        path = os.path.join(INST, iid + ".md")
        try:
            proposed = clamp(float(it.get("confidence", 0.3) or 0.3), 0.3, 0.9)
        except (TypeError, ValueError):
            proposed = 0.3
        existing = read_conf(path)
        has_content = bool((it.get("action") or "").strip() or (it.get("trigger") or "").strip())
        if existing is not None and not has_content:
            # дедуп-ответ analyze.sh: только id + confidence → бамп без перезаписи
            conf = clamp(max(existing, proposed) + 0.05, 0.3, 0.9)
            bump_existing(path, conf, today)
            written += 1
            print(f"  instinct: {iid} (match существующего, conf {conf:.2f})")
            continue
        if existing is None and not has_content:
            print(f"  writer: пропуск {iid} — новый id без action/trigger (пустышку не пишем)")
            continue
        # повтор паттерна растит уверенность; новый — берём как есть
        conf = clamp(max(existing, proposed) + 0.05, 0.3, 0.9) if existing is not None else proposed
        title = (it.get("title") or iid.replace("-", " ").capitalize()).strip()
        trigger = (it.get("trigger") or "").replace('"', "'").strip()
        domain = slug(it.get("domain") or "general")
        action = (it.get("action") or "").strip()
        evidence = (it.get("evidence") or "").strip()

        body = (
            f"---\n"
            f"id: {iid}\n"
            f'trigger: "{trigger}"\n'
            f"confidence: {conf:.2f}\n"
            f"domain: {domain}\n"
            f"source: session-observation\n"
            f"last_observed: {today}\n"
            f"---\n\n"
            f"# {title}\n\n"
            f"## Action\n{action}\n\n"
            f"## Evidence\n{evidence}\n"
        )
        open(path, "w", encoding="utf-8").write(body)
        written += 1
        print(f"  instinct: {iid} (conf {conf:.2f})")
    print(f"  writer: записано {written}")


if __name__ == "__main__":
    main()

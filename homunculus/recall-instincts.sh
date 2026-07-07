#!/bin/bash
# SessionStart-хук continuous-learning-v2: ПЕТЛЯ ПРИПОМИНАНИЯ.
#
# Скилл из коробки только КОПИТ инстинкты в файлы, но не возвращает их в
# сессию. Этот хук вливает накопленные инстинкты (confidence >= порога) в
# контекст новой сессии через additionalContext. Без него «Клод тебя
# запоминает» не работает. (Дистилляцию наблюдений в инстинкты делает
# launchd-агент analyze.sh, не этот хук.)

# Не вливаем в служебную сессию анализатора.
[ -n "${HOMUNCULUS_ANALYZING:-}" ] && exit 0

DIR="${HOME}/.claude/homunculus/instincts/personal"
[ -d "$DIR" ] || exit 0

python3 - "$DIR" <<'PY'
import sys, os, glob, re, json

d = sys.argv[1]
THRESHOLD = 0.5   # порог припоминания
items = []
for f in sorted(glob.glob(os.path.join(d, "*.md"))):
    try:
        txt = open(f, encoding="utf-8").read()
    except Exception:
        continue
    m = re.search(r'confidence:\s*([0-9.]+)', txt)
    conf = float(m.group(1)) if m else 0.0
    if conf < THRESHOLD:
        continue
    body = txt.split('---', 2)[-1].strip()
    title = re.search(r'^#\s*(.+)$', body, re.M)
    label = title.group(1).strip() if title else os.path.basename(f)[:-3]
    first = next((l.strip() for l in body.splitlines()
                  if l.strip() and not l.startswith('#')), '')
    items.append((conf, label, first))

if not items:
    sys.exit(0)

items.sort(key=lambda x: -x[0])
lines = [
    "# Выученные предпочтения Михаила (continuous-learning, conf>=%.1f)" % THRESHOLD,
    "Применяй, когда уместно. Если Михаил поправит — упомяни, это снизит уверенность инстинкта.",
    "",
]
# Кап: только топ-25 по confidence — держим инжект компактным (~10KB, не 24KB).
for conf, label, first in items[:25]:
    lines.append(f"- ({conf:.2f}) **{label}** — {first}")

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "\n".join(lines),
    }
}))
PY
exit 0

#!/bin/bash
# SessionStart-хук: авто-подгрузка session-memory (task-harvester) в контекст.
# Маппинг: basename(cwd) → <memory>/sessions/<name>.md
# Точного файла нет → компактный индекс доступных проектов (harvester путает
# похожие слаги, поэтому индекс важнее умного маппинга).
# env: CTM_MEMORY_DIR — каталог памяти (тот же, что у harvester)

# Гарды: фоновые headless-вызовы (homunculus/harvester) не кормим
[ -n "$HOMUNCULUS_ANALYZING" ] && exit 0
[ -n "$CC_BACKGROUND" ] && exit 0

MEM="${CTM_MEMORY_DIR:-$HOME/.claude/projects/${HOME//\//-}/memory}"
SESS_DIR="$MEM/sessions"
[ -d "$SESS_DIR" ] || exit 0

CWD=$(python3 -c "import sys,json; print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null)
if [ -z "$CWD" ] || [ "$CWD" = "/" ]; then exit 0; fi

NAME=$(basename "$CWD")
# Worktree-устойчивость: из любого git worktree настоящее имя репо = родитель
# главного .git (git-common-dir), а не имя worktree-директории.
GITCOMMON=$(git -C "$CWD" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
if [ -n "$GITCOMMON" ] && [ "$(basename "$GITCOMMON")" = ".git" ]; then
  NAME=$(basename "$(dirname "$GITCOMMON")")
fi
FILE="$SESS_DIR/$NAME.md"

# Фолбэк: самый длинный слаг, являющийся префиксом имени
# (fuel-python-ui-test-a1b2c → fuel-python-ui-test.md)
if [ ! -f "$FILE" ]; then
  best=""
  for f in "$SESS_DIR"/*.md; do
    b=$(basename "$f" .md)
    case "$NAME" in "$b"*) [ ${#b} -gt ${#best} ] && best="$b" ;; esac
  done
  if [ -n "$best" ]; then NAME="$best"; FILE="$SESS_DIR/$best.md"; fi
fi

if [ -f "$FILE" ]; then
  echo "== Авто-контекст: session-memory «$NAME» (task-harvester) =="
  awk '/^## 🔖/{f=1} /^## Журнал/{f=0} f' "$FILE" | head -40
  echo "→ Полная история: $FILE (раздел «Журнал»). Файл авто-генерируется, руками не править."
  RUNS="$HOME/.claude/memory-testruns/$NAME.log"
  if [ -f "$RUNS" ]; then
    echo "Последние прогоны тестов (testrun-capture):"
    tail -3 "$RUNS" | sed 's/^/  /'
  fi
else
  echo "== Session-memory (task-harvester): файла для «$NAME» нет =="
  echo "Доступные проекты (свежие сверху); когда попросят «подними контекст по X» — прочитай $SESS_DIR/<X>.md:"
  ls -t "$SESS_DIR" 2>/dev/null | head -12 | sed 's/\.md$//; s/^/  • /'
fi
exit 0

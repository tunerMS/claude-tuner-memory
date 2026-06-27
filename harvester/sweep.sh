#!/bin/bash
# launchd-обёртка свипера жнеца. Гонит sweep.py каждые ~15 мин.
set -u
DIR="${HOME}/.claude/harvester"
LOCK="${DIR}/.sweeping"
LOG="${DIR}/sweep.log"

[ -f "${DIR}/disabled" ] && exit 0
[ -n "${HARVESTER_RUNNING:-}" ] && exit 0
if [ -f "$LOCK" ]; then
  if [ -n "$(find "$LOCK" -mmin +60 2>/dev/null)" ]; then rm -f "$LOCK"; else exit 0; fi
fi
command -v claude >/dev/null 2>&1 || { echo "[$(date)] sweep: claude не найден" >> "$LOG"; exit 0; }

touch "$LOCK"
echo "[$(date)] sweep: старт" >> "$LOG"
HARVESTER_RUNNING=1 python3 "${DIR}/sweep.py" >> "$LOG" 2>&1
rm -f "$LOCK"
echo "[$(date)] sweep: готово" >> "$LOG"
exit 0

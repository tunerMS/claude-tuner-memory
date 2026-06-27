#!/bin/bash
# Захват наблюдений для continuous-learning-v2 + security-предохранитель.
#
# Заменяет штатный observe.sh (тот вклеивает JSON в исходник Python →
# хрупко и инъекционно-опасно). Здесь JSON парсится БЕЗОПАСНО как данные
# в _capture.py (stdin). Хук в settings.json указывает СЮДА.
#
# arg $1 = pre|post (tool_start|tool_complete).

INPUT=$(cat)
[ -z "$INPUT" ] && exit 0

# Рвём петлю: не наблюдаем активность самого homunculus.
case "$INPUT" in
  *homunculus*) exit 0 ;;
esac

printf '%s' "$INPUT" | \
  EVENT="${1:-pre}" \
  STORE="${HOME}/.claude/homunculus/observations.jsonl" \
  EXCLUDE="${HOME}/.claude/homunculus/exclude_paths" \
  MAX_MB=10 \
  python3 "${HOME}/.claude/homunculus/_capture.py"
exit 0

#!/bin/bash
# launchd-вход: локальное обслуживание памяти (бесплатно, без сети).
#   index    — освежить семантический индекс (инкрементально)
#   lifecycle — отчёт _review.md (протухание + near-dup)
#   link     — обновить блоки «Связанные (авто)»
# Точку 4 (graphify) сюда НЕ включаем — она платная/по требованию.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Пауза-рубильник, по аналогии с homunculus/harvester.
[ -f "$DIR/disabled" ] && { echo "$(date '+%F %T') disabled, skip"; exit 0; }

ts() { date '+%F %T'; }
echo "$(ts) maintain start"
"$DIR/mem" maintain
echo "$(ts) maintain done"

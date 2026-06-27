#!/usr/bin/env bash
# claude-tuner-memory — удаление. Снимает launchd-агенты и удаляет код подсистем.
# ПО УМОЛЧАНИЮ НЕ ТРОГАЕТ ТВОИ ДАННЫЕ (память, инстинкты, наблюдения).
# Флаг --purge-data удалит и их (НЕОБРАТИМО).
set -euo pipefail
HOME_DIR="${HOME}"; CLAUDE="${HOME_DIR}/.claude"; LA="${HOME_DIR}/Library/LaunchAgents"
PURGE=0; [ "${1:-}" = "--purge-data" ] && PURGE=1

for ag in com.memory.maintain com.harvester.sweep com.homunculus.observer; do
  launchctl unload "${LA}/${ag}.plist" 2>/dev/null || true
  rm -f "${LA}/${ag}.plist"
done

# код подсистем (не данные)
rm -rf "${CLAUDE}/memory-tools/memtools" "${CLAUDE}/memory-tools/tests" \
       "${CLAUDE}/memory-tools/.venv" "${CLAUDE}/memory-tools/.index" \
       "${CLAUDE}/memory-tools/"{mem,maintain.sh,pyproject.toml}
rm -f "${CLAUDE}/harvester/"{harvest.py,harvester.py,sweep.py,sweep.sh}
rm -f "${CLAUDE}/homunculus/"{capture-guard.sh,recall-instincts.sh,analyze.sh,_capture.py,_write_instincts.py}

if [ "$PURGE" -eq 1 ]; then
  echo "[!] --purge-data: удаляю наблюдения/инстинкты/состояние harvester"
  rm -rf "${CLAUDE}/homunculus/instincts" "${CLAUDE}/homunculus/observations"* \
         "${CLAUDE}/harvester/processed.json"
  echo "    (файлы памяти ~/.claude/projects/*/memory НЕ тронуты — удали вручную при желании)"
fi
echo "Готово. Не забудь убрать блок hooks из ~/.claude/settings.json."

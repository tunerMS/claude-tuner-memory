#!/usr/bin/env bash
# claude-tuner-memory — установщик.
# Раскладывает три подсистемы в ~/.claude/, поднимает venv memtools + локальную
# модель, шаблонит launchd-плисты. НЕ трогает твои данные и НЕ редактирует
# settings.json/CLAUDE.md (это печатается как ручные шаги в конце).
#
# Использование:
#   ./install.sh                 # всё: memtools + harvester + homunculus
#   ./install.sh --memtools-only # только семантический слой
#   ./install.sh --load-agents   # ещё и launchctl load плистов (macOS)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${HOME}"
CLAUDE="${HOME_DIR}/.claude"
MEMTOOLS_ONLY=0
LOAD_AGENTS=0
for a in "$@"; do
  case "$a" in
    --memtools-only) MEMTOOLS_ONLY=1 ;;
    --load-agents)   LOAD_AGENTS=1 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "неизвестный флаг: $a"; exit 1 ;;
  esac
done

say() { printf '\033[1;36m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$1"; }

command -v uv >/dev/null 2>&1 || { warn "нужен uv (https://docs.astral.sh/uv/). Установи и повтори."; exit 1; }
mkdir -p "$CLAUDE"

# ── memtools ───────────────────────────────────────────────────────────────
say "memtools → ${CLAUDE}/memory-tools"
mkdir -p "${CLAUDE}/memory-tools"
cp -R "${REPO}/memtools/memtools" "${CLAUDE}/memory-tools/"
cp -R "${REPO}/memtools/tests" "${CLAUDE}/memory-tools/"
cp "${REPO}/memtools/pyproject.toml" "${REPO}/memtools/mem" "${REPO}/memtools/maintain.sh" "${CLAUDE}/memory-tools/"
chmod +x "${CLAUDE}/memory-tools/mem" "${CLAUDE}/memory-tools/maintain.sh"

say "venv + зависимости (uv)"
( cd "${CLAUDE}/memory-tools" && uv venv .venv --python 3.12 >/dev/null 2>&1 || true
  uv pip install --python .venv -e . >/dev/null )

say "скачиваю локальную модель эмбеддингов (~1 раз, может занять минуты)"
"${CLAUDE}/memory-tools/.venv/bin/python" - <<'PY' || warn "модель не докачалась — повтори 'mem index' позже"
from sentence_transformers import SentenceTransformer
SentenceTransformer("intfloat/multilingual-e5-small")
print("модель готова")
PY

# launchd-плист memtools
if [ "$(uname)" = "Darwin" ]; then
  sed "s#@HOME@#${HOME_DIR}#g" "${REPO}/launchd/com.memory.maintain.plist.template" \
    > "${HOME_DIR}/Library/LaunchAgents/com.memory.maintain.plist"
fi

# ── harvester + homunculus ─────────────────────────────────────────────────
if [ "$MEMTOOLS_ONLY" -eq 0 ]; then
  say "harvester → ${CLAUDE}/harvester"
  mkdir -p "${CLAUDE}/harvester"
  cp "${REPO}/harvester/"{harvest.py,harvester.py,sweep.py,sweep.sh} "${CLAUDE}/harvester/"
  chmod +x "${CLAUDE}/harvester/sweep.sh"

  say "homunculus → ${CLAUDE}/homunculus"
  mkdir -p "${CLAUDE}/homunculus/instincts/personal"
  cp "${REPO}/homunculus/"{capture-guard.sh,recall-instincts.sh,analyze.sh,_capture.py,_write_instincts.py} "${CLAUDE}/homunculus/"
  chmod +x "${CLAUDE}/homunculus/"*.sh
  # денилист — не перезаписываем существующий
  if [ ! -f "${CLAUDE}/homunculus/exclude_paths" ]; then
    cp "${REPO}/homunculus/exclude_paths.example" "${CLAUDE}/homunculus/exclude_paths"
    warn "отредактируй ${CLAUDE}/homunculus/exclude_paths — добавь свои приватные репо"
  fi

  if [ "$(uname)" = "Darwin" ]; then
    sed "s#@HOME@#${HOME_DIR}#g" "${REPO}/launchd/com.harvester.sweep.plist.template" \
      > "${HOME_DIR}/Library/LaunchAgents/com.harvester.sweep.plist"
    sed "s#@HOME@#${HOME_DIR}#g" "${REPO}/launchd/com.homunculus.observer.plist.template" \
      > "${HOME_DIR}/Library/LaunchAgents/com.homunculus.observer.plist"
  fi
fi

# ── launchd load (опционально) ─────────────────────────────────────────────
AGENTS=(com.memory.maintain)
[ "$MEMTOOLS_ONLY" -eq 0 ] && AGENTS+=(com.harvester.sweep com.homunculus.observer)
if [ "$LOAD_AGENTS" -eq 1 ] && [ "$(uname)" = "Darwin" ]; then
  for ag in "${AGENTS[@]}"; do
    launchctl unload "${HOME_DIR}/Library/LaunchAgents/${ag}.plist" 2>/dev/null || true
    launchctl load -w "${HOME_DIR}/Library/LaunchAgents/${ag}.plist" && say "загружен ${ag}"
  done
fi

# ── финал: ручные шаги ─────────────────────────────────────────────────────
cat <<EOF

$(say "Готово. Осталось 3 ручных шага (намеренно не автоматизированы):")

1) КОНВЕНЦИЯ ПАМЯТИ — добавь содержимое в ~/.claude/CLAUDE.md:
     memory-convention/memory-instructions.md
   и создай стартовый индекс (если ещё нет):
     cp memory-convention/MEMORY.template.md <твой-memory>/MEMORY.md

2) ХУКИ ОБУЧЕНИЯ (если ставил harvester+homunculus) — слей блок hooks
   из hooks/settings.hooks.json в ~/.claude/settings.json
   (добавляй в существующие массивы, не затирай).

3) ВКЛЮЧИ ФОНОВЫЕ АГЕНТЫ (если не указывал --load-agents):
EOF
for ag in "${AGENTS[@]}"; do
  echo "     launchctl load -w ~/Library/LaunchAgents/${ag}.plist"
done
cat <<EOF

Проверка memtools:
     ~/.claude/memory-tools/mem index
     ~/.claude/memory-tools/mem recall "что-нибудь из твоей памяти"

Пауза любой подсистемы: touch ~/.claude/<memory-tools|harvester|homunculus>/disabled
EOF

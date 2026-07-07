#!/bin/bash
# Дистилляция наблюдений → инстинкты. Запускается launchd-агентом каждые 30 мин.
# Мгновенно выходит, если свежих наблюдений мало → токены тратятся только
# после реальной активности. Развязан от сессий, переживает ребут.
set -u

DIR="${HOME}/.claude/homunculus"
OBS="${DIR}/observations.jsonl"
INST="${DIR}/instincts/personal"
LOG="${DIR}/observer.log"
LOCK="${DIR}/.analyzing"
MIN_OBS=10
MODEL="sonnet"   # шаг, определяющий качество обучения; дёшево из-за чистки наблюдений после прогона

# guard: ручной стоп-кран
[ -f "${DIR}/disabled" ] && exit 0
# guard: не запускаться из служебной сессии анализатора (на всякий случай)
[ -n "${HOMUNCULUS_ANALYZING:-}" ] && exit 0
# guard: лок (чистим, если завис > 20 мин)
if [ -f "$LOCK" ]; then
  if [ -n "$(find "$LOCK" -mmin +20 2>/dev/null)" ]; then rm -f "$LOCK"; else exit 0; fi
fi

mkdir -p "$INST"
n=$(wc -l < "$OBS" 2>/dev/null || echo 0)
[ "${n:-0}" -lt "$MIN_OBS" ] && exit 0

if ! command -v claude >/dev/null 2>&1; then
  echo "[$(date)] analyze: claude CLI не найден в PATH" >> "$LOG"
  exit 0
fi

touch "$LOCK"
echo "[$(date)] analyze: $n наблюдений (модель $MODEL)" >> "$LOG"

# Инлайним наблюдения в промпт (без тулов claude → headless-безопасно).
OBS_CONTENT=$(tail -c 120000 "$OBS")

# Существующие инстинкты (id: триггер) — модель должна матчить паттерн в них,
# а не плодить новые слаги-дубли (bash-tail-limit / cap-bash-output / ...).
# Подстановка $EXISTING в PROMPT безопасна: значение переменной bash не
# re-евалюирует (backtick-и из триггеров не исполняются).
EXISTING=$(python3 - "$INST" <<'PY'
import sys, os, glob, re
d = sys.argv[1]
for f in sorted(glob.glob(os.path.join(d, "*.md"))):
    try:
        txt = open(f, encoding="utf-8").read()
    except Exception:
        continue
    m = re.search(r'^trigger:\s*"?(.*?)"?\s*$', txt, re.M)
    print(f"- {os.path.basename(f)[:-3]}: {(m.group(1) if m else '')[:90]}")
PY
)

PROMPT="Ниже JSONL-лог моих действий в Claude Code (наблюдения за сессиями). Найди ПОВТОРЯЮЩИЕСЯ паттерны (3+ раз): предпочтения инструментов, типовые воркфлоу, повторяющиеся правки, схемы error->fix, мои поправки.
Верни СТРОГО один JSON-объект и больше ничего (без \`\`\` и пояснений):
{\"instincts\":[{\"id\":\"kebab-slug\",\"title\":\"короткий заголовок\",\"trigger\":\"когда ...\",\"confidence\":<0.3-0.9 по частоте>,\"domain\":\"workflow|code-style|testing|git|debugging|tooling\",\"action\":\"что делать\",\"evidence\":\"на чём основано\"}]}
Будь консервативен — только явные повторы (3+). НИКОГДА не клади секреты, токены или сырое содержимое файлов — только поведенческие паттерны. Нет чёткого паттерна — верни {\"instincts\":[]}.

УЖЕ ИЗВЕСТНЫЕ ИНСТИНКТЫ (id: триггер):
$EXISTING

ДЕДУПЛИКАЦИЯ: если найденный паттерн ПО СМЫСЛУ совпадает с уже известным (та же привычка, даже если формулировка другая) — верни объект {\"id\":\"<точный-id-из-списка>\",\"confidence\":<0.3-0.9>} БЕЗ полей title/trigger/action/evidence: система сама повысит уверенность существующего. НЕ создавай новый id для вариации известного паттерна. Новый id — только для паттерна, которого в списке нет.

НАБЛЮДЕНИЯ:
$OBS_CONTENT"

# claude ВОЗВРАЩАЕТ JSON (без тулов), файлы пишет _write_instincts.py.
RESULT=$(HOMUNCULUS_ANALYZING=1 claude --model "$MODEL" --print --max-turns 1 "$PROMPT" 2>>"$LOG")
printf '%s' "$RESULT" | python3 "${DIR}/_write_instincts.py" >> "$LOG" 2>&1 || true

# архивируем обработанное и обнуляем
adir="${DIR}/observations.archive"
mkdir -p "$adir"
mv "$OBS" "${adir}/processed-$(date +%Y%m%d-%H%M%S).jsonl" 2>/dev/null || true
: > "$OBS"
rm -f "$LOCK"
echo "[$(date)] analyze: готово" >> "$LOG"
exit 0

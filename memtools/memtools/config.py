"""Пути и константы. Все значения переопределяются через env (MEMTOOLS_*)."""
import os
from pathlib import Path

HOME = Path(os.path.expanduser("~"))


def _default_mem_dir() -> Path:
    """Канон файловой памяти Claude Code.

    Claude хранит память в ~/.claude/projects/<slug>/memory, где <slug> — это
    рабочая директория сессии с '/' заменёнными на '-'. Для сессий из домашней
    папки это HOME со слэшами-в-дефисы (напр. /Users/alice → -Users-alice).
    Переопредели MEMTOOLS_MEM_DIR, если запускаешь Claude из другого места.
    """
    slug = str(HOME).replace("/", "-")
    return HOME / ".claude" / "projects" / slug / "memory"


# Канон файловой памяти Claude.
MEM_DIR = Path(os.environ.get("MEMTOOLS_MEM_DIR", _default_mem_dir()))

# Куда кладём индекс/служебные артефакты (вне корпуса памяти, чтобы не зашумлять).
TOOLS_DIR = Path(os.environ.get(
    "MEMTOOLS_DIR", HOME / ".claude" / "memory-tools",
))
INDEX_DIR = Path(os.environ.get("MEMTOOLS_INDEX_DIR", TOOLS_DIR / ".index"))

# Локальная мультиязычная модель (RU + EN). e5 — асимметричный retrieval
# (короткий запрос → длинный документ); префиксы query:/passage: включаются сами.
# Лёгкая альтернатива: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
MODEL_NAME = os.environ.get("MEMTOOLS_MODEL", "intfloat/multilingual-e5-small")
# Префиксы query:/passage: нужны моделям e5 (асимметрия). Для остальных — пусто.
# Авто-детект по имени; перекрывается env MEMTOOLS_QUERY_PREFIX / _PASSAGE_PREFIX.
_IS_E5 = "e5" in MODEL_NAME.lower()
QUERY_PREFIX = os.environ.get("MEMTOOLS_QUERY_PREFIX", "query: " if _IS_E5 else "")
PASSAGE_PREFIX = os.environ.get("MEMTOOLS_PASSAGE_PREFIX", "passage: " if _IS_E5 else "")

# Файлы, которые НЕ индексируем и НЕ линкуем (служебные/авто-перезаписываемые).
EXCLUDE_NAMES = {"_review.md"}

# Подкаталог авто-харвеста: индексируем для recall, но НЕ линкуем
# (harvester перезаписывает эти файлы — наш блок затрётся).
SESSIONS_SUBDIR = "sessions"

# Чанкинг.
MAX_CHUNK_CHARS = int(os.environ.get("MEMTOOLS_MAX_CHUNK_CHARS", "1500"))

# Lifecycle. Пороги — в ЦЕНТРИРОВАННОМ косинусе (см. filevec.file_vectors):
# там mean≈0, max≈0.65, поэтому значения сильно ниже «сырых» 0.9+.
STALE_DAYS = int(os.environ.get("MEMTOOLS_STALE_DAYS", "30"))
DUP_THRESHOLD = float(os.environ.get("MEMTOOLS_DUP_THRESHOLD", "0.55"))

# Linker (тоже центрированный косинус).
LINK_TOP_N = int(os.environ.get("MEMTOOLS_LINK_TOP_N", "3"))
LINK_THRESHOLD = float(os.environ.get("MEMTOOLS_LINK_THRESHOLD", "0.25"))
# Файлы, которые не линкуем и не делаем целью ссылок (всегда-загружаемый индекс).
LINK_EXCLUDE = {"MEMORY.md"}
RELATED_START = "<!-- auto-related:start -->"
RELATED_END = "<!-- auto-related:end -->"

# Recall.
DEFAULT_K = int(os.environ.get("MEMTOOLS_K", "8"))

"""Режет markdown-файл памяти на чанки с провенансом (файл + заголовок).

Стратегия (KISS):
  - frontmatter (--- ... ---) отбрасываем из тела, но имя/слаг достаём отдельно;
  - тело режем по заголовкам markdown (строки, начинающиеся с #);
  - длинные секции добивочно дробим по абзацам до MAX_CHUNK_CHARS;
  - авто-блок «Связанные» (RELATED_START..END) вырезаем — это наш же продукт,
    индексировать его смысла нет.
"""
import re
from dataclasses import dataclass

from . import config

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
_NAME = re.compile(r"^name:\s*(.+)$", re.M)
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass(frozen=True)
class Chunk:
    file: str        # путь относительно MEM_DIR
    heading: str     # ближайший заголовок (или "" для преамбулы)
    text: str
    ord: int         # порядковый номер чанка в файле


def slug_of(raw: str, fallback: str) -> str:
    """Слаг из frontmatter name:, иначе имя файла без расширения."""
    m = _FRONTMATTER.match(raw)
    if m:
        nm = _NAME.search(m.group(1))
        if nm:
            return nm.group(1).strip()
    return fallback


def strip_frontmatter(raw: str) -> str:
    return _FRONTMATTER.sub("", raw, count=1)


def strip_related_block(raw: str) -> str:
    """Удаляет управляемый блок «Связанные (авто)», если он есть."""
    s, e = config.RELATED_START, config.RELATED_END
    if s in raw and e in raw:
        pre, _, rest = raw.partition(s)
        _, _, post = rest.partition(e)
        return (pre.rstrip() + "\n" + post.lstrip()).strip() + "\n"
    return raw


def _split_long(text: str, limit: int) -> list[str]:
    """Дробит длинный текст по абзацам, не разрывая их, до лимита символов."""
    text = text.strip()
    if len(text) <= limit:
        return [text] if text else []
    out, buf = [], ""
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if buf and len(buf) + len(para) + 2 > limit:
            out.append(buf)
            buf = para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf:
        out.append(buf)
    return out


def chunk_text(rel_path: str, raw: str, limit: int | None = None) -> list[Chunk]:
    """Главная функция: сырой текст файла → список Chunk."""
    limit = limit or config.MAX_CHUNK_CHARS
    body = strip_related_block(strip_frontmatter(raw))

    # Группируем строки по заголовкам.
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in body.splitlines():
        m = _HEADING.match(line)
        if m:
            sections.append((m.group(2).strip(), []))
        else:
            sections[-1][1].append(line)

    chunks: list[Chunk] = []
    n = 0
    for heading, lines in sections:
        text = "\n".join(lines).strip()
        if heading:
            # Заголовок тоже несёт смысл — приклеиваем к телу секции.
            text = f"{heading}\n{text}".strip()
        for piece in _split_long(text, limit):
            chunks.append(Chunk(file=rel_path, heading=heading, text=piece, ord=n))
            n += 1
    return chunks

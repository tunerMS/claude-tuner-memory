"""Точка 3 — «memify»-линковка: авто-блок «Связанные» с [[links]].

Для каждого курируемого файла верхнего уровня находим top-N семантически
близких и поддерживаем управляемый блок в конце файла. Блок аддитивен и
регенерируется целиком (идемпотентно) — ручной текст файла не трогаем.

sessions/* НЕ линкуем: harvester их перезаписывает, блок бы терялся.
"""
from pathlib import Path

import numpy as np

from . import config
from .chunker import slug_of
from .filevec import file_vectors


def _remove_block(raw: str) -> str:
    s, e = config.RELATED_START, config.RELATED_END
    if s not in raw:
        return raw.rstrip() + "\n"
    pre = raw.split(s, 1)[0].rstrip()
    post = raw.split(e, 1)[1].strip() if e in raw else ""
    body = pre + (("\n\n" + post) if post else "")
    return body.rstrip() + "\n"


def _render_block(related: list[tuple[str, float]]) -> str:
    lines = [config.RELATED_START, "## Связанные (авто)"]
    for slug, score in related:
        lines.append(f"- [[{slug}]] — {score:.2f}")
    lines.append(config.RELATED_END)
    return "\n".join(lines)


def compute_links(top_n: int | None = None, threshold: float | None = None) -> dict:
    """rel-имя файла → список (slug_цели, score). Только верхний уровень."""
    top_n = top_n or config.LINK_TOP_N
    threshold = threshold if threshold is not None else config.LINK_THRESHOLD
    names, mat = file_vectors(only_top_level=True, centered=True)
    if len(names) < 2:
        return {}

    # rel → slug цели: frontmatter name:, иначе кебаб от имени файла
    # (конвенция памяти — [[kebab-case]], подчёркивания не используются).
    slugs: dict[str, str] = {}
    for rel in names:
        raw = (config.MEM_DIR / rel).read_text(encoding="utf-8", errors="ignore")
        slugs[rel] = slug_of(raw, Path(rel).stem.replace("_", "-"))

    sim = mat @ mat.T
    out: dict[str, list[tuple[str, float]]] = {}
    for i, rel in enumerate(names):
        if rel in config.LINK_EXCLUDE:          # индекс/служебные — не линкуем
            continue
        order = np.argsort(-sim[i])
        rel_links: list[tuple[str, float]] = []
        for j in order:
            if int(j) == i or names[int(j)] in config.LINK_EXCLUDE:
                continue
            score = float(sim[i, int(j)])
            if score < threshold:
                break
            rel_links.append((slugs[names[int(j)]], score))
            if len(rel_links) >= top_n:
                break
        if rel_links:
            out[rel] = rel_links
    return out


def apply_links(top_n: int | None = None, threshold: float | None = None) -> dict:
    """Пишет/обновляет блоки «Связанные» в файлах. → статистика."""
    links = compute_links(top_n, threshold)
    written = 0
    for rel, related in links.items():
        path = config.MEM_DIR / rel
        raw = path.read_text(encoding="utf-8", errors="ignore")
        body = _remove_block(raw)
        new = body.rstrip() + "\n\n" + _render_block(related) + "\n"
        if new != raw:
            path.write_text(new, encoding="utf-8")
            written += 1
    return {"linked_files": len(links), "written": written}

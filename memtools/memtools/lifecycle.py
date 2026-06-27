"""Точка 2 — жизненный цикл памяти: протухание + near-dup.

ВАЖНО: ничего не удаляет. Только формирует отчёт _review.md с кандидатами
на ревизию — решение оставляет человеку/агенту (норма «посмотри перед удалением»).
"""
import time
from pathlib import Path

import numpy as np

from . import config
from .filevec import file_vectors


def stale_files(mem_dir: Path | None = None, days: int | None = None) -> list[dict]:
    """Файлы верхнего уровня, не менявшиеся дольше N дней."""
    mem_dir = mem_dir or config.MEM_DIR
    days = days if days is not None else config.STALE_DAYS
    now = time.time()
    out = []
    for p in sorted(mem_dir.glob("*.md")):
        if p.name in config.EXCLUDE_NAMES or p.name == "MEMORY.md":
            continue
        age = (now - p.stat().st_mtime) / 86400.0
        if age >= days:
            out.append({"file": p.name, "age_days": round(age, 1)})
    out.sort(key=lambda x: -x["age_days"])
    return out


def dup_pairs(threshold: float | None = None) -> list[dict]:
    """Пары файлов с косинусной близостью выше порога (кандидаты на дубль/слияние)."""
    threshold = threshold if threshold is not None else config.DUP_THRESHOLD
    names, mat = file_vectors(only_top_level=True, centered=True)
    if len(names) < 2:
        return []
    sim = mat @ mat.T
    pairs = []
    n = len(names)
    for i in range(n):
        for j in range(i + 1, n):
            s = float(sim[i, j])
            if s >= threshold:
                pairs.append({"a": names[i], "b": names[j], "score": round(s, 3)})
    pairs.sort(key=lambda x: -x["score"])
    return pairs


def build_report(mem_dir: Path | None = None) -> str:
    """Собирает текст _review.md (не пишет на диск)."""
    mem_dir = mem_dir or config.MEM_DIR
    stale = stale_files(mem_dir)
    dups = dup_pairs()
    lines = [
        "# Ревизия памяти (авто, memtools)",
        "",
        "Сгенерировано автоматически. **Ничего не удалено** — это кандидаты на ревизию.",
        "Реши вручную: обновить / слить / удалить / оставить.",
        "",
        f"## Протухшие (> {config.STALE_DAYS} дн. без правок) — {len(stale)}",
        "",
    ]
    if stale:
        for s in stale:
            lines.append(f"- `{s['file']}` — {s['age_days']} дн.")
    else:
        lines.append("_нет_")
    lines += ["", f"## Похожие пары (cosine ≥ {config.DUP_THRESHOLD}) — {len(dups)}", ""]
    if dups:
        for d in dups:
            lines.append(f"- `{d['a']}` ⇄ `{d['b']}` — {d['score']}")
    else:
        lines.append("_нет_")
    lines.append("")
    return "\n".join(lines)


def write_report(mem_dir: Path | None = None) -> Path:
    mem_dir = mem_dir or config.MEM_DIR
    path = mem_dir / "_review.md"
    path.write_text(build_report(mem_dir), encoding="utf-8")
    return path

"""Семантический recall: запрос → top-k чанков с провенансом.

Векторы уже L2-нормированы → косинус = скалярное произведение.
"""
import numpy as np

from . import config
from .index import load_index


def recall(query: str, embed_fn, k: int | None = None) -> list[dict]:
    """→ список {score, file, heading, text}, отсортирован по убыванию score."""
    k = k or config.DEFAULT_K
    vectors, meta = load_index()
    if vectors is None or vectors.shape[0] == 0:
        return []
    qv = embed_fn([query], "query")[0]
    scores = vectors @ qv
    top = np.argsort(-scores)[:k]
    out = []
    for i in top:
        ch = meta["chunks"][int(i)]
        out.append({
            "score": float(scores[int(i)]),
            "file": ch["file"],
            "heading": ch["heading"],
            "text": ch["text"],
        })
    return out


def format_results(results: list[dict], max_chars: int = 600) -> str:
    """Человекочитаемый вывод для CLI / инъекции в контекст."""
    if not results:
        return "(индекс пуст или совпадений нет)"
    blocks = []
    for r in results:
        head = f"[{r['score']:.3f}] {r['file']}" + (f" › {r['heading']}" if r['heading'] else "")
        text = r["text"]
        if len(text) > max_chars:
            text = text[:max_chars].rstrip() + " …"
        blocks.append(f"{head}\n{text}")
    return "\n\n".join(blocks)

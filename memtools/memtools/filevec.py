"""Векторы уровня файла (усреднение чанков) — для near-dup и линковки.

Берём строки из готового индекса, агрегируем по файлам, L2-нормируем.
Так lifecycle/linker не переэмбеддят — работают поверх index.
"""
import numpy as np

from .index import load_index


def _l2(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


def file_vectors(only_top_level: bool = False, centered: bool = False):
    """→ (names: list[str], matrix: np.ndarray[len(names), dim]).

    only_top_level=True исключает sessions/* (для линковки курируемых файлов).
    Вектор файла = L2-нормированное среднее его чанк-векторов.

    centered=True вычитает средний вектор корпуса и ренормирует — лечит
    анизотропию эмбеддингов (e5 кладёт всё в узкий конус, сырой косинус ≈0.9+
    у всего подряд). Для near-dup и линковки нужен именно центрированный косинус.
    """
    vectors, meta = load_index()
    if vectors is None or vectors.shape[0] == 0:
        return [], np.zeros((0, 0), dtype=np.float32)

    names: list[str] = []
    rows: list[np.ndarray] = []
    for rel, fm in meta["files"].items():
        if only_top_level and "/" in rel:
            continue
        c = fm["row_count"]
        if c == 0:
            continue
        s = fm["row_start"]
        mean = vectors[s:s + c].mean(axis=0)
        norm = np.linalg.norm(mean)
        if norm == 0:
            continue
        names.append(rel)
        rows.append(mean / norm)
    if not rows:
        return [], np.zeros((0, 0), dtype=np.float32)
    mat = np.vstack(rows).astype(np.float32)
    if centered and mat.shape[0] >= 2:
        mat = _l2(mat - mat.mean(axis=0, keepdims=True))
    return names, mat

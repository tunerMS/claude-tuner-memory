"""Инкрементальный векторный индекс корпуса памяти.

Хранилище (в INDEX_DIR):
  vectors.npy  — матрица float32 [N, dim], строки выровнены с meta["chunks"]
  meta.json    — {model, files:{rel:{hash,row_start,row_count,mtime}}, chunks:[...]}

Инкрементальность: для файла с неизменившимся content-hash переиспользуем
старые строки векторов — не переэмбеддим. Меняется модель → полный ребилд.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from . import config
from .chunker import chunk_text


def discover_files(mem_dir: Path | None = None) -> list[Path]:
    """Все .md корпуса: верхний уровень + sessions/, кроме служебных/архива."""
    mem_dir = mem_dir or config.MEM_DIR
    files: list[Path] = []
    for p in sorted(mem_dir.glob("*.md")):
        if p.name not in config.EXCLUDE_NAMES:
            files.append(p)
    sess = mem_dir / config.SESSIONS_SUBDIR
    if sess.is_dir():
        files.extend(sorted(sess.glob("*.md")))
    return files


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _vectors_path() -> Path:
    return config.INDEX_DIR / "vectors.npy"


def _meta_path() -> Path:
    return config.INDEX_DIR / "meta.json"


def load_index():
    """→ (vectors|None, meta|None). Отсутствие индекса не ошибка."""
    vp, mp = _vectors_path(), _meta_path()
    if not vp.exists() or not mp.exists():
        return None, None
    try:
        vectors = np.load(vp)
        meta = json.loads(mp.read_text(encoding="utf-8"))
        return vectors, meta
    except Exception:
        return None, None


def _save(vectors: np.ndarray, meta: dict) -> None:
    config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    vp, mp = _vectors_path(), _meta_path()
    tmp_v = config.INDEX_DIR / "vectors.tmp.npy"   # ends with .npy → np.save не дописывает
    np.save(tmp_v, vectors)
    tmp_v.replace(vp)
    tmp_m = config.INDEX_DIR / "meta.tmp.json"
    tmp_m.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    tmp_m.replace(mp)


def build_index(embed_fn, mem_dir: Path | None = None) -> dict:
    """(Пере)строить индекс. embed_fn: list[str] -> np.ndarray. → статистика."""
    mem_dir = mem_dir or config.MEM_DIR
    old_vecs, old_meta = load_index()
    model_changed = not old_meta or old_meta.get("model") != config.MODEL_NAME
    old_files = {} if model_changed else (old_meta or {}).get("files", {})

    rows: list[np.ndarray] = []
    chunks_meta: list[dict] = []
    files_meta: dict[str, dict] = {}
    reused = embedded = 0

    for path in discover_files(mem_dir):
        rel = str(path.relative_to(mem_dir))
        raw = path.read_text(encoding="utf-8", errors="ignore")
        h = _hash(raw)
        prev = old_files.get(rel)

        if prev and prev.get("hash") == h and old_vecs is not None:
            s, c = prev["row_start"], prev["row_count"]
            block = old_vecs[s:s + c]
            block_chunks = old_meta["chunks"][s:s + c]
            reused += c
        else:
            chunks = chunk_text(rel, raw)
            block = (
                embed_fn([c.text for c in chunks], "passage")
                if chunks else np.zeros((0, 0))
            )
            block_chunks = [
                {"file": c.file, "heading": c.heading, "text": c.text, "ord": c.ord}
                for c in chunks
            ]
            embedded += len(block_chunks)

        start = sum(r.shape[0] for r in rows)
        if block.shape[0]:
            rows.append(block)
        chunks_meta.extend(block_chunks)
        files_meta[rel] = {
            "hash": h,
            "row_start": start,
            "row_count": len(block_chunks),
            "mtime": path.stat().st_mtime,
        }

    vectors = (
        np.vstack(rows).astype(np.float32) if rows
        else np.zeros((0, 384), dtype=np.float32)
    )
    meta = {"model": config.MODEL_NAME, "files": files_meta, "chunks": chunks_meta}
    _save(vectors, meta)
    return {
        "files": len(files_meta),
        "chunks": len(chunks_meta),
        "reused": reused,
        "embedded": embedded,
        "model_changed": model_changed,
    }

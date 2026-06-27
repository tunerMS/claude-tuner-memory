"""Общие фикстуры: временный корпус памяти + детерминированный фейковый эмбеддер."""
import hashlib
import re

import numpy as np
import pytest

from memtools import config

DIM = 64


def fake_embed(texts, kind="passage"):
    """Bag-of-tokens хэш-эмбеддинг: стабильный, без модели, схожие тексты близки.

    kind игнорируем — фейк симметричен (префиксы e5 на хэш не влияют по смыслу).
    """
    out = np.zeros((len(texts), DIM), dtype=np.float32)
    for i, t in enumerate(texts):
        for tok in re.findall(r"\w+", t.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM
            out[i, h] += 1.0
    norms = np.linalg.norm(out, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (out / norms).astype(np.float32)


@pytest.fixture
def mem(tmp_path, monkeypatch):
    """Пустой временный корпус с пропатченными путями config."""
    mem_dir = tmp_path / "memory"
    (mem_dir / "sessions").mkdir(parents=True)
    index_dir = tmp_path / ".index"
    monkeypatch.setattr(config, "MEM_DIR", mem_dir)
    monkeypatch.setattr(config, "INDEX_DIR", index_dir)
    monkeypatch.setattr(config, "TOOLS_DIR", tmp_path)
    return mem_dir


def write(mem_dir, name, text):
    p = mem_dir / name
    p.write_text(text, encoding="utf-8")
    return p

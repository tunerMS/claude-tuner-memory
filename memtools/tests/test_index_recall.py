from memtools.index import build_index, load_index
from memtools.recall import recall
from conftest import fake_embed, write


def test_build_and_load(mem):
    write(mem, "a.md", "# Кафка\nтопики оффсеты консьюмер группа")
    write(mem, "b.md", "# Верстка\nfigma пиксели наложение")
    stats = build_index(fake_embed, mem)
    assert stats["files"] == 2
    assert stats["chunks"] >= 2
    vectors, meta = load_index()
    assert vectors.shape[0] == len(meta["chunks"])


def test_incremental_reuse(mem):
    write(mem, "a.md", "# Кафка\nтопики оффсеты")
    write(mem, "b.md", "# Верстка\nfigma пиксели")
    build_index(fake_embed, mem)
    stats2 = build_index(fake_embed, mem)
    assert stats2["embedded"] == 0
    assert stats2["reused"] > 0


def test_incremental_reembeds_changed(mem):
    write(mem, "a.md", "# Кафка\nтопики")
    write(mem, "b.md", "# Верстка\nfigma")
    build_index(fake_embed, mem)
    write(mem, "a.md", "# Кафка\nтопики оффсеты консьюмер новый текст")
    stats = build_index(fake_embed, mem)
    assert stats["embedded"] >= 1
    assert stats["reused"] >= 1


def test_recall_ranks_relevant_first(mem):
    write(mem, "kafka.md", "# Кафка\nтопики оффсеты консьюмер группа лаг")
    write(mem, "figma.md", "# Верстка\nfigma пиксели наложение макет")
    build_index(fake_embed, mem)
    res = recall("консьюмер оффсеты лаг", fake_embed, k=2)
    assert res
    assert res[0]["file"] == "kafka.md"


def test_recall_empty_index(mem):
    assert recall("что угодно", fake_embed) == []

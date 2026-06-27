from memtools import config
from memtools.index import build_index
from memtools.linker import apply_links, compute_links
from conftest import fake_embed, write

A = "---\nname: alpha\n---\n# Alpha\nтопики оффсеты консьюмер группа кафка лаг"
B = "---\nname: beta\n---\n# Beta\nтопики оффсеты консьюмер группа кафка стрим"
C = "---\nname: gamma\n---\n# Gamma\nфигма пиксели макет верстка наложение"


def test_compute_links_pairs_similar(mem):
    write(mem, "a.md", A)
    write(mem, "b.md", B)
    write(mem, "c.md", C)
    build_index(fake_embed, mem)
    links = compute_links(top_n=3, threshold=0.1)
    # a и b похожи → ссылаются на слаги друг друга
    assert "a.md" in links
    targets = [slug for slug, _ in links["a.md"]]
    assert "beta" in targets


def test_apply_writes_block_with_wikilinks(mem):
    write(mem, "a.md", A)
    write(mem, "b.md", B)
    write(mem, "c.md", C)  # ≥3 файла: центрирование не вырождается в антиподы
    build_index(fake_embed, mem)
    apply_links(top_n=2, threshold=0.1)
    body = (mem / "a.md").read_text(encoding="utf-8")
    assert config.RELATED_START in body
    assert config.RELATED_END in body
    assert "[[beta]]" in body


def test_apply_is_idempotent(mem):
    write(mem, "a.md", A)
    write(mem, "b.md", B)
    write(mem, "c.md", C)
    build_index(fake_embed, mem)
    apply_links(top_n=2, threshold=0.1)
    first = (mem / "a.md").read_text(encoding="utf-8")
    stats = apply_links(top_n=2, threshold=0.1)
    second = (mem / "a.md").read_text(encoding="utf-8")
    assert first == second
    assert second.count(config.RELATED_START) == 1
    assert stats["written"] == 0


def test_sessions_not_linked(mem):
    write(mem, "a.md", A)
    write(mem, "b.md", B)
    (mem / "sessions" / "s.md").write_text(B, encoding="utf-8")
    build_index(fake_embed, mem)
    apply_links(top_n=2, threshold=0.1)
    sess_body = (mem / "sessions" / "s.md").read_text(encoding="utf-8")
    assert config.RELATED_START not in sess_body

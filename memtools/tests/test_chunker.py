from memtools import config
from memtools.chunker import chunk_text, slug_of, strip_related_block

FM = "---\nname: my-slug\ndescription: x\n---\n"


def test_strips_frontmatter_and_keeps_body():
    chunks = chunk_text("f.md", FM + "# Заголовок\nтело секции")
    assert chunks
    joined = " ".join(c.text for c in chunks)
    assert "name: my-slug" not in joined
    assert "тело секции" in joined


def test_splits_by_headings():
    raw = "# A\naaa\n# B\nbbb"
    chunks = chunk_text("f.md", raw)
    headings = {c.heading for c in chunks}
    assert "A" in headings and "B" in headings


def test_slug_from_frontmatter():
    assert slug_of(FM + "body", "fallback") == "my-slug"
    assert slug_of("no frontmatter", "fallback") == "fallback"


def test_long_section_is_split(monkeypatch):
    monkeypatch.setattr(config, "MAX_CHUNK_CHARS", 50)
    para = "x" * 40
    raw = f"# H\n{para}\n\n{para}\n\n{para}"
    chunks = chunk_text("f.md", raw)
    assert len(chunks) >= 2
    assert all(len(c.text) <= 120 for c in chunks)


def test_related_block_stripped():
    raw = (
        "# H\nтело\n\n"
        f"{config.RELATED_START}\n## Связанные (авто)\n- [[x]] — 0.50\n{config.RELATED_END}\n"
    )
    chunks = chunk_text("f.md", raw)
    joined = " ".join(c.text for c in chunks)
    assert "Связанные" not in joined
    assert "тело" in joined


def test_strip_related_idempotent_without_block():
    raw = "# H\nтело\n"
    assert "тело" in strip_related_block(raw)

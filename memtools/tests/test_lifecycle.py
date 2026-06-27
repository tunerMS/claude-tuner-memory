import os
import time

from memtools import config
from memtools.index import build_index
from memtools.lifecycle import build_report, dup_pairs, stale_files
from conftest import fake_embed, write


def test_stale_detects_old_file(mem):
    p = write(mem, "old.md", "# X\nдавно не трогали")
    write(mem, "fresh.md", "# Y\nсвежий")
    old = time.time() - 40 * 86400
    os.utime(p, (old, old))
    stale = stale_files(mem, days=30)
    names = {s["file"] for s in stale}
    assert "old.md" in names
    assert "fresh.md" not in names


def test_memory_md_excluded_from_stale(mem):
    p = write(mem, "MEMORY.md", "индекс")
    old = time.time() - 90 * 86400
    os.utime(p, (old, old))
    assert all(s["file"] != "MEMORY.md" for s in stale_files(mem, days=30))


def test_dup_pairs_finds_near_duplicates(mem):
    text = "# Тема\nодинаковый смысл топики оффсеты консьюмер группа"
    write(mem, "one.md", text)
    write(mem, "two.md", text)
    write(mem, "other.md", "# Другое\nфигма пиксели макет верстка")
    build_index(fake_embed, mem)
    pairs = dup_pairs(threshold=0.95)
    flat = {(p["a"], p["b"]) for p in pairs}
    assert ("one.md", "two.md") in flat or ("two.md", "one.md") in flat
    assert all("other.md" not in (p["a"], p["b"]) for p in pairs)


def test_report_mentions_sections(mem):
    write(mem, "a.md", "# A\nтекст")
    build_index(fake_embed, mem)
    report = build_report(mem)
    assert "Протухшие" in report
    assert "Похожие пары" in report
    assert "Ничего не удалено" in report

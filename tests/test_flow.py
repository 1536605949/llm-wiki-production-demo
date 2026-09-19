import os
from llmwiki.service import LLMWikiService

def make_ws(tmp_path):
    svc = LLMWikiService(str(tmp_path / "wiki"))
    svc.init()
    return svc

def test_immutable_raw(tmp_path):
    svc = make_ws(tmp_path)
    svc.add_text("a.md", "# A\none")
    try:
        svc.add_text("a.md", "# A\ntwo")
        assert False, "expected immutable-source protection"
    except FileExistsError:
        pass

def test_ingest_refactors_existing_concept(tmp_path):
    svc = make_ws(tmp_path)
    svc.add_text("a.md", "# LLM-Wiki\nLLM-Wiki compiles knowledge.")
    svc.ingest("raw/a.md")
    svc.add_text("b.md", "# Compounding\nLLM-Wiki knowledge compounding revises durable knowledge.")
    svc.ingest("raw/b.md")
    text = svc.ws.read_page("concepts/llm-wiki.md")
    assert "raw/a.md" in text and "raw/b.md" in text

def test_query_save_back(tmp_path):
    svc = make_ws(tmp_path)
    svc.add_text("a.md", "# LLM-Wiki\nLLM-Wiki compiles durable Markdown knowledge.")
    svc.ingest("raw/a.md")
    out = svc.query("LLM-Wiki", save=True)
    assert out["saved"]
    assert svc.ws.wiki_path(out["saved"]).exists()

def test_reindex_is_rebuildable(tmp_path):
    svc = make_ws(tmp_path)
    svc.add_text("a.md", "# LLM-Wiki\nLLM-Wiki.")
    svc.ingest("raw/a.md")
    svc.ws.db.unlink()
    out = svc.reindex()
    assert out["indexed_pages"] >= 2
    assert svc.ws.db.exists()

def test_lint_detects_broken_link(tmp_path):
    svc = make_ws(tmp_path)
    svc.add_text("a.md", "# LLM-Wiki\nLLM-Wiki.")
    svc.ingest("raw/a.md")
    p = svc.ws.wiki_path("concepts/llm-wiki.md")
    p.write_text(p.read_text(encoding="utf-8") + "\n[bad](missing.md)\n", encoding="utf-8")
    issues = svc.lint()["issues"]
    assert any(x["kind"] == "broken-link" for x in issues)


def test_repeated_ingest_does_not_nest(tmp_path):
    """Regression: the mock compiler used to re-embed the whole prior page,
    so every ingest nested one more level. Page size must stay bounded."""
    svc = make_ws(tmp_path)
    sizes = []
    for i in range(5):
        svc.add_text(f"s{i}.md", f"# LLM-Wiki\nLLM-Wiki round {i} evidence about knowledge compounding.")
        svc.ingest(f"raw/s{i}.md")
        sizes.append(len(svc.ws.read_page("concepts/llm-wiki.md")))
    assert sizes[-1] < sizes[1] * 2, f"page grew unbounded: {sizes}"
    text = svc.ws.read_page("concepts/llm-wiki.md")
    assert text.count("## Prior synthesis retained") == 1


def test_stale_lock_is_recovered(tmp_path):
    svc = make_ws(tmp_path)
    svc.ws.lockfile.parent.mkdir(parents=True, exist_ok=True)
    svc.ws.lockfile.write_text("999999999", encoding="utf-8")
    os.utime(svc.ws.lockfile, (0, 0))
    svc.add_text("a.md", "# LLM-Wiki\nLLM-Wiki.")
    out = svc.ingest("raw/a.md")
    assert out["pages"]
    assert not svc.ws.lockfile.exists()

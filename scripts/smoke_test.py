from pathlib import Path
import tempfile
from llmwiki.service import LLMWikiService

with tempfile.TemporaryDirectory() as d:
    svc = LLMWikiService(str(Path(d) / "wiki"))
    svc.init()
    svc.add_text("a.md", "# LLM-Wiki\nLLM-Wiki compiles durable knowledge.")
    print(svc.ingest("raw/a.md"))
    print(svc.query("LLM-Wiki", save=True))
    print(svc.lint())

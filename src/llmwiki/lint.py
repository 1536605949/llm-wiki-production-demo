from __future__ import annotations
from pathlib import Path
import posixpath
from .config import Settings
from .llm import make_llm
from .storage import Workspace
from .utils import extract_links, parse_frontmatter

class WikiLinter:
    def __init__(self, ws: Workspace, settings: Settings | None = None):
        self.ws = ws
        self.settings = settings or Settings.from_env()
        self.llm = make_llm(self.settings)

    def run(self, semantic: bool = False) -> list[dict]:
        issues = []
        pages = set(self.ws.list_pages())
        titles = {}
        inbound = {p: 0 for p in pages}
        for rel in sorted(pages):
            text = self.ws.read_page(rel)
            meta, body = parse_frontmatter(text)
            title = meta.get("title")
            if not title:
                issues.append({"kind":"missing-title","page":rel,"message":"frontmatter title is missing"})
            else:
                title_key = (meta.get("type", ""), title)
                if title_key in titles:
                    issues.append({"kind":"duplicate-title","page":rel,"message":f"same title/type as {titles[title_key]}"})
                titles[title_key] = rel
            sources = meta.get("sources", [])
            if not isinstance(sources, list) or (rel.startswith(("concepts/","entities/","analyses/")) and not sources):
                issues.append({"kind":"missing-provenance","page":rel,"message":"durable page has no source provenance"})
            for link in extract_links(body):
                if link.startswith(("http://","https://","mailto:","#")):
                    continue
                link = link.split("#",1)[0]
                target = posixpath.normpath(posixpath.join(posixpath.dirname(rel), link))
                if target.startswith("../"):
                    continue
                if target.endswith(".md"):
                    if target not in pages and target not in {"index.md","log.md"}:
                        issues.append({"kind":"broken-link","page":rel,"message":f"{link} -> {target}"})
                    elif target in inbound:
                        inbound[target] += 1

        # index.md is the global navigation root; count its links as inbound edges.
        index_text = (self.ws.wiki / "index.md").read_text(encoding="utf-8") if (self.ws.wiki / "index.md").exists() else ""
        for link in extract_links(index_text):
            target = link.split("#", 1)[0]
            if target in inbound:
                inbound[target] += 1
        for rel, count in inbound.items():
            if count == 0 and not rel.startswith(("sources/", "queries/")):
                issues.append({"kind":"orphan-page","page":rel,"message":"not reachable from index or another Wiki page"})

        if semantic and self.llm is not None:
            sample = "\n\n".join(f"--- {p} ---\n{self.ws.read_page(p)[:3500]}" for p in sorted(pages)[:10])
            result = self.llm.chat(
                "You are an epistemic Wiki linter.",
                "List only concrete contradictions, stale claims, or synthesis gaps. Be concise.\n\n" + sample,
            )
            if result.strip():
                issues.append({"kind":"semantic-review","page":"*","message":result.strip()})
        return issues

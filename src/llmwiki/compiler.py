from __future__ import annotations
from pathlib import Path
import json, re
from .config import Settings
from .llm import make_llm
from .search import SearchIndex
from .storage import Workspace
from .utils import slugify, parse_frontmatter

RETAINED_MARKER = "## Prior synthesis retained"

class KnowledgeCompiler:
    def __init__(self, ws: Workspace, settings: Settings | None = None):
        self.ws = ws
        self.settings = settings or Settings.from_env()
        self.search = SearchIndex(ws)
        self.llm = make_llm(self.settings)

    def _source_title(self, content: str, raw_path: str) -> str:
        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return Path(raw_path).stem.replace("-", " ").title()

    def _mock_concepts(self, content: str) -> list[tuple[str,str]]:
        low = content.lower()
        concepts = []
        if "llm-wiki" in low or "llm wiki" in low:
            concepts.append(("LLM-Wiki", "llm-wiki"))
        if "graphrag" in low or "graph rag" in low:
            concepts.append(("GraphRAG", "graphrag"))
        if "knowledge compounding" in low or "知识复利" in content or "知识编译" in content:
            concepts.append(("Knowledge Compounding", "knowledge-compounding"))
        if not concepts:
            # Pick a stable concept from the document title.
            title = self._source_title(content, "source.md")
            concepts.append((title, slugify(title)))
        return concepts[:4]

    @staticmethod
    def _strip_retained(body: str) -> str:
        """Drop any previously retained block.

        Splitting on the *first* marker means a page that was already polluted
        by an older build heals itself on the next ingest instead of nesting
        one level deeper.
        """
        return body.split(RETAINED_MARKER, 1)[0]

    def _prior_synthesis(self, body: str, limit: int = 800) -> str:
        """Extract only the durable prose from an existing page.

        Evidence dumps and retained blocks are deliberately excluded, which is
        what keeps repeated ingests bounded instead of growing the page.
        """
        head = self._strip_retained(body)
        for stop in ("### Evidence notes", "## Evidence notes", "## Related source"):
            head = head.split(stop, 1)[0]
        lines = [ln.strip() for ln in head.splitlines()]
        prose = " ".join(ln for ln in lines if ln and not ln.startswith("#"))
        return prose[:limit]

    def _mock_compile(self, raw_path: str, content: str) -> list[dict]:
        title = self._source_title(content, raw_path)
        raw_ref = raw_path if raw_path.startswith("raw/") else f"raw/{raw_path}"
        excerpt = " ".join(x.strip() for x in content.splitlines() if x.strip())[:1800]
        updates = [{
            "path": f"sources/{Path(raw_ref).stem}.md",
            "title": title,
            "type": "source",
            "sources": [raw_ref],
            "body": f"# {title}\n\n## Source summary\n\n{excerpt}\n\n## Provenance\n\n- `{raw_ref}`",
        }]
        for cname, slug in self._mock_concepts(content):
            rel = f"concepts/{slug}.md"
            prior_notes = ""
            if self.ws.wiki_path(rel).exists():
                _, prior_body = parse_frontmatter(self.ws.read_page(rel))
                prior_text = self._prior_synthesis(prior_body)
                if prior_text:
                    prior_notes = f"\n\n{RETAINED_MARKER}\n\n{prior_text}\n"
            body = (
                f"# {cname}\n\n"
                f"## Current synthesis\n\n"
                f"This durable concept page is maintained at ingest time. The latest evidence from `{raw_ref}` "
                f"has been integrated into the existing Wiki rather than stored only as an opaque retrieval chunk.\n\n"
                f"### Evidence notes\n\n{excerpt[:1200]}\n"
                f"{prior_notes}\n\n"
                f"## Related source\n\n- [{title}](../sources/{Path(raw_ref).stem}.md)"
            )
            updates.append({"path":rel,"title":cname,"type":"concept","sources":[raw_ref],"body":body})
        return updates

    def _llm_compile(self, raw_path: str, content: str) -> list[dict]:
        schema = (self.ws.root / "AGENTS.md").read_text(encoding="utf-8")
        related = self.search.search(content[:1200], limit=5)
        existing = []
        for r in related:
            existing.append(f"--- {r['path']} ---\n{self.ws.read_page(r['path'])[:5000]}")
        prompt = f"""You are the knowledge compiler for an LLM-Wiki.
Return ONLY valid JSON, an array of page updates.
Each update must have: path, title, type, sources, body.
Allowed path prefixes: sources/, concepts/, entities/, analyses/, contradictions/.
The source path must be preserved in sources.
Prefer refactoring existing durable pages over creating duplicates.

SCHEMA:
{schema}

NEW SOURCE: {raw_path}
{content[:14000]}

RELATED EXISTING WIKI:
{chr(10).join(existing)[:14000]}
"""
        raw = self.llm.chat("Compile evidence into a persistent Markdown Wiki. Output JSON only.", prompt)
        m = re.search(r"\[.*\]", raw, flags=re.S)
        if not m:
            raise ValueError("LLM did not return a JSON array")
        updates = json.loads(m.group(0))
        if not isinstance(updates, list):
            raise ValueError("compiler plan must be a list")
        return updates

    def ingest(self, raw_path: str) -> dict:
        self.ws.ensure()
        p = self.ws.raw_path(raw_path)
        if not p.exists():
            raise FileNotFoundError(p)
        raw_ref = "raw/" + p.relative_to(self.ws.raw).as_posix()
        content = p.read_text(encoding="utf-8")
        updates = self._mock_compile(raw_ref, content) if self.llm is None else self._llm_compile(raw_ref, content)

        written = []
        with self.ws.lock():
            for u in updates:
                rel = str(u["path"]).lstrip("/")
                if not any(rel.startswith(prefix) for prefix in ("sources/","concepts/","entities/","analyses/","contradictions/")):
                    raise ValueError(f"compiler attempted disallowed wiki path: {rel}")
                self.ws.upsert_page(
                    rel=rel,
                    title=str(u.get("title", rel)),
                    page_type=str(u.get("type", "concept")),
                    body=str(u.get("body", "")),
                    sources=list(u.get("sources") or [raw_ref]),
                )
                written.append(rel)
            self.ws.rebuild_index()
            self.ws.append_log(f"ingest {raw_ref}: {', '.join(written)}")
            self.ws.audit_event("ingest", {"source": raw_ref, "pages": written, "provider": self.settings.provider})
            self.search.rebuild()
        return {"source": raw_ref, "pages": written}

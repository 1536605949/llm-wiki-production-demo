from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import re
from .config import Settings
from .llm import make_llm
from .search import SearchIndex
from .storage import Workspace
from .utils import slugify, parse_frontmatter

class QueryService:
    def __init__(self, ws: Workspace, settings: Settings | None = None):
        self.ws = ws
        self.settings = settings or Settings.from_env()
        self.search = SearchIndex(ws)
        self.llm = make_llm(self.settings)

    def _expand_links(self, paths: list[str], max_extra: int = 4) -> list[str]:
        out = list(paths)
        for rel in list(paths):
            try:
                text = self.ws.read_page(rel)
            except FileNotFoundError:
                continue
            for link in re.findall(r"\[[^\]]+\]\(([^)#?]+)", text):
                if link.startswith(("http://","https://","mailto:")):
                    continue
                base = (Path(rel).parent / link).as_posix()
                norm = Path(base)
                parts = []
                for part in norm.parts:
                    if part == "..":
                        if parts: parts.pop()
                    elif part not in {".",""}:
                        parts.append(part)
                target = "/".join(parts)
                if target.endswith(".md") and target not in out and self.ws.wiki_path(target).exists():
                    out.append(target)
                    if len(out) >= len(paths) + max_extra:
                        return out
        return out

    def query(self, question: str, save: bool = False) -> dict:
        hits = self.search.search(question, limit=6)
        paths = self._expand_links([h["path"] for h in hits[:4]])
        contexts, citations = [], []
        for rel in paths:
            text = self.ws.read_page(rel)
            _, body = parse_frontmatter(text)
            contexts.append(f"--- wiki:{rel} ---\n{body[:5000]}")
            citations.append(f"[wiki:{rel}]")

        if self.llm is None:
            if not contexts:
                answer = "Mock mode: no compiled Wiki page matched this question. Ingest evidence first."
            else:
                summaries = []
                for rel in paths[:4]:
                    _, body = parse_frontmatter(self.ws.read_page(rel))
                    plain = " ".join(x.strip("# -*`") for x in body.splitlines() if x.strip())
                    summaries.append(f"- {plain[:350]} [wiki:{rel}]")
                answer = (
                    "Mock mode（确定性体验，不冒充真实大模型）：\n\n"
                    "本次回答优先消费已经编译进 Wiki 的持久知识，而不是直接从 raw chunks 临时拼接。\n\n"
                    + "\n".join(summaries)
                )
        else:
            prompt = f"""Answer the question using the compiled Wiki context.
Cite claims with [wiki:path] markers. If evidence is insufficient, say so.

QUESTION:
{question}

WIKI CONTEXT:
{chr(10).join(contexts)[:22000]}
"""
            answer = self.llm.chat("You are a Wiki-first reasoning agent. Preserve citations.", prompt)

        saved = None
        if save:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            rel = f"queries/{ts}-{slugify(question)[:60]}.md"
            body = f"# Query: {question}\n\n## Answer\n\n{answer}\n\n## Retrieved pages\n\n" + "\n".join(f"- [{p}](../{p})" for p in paths)
            source_refs = []
            for p in paths:
                meta, _ = parse_frontmatter(self.ws.read_page(p))
                if isinstance(meta.get("sources"), list):
                    for s in meta["sources"]:
                        if s not in source_refs: source_refs.append(s)
            with self.ws.lock():
                self.ws.upsert_page(rel, f"Query: {question}", "query", body, source_refs)
                self.ws.rebuild_index()
                self.ws.append_log(f"save-back query: {rel}")
                self.ws.audit_event("query.save", {"question": question, "path": rel})
                self.search.rebuild()
            saved = rel
        return {"question": question, "answer": answer, "pages": paths, "citations": citations, "saved": saved}

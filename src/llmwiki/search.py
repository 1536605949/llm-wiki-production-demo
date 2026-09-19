from __future__ import annotations
from pathlib import Path
import re, sqlite3
from .storage import Workspace
from .utils import parse_frontmatter

class SearchIndex:
    def __init__(self, ws: Workspace):
        self.ws = ws

    def rebuild(self) -> int:
        self.ws.meta.mkdir(parents=True, exist_ok=True)
        if self.ws.db.exists():
            self.ws.db.unlink()
        con = sqlite3.connect(self.ws.db)
        try:
            con.execute("CREATE VIRTUAL TABLE pages USING fts5(path UNINDEXED, title, body, tokenize='unicode61')")
            count = 0
            for rel in self.ws.list_pages():
                text = self.ws.read_page(rel)
                meta, body = parse_frontmatter(text)
                title = str(meta.get("title", rel))
                con.execute("INSERT INTO pages(path,title,body) VALUES(?,?,?)", (rel, title, body))
                count += 1
            con.commit()
            return count
        finally:
            con.close()

    def search(self, query: str, limit: int = 6) -> list[dict]:
        if not self.ws.db.exists():
            self.rebuild()
        con = sqlite3.connect(self.ws.db)
        con.row_factory = sqlite3.Row
        rows = []
        try:
            tokens = re.findall(r"[\w\u4e00-\u9fff-]+", query.lower())
            fts_q = " OR ".join(f'"{t}"' for t in tokens if len(t) > 1)
            if fts_q:
                try:
                    rows = con.execute(
                        "SELECT path,title,body,bm25(pages) AS score FROM pages WHERE pages MATCH ? ORDER BY score LIMIT ?",
                        (fts_q, limit),
                    ).fetchall()
                except sqlite3.OperationalError:
                    rows = []
        finally:
            con.close()
        if rows:
            return [dict(r) for r in rows]

        # Robust fallback, especially useful for Chinese text with simple FTS tokenization.
        scored = []
        qparts = set(re.findall(r"[a-z0-9_-]+|[\u4e00-\u9fff]", query.lower()))
        for rel in self.ws.list_pages():
            text = self.ws.read_page(rel)
            meta, body = parse_frontmatter(text)
            hay = (str(meta.get("title","")) + "\n" + body).lower()
            score = sum(hay.count(p) for p in qparts if p.strip())
            if score:
                scored.append({"path": rel, "title": meta.get("title", rel), "body": body, "score": -score})
        return sorted(scored, key=lambda x: x["score"])[:limit]

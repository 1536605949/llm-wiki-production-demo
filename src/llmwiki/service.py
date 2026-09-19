from __future__ import annotations
from .compiler import KnowledgeCompiler
from .config import Settings
from .lint import WikiLinter
from .query import QueryService
from .search import SearchIndex
from .storage import Workspace
from .gitops import maybe_git_commit

class LLMWikiService:
    def __init__(self, root: str, settings: Settings | None = None):
        self.ws = Workspace(root)
        self.settings = settings or Settings.from_env()

    def init(self):
        self.ws.init()
        SearchIndex(self.ws).rebuild()
        return self.status()

    def add_text(self, name: str, content: str):
        p = self.ws.add_source_text(name, content)
        return {"path": "raw/" + p.name}

    def ingest(self, raw_path: str):
        out = KnowledgeCompiler(self.ws, self.settings).ingest(raw_path)
        maybe_git_commit(self.ws, f"compile {raw_path}", self.settings.auto_git_commit)
        return out

    def query(self, question: str, save: bool = False):
        out = QueryService(self.ws, self.settings).query(question, save=save)
        if save:
            maybe_git_commit(self.ws, f"save query: {question[:60]}", self.settings.auto_git_commit)
        return out

    def lint(self, semantic: bool = False):
        issues = WikiLinter(self.ws, self.settings).run(semantic=semantic)
        return {"count": len(issues), "issues": issues}

    def reindex(self):
        n = SearchIndex(self.ws).rebuild()
        return {"indexed_pages": n}

    def status(self):
        self.ws.ensure()
        return {
            "workspace": str(self.ws.root),
            "raw_sources": len(list(self.ws.raw.glob("*"))),
            "wiki_pages": len(self.ws.list_pages()),
            "index_exists": self.ws.db.exists(),
            "provider": self.settings.provider,
        }

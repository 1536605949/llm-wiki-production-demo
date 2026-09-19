from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
import json, os, subprocess, time
from .utils import atomic_write, parse_frontmatter, render_frontmatter, sha256_text

DEFAULT_AGENTS = """# LLM-Wiki Knowledge Contract

## Ownership
- `raw/`: immutable evidence. Never rewrite source history.
- `wiki/`: compiled knowledge maintained by the knowledge compiler.
- `AGENTS.md`: schema, page conventions, and workflow contract.

## Compile policy
1. Read the new source.
2. Search existing Wiki pages that may be affected.
3. Prefer updating/refactoring durable concepts over creating duplicates.
4. Create a source summary for every ingested source.
5. Rebuild `index.md` and the derived search index.
6. Query results enter long-term knowledge only through explicit save-back.
"""

class Workspace:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.raw = self.root / "raw"
        self.wiki = self.root / "wiki"
        self.meta = self.root / ".llmwiki"
        self.db = self.meta / "meta.sqlite"
        self.audit = self.meta / "audit.jsonl"
        self.lockfile = self.meta / "workspace.lock"

    def init(self) -> None:
        for p in [self.raw, self.wiki, self.meta]:
            p.mkdir(parents=True, exist_ok=True)
        for sub in ["sources","concepts","entities","analyses","queries","contradictions"]:
            (self.wiki / sub).mkdir(exist_ok=True)
        if not (self.root / "AGENTS.md").exists():
            atomic_write(self.root / "AGENTS.md", DEFAULT_AGENTS)
        if not (self.wiki / "log.md").exists():
            atomic_write(self.wiki / "log.md", "# Knowledge Log\n\n")
        self.rebuild_index()

    def ensure(self) -> None:
        if not self.root.exists() or not self.wiki.exists():
            raise FileNotFoundError(f"Not an LLM-Wiki workspace: {self.root}")

    def _pid_alive(self, pid: int) -> bool:
        """Best-effort liveness probe; unknown failures are treated as alive.

        `tasklist` writes in the OEM code page, so the output is captured as
        bytes and decoded leniently — decoding as UTF-8 would raise and make a
        dead PID look alive, which is exactly the case we need to detect.
        """
        try:
            if os.name == "nt":
                out = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True, timeout=5,
                ).stdout.decode("utf-8", errors="replace")
                return str(pid) in out
            os.kill(pid, 0)
            return True
        except (OSError, subprocess.SubprocessError):
            return False
        except Exception:
            return True

    def _break_stale_lock(self, timeout: float) -> bool:
        """Remove a lock whose owner died, so a crash cannot wedge the workspace."""
        try:
            age = time.time() - self.lockfile.stat().st_mtime
            if age < timeout:
                return False
            raw = self.lockfile.read_text(encoding="utf-8").strip()
            pid = int(raw) if raw.isdigit() else -1
            if pid > 0 and self._pid_alive(pid):
                return False
            self.lockfile.unlink(missing_ok=True)
            return True
        except (FileNotFoundError, ValueError, OSError):
            return False

    @contextmanager
    def lock(self, timeout: float = 10.0):
        self.meta.mkdir(parents=True, exist_ok=True)
        start, fd = time.time(), None
        while True:
            try:
                fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                break
            except FileExistsError:
                if self._break_stale_lock(timeout):
                    continue
                if time.time() - start > timeout:
                    raise TimeoutError("workspace is locked")
                time.sleep(0.05)
        try:
            yield
        finally:
            if fd is not None:
                os.close(fd)
            try:
                self.lockfile.unlink()
            except FileNotFoundError:
                pass

    def add_source(self, source: str | Path, name: str | None = None) -> Path:
        src = Path(source)
        return self.add_source_text(name or src.name, src.read_text(encoding="utf-8"))

    def add_source_text(self, name: str, content: str) -> Path:
        self.ensure()
        name = Path(name).name
        dest = self.raw / name
        if dest.exists():
            old = dest.read_text(encoding="utf-8")
            if old != content:
                raise FileExistsError(f"Immutable raw source exists with different content: raw/{name}")
            return dest
        atomic_write(dest, content)
        self.audit_event("source.add", {"path": f"raw/{name}", "sha256": sha256_text(content)})
        return dest

    def raw_path(self, raw_path: str) -> Path:
        rel = raw_path[4:] if raw_path.startswith("raw/") else raw_path
        p = (self.raw / rel).resolve()
        if self.raw not in p.parents and p != self.raw:
            raise ValueError("path traversal rejected")
        return p

    def wiki_path(self, rel: str) -> Path:
        p = (self.wiki / rel).resolve()
        if self.wiki not in p.parents and p != self.wiki:
            raise ValueError("path traversal rejected")
        return p

    def read_raw(self, raw_path: str) -> str:
        return self.raw_path(raw_path).read_text(encoding="utf-8")

    def list_pages(self) -> list[str]:
        self.ensure()
        out = []
        for p in self.wiki.rglob("*.md"):
            rel = p.relative_to(self.wiki).as_posix()
            if rel not in {"index.md", "log.md"}:
                out.append(rel)
        return sorted(out)

    def read_page(self, rel: str) -> str:
        return self.wiki_path(rel).read_text(encoding="utf-8")

    def write_page(self, rel: str, text: str) -> None:
        atomic_write(self.wiki_path(rel), text)

    def upsert_page(self, rel: str, title: str, page_type: str, body: str, sources: list[str]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        existing_sources = []
        p = self.wiki_path(rel)
        if p.exists():
            meta, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
            if isinstance(meta.get("sources"), list):
                existing_sources = meta["sources"]
        merged = []
        for s in [*existing_sources, *sources]:
            if s and s not in merged:
                merged.append(s)
        meta = {"title": title, "type": page_type, "updated_at": now, "sources": merged}
        self.write_page(rel, render_frontmatter(meta, body))

    def rebuild_index(self) -> None:
        self.wiki.mkdir(parents=True, exist_ok=True)
        lines = ["# LLM-Wiki Index", "", "Compiled knowledge pages:", ""]
        for rel in self.list_pages() if self.root.exists() else []:
            try:
                meta, body = parse_frontmatter(self.read_page(rel))
                title = meta.get("title") or next((x[2:].strip() for x in body.splitlines() if x.startswith("# ")), rel)
            except Exception:
                title = rel
            lines.append(f"- [{title}]({rel})")
        lines.append("")
        atomic_write(self.wiki / "index.md", "\n".join(lines))

    def append_log(self, message: str) -> None:
        p = self.wiki / "log.md"
        old = p.read_text(encoding="utf-8") if p.exists() else "# Knowledge Log\n\n"
        ts = datetime.now(timezone.utc).isoformat()
        atomic_write(p, old + f"- {ts} — {message}\n")

    def audit_event(self, event: str, data: dict) -> None:
        self.meta.mkdir(parents=True, exist_ok=True)
        row = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, "data": data}
        with self.audit.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

from __future__ import annotations
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from .service import LLMWikiService

log = logging.getLogger("llmwiki.api")


def _fail(exc: Exception, status: int = 400) -> HTTPException:
    """Log the real error server-side, return a message that leaks no paths."""
    log.warning("api error: %s: %s", type(exc).__name__, exc)
    if isinstance(exc, FileNotFoundError):
        return HTTPException(404, "resource not found")
    if isinstance(exc, FileExistsError):
        return HTTPException(409, "resource already exists and is immutable")
    if isinstance(exc, TimeoutError):
        return HTTPException(503, "workspace is busy, retry shortly")
    if isinstance(exc, (ValueError, PermissionError)):
        return HTTPException(400, "invalid request")
    return HTTPException(status, "request failed")

class SourceIn(BaseModel):
    name: str
    content: str

class IngestIn(BaseModel):
    raw_path: str

class QueryIn(BaseModel):
    question: str
    save: bool = False

class LintIn(BaseModel):
    semantic: bool = False

def create_app(workspace: str) -> FastAPI:
    svc = LLMWikiService(workspace)
    app = FastAPI(title="LLM-Wiki Production Demo", version="0.2.0")

    @app.get("/", response_class=HTMLResponse)
    def home():
        return """<!doctype html><html><head><meta charset="utf-8"><title>LLM-Wiki Demo</title>
<style>body{font-family:system-ui;max-width:1000px;margin:40px auto;padding:0 20px}textarea,input{width:100%;box-sizing:border-box;margin:6px 0;padding:10px}button{padding:10px 16px;margin:6px 6px 6px 0}pre{white-space:pre-wrap;background:#f4f4f4;padding:16px;border-radius:8px}</style></head>
<body><h1>LLM-Wiki Production Demo</h1><p>Raw → Compile → Wiki → Query → Save Back → Lint</p>
<h2>Query</h2><input id=q value="LLM-Wiki 和 GraphRAG 的核心差异是什么？"><button onclick="query(false)">Query</button><button onclick="query(true)">Query + Save Back</button>
<h2>Add & Ingest Source</h2><input id=n value="new-note.md"><textarea id=c rows=8># LLM-Wiki new evidence\nThis source says knowledge should be compiled into durable wiki pages.</textarea><button onclick="add()">Add + Ingest</button>
<h2>Knowledge Health</h2><button onclick="lint()">Lint</button><button onclick="status()">Status</button><pre id=o>Ready.</pre>
<script>
async function post(u,b){let r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});return await r.json()}
function show(x){o.textContent=JSON.stringify(x,null,2)}
async function query(save){show(await post('/api/query',{question:q.value,save}))}
async function add(){let a=await post('/api/sources',{name:n.value,content:c.value});show(await post('/api/ingest',{raw_path:a.path}))}
async function lint(){show(await post('/api/lint',{semantic:false}))}
async function status(){show(await (await fetch('/api/status')).json())}
</script></body></html>"""

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.get("/api/status")
    def status():
        return svc.status()

    @app.get("/api/pages")
    def pages():
        return {"pages": svc.ws.list_pages()}

    @app.get("/api/page")
    def page(path: str):
        try:
            return {"path": path, "content": svc.ws.read_page(path)}
        except Exception as e:
            raise _fail(e)

    @app.post("/api/sources")
    def add_source(body: SourceIn):
        try:
            return svc.add_text(body.name, body.content)
        except Exception as e:
            raise _fail(e)

    @app.post("/api/ingest")
    def ingest(body: IngestIn):
        try:
            return svc.ingest(body.raw_path)
        except Exception as e:
            raise _fail(e)

    @app.post("/api/query")
    def query(body: QueryIn):
        try:
            return svc.query(body.question, body.save)
        except Exception as e:
            raise _fail(e)

    @app.post("/api/lint")
    def lint(body: LintIn):
        try:
            return svc.lint(body.semantic)
        except Exception as e:
            raise _fail(e)

    @app.post("/api/reindex")
    def reindex():
        try:
            return svc.reindex()
        except Exception as e:
            raise _fail(e)

    return app

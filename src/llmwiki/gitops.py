from __future__ import annotations
import subprocess
from .storage import Workspace

def maybe_git_commit(ws: Workspace, message: str, enabled: bool) -> bool:
    if not enabled:
        return False
    try:
        if not (ws.root / ".git").exists():
            subprocess.run(["git","init"], cwd=ws.root, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["git","config","user.email","llmwiki@example.local"], cwd=ws.root, check=True)
            subprocess.run(["git","config","user.name","LLM-Wiki Demo"], cwd=ws.root, check=True)
        subprocess.run(["git","add","wiki","raw","AGENTS.md",".llmwiki/audit.jsonl"], cwd=ws.root, check=True)
        subprocess.run(["git","commit","-m",message], cwd=ws.root, check=True, stdout=subprocess.DEVNULL)
        return True
    except Exception:
        return False

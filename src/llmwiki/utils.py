from __future__ import annotations
from pathlib import Path
import hashlib, json, os, re, tempfile, unicodedata

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).strip().lower()
    text = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "page"

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def atomic_write(path: Path, text: str) -> None:
    """Write atomically, always with LF line endings.

    Forcing newline="\\n" keeps generated Wiki pages byte-identical across
    Windows and Linux, so a Windows run does not show up as a spurious diff
    in a repository that normalises to LF.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    data, current_list = {}, None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_list:
            data.setdefault(current_list, []).append(line[4:].strip())
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if v == "":
                data[k] = []
                current_list = k
            else:
                current_list = None
                data[k] = (v == "true") if v in {"true", "false"} else v.strip('"')
    return data, body

def render_frontmatter(meta: dict, body: str) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            s = str(v).replace('"', '\\"')
            lines.append(f'{k}: "{s}"')
    return "\n".join(lines + ["---", "", body.rstrip(), ""])

def extract_links(markdown: str) -> list[str]:
    return re.findall(r"\[[^\]]*\]\(([^)]+)\)", markdown) + re.findall(r"\[\[([^\]|#]+)", markdown)

def json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)

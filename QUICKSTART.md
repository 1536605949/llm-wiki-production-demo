# Quick Start

## 1. 安装

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -e . --no-build-isolation
```

## 2. 直接体验预置 Wiki

```bash
llmwiki status demo
llmwiki query demo "LLM-Wiki 和 GraphRAG 的核心差异是什么？"
llmwiki lint demo
```

## 3. 从零观察“知识复利”

```bash
llmwiki init mywiki
llmwiki add mywiki examples/02-llm-wiki.md
llmwiki ingest mywiki raw/02-llm-wiki.md

llmwiki add mywiki examples/03-compounding.md
llmwiki ingest mywiki raw/03-compounding.md

cat mywiki/wiki/concepts/llm-wiki.md
```

此时 `concepts/llm-wiki.md` 的 `sources:` 会同时包含两份 raw evidence。

## 4. Query Save-Back

```bash
llmwiki query mywiki "解释知识复利" --save
```

观察 `mywiki/wiki/queries/`。

## 5. 删除搜索索引再恢复

```bash
rm mywiki/.llmwiki/meta.sqlite
llmwiki reindex mywiki
```

知识不会丢失，因为 Markdown Wiki 才是 source of truth。

## 6. Web UI

Web UI 需要 FastAPI/Uvicorn：

```bash
pip install -e ".[web]" --no-build-isolation
llmwiki serve demo --host 0.0.0.0 --port 8000
```

浏览器打开 `http://localhost:8000`。

## 7. 切换真实模型

```bash
export LLMWIKI_PROVIDER=openai_compatible
export LLMWIKI_BASE_URL=http://localhost:11434/v1
export LLMWIKI_MODEL=qwen3:8b
export LLMWIKI_API_KEY=ollama
```

然后对一个新 workspace 重跑 ingest/query。

## 8. 跑测试

```bash
pip install -e ".[dev]" --no-build-isolation
pytest
```

预期输出 `8 passed`。`pyproject.toml` 里已配置 `pythonpath = ["src"]`，
所以即使没做 editable 安装，`pytest` 也能直接找到包。

## 9. 关于 .llmwiki/

`.llmwiki/` 里全是派生数据（FTS 索引、审计日志、进程锁），已被 `.gitignore` 忽略。
删掉整个目录不影响知识，首次查询会自动重建索引。

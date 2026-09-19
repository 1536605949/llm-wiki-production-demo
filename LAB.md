# LLM-Wiki Hands-on Lab：从“RAG 思维”切换到“知识编译思维”

这份实验建议你不要只看代码，而是按顺序操作文件。核心目标是亲眼看到：**知识不是每次 Query 临时重建，而是在 Ingest 时持续编译并沉淀到 Wiki。**

## Lab 0 — 先看三层所有权

打开 `demo/`：

```text
demo/raw/       人拥有：不可变证据
demo/wiki/      LLM 拥有：编译后的长期知识
demo/AGENTS.md  人 + LLM：共同演化的 schema / workflow contract
```

先读 `AGENTS.md`。它不是 prompt 小技巧，而是知识系统的“编译规范”。

## Lab 1 — 删除派生索引，证明 Markdown 才是知识真相

```bash
rm demo/.llmwiki/meta.sqlite
llmwiki reindex demo
llmwiki query demo "LLM-Wiki"
```

如果系统仍然恢复工作，说明 SQLite 只是派生索引。真正知识仍在 `wiki/*.md`。

## Lab 2 — 从零编译第一份资料

```bash
rm -rf labwiki
llmwiki init labwiki
llmwiki add labwiki examples/02-llm-wiki.md
llmwiki ingest labwiki raw/02-llm-wiki.md
```

观察：

```bash
find labwiki/wiki -type f -maxdepth 3 -print
cat labwiki/wiki/concepts/llm-wiki.md
cat labwiki/wiki/sources/02-llm-wiki.md
```

你会看到一份 raw source 被“编译”为 source summary + durable concept page，而不是只变成 chunks。

## Lab 3 — 第二份证据到来：观察同一知识页被 Refactor

```bash
cp labwiki/wiki/concepts/llm-wiki.md /tmp/before.md
llmwiki add labwiki examples/03-compounding.md
llmwiki ingest labwiki raw/03-compounding.md

diff -u /tmp/before.md labwiki/wiki/concepts/llm-wiki.md || true
```

重点看 frontmatter：

```yaml
sources:
  - raw/02-llm-wiki.md
  - raw/03-compounding.md
```

这一步就是 **knowledge compounding**：新资料进入后更新已有持久知识，而不是新增一个互不相干的检索 chunk。

## Lab 4 — Query 是 Wiki-first

```bash
llmwiki query labwiki "为什么 LLM-Wiki 不等于普通 RAG？"
```

Mock 模式会明确展示命中的 Wiki 页面和 `[wiki:...]` 引用，不会冒充真正大模型。

## Lab 5 — Save Back：让一次查询变成长期知识

```bash
llmwiki query labwiki "总结知识复利的工程价值" --save
find labwiki/wiki/queries -type f -print
```

`--save` 后，查询结果成为持久 Wiki 页面。下一次检索可以命中它。

注意：生产系统中通常要把 Save Back 接到 human approval / policy gate，而不是所有聊天都自动写入长期知识。

## Lab 6 — 故意制造坏知识，再用 Lint 找出来

在某个 concept 页追加：

```markdown
[broken](missing.md)
```

然后：

```bash
llmwiki lint labwiki
```

你会看到 `broken-link`。恢复文件后重新 lint。

真实 LLM 模式还可以：

```bash
llmwiki lint labwiki --semantic
```

让模型检查 contradiction / stale claims / synthesis gaps。

## Lab 7 — 切到真正 LLM

例如你本机已有 OpenAI-compatible endpoint：

```bash
export LLMWIKI_PROVIDER=openai_compatible
export LLMWIKI_BASE_URL=http://localhost:11434/v1
export LLMWIKI_MODEL=qwen3:8b
export LLMWIKI_API_KEY=ollama
```

重新从一个干净 workspace 做 Lab 2/3。此时 `compiler.py` 会把：

- `AGENTS.md`
- 新 raw source
- FTS 找到的相关旧 Wiki pages

一起交给模型，让模型返回 **multi-page update plan**。

最值得读：`src/llmwiki/compiler.py::KnowledgeCompiler.plan()`。

## Lab 8 — 打开 Web UI

```bash
llmwiki serve demo --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000`，可以直接：

- 添加 immutable source
- Ingest / Compile
- Query
- Save Back
- 看 Wiki page list
- Lint / Status

## Lab 9 — 看 Git / Audit 思维

启用：

```bash
export LLMWIKI_AUTO_GIT_COMMIT=true
```

Ingest 后查看：

```bash
git -C labwiki log --oneline --all
git -C labwiki diff HEAD~1 HEAD -- wiki/
cat labwiki/.llmwiki/audit.jsonl
```

生产环境一般会进一步变成 PR + reviewer + policy checks。

## Lab 10 — 你真正应该记住的架构不变量

1. Raw 是 evidence，不让模型静默改历史。
2. Wiki 是 compiled knowledge，不是 opaque embedding cache。
3. Ingest 的工作是“整合 / 更新 / 重构”，不只是“追加索引”。
4. Query 先消费已经积累的知识。
5. Save Back 是显式知识晋升动作。
6. Lint 是 Wiki 的长期健康机制。
7. FTS / vector / graph 都可以存在，但它们是 **accelerator**，不是 LLM-Wiki 的定义本身。

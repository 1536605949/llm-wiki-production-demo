# LLM-Wiki Production Demo

一套**可运行**的 LLM-Wiki 参考实现，用约 900 行纯标准库 Python 演示一个核心主张：

> **Markdown Wiki 才是知识真相，检索索引只是可丢弃、可重建的加速器。**

它不是 RAG 的另一种写法。RAG 在查询时把原始文本切片喂给模型；LLM-Wiki 在**摄入时**就把新证据编译进一份持久的知识制品里，之后查询消费的是已经综合过的知识。

```
raw/ (不可变证据) → ingest/compile → wiki/ (持久知识) → query → save-back → lint → 复利
```

---

## 目录

- [它和 RAG 差在哪](#它和-rag-差在哪)
- [30 秒跑起来](#30-秒跑起来)
- [从零体验知识复利](#从零体验知识复利)
- [接入真实 LLM](#接入真实-llm)
- [目录结构](#目录结构)
- [核心设计原则](#核心设计原则)
- [命令行](#命令行)
- [HTTP API](#http-api)
- [架构](#架构)
- [测试](#测试)
- [已知限制](#已知限制)
- [距离生产级还差什么](#距离生产级还差什么)
- [配套材料](#配套材料)

---

## 它和 RAG 差在哪

| | 传统 RAG | 本项目（LLM-Wiki） |
|---|---|---|
| 知识存放 | 原始切片 + 向量库 | Markdown 页面，人可直接读 |
| 综合发生在 | 每次查询时 | 摄入时（compile-time） |
| 新证据到来 | 追加一个 chunk | **改写已有知识页** |
| 索引地位 | 唯一真相，丢了就完了 | 派生加速器，`reindex` 即可重建 |
| 溯源 | 通常靠 chunk 元数据 | 每页 frontmatter 维护 `sources` |
| 查询产物 | 用完即弃 | 可显式 save-back 成为长期知识 |

一句话：**Ingest 是一次"知识编译"，不是一次"文档入库"。**

---

## 30 秒跑起来

要求 Python 3.11+。运行时**零第三方依赖**（Web UI 可选装 FastAPI）。

```bash
git clone https://github.com/1536605949/llm-wiki-production-demo.git
cd llm-wiki-production-demo

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e . --no-build-isolation

# 仓库自带一个已编译好的 demo 工作区
llmwiki status demo
llmwiki query demo "LLM-Wiki 和 GraphRAG 的核心差异是什么？"
llmwiki lint demo
```

默认 `LLMWIKI_PROVIDER=mock`，**不需要任何 API Key**。mock 模式是确定性启发式逻辑，它不会伪装成真实大模型，目的是让你先完整体验一遍生命周期。

启动 Web UI（需额外装 `fastapi` / `uvicorn`）：

```bash
pip install -e ".[web]" --no-build-isolation
llmwiki serve demo --host 0.0.0.0 --port 8000
# 浏览器打开 http://localhost:8000
```

---

## 从零体验"知识复利"

```bash
rm -rf mywiki
llmwiki init mywiki

# 第一份证据
llmwiki add mywiki examples/01-graphrag.md
llmwiki ingest mywiki raw/01-graphrag.md

# 第二份证据 —— 注意它改写的是【同一个】概念页，而不是新加一个 chunk
llmwiki add mywiki examples/02-llm-wiki.md
llmwiki ingest mywiki raw/02-llm-wiki.md

cat mywiki/wiki/concepts/llm-wiki.md
```

此时 `concepts/llm-wiki.md` 的 `sources:` 会同时列出两份 raw 证据 —— 这就是"复利"。

继续走完查询与质检：

```bash
# 查询结果可以提升为长期知识
llmwiki query mywiki "为什么 LLM-Wiki 不等于 RAG？" --save
ls mywiki/wiki/queries/

# 结构健康检查
llmwiki lint mywiki

# 删掉派生索引，证明 Markdown 才是真相
rm mywiki/.llmwiki/meta.sqlite
llmwiki reindex mywiki
```

---

## 接入真实 LLM

使用 OpenAI 兼容的 Chat Completions 协议，适配本地 vLLM、Ollama、LM Studio 等。

```bash
export LLMWIKI_PROVIDER=openai_compatible
export LLMWIKI_BASE_URL=http://localhost:11434/v1
export LLMWIKI_MODEL=qwen3:8b
export LLMWIKI_API_KEY=ollama

llmwiki ingest demo raw/03-compounding.md
llmwiki query demo "综合所有资料解释知识复利" --save
```

接上真实 LLM 后，`ingest` 会把「新证据 + 已有 Wiki 相关页 + AGENTS.md 契约」一起交给模型，要求它返回一份 **JSON 格式的多页更新计划**，再由编译器原子落盘。切到真实模型后，下面的 mock 限制自动消失。

配置项见 [`.env.example`](.env.example)。

---

## 目录结构

```text
workspace/
├── raw/                         # 人类拥有；不可变证据
├── wiki/                        # LLM 拥有；持久知识
│   ├── index.md                 # 全局目录（自动生成）
│   ├── log.md                   # append-only 操作日志
│   ├── entities/
│   ├── concepts/
│   ├── sources/
│   ├── analyses/
│   ├── queries/                 # save-back 的查询结果
│   └── contradictions/
├── AGENTS.md                    # Schema / 编译规则 / 工作流契约
└── .llmwiki/                    # 全部是派生数据，可安全删除
    ├── meta.sqlite              # FTS 检索索引
    ├── audit.jsonl              # 机器可读审计日志
    └── workspace.lock           # 写入锁
```

> `.llmwiki/` 已被 `.gitignore` 忽略。它是纯派生状态，删除后首次查询会自动重建。

---

## 核心设计原则

- **Markdown-first**：SQLite、向量索引、图索引都是派生加速器，不能成为唯一知识真相。
- **Compile-time synthesis**：Ingest 时把新证据融入已有知识，而不是等到 Query 时重做推理。
- **Multi-page refactor**：一次 Ingest 可以修改多个页面；写入使用 workspace lock + 原子替换。
- **Provenance first**：Wiki 页 frontmatter 维护 `sources`；答案输出 Wiki 引用。
- **Human govern / LLM maintain**：人管 `raw/` 与 schema，LLM 管 `wiki/`。
- **Rebuildable infrastructure**：索引坏了直接 `reindex`，知识不丢。

---

## 命令行

| 命令 | 说明 |
|---|---|
| `llmwiki init <ws>` | 初始化工作区 |
| `llmwiki status <ws>` | 查看工作区状态 |
| `llmwiki add <ws> <file>` | 把文件加入 `raw/`（内容变更会被拒绝） |
| `llmwiki ingest <ws> <raw_path>` | 编译证据进 Wiki |
| `llmwiki query <ws> "<问题>" [--save]` | Wiki-first 查询，可选 save-back |
| `llmwiki lint <ws> [--semantic]` | 结构检查；`--semantic` 需真实 LLM |
| `llmwiki reindex <ws>` | 重建派生索引 |
| `llmwiki serve <ws> [--host] [--port]` | 启动 Web UI + API |

---

## HTTP API

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/api/status` | 工作区状态 |
| `GET` | `/api/pages` | 列出所有 Wiki 页 |
| `GET` | `/api/page?path=concepts/llm-wiki.md` | 读取单页 |
| `POST` | `/api/sources` | `{"name":"note.md","content":"..."}` |
| `POST` | `/api/ingest` | `{"raw_path":"raw/note.md"}` |
| `POST` | `/api/query` | `{"question":"...","save":true}` |
| `POST` | `/api/lint` | `{"semantic":false}` |
| `POST` | `/api/reindex` | 重建索引 |

错误响应只返回语义化消息（如 `resource not found`），内部路径与异常详情只写服务端日志，不回传给调用方。

---

## 架构

完整的 Mermaid 架构图、Ingest / Query 时序图，以及「Demo 组件 → 企业部署」的映射表见 [**ARCHITECTURE.md**](ARCHITECTURE.md)。

4K 架构图：`docs/LLM-Wiki_Architecture_4x3_4096x3072.png`

核心不变量：

1. `raw/` 不被模型改写。
2. `wiki/` 才是持久、可审查的"编译后知识"。
3. 检索索引必须能从 Wiki 完全重建。
4. 每个重要 claim 都能回到 source / page 溯源。
5. Ingest 可以重构旧页；否则系统会退化成"另一种 append-only RAG"。
6. Query 产生的新洞见，只有经过显式 save-back 才进入长期知识。

---

## 测试

```bash
pytest
```

当前 **8 个测试全部通过**，覆盖：

- raw 不可变性（内容变更被拒绝）
- 同一概念页被多份证据 refactor
- query save-back 落盘
- 索引可删除重建
- lint 检出断链
- **回归**：反复 ingest 不再导致页面无限嵌套
- **回归**：残留的过期锁能被自动回收

---

## 已知限制

这个项目是 **production-shaped 参考实现**，不是生产系统。诚实地列出当前边界：

1. **mock 模式的 query 不是真回答**。它把命中的 Wiki 页正文截断拼接，用于验证管线通畅，别当作问答质量。接真实 LLM 后正常。
2. **文件名 slug 冲突会静默覆盖**。两个不同 raw 文件若 stem 相同，会写到同一个 Wiki 页。
3. **锁只做单机文件锁**。跨机器 / 容器需要换成 Redis、etcd 或 Postgres 咨询锁。
4. **无并发压力测试**。当前测试未覆盖多进程同时 ingest。
5. **semantic lint 依赖真实 LLM**，mock 模式下自动跳过。
6. **Web UI 是极简演示页**，不是产品级前端。

---

## 距离"生产级"还差什么

正式上云通常还要补：OIDC / RBAC、多租户 workspace 隔离、对象存储（S3 / OSS）、Postgres、队列与工作流（Temporal / Celery）、分布式锁、审批流、secret manager、指标与 trace、备份、内容安全、模型网关、成本配额。

[ARCHITECTURE.md](ARCHITECTURE.md) 第 5 节给出了逐项对应关系。

---

## 配套材料

| 文件 | 内容 |
|---|---|
| [QUICKSTART.md](QUICKSTART.md) | 更详细的安装与上手 |
| [LAB.md](LAB.md) | 10 个按顺序做的动手实验 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 可编辑的 Mermaid 架构图与时序图 |
| [REFERENCES.md](REFERENCES.md) | 概念来源与实现参考 |
| `examples/` | 用于体验的示例资料 |
| `demo/` | 预编译好的示例工作区 |

---

## 许可证

[MIT](LICENSE)

# Production-Grade LLM-Wiki Architecture

## 1. 核心不是 RAG，而是 Knowledge Compiler

```mermaid
flowchart LR
    H[Human / Connectors] --> RAW[Raw Sources\nImmutable Evidence]
    SCHEMA[AGENTS.md\nSchema + Rules] --> COMPILER
    RAW --> COMPILER[LLM Knowledge Compiler\nParse · Analyze · Plan · Refactor]
    WIKI[Compiled Markdown Wiki\nPersistent Knowledge] --> COMPILER
    COMPILER --> REVIEW{Policy / Human Review}
    REVIEW -->|approve| WIKI
    WIKI --> SEARCH[Derived Search\nindex.md + SQLite FTS\noptional vector/BM25]
    SEARCH --> QUERY[Query Planner\nSearch · Expand Links · Assemble Context]
    QUERY --> LLM[LLM Reasoning]
    LLM --> ANSWER[Answer + Citations]
    ANSWER -->|save valuable result| WIKI
    WIKI --> LINT[Lint / Knowledge Health]
    LINT --> COMPILER
```

## 2. 生产级分层

```mermaid
flowchart TB
  subgraph G[Governance Plane]
    IAM[OIDC / RBAC / Tenant Isolation]
    POL[Policy / Approval / Quota]
    AUD[Audit / Provenance]
  end

  subgraph E[Evidence Plane]
    C[Connectors]
    R[Raw Object Store / raw/]
    HASH[Hash / Version / Metadata]
    C --> R --> HASH
  end

  subgraph K[Knowledge Compilation Plane]
    P[Parse & Understand]
    A[Analyze Existing Wiki]
    U[Update Planner]
    REF[Generate / Refactor Pages]
    P --> A --> U --> REF
  end

  subgraph W[Compiled Knowledge Plane]
    IDX[index.md]
    LOG[log.md]
    ENT[entities/]
    CON[concepts/]
    SRC[sources/]
    ANA[analyses/]
    QRY[queries/]
  end

  subgraph Q[Query & Reasoning Plane]
    SRCH[Wiki Search]
    EXP[Wikilink / Backlink Expansion]
    CTX[Context Assembly]
    GEN[LLM Reasoning]
    CIT[Answer + Citations]
    SRCH --> EXP --> CTX --> GEN --> CIT
  end

  subgraph L[Quality Plane]
    SL[Structural Lint]
    EL[Epistemic / Semantic Lint]
    ST[Staleness / Contradictions / Coverage]
  end

  subgraph O[Operations Plane]
    API[API / MCP / CLI]
    OBS[Metrics / Logs / Traces]
    GIT[Git / Version / Rollback]
    IDX2[Derived FTS / Vector Index]
  end

  HASH --> P
  REF --> W
  W --> SRCH
  CIT -->|Save Back| QRY
  W --> SL --> EL --> ST --> U
  W --> IDX2 --> SRCH
  G --> K
  G --> Q
  API --> K
  API --> Q
  W --> GIT
```

## 3. Ingest 时序：一次“知识编译”，不是一次“文档入库”

```mermaid
sequenceDiagram
    participant U as User/Connector
    participant S as Storage
    participant X as Search Index
    participant C as Compiler
    participant M as LLM
    participant W as Wiki
    participant G as Git/Audit

    U->>S: add raw/source.md (immutable)
    C->>S: read source + AGENTS.md
    C->>X: retrieve affected existing pages
    C->>M: source + current wiki + schema -> update plan
    M-->>C: multi-page upserts
    C->>W: atomic write source/concept/entity/... pages
    C->>W: rebuild index.md + append log.md
    C->>X: rebuild derived FTS
    C->>G: audit + optional git commit
```

## 4. Query 时序：Wiki-first，而不是 Raw-chunk-first

```mermaid
sequenceDiagram
    participant U as User
    participant Q as Query Service
    participant X as Wiki Search
    participant W as Markdown Wiki
    participant M as LLM

    U->>Q: question
    Q->>X: search compiled knowledge
    X-->>Q: relevant wiki pages
    Q->>W: expand wikilinks / collect provenance
    Q->>M: compiled context + question
    M-->>Q: answer with page citations
    Q-->>U: answer
    opt save-back
      Q->>W: queries/<slug>.md
      Q->>X: reindex
    end
```

## 5. 本仓库实现与企业部署映射

| Demo 组件 | 企业部署替代/扩展 |
|---|---|
| local filesystem `raw/` | S3/OSS/Blob + WORM/versioning |
| Markdown `wiki/` | Git + object store；或 Postgres JSONB + export-to-markdown |
| file lock | Redis/etcd/Postgres advisory lock |
| SQLite FTS5 | OpenSearch/Elasticsearch；可选 pgvector/Qdrant |
| FastAPI | API Gateway + autoscaled workers |
| local audit.jsonl | centralized audit stream / SIEM |
| subprocess Git | GitHub/GitLab PR + approval workflow |
| env secrets | Vault/KMS/Secret Manager |
| direct LLM call | model gateway + policy + quota + fallback |
| synchronous ingest | Temporal/Celery/Kafka workflow |

## 6. 关键不变量

1. `raw/` 不被模型改写。
2. `wiki/` 才是持久、可审查的“编译后知识”。
3. 检索索引必须可以从 Wiki 完全重建。
4. 每个重要 claim 必须能回到 source/page provenance。
5. Ingest 可以重构旧页；否则系统会退化成“另一种 append-only RAG”。
6. Query 产生的新洞见，只有通过显式 save-back/审批后才进入长期知识。

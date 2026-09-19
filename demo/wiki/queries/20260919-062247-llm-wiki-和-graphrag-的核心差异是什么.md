---
title: "Query: LLM-Wiki 和 GraphRAG 的核心差异是什么？"
type: "query"
updated_at: "2026-09-19T06:22:47.367061+00:00"
sources:
  - raw/01-graphrag.md
  - raw/02-llm-wiki.md
  - raw/03-compounding.md
---

# Query: LLM-Wiki 和 GraphRAG 的核心差异是什么？

## Answer

Mock mode（确定性体验，不冒充真实大模型）：

本次回答优先消费已经编译进 Wiki 的持久知识，而不是直接从 raw chunks 临时拼接。

- GraphRAG Current synthesis This durable concept page is maintained at ingest time. The latest evidence from `raw/01-graphrag.md` has been integrated into the existing Wiki rather than stored only as an opaque retrieval chunk. Evidence notes GraphRAG GraphRAG is a retrieval architecture that extracts entities and relationships, builds graph-oriented [wiki:concepts/graphrag.md]
- GraphRAG Source summary GraphRAG GraphRAG is a retrieval architecture that extracts entities and relationships, builds graph-oriented indexes, and uses graph structure plus text evidence to improve retrieval and synthesis. Its center of gravity remains retrieval-time context construction. The graph index can help answer global and local questions b [wiki:sources/01-graphrag.md]
- LLM-Wiki Source summary LLM-Wiki LLM-Wiki treats raw sources as immutable evidence and asks an LLM knowledge compiler to maintain a persistent Markdown Wiki. Ingest is not merely chunking plus embedding: new evidence may create source pages, update existing concept pages, add links, record provenance, and refactor previous synthesis. Query is Wiki- [wiki:sources/02-llm-wiki.md]
- Knowledge Compounding in LLM-Wiki Source summary Knowledge Compounding in LLM-Wiki Knowledge compounding means that later evidence can revise an already-existing durable concept page. The system does not need to rediscover the same synthesis from raw chunks on every query. A valuable query result can be explicitly promoted back into the Wiki throug [wiki:sources/03-compounding.md]

## Retrieved pages

- [concepts/graphrag.md](../concepts/graphrag.md)
- [sources/01-graphrag.md](../sources/01-graphrag.md)
- [sources/02-llm-wiki.md](../sources/02-llm-wiki.md)
- [sources/03-compounding.md](../sources/03-compounding.md)

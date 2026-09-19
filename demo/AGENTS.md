# LLM-Wiki Knowledge Contract

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

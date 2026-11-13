# data-platform-mcp

**Bring your data platform to AI agents.** An open, production-minded [Model Context Protocol](https://modelcontextprotocol.io) server that exposes metadata, data lineage, and metrics as first-class tools for LLM agents.

```
Agent  ──MCP──>  data-platform-mcp  ──adapter──>  your data platform
                                              (OpenLineage / DataHub / OpenMetadata / custom)
```

## Why

Data agents today burn most of their reasoning budget on *addressing* — finding the right table, the right metric definition, the right upstream dependency — not on the analysis itself. The fix is not a smarter model; it is exposing your data platform's semantic inventory through a stable, tool-oriented interface.

`data-platform-mcp` packages the tool categories a data agent actually needs, so platform teams can mount their metadata/lineage/metrics estate onto any MCP-capable agent (Claude Code, Claude Desktop, Codex, custom orchestrators) in an afternoon instead of a quarter.

> Design distilled from operating an enterprise-grade data MCP in production (six-figure monthly tool calls, dozens of daily active analyst users). This repo is a clean-room, vendor-neutral re-implementation — it contains no proprietary code.

## Tool surface (v0 roadmap)

| Category | Tools | What agents get |
|---|---|---|
| **Metadata** | `search_tables`, `get_table_detail`, `list_fields` | Find and understand tables without dumping schemas into context |
| **Lineage** | `query_upstream`, `query_downstream`, `impact_analysis` | Trace where data comes from and what breaks when it changes |
| **Metrics** | `search_metrics`, `get_metric_definition`, `query_metric_data` | Resolve business terms to governed definitions (one number, one meaning) |
| **Guardrails** | `check_permission`, `describe_limits` | Enforce row/column-level access and rate limits at the tool layer, not in prompts |

Design principles carried through every tool:

1. **Progressive disclosure** — return summaries first; detail on explicit drill-down. Never dump a 10k-table catalog into the context window.
2. **Structured facts, not prose** — tools return typed, bounded JSON. Interpretation is the agent's job.
3. **Address-first** — every entity carries a stable ID + a human term; term-to-ID resolution is a first-class operation, because term mismatch is the #1 failure mode of natural-language data access.
4. **Refuse over guess** — when no match is found, return near-misses and confidence, not a wrong answer.

## Project layout

```
data-platform-mcp/
├── src/            # MCP server core (tool registry, auth, caching, paging)
├── adapters/       # one adapter per backend (openlineage, datahub, openmetadata, rest)
├── docs/           # tool specs, design notes, deployment guide
└── examples/       # wiring samples for common agent clients
```

## Status

**v0 — spec & skeleton.** The tool contracts in `docs/tools.md` are the source of truth and are being implemented against the adapter API. Contributions welcome, especially adapters.

## Roadmap

- [ ] v0.1 — MCP server core + in-memory demo adapter (runnable end-to-end)
- [ ] v0.2 — OpenLineage + OpenMetadata adapters
- [ ] v0.3 — metric semantics layer (term resolution, definition governance)
- [ ] v0.4 — row/column-level permission enforcement hooks
- [ ] v1.0 — battle-tested, documented, semver-stable tool contracts

## License

[MIT](LICENSE)

# Tool Contracts (v0 draft)

Every tool follows the same response envelope:

```json
{
  "ok": true,
  "data": { "…": "typed, bounded payload" },
  "meta": { "total": 123, "page": 1, "pageSize": 20, "truncated": false },
  "warnings": ["optional near-miss / deprecation notes"]
}
```

Contracts are versioned per tool (`tool_version` field). Breaking changes bump the major and old shapes are kept for one release cycle.

## Metadata

### search_tables
Find tables by business term, not by exact name.

- input: `{ "q": string, "domain": string?, "pageSize": int? }`
- output: table summaries — `{ id, name, title, domain, owner, rowEstimate, freshness }[]`
- semantics: ranked fuzzy match; include `warnings` with near-misses when the top score is below threshold.

### get_table_detail
- input: `{ "tableId": string }`
- output: full schema (fields, types, comments), partition info, quality stats, direct lineage counts.
- size rule: field list is capped at 200; drill into `list_fields` for wide tables.

### list_fields
- input: `{ "tableId": string, "page": int?, "filter": string? }`

## Lineage

### query_upstream / query_downstream
- input: `{ "nodeId": string, "depth": int = 1..5, "direction": "table" | "column" }`
- output: subgraph, bounded to `maxNodes` (default 50) with `truncated` flag.

### impact_analysis
- input: `{ "nodeId": string, "change": "schema" | "data" | "deprecation" }`
- output: downstream blast radius grouped by domain + owner, for change review.

## Metrics

### search_metrics / get_metric_definition
- term resolution first: `{ "q": "monthly active users" }` → candidate metrics with definition, owner, and *caveats* (each candidate carries its own time grain / filter semantics — differences are surfaced, not hidden).

### query_metric_data
- gated: checks permission before executing; date-window caps enforced server-side.

## Guardrails

- `check_permission` — agent-callable, but enforcement is server-side on every data-returning tool.
- `describe_limits` — returns paging caps, rate limits, and default time windows so the agent can plan its calls.

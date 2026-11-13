"""data-platform-mcp server (v0.1).

Exposes the tool contracts in docs/tools.md over MCP using the official
Python SDK (FastMCP). The backend is chosen by env var:

    DATA_PLATFORM_ADAPTER = "inmemory" (default) | future: "openlineage", ...

Run:
    pip install -e .[dev]
    python -m src.server          # stdio transport, ready for Claude Desktop / Claude Code
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

from adapters.inmemory import InMemoryAdapter

mcp = FastMCP("data-platform-mcp")

_adapter = InMemoryAdapter()

PAGE_SIZE_CAP = 50
DEPTH_CAP = 5
MAX_NODES = 50


def _ok(data, **meta) -> dict:
    envelope = {"ok": True, "data": data, "meta": meta, "warnings": []}
    return envelope


def _warn(data, warnings: list[str], **meta) -> dict:
    return {"ok": True, "data": data, "meta": meta, "warnings": warnings}


def _refuse(near_misses: list[dict], reason: str) -> dict:
    return {"ok": False, "data": {"nearMisses": near_misses}, "meta": {}, "warnings": [reason]}


# -- metadata -----------------------------------------------------------


@mcp.tool()
def search_tables(q: str, domain: str = "", page: int = 1, page_size: int = 20) -> dict:
    """Find tables by business term. Returns ranked summaries; check warnings
    for near-misses before trusting the top hit."""
    page_size = min(page_size, PAGE_SIZE_CAP)
    res = _adapter.search_tables(q, domain or None, page, page_size)
    if not res["rows"]:
        return _refuse(res["rows"], f"no table matches the term {q!r}; try a broader term or clear the domain filter")
    return _warn(res["rows"], res["warnings"], total=res["total"], page=page, page_size=page_size)


@mcp.tool()
def get_table_detail(table_id: str) -> dict:
    """Full schema, partitions, quality stats, and lineage counts for one table."""
    d = _adapter.get_table_detail(table_id)
    if d is None:
        return _refuse([], f"unknown table id {table_id!r}; call search_tables first")
    return _ok(d)


@mcp.tool()
def list_fields(table_id: str, page: int = 1, page_size: int = 20, filter: str = "") -> dict:
    """Field list for a table, paginated; use filter for wide tables."""
    page_size = min(page_size, PAGE_SIZE_CAP)
    res = _adapter.list_fields(table_id, page, page_size, filter or None)
    return _warn(res["rows"], res["warnings"], total=res["total"], page=page, page_size=page_size)


# -- lineage ------------------------------------------------------------


@mcp.tool()
def query_upstream(node_id: str, depth: int = 1) -> dict:
    """Trace upstream dependencies of a table (depth 1-5), bounded graph."""
    depth = max(1, min(depth, DEPTH_CAP))
    res = _adapter.query_graph(node_id, "upstream", depth, MAX_NODES)
    return _ok(res, truncated=res["truncated"])


@mcp.tool()
def query_downstream(node_id: str, depth: int = 1) -> dict:
    """Trace downstream dependents of a table (depth 1-5), bounded graph."""
    depth = max(1, min(depth, DEPTH_CAP))
    res = _adapter.query_graph(node_id, "downstream", depth, MAX_NODES)
    return _ok(res, truncated=res["truncated"])


@mcp.tool()
def impact_analysis(node_id: str, change: str = "schema") -> dict:
    """Downstream blast radius of a change (schema | data | deprecation),
    grouped by domain and owner, for change review."""
    res = _adapter.query_graph(node_id, "downstream", DEPTH_CAP, MAX_NODES)
    nodes = [n["id"] for n in res["nodes"] if n["id"] != node_id]
    groups: dict[str, list[str]] = {}
    for n in nodes:
        t = _adapter.get_table_detail(n)
        if t:
            groups.setdefault(f"{t['domain']}/{t['owner']}", []).append(t["name"])
    return _ok(
        {
            "change": change,
            "affectedCount": len(nodes),
            "truncated": res["truncated"],
            "byOwner": groups,
        }
    )


# -- metrics ------------------------------------------------------------


@mcp.tool()
def search_metrics(q: str) -> dict:
    """Resolve a business term to candidate metrics. Candidates with the same
    name but different grains are all returned, differences stated."""
    hits = _adapter.search_metrics(q)
    if not hits:
        return _refuse([], f"no metric matches the term {q!r}; avoid guessing — ask the user for the intended grain")
    return _ok(hits)


@mcp.tool()
def get_metric_definition(metric_id: str) -> dict:
    """The governed definition, owner, and caveats of one metric."""
    m = _adapter.get_metric_definition(metric_id)
    if m is None:
        return _refuse([], f"unknown metric id {metric_id!r}; call search_metrics first")
    return _ok(m)


# -- guardrails ---------------------------------------------------------


@mcp.tool()
def describe_limits() -> dict:
    """Server-side caps (paging, depth, graph size) so the agent can plan calls."""
    return _ok(
        {
            "pageSizeCap": PAGE_SIZE_CAP,
            "depthCap": DEPTH_CAP,
            "maxGraphNodes": MAX_NODES,
            "note": "enforcement is server-side on every tool; this tool is for planning only",
        }
    )


if __name__ == "__main__":
    mcp.run()

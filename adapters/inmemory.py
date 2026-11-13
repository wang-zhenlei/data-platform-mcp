"""In-memory demo catalog.

A tiny synthetic dataset (e-commerce domain) so the server runs end-to-end
with zero infrastructure. Real backends implement the same adapter protocol.
"""

from __future__ import annotations

from typing import Any


def _score(term: str, target: str) -> float:
    """Cheap lexical overlap score in [0, 1]; not a search engine."""
    t = set(term.lower().split())
    g = set(target.lower().replace("_", " ").split())
    if not t or not g:
        return 0.0
    return len(t & g) / len(t)


DEMO_TABLES = {
    "tbl_orders": {
        "id": "tbl_orders",
        "name": "dw.fact_orders",
        "title": "Order fact table",
        "domain": "sales",
        "owner": "data-eng",
        "rowEstimate": 480_000_000,
        "freshness": "daily (T+1)",
        "fields": [
            {"name": "order_id", "type": "string", "comment": "PK"},
            {"name": "customer_id", "type": "string", "comment": "FK -> customers"},
            {"name": "product_id", "type": "string", "comment": "FK -> products"},
            {"name": "region", "type": "string", "comment": "sale region code"},
            {"name": "amount", "type": "decimal", "comment": "order amount"},
            {"name": "status", "type": "string", "comment": "created/paid/refunded"},
            {"name": "dt", "type": "date", "comment": "partition column"},
        ],
        "partitions": ["dt"],
        "quality": {"nullRate": 0.002, "dupRate": 0.0001},
    },
    "tbl_customers": {
        "id": "tbl_customers",
        "name": "dw.dim_customers",
        "title": "Customer dimension",
        "domain": "sales",
        "owner": "data-eng",
        "rowEstimate": 3_200_000,
        "freshness": "daily",
        "fields": [
            {"name": "customer_id", "type": "string", "comment": "PK"},
            {"name": "customer_level", "type": "string", "comment": "bronze/silver/gold"},
            {"name": "region", "type": "string", "comment": "registered region"},
            {"name": "signup_dt", "type": "date", "comment": ""},
        ],
        "partitions": [],
        "quality": {"nullRate": 0.0, "dupRate": 0.0},
    },
    "tbl_products": {
        "id": "tbl_products",
        "name": "dw.dim_products",
        "title": "Product dimension",
        "domain": "product",
        "owner": "data-eng",
        "rowEstimate": 85_000,
        "freshness": "daily",
        "fields": [
            {"name": "product_id", "type": "string", "comment": "PK"},
            {"name": "category", "type": "string", "comment": "leaf category"},
            {"name": "price", "type": "decimal", "comment": "list price"},
        ],
        "partitions": [],
        "quality": {"nullRate": 0.001, "dupRate": 0.0},
    },
    "tbl_returns": {
        "id": "tbl_returns",
        "name": "dw.fact_returns",
        "title": "Return fact table",
        "domain": "sales",
        "owner": "data-eng",
        "rowEstimate": 12_000_000,
        "freshness": "daily",
        "fields": [
            {"name": "return_id", "type": "string", "comment": "PK"},
            {"name": "order_id", "type": "string", "comment": "FK -> orders"},
            {"name": "reason", "type": "string", "comment": "return reason"},
            {"name": "dt", "type": "date", "comment": "partition column"},
        ],
        "partitions": ["dt"],
        "quality": {"nullRate": 0.01, "dupRate": 0.0},
    },
}

# Directed edges: source -> target (source feeds target)
DEMO_EDGES = [
    ("tbl_orders", "tbl_returns"),
    ("tbl_customers", "tbl_orders"),
    ("tbl_products", "tbl_orders"),
]

DEMO_METRICS = {
    "m_gmv": {
        "id": "m_gmv",
        "name": "GMV",
        "aliases": ["gmv", "gross merchandise value", "total sales"],
        "definition": "SUM(amount) over paid orders (status = 'paid')",
        "owner": "data-eng",
        "sourceTable": "tbl_orders",
        "timeGrain": "day",
        "caveats": ["excludes refunded orders", "amount is list price, not settled"],
    },
    "m_return_rate": {
        "id": "m_return_rate",
        "name": "return_rate",
        "aliases": ["return rate", "returns ratio"],
        "definition": "return orders / paid orders, by region",
        "owner": "data-eng",
        "sourceTable": "tbl_returns",
        "timeGrain": "day",
        "caveats": ["same-day returns counted in the same window as the paid order"],
    },
}


class InMemoryAdapter:
    """Implements the CatalogAdapter protocol over the demo dataset."""

    def __init__(self) -> None:
        self._upstream: dict[str, list[str]] = {}
        self._downstream: dict[str, list[str]] = {}
        for src, dst in DEMO_EDGES:
            self._downstream.setdefault(src, []).append(dst)
            self._upstream.setdefault(dst, []).append(src)

    # -- tables ---------------------------------------------------------

    def search_tables(self, q: str, domain: str | None, page: int, page_size: int) -> dict[str, Any]:
        rows = []
        for t in DEMO_TABLES.values():
            if domain and t["domain"] != domain:
                continue
            s = max(_score(q, t["name"]), _score(q, t["title"]), _score(q, t["domain"]))
            rows.append((s, t))
        rows.sort(key=lambda x: -x[0])
        hits = [t for s, t in rows if s > 0]
        warnings: list[str] = []
        if hits and rows[0][0] < 0.6:
            warnings.append("top match score is low; near-misses returned, confirm before use")
        total = len(hits)
        start = (page - 1) * page_size
        page_rows = [
            {k: t[k] for k in ("id", "name", "title", "domain", "owner", "rowEstimate", "freshness")}
            for t in hits[start : start + page_size]
        ]
        return {"rows": page_rows, "total": total, "warnings": warnings}

    def get_table_detail(self, table_id: str) -> dict[str, Any] | None:
        t = DEMO_TABLES.get(table_id)
        if not t:
            return None
        d = dict(t)
        d["upstreamCount"] = len(self._upstream.get(table_id, []))
        d["downstreamCount"] = len(self._downstream.get(table_id, []))
        return d

    def list_fields(self, table_id: str, page: int, page_size: int, filter: str | None) -> dict[str, Any]:
        t = DEMO_TABLES.get(table_id)
        if not t:
            return {"rows": [], "total": 0, "warnings": ["table not found"]}
        fields = t["fields"]
        if filter:
            fields = [f for f in fields if filter.lower() in f["name"].lower()]
        start = (page - 1) * page_size
        return {"rows": fields[start : start + page_size], "total": len(fields)}

    # -- lineage --------------------------------------------------------

    def query_graph(self, node_id: str, direction: str, depth: int, max_nodes: int) -> dict[str, Any]:
        adj = self._upstream if direction == "upstream" else self._downstream
        nodes: dict[str, dict[str, Any]] = {node_id: {"id": node_id}}
        edges: list[dict[str, str]] = []
        frontier = [node_id]
        truncated = False
        for _ in range(depth):
            nxt: list[str] = []
            for n in frontier:
                for m in adj.get(n, []):
                    if len(nodes) >= max_nodes:
                        truncated = True
                        break
                    if m not in nodes:
                        nodes[m] = {"id": m}
                        nxt.append(m)
                    if direction == "upstream":
                        edges.append({"source": m, "target": n})
                    else:
                        edges.append({"source": n, "target": m})
            frontier = nxt
        return {"nodes": list(nodes.values()), "edges": edges, "truncated": truncated}

    # -- metrics --------------------------------------------------------

    def search_metrics(self, q: str) -> list[dict[str, Any]]:
        out = []
        for m in DEMO_METRICS.values():
            s = max([_score(q, a) for a in [m["name"], *m["aliases"]]] or [0.0])
            if s > 0:
                out.append((s, m))
        out.sort(key=lambda x: -x[0])
        return [m for _, m in out]

    def get_metric_definition(self, metric_id: str) -> dict[str, Any] | None:
        return DEMO_METRICS.get(metric_id)

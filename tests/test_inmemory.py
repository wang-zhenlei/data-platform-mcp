"""Smoke tests for the demo adapter and tool semantics.

Run: pytest -q
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters.inmemory import InMemoryAdapter


def test_search_tables_hits():
    a = InMemoryAdapter()
    res = a.search_tables("orders", None, 1, 20)
    assert res["total"] >= 1
    assert res["rows"][0]["id"] == "tbl_orders"


def test_search_tables_low_confidence_warns():
    a = InMemoryAdapter()
    res = a.search_tables("order", None, 1, 20)
    # "order" overlaps only partially -> either hit-with-warning or no hit; both fine
    assert "warnings" in res


def test_table_detail_lineage_counts():
    a = InMemoryAdapter()
    d = a.get_table_detail("tbl_orders")
    assert d is not None
    assert d["upstreamCount"] == 2
    assert d["downstreamCount"] == 1


def test_unknown_table_returns_none():
    a = InMemoryAdapter()
    assert a.get_table_detail("tbl_nope") is None


def test_upstream_graph_bounded():
    a = InMemoryAdapter()
    g = a.query_graph("tbl_returns", "upstream", depth=3, max_nodes=50)
    ids = {n["id"] for n in g["nodes"]}
    assert "tbl_orders" in ids
    assert "tbl_customers" in ids
    assert not g["truncated"]


def test_downstream_truncation():
    a = InMemoryAdapter()
    g = a.query_graph("tbl_customers", "downstream", depth=5, max_nodes=2)
    assert len(g["nodes"]) <= 2


def test_metric_term_resolution():
    a = InMemoryAdapter()
    hits = a.search_metrics("gmv")
    assert [m["id"] for m in hits] == ["m_gmv"]
    assert hits[0]["caveats"]  # caveats are first-class


def test_metric_no_match():
    a = InMemoryAdapter()
    assert a.search_metrics("churn") == []

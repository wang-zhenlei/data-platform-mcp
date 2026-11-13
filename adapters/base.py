"""Adapter protocol.

Every backend (OpenLineage, OpenMetadata, DataHub, or in-memory demo)
implements this read API. Tool contracts in docs/tools.md are the normative
reference; the server never talks to a backend directly.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CatalogAdapter(Protocol):
    """Read-only view over a data platform's semantic inventory."""

    def search_tables(self, q: str, domain: str | None, page: int, page_size: int) -> dict[str, Any]:
        """Ranked table summaries. Must include `warnings` with near-misses."""

    def get_table_detail(self, table_id: str) -> dict[str, Any] | None:
        """Full schema, partitions, quality stats, lineage counts."""

    def list_fields(self, table_id: str, page: int, page_size: int, filter: str | None) -> dict[str, Any]:
        """Field list for wide tables (capped, paginated)."""

    def query_graph(self, node_id: str, direction: str, depth: int, max_nodes: int) -> dict[str, Any]:
        """Upstream/downstream subgraph, bounded, with `truncated` flag."""

    def search_metrics(self, q: str) -> list[dict[str, Any]]:
        """Metric candidates with definition, owner, and caveats."""

    def get_metric_definition(self, metric_id: str) -> dict[str, Any] | None:
        """Single governed metric definition."""

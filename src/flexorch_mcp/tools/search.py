"""Tool 5: search_documents — full-text and semantic search across indexed datasets."""
from __future__ import annotations

from typing import Any

from ..client import FlexOrchMCPClient
from ..errors import FlexOrchAPIError

_VALID_MODES = {"auto", "semantic", "structured", "hybrid"}
_MAX_TOP_K = 50


async def run(
    client: FlexOrchMCPClient,
    query: str,
    top_k: int = 5,
    mode: str = "auto",
    document_type: str = "",
    language: str = "",
    quality_grade: str = "",
) -> dict[str, Any]:
    query = query.strip()
    if not query:
        return {"isError": True, "error": "Query cannot be empty."}
    if len(query) > 1000:
        return {"isError": True, "error": "Query too long. Max 1000 characters."}
    if mode not in _VALID_MODES:
        return {"isError": True, "error": f"Invalid mode '{mode}'. Choose: auto, semantic, structured, hybrid"}

    top_k = min(max(top_k, 1), _MAX_TOP_K)

    payload: dict[str, Any] = {"query": query, "top_k": top_k, "mode": mode}
    filters: dict[str, Any] = {}
    if document_type:
        filters["document_type"] = document_type
    if language:
        filters["language"] = language
    if quality_grade:
        filters["quality_grade"] = quality_grade
    if filters:
        payload["filters"] = filters

    try:
        response: dict[str, Any] = await client.post("/search", json=payload)
    except FlexOrchAPIError as exc:
        return {"isError": True, "error": str(exc)}

    data = response.get("data", response)
    return {
        "results": data.get("results", []),
        "total_results": data.get("total_results", 0),
        "mode": data.get("mode", mode),
        "query": query,
    }

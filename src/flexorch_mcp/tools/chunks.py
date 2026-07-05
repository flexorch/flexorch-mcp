"""Tool 8: list_chunks — retrieve RAG-ready text chunks from an indexed dataset (Pro+ plan required)."""
from __future__ import annotations

from typing import Any

from ..client import FlexOrchMCPClient
from ..errors import FlexOrchAPIError

_VALID_GRADES = {"A", "B", "C", "D"}
_GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}
_MAX_PAGE_SIZE = 100


def _grades_and_above(threshold: str) -> str:
    """Return comma-separated grades >= threshold. E.g. "B" → "A,B"."""
    t = _GRADE_ORDER.get(threshold.upper(), 3)
    return ",".join(g for g, rank in _GRADE_ORDER.items() if rank <= t)


async def run(
    client: FlexOrchMCPClient,
    dataset_id: int,
    min_quality: str = "B",
    pii_masked_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    if dataset_id <= 0:
        return {"isError": True, "error": "dataset_id must be a positive integer."}

    min_quality = min_quality.strip().upper()
    if min_quality not in _VALID_GRADES:
        return {"isError": True, "error": f"min_quality must be A, B, C, or D — got '{min_quality}'."}

    page = max(1, page)
    page_size = min(max(1, page_size), _MAX_PAGE_SIZE)

    params: dict[str, Any] = {
        "page": page,
        "page_size": page_size,
        "quality_grade": _grades_and_above(min_quality),
    }
    if pii_masked_only:
        params["pii_masked"] = "true"

    try:
        response: dict[str, Any] = await client.get(
            f"/datasets/{dataset_id}/chunks", params=params
        )
    except FlexOrchAPIError as exc:
        if exc.status_code == 403:
            return {
                "isError": True,
                "error": (
                    "Chunk listing requires a Pro plan (dataset must also be indexed). "
                    "Upgrade at app.flexorch.com/settings/billing."
                ),
            }
        if exc.status_code == 404:
            return {"isError": True, "error": f"Dataset {dataset_id} not found or not indexed yet. Run dataset.index({dataset_id}) first."}
        return {"isError": True, "error": str(exc)}

    data = response.get("data", response)
    items = data.get("items", [])
    total = data.get("total", 0)

    return {
        "dataset_id": dataset_id,
        "chunks": items,
        "chunk_count": len(items),
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (page * page_size) < total,
    }

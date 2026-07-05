"""Tool 7: index_dataset — trigger semantic indexing for a dataset (Pro+ plan required)."""
from __future__ import annotations

from typing import Any

from ..client import FlexOrchMCPClient
from ..errors import FlexOrchAPIError


async def run(client: FlexOrchMCPClient, dataset_id: int) -> dict[str, Any]:
    if dataset_id <= 0:
        return {"isError": True, "error": "dataset_id must be a positive integer."}

    try:
        response: dict[str, Any] = await client.post(f"/datasets/{dataset_id}/index")
    except FlexOrchAPIError as exc:
        if exc.status_code == 403:
            return {
                "isError": True,
                "error": (
                    "Semantic indexing requires a Pro plan. "
                    "Upgrade at app.flexorch.com/settings/billing."
                ),
            }
        return {"isError": True, "error": str(exc)}

    data = response.get("data", response)
    status = data.get("status", "indexing")
    return {
        "dataset_id": dataset_id,
        "status": status,
        "message": data.get("message", "Indexing started."),
        "index_hint": (
            f"Use dataset.chunks(dataset_id={dataset_id}) to retrieve chunks "
            "once indexing is complete. Indexing typically takes 10–60 seconds "
            "depending on dataset size."
        ),
    }

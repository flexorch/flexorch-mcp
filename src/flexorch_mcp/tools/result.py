"""Tool 3: get_extraction_result — structured fields + quality + privacy from an execution."""
from __future__ import annotations

from typing import Any

from ..client import FlexOrchMCPClient
from ..errors import FlexOrchAPIError

_RECORDS_PREVIEW_LIMIT = 100


async def run(client: FlexOrchMCPClient, execution_id: int) -> dict[str, Any]:
    try:
        response: dict[str, Any] = await client.get(f"/executions/{execution_id}")
    except FlexOrchAPIError as exc:
        return {"isError": True, "error": str(exc)}

    exec_data: dict[str, Any] = response.get("data", response)
    result_meta: dict[str, Any] = exec_data.get("result_meta") or {}
    privacy_block: dict[str, Any] = exec_data.get("privacy") or {}
    output_summary: dict[str, Any] = exec_data.get("output_summary") or {}
    records: list[dict[str, Any]] = exec_data.get("records") or []
    dataset_info: dict[str, Any] | None = exec_data.get("dataset")

    document_type = result_meta.get("document_type") or exec_data.get("document_type")
    detected_language = result_meta.get("detected_language")

    quality: dict[str, Any] = {
        "grade": result_meta.get("grade"),
        "score": result_meta.get("score"),
        "warnings": result_meta.get("warnings") or [],
    }
    privacy: dict[str, Any] = {
        "pii_findings_count": privacy_block.get("pii_findings_count", 0),
        "pii_masked": bool(privacy_block.get("privacy_applied", False)),
    }

    columns: list[str] = output_summary.get("columns") or []
    row_count: int = output_summary.get("row_count", 0)

    result: dict[str, Any] = {
        "execution_id": execution_id,
        "document_type": document_type,
        "detected_language": detected_language,
        "quality": quality,
        "privacy": privacy,
        "row_count": row_count,
        "columns": columns,
    }

    if records:
        result["fields"] = records[:_RECORDS_PREVIEW_LIMIT]
        if len(records) > _RECORDS_PREVIEW_LIMIT:
            result["has_more"] = True
            dataset_id = dataset_info["id"] if dataset_info else None
            id_hint = f"dataset_id={dataset_id}" if dataset_id else "dataset_id"
            result["has_more_hint"] = (
                f"Showing first {_RECORDS_PREVIEW_LIMIT} of {len(records)} records. "
                f"Call export_dataset({id_hint}, format='jsonl') to retrieve all records at once."
            )
    else:
        result["fields_hint"] = (
            "Field values are available after building a dataset. "
            f"Call build_dataset(execution_id={execution_id}) then export_dataset(dataset_id, format)."
        )

    return result

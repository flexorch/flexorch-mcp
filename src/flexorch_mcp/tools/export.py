"""Tool 6: export_dataset — download a built dataset in text format."""
from __future__ import annotations

from typing import Any

from ..client import FlexOrchMCPClient
from ..errors import FlexOrchAPIError

_TEXT_FORMATS = {"json", "jsonl", "csv", "md", "xml", "rag"}
_BINARY_FORMATS = {"parquet", "hf"}
_VALID_FORMATS = _TEXT_FORMATS | _BINARY_FORMATS


async def run(
    client: FlexOrchMCPClient,
    dataset_id: int,
    format: str = "jsonl",
) -> dict[str, Any]:
    fmt = format.lower().strip()
    if fmt not in _VALID_FORMATS:
        return {
            "isError": True,
            "error": (
                f"Unsupported format '{fmt}'. "
                f"Text formats: {', '.join(sorted(_TEXT_FORMATS))}. "
                "Binary formats (parquet, hf) must be downloaded via the FlexOrch API directly."
            ),
        }
    if fmt in _BINARY_FORMATS:
        return {
            "isError": True,
            "error": (
                f"Format '{fmt}' is binary and cannot be returned as text via MCP. "
                f"Download it directly from: GET /v1/datasets/{dataset_id}/export/{fmt}"
            ),
        }

    try:
        content_bytes, _, filename = await client.get_raw(
            f"/datasets/{dataset_id}/export/{fmt}"
        )
    except FlexOrchAPIError as exc:
        return {"isError": True, "error": str(exc)}

    try:
        content_text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return {"isError": True, "error": "Export content could not be decoded as UTF-8."}

    return {
        "dataset_id": dataset_id,
        "format": fmt,
        "filename": filename,
        "content": content_text,
        "byte_count": len(content_bytes),
    }

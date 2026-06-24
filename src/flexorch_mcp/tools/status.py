"""Tool 2: get_job_status — poll a processing or build job."""
from __future__ import annotations

from typing import Any

from ..client import FlexOrchMCPClient
from ..errors import FlexOrchAPIError


async def run(client: FlexOrchMCPClient, job_id: int) -> dict[str, Any]:
    try:
        response: dict[str, Any] = await client.get(f"/jobs/{job_id}")
    except FlexOrchAPIError as exc:
        return {"isError": True, "error": str(exc)}

    # Unwrap envelope: {"status":"success","data":{...job...},"error":null}
    job: dict[str, Any] = response.get("data", response)

    status: str = job.get("status", "")
    job_type: str = job.get("job_type", "data_process")
    result_meta: dict[str, Any] = job.get("result_meta") or {}

    if status == "failed":
        exec_summary: dict[str, Any] = job.get("execution_summary") or {}
        reason = (
            exec_summary.get("failure_reason")
            or job.get("error")
            or "Unknown error"
        )
        return {
            "job_id": job_id,
            "status": "failed",
            "reason": reason,
        }

    if status == "running":
        stage = result_meta.get("pipeline_stage")
        out: dict[str, Any] = {"job_id": job_id, "status": "running"}
        if stage:
            out["stage"] = stage
        return out

    if status in ("queued",):
        return {"job_id": job_id, "status": status}

    if status == "completed":
        if job_type == "dataset_build":
            ds: dict[str, Any] = job.get("dataset_summary") or {}
            return {
                "job_id": job_id,
                "status": "completed",
                "dataset_id": ds.get("dataset_id"),
                "dataset_name": ds.get("name"),
                "row_count": ds.get("row_count"),
                "poll_hint": (
                    f"Dataset is ready. Use export_dataset({ds.get('dataset_id')}, format) to download. "
                    "Supported formats: jsonl, csv, json, xml, xlsx, md, rag, hf"
                ),
            }

        # data_process job
        ps: dict[str, Any] = job.get("processing_summary") or {}
        quality: dict[str, Any] = ps.get("quality") or {}
        privacy: dict[str, Any] = ps.get("privacy") or {}
        execution_id: int | None = ps.get("execution_id")

        return {
            "job_id": job_id,
            "status": "completed",
            "execution_id": execution_id,
            "quality_grade": quality.get("grade"),
            "quality_score": quality.get("score"),
            "pii_found": bool(privacy.get("pii_findings_count", 0)),
            "pii_masked": bool(privacy.get("privacy_applied", False)),
            "pii_count": privacy.get("pii_findings_count", 0),
            "row_count": ps.get("row_count"),
            "has_dataset": bool(ps.get("has_dataset", False)),
            "poll_hint": (
                f"Processing complete. Use get_extraction_result({execution_id}) "
                "to retrieve structured fields and quality details."
            ),
        }

    # Unknown status — pass through
    return {"job_id": job_id, "status": status}

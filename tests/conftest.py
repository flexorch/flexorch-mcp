"""Test fixtures for flexorch-mcp.

Uses respx to intercept httpx calls — no real HTTP requests are made.
Response shapes match the actual FlexOrch API (envelope + nested summaries).
"""
from __future__ import annotations

import pytest
import respx
import httpx

_BASE = "https://api.flexorch.com/v1"

# -------------------------------------------------------------------
# Shared response fixtures
# -------------------------------------------------------------------

_JOB_COMPLETED = {
    "status": "success",
    "data": {
        "id": 1001,
        "job_type": "data_process",
        "status": "completed",
        "result_meta": {},
        "error": None,
        "processing_summary": {
            "execution_id": 501,
            "quality": {"grade": "A", "score": 91.0, "warnings": []},
            "privacy": {"pii_findings_count": 2, "privacy_applied": True, "masked_record_count": 2},
            "row_count": 12,
            "has_dataset": False,
        },
    },
    "error": None,
}

_JOB_RUNNING = {
    "status": "success",
    "data": {
        "id": 1002,
        "job_type": "data_process",
        "status": "running",
        "result_meta": {"pipeline_stage": "privacy"},
        "error": None,
    },
    "error": None,
}

_JOB_FAILED = {
    "status": "success",
    "data": {
        "id": 1003,
        "job_type": "data_process",
        "status": "failed",
        "result_meta": {},
        "error": None,
        "execution_summary": {
            "execution_id": 503,
            "status": "failed",
            "failure_reason": "UNSUPPORTED_FILE",
            "privacy": {"pii_findings_count": 0, "privacy_applied": False, "masked_record_count": 0},
        },
    },
    "error": None,
}

_JOB_DATASET_BUILD_COMPLETED = {
    "status": "success",
    "data": {
        "id": 1004,
        "job_type": "dataset_build",
        "status": "completed",
        "result_meta": {},
        "error": None,
        "dataset_summary": {
            "dataset_id": 89,
            "name": "q1_invoices",
            "slug": "q1-invoices",
            "status": "ready",
            "version": 1,
            "row_count": 12,
        },
    },
    "error": None,
}

_EXECUTION_NO_DATASET = {
    "status": "success",
    "data": {
        "id": 501,
        "status": "completed",
        "result_meta": {
            "document_type": "invoice",
            "detected_language": "tr",
            "grade": "A",
            "score": 91.0,
            "warnings": [],
            "privacy_applied": True,
            "pii_findings_count": 2,
        },
        "privacy": {
            "pii_findings_count": 2,
            "privacy_applied": True,
            "masked_record_count": 2,
        },
        "output_summary": {
            "row_count": 1,
            "column_count": 5,
            "columns": ["invoice_number", "vendor_name", "total_amount", "currency", "due_date"],
            "pii_type_summary": {"email": 1, "national_id_tr": 1},
        },
        "records": [],
        "dataset": None,
    },
    "error": None,
}

_EXECUTION_WITH_DATASET = {
    "status": "success",
    "data": {
        "id": 502,
        "status": "completed",
        "result_meta": {
            "document_type": "invoice",
            "detected_language": "tr",
            "grade": "A",
            "score": 91.0,
            "warnings": [],
            "privacy_applied": True,
            "pii_findings_count": 1,
        },
        "privacy": {"pii_findings_count": 1, "privacy_applied": True, "masked_record_count": 1},
        "output_summary": {
            "row_count": 1,
            "column_count": 4,
            "columns": ["invoice_number", "vendor_name", "total_amount", "currency"],
            "pii_type_summary": {"name": 1},
        },
        "records": [
            {
                "invoice_number": "FTR-2024-001",
                "vendor_name": "[MASKED_NAME]",
                "total_amount": 1487.50,
                "currency": "TRY",
            }
        ],
        "dataset": {"id": 89, "name": "q1_invoices", "slug": "q1-invoices", "status": "ready", "row_count": 1},
    },
    "error": None,
}

_DATASET_ROWS = {
    "status": "success",
    "data": {
        "dataset_id": 89,
        "dataset_name": "q1_invoices",
        "dataset_slug": "q1-invoices",
        "columns": ["invoice_number", "vendor_name", "total_amount", "currency"],
        "pagination": {"page": 1, "page_size": 1, "total_rows": 1, "filtered_total": 1, "returned_rows": 1, "has_next": False},
        "query": None,
        "rows": [
            {
                "invoice_number": "FTR-2024-001",
                "vendor_name": "[MASKED_NAME]",
                "total_amount": 1487.50,
                "currency": "TRY",
            }
        ],
    },
    "error": None,
}


@pytest.fixture
def mock_api():
    """Activate respx mock router for all FlexOrch API endpoints."""
    with respx.mock(base_url=_BASE, assert_all_called=False) as router:
        # POST /data-process/async
        router.post("/data-process/async").mock(
            return_value=httpx.Response(
                202,
                json={
                    "status": "accepted",
                    "data": {
                        "accepted": 1,
                        "rejected": [],
                        "jobs": [{"filename": "invoice.pdf", "job_id": 1001, "status": "queued"}],
                    },
                    "error": None,
                },
            )
        )

        # GET /jobs/{id}
        router.get("/jobs/1001").mock(return_value=httpx.Response(200, json=_JOB_COMPLETED))
        router.get("/jobs/1002").mock(return_value=httpx.Response(200, json=_JOB_RUNNING))
        router.get("/jobs/1003").mock(return_value=httpx.Response(200, json=_JOB_FAILED))
        router.get("/jobs/1004").mock(return_value=httpx.Response(200, json=_JOB_DATASET_BUILD_COMPLETED))

        # GET /executions/{id}
        router.get("/executions/501").mock(return_value=httpx.Response(200, json=_EXECUTION_NO_DATASET))
        router.get("/executions/502").mock(return_value=httpx.Response(200, json=_EXECUTION_WITH_DATASET))

        # GET /datasets/89/rows
        router.get("/datasets/89/rows").mock(return_value=httpx.Response(200, json=_DATASET_ROWS))

        # POST /datasets/build-from-execution/501
        router.post("/datasets/build-from-execution/501").mock(
            return_value=httpx.Response(
                202,
                json={
                    "status": "accepted",
                    "data": {
                        "job_id": 1004,
                        "job_type": "dataset_build",
                        "status": "queued",
                        "reference_id": 89,
                    },
                    "meta": {"poll": "/v1/jobs/1004"},
                    "error": None,
                },
            )
        )

        # POST /search
        router.post("/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "results": [
                            {
                                "chunk_id": "abc-123",
                                "dataset_id": 89,
                                "dataset_name": "q1_invoices",
                                "score": 0.94,
                                "text": "Sample invoice text...",
                                "metadata": {
                                    "doc_type": "invoice",
                                    "language": "tr",
                                    "quality_grade": "A",
                                    "mode": "structured",
                                },
                            }
                        ],
                        "query": "invoice",
                        "total_results": 1,
                        "mode": "structured",
                        "alpha": None,
                    },
                    "error": None,
                },
            )
        )

        # GET /datasets/89/export/jsonl
        router.get("/datasets/89/export/jsonl").mock(
            return_value=httpx.Response(
                200,
                content=b'{"invoice_number":"FTR-2024-001","total_amount":1487.5}\n',
                headers={"Content-Type": "application/x-ndjson", "Content-Disposition": 'attachment; filename="q1-invoices.jsonl"'},
            )
        )

        # GET /datasets/89/export/csv
        router.get("/datasets/89/export/csv").mock(
            return_value=httpx.Response(
                200,
                content=b"invoice_number,total_amount\nFTR-2024-001,1487.5\n",
                headers={"Content-Type": "text/csv"},
            )
        )

        # GET /usage/current  — for --check
        router.get("/usage/current").mock(
            return_value=httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "plan": "starter",
                        "credits_used": 42,
                        "credits_limit": 1200,
                        "credits_remaining": 1158,
                        "reset_at": "2026-07-01T00:00:00Z",
                        "period_start": "2026-06-01T00:00:00Z",
                        "period_end": "2026-07-01T00:00:00Z",
                    },
                    "error": None,
                },
            )
        )

        # Error scenarios
        router.get("/jobs/9999").mock(
            return_value=httpx.Response(
                401,
                json={"error": {"code": "INVALID_API_KEY", "message": "Invalid API key"}},
            )
        )
        router.get("/jobs/8888").mock(
            return_value=httpx.Response(
                402,
                json={"error": {"code": "QUOTA_EXCEEDED", "message": "Quota exceeded"}},
            )
        )
        router.get("/jobs/7777").mock(
            return_value=httpx.Response(
                429,
                headers={"Retry-After": "30"},
                json={"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Rate limit"}},
            )
        )

        yield router

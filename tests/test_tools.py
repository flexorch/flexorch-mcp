"""Unit tests for Tool 1–6: process_document, get_job_status, get_extraction_result, build_dataset, search_documents, export_dataset."""
from __future__ import annotations

import pytest
import respx
import httpx

from flexorch_mcp.client import FlexOrchMCPClient
from flexorch_mcp.tools import process as tools_process
from flexorch_mcp.tools import status as tools_status
from flexorch_mcp.tools import result as tools_result
from flexorch_mcp.tools import build as tools_build
from flexorch_mcp.tools import search as tools_search
from flexorch_mcp.tools import export as tools_export

_BASE = "https://api.flexorch.com/v1"
_TEST_KEY = "dfx_testkey_000000000"


@pytest.fixture
def client():
    return FlexOrchMCPClient(_TEST_KEY)


# ===========================================================================
# Tool 1: process_document
# ===========================================================================


class TestProcessDocument:
    @pytest.mark.asyncio
    async def test_valid_url_returns_job_id(self, client, mock_api):
        with respx.mock(assert_all_called=False) as outer:
            # Mock the external file download
            outer.get("https://example.com/invoice.pdf").mock(
                return_value=httpx.Response(
                    200,
                    content=b"%PDF-1.4 fake content",
                    headers={"Content-Type": "application/pdf"},
                )
            )
            result = await tools_process.run(client, "https://example.com/invoice.pdf")

        assert result["job_id"] == 1001
        assert result["status"] == "queued"
        assert "get_job_status(1001)" in result["poll_hint"]

    @pytest.mark.asyncio
    async def test_invalid_scheme_returns_error(self, client, mock_api):
        result = await tools_process.run(client, "file:///etc/passwd")
        assert result.get("isError") is True
        assert "http" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_file_too_large_returns_error(self, client, mock_api):
        big_content = b"x" * (51 * 1024 * 1024)  # 51 MB
        with respx.mock(assert_all_called=False) as outer:
            outer.get("https://example.com/big.pdf").mock(
                return_value=httpx.Response(
                    200,
                    content=big_content,
                    headers={"Content-Type": "application/pdf"},
                )
            )
            result = await tools_process.run(client, "https://example.com/big.pdf")

        assert result.get("isError") is True
        assert "50 MB" in result["error"]

    @pytest.mark.asyncio
    async def test_download_failure_returns_error(self, client, mock_api):
        with respx.mock(assert_all_called=False) as outer:
            outer.get("https://example.com/not-found.pdf").mock(
                return_value=httpx.Response(404)
            )
            result = await tools_process.run(client, "https://example.com/not-found.pdf")

        assert result.get("isError") is True
        assert "accessible" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_api_error_propagates(self, client):
        with respx.mock(base_url=_BASE, assert_all_called=False) as router:
            router.post("/data-process/async").mock(
                return_value=httpx.Response(
                    402,
                    json={"error": {"code": "QUOTA_EXCEEDED", "message": "Quota exceeded"}},
                )
            )
            with respx.mock(assert_all_called=False) as outer:
                outer.get("https://example.com/invoice.pdf").mock(
                    return_value=httpx.Response(200, content=b"data", headers={"Content-Type": "application/pdf"})
                )
                result = await tools_process.run(client, "https://example.com/invoice.pdf")

        assert result.get("isError") is True
        assert "app.flexorch.com" in result["error"]


# ===========================================================================
# Tool 2: get_job_status
# ===========================================================================


class TestGetJobStatus:
    @pytest.mark.asyncio
    async def test_completed_data_process_job(self, client, mock_api):
        result = await tools_status.run(client, 1001)
        assert result["status"] == "completed"
        assert result["execution_id"] == 501
        assert result["quality_grade"] == "A"
        assert result["quality_score"] == 91.0
        assert result["pii_found"] is True
        assert result["pii_masked"] is True
        assert result["pii_count"] == 2
        assert result["row_count"] == 12
        assert "get_extraction_result(501)" in result["poll_hint"]

    @pytest.mark.asyncio
    async def test_running_job_with_stage(self, client, mock_api):
        result = await tools_status.run(client, 1002)
        assert result["status"] == "running"
        assert result["stage"] == "privacy"

    @pytest.mark.asyncio
    async def test_failed_job_returns_reason(self, client, mock_api):
        result = await tools_status.run(client, 1003)
        assert result["status"] == "failed"
        assert result["reason"] == "UNSUPPORTED_FILE"

    @pytest.mark.asyncio
    async def test_dataset_build_completed(self, client, mock_api):
        result = await tools_status.run(client, 1004)
        assert result["status"] == "completed"
        assert result["dataset_id"] == 89
        assert result["dataset_name"] == "q1_invoices"
        assert result["row_count"] == 12
        assert "export_dataset" in result["poll_hint"]

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_error(self, client, mock_api):
        result = await tools_status.run(client, 9999)
        assert result.get("isError") is True
        assert "FLEXORCH_API_KEY" in result["error"]

    @pytest.mark.asyncio
    async def test_quota_exceeded_returns_error(self, client, mock_api):
        result = await tools_status.run(client, 8888)
        assert result.get("isError") is True
        assert "app.flexorch.com" in result["error"]

    @pytest.mark.asyncio
    async def test_rate_limit_includes_retry_after(self, client, mock_api):
        result = await tools_status.run(client, 7777)
        assert result.get("isError") is True
        assert "30" in result["error"]


# ===========================================================================
# Tool 3: get_extraction_result
# ===========================================================================


class TestGetExtractionResult:
    @pytest.mark.asyncio
    async def test_execution_without_records_returns_metadata(self, client, mock_api):
        result = await tools_result.run(client, 501)
        assert result["execution_id"] == 501
        assert result["document_type"] == "invoice"
        assert result["detected_language"] == "tr"
        assert result["quality"]["grade"] == "A"
        assert result["quality"]["score"] == 91.0
        assert result["privacy"]["pii_findings_count"] == 2
        assert "invoice_number" in result["columns"]
        assert "fields" not in result
        assert "fields_hint" in result
        assert "build_dataset" in result["fields_hint"]

    @pytest.mark.asyncio
    async def test_execution_with_records_returns_all_rows(self, client, mock_api):
        result = await tools_result.run(client, 502)
        assert result["document_type"] == "invoice"
        assert "fields" in result
        # fields is a list of records, not a dict
        assert isinstance(result["fields"], list)
        assert len(result["fields"]) == 1
        first = result["fields"][0]
        assert first["invoice_number"] == "FTR-2024-001"
        assert first["vendor_name"] == "[MASKED_NAME]"
        assert first["total_amount"] == 1487.50
        # No second HTTP call needed — came directly from execution response
        assert "has_more" not in result

    @pytest.mark.asyncio
    async def test_masked_fields_never_contain_raw_pii(self, client, mock_api):
        result = await tools_result.run(client, 502)
        for row in result.get("fields", []):
            for value in row.values():
                if isinstance(value, str) and "MASKED" in value:
                    assert value.startswith("[MASKED_")

    @pytest.mark.asyncio
    async def test_api_error_returns_error_dict(self, client):
        with respx.mock(base_url=_BASE, assert_all_called=False) as router:
            router.get("/executions/9999").mock(
                return_value=httpx.Response(
                    401,
                    json={"error": {"code": "INVALID_API_KEY", "message": "Invalid key"}},
                )
            )
            result = await tools_result.run(client, 9999)

        assert result.get("isError") is True
        assert "FLEXORCH_API_KEY" in result["error"]


# ===========================================================================
# Tool 4: build_dataset
# ===========================================================================


class TestBuildDataset:
    @pytest.mark.asyncio
    async def test_returns_job_id_and_poll_hint(self, client, mock_api):
        result = await tools_build.run(client, 501)
        assert result["job_id"] == 1004
        assert result["status"] == "queued"
        assert "get_job_status(1004)" in result["poll_hint"]
        assert "export_dataset" in result["poll_hint"]

    @pytest.mark.asyncio
    async def test_with_name_passes_payload(self, client, mock_api):
        result = await tools_build.run(client, 501, name="my_dataset")
        assert result["job_id"] == 1004

    @pytest.mark.asyncio
    async def test_api_error_returns_error_dict(self, client):
        with respx.mock(base_url=_BASE, assert_all_called=False) as router:
            router.post("/datasets/build-from-execution/9999").mock(
                return_value=httpx.Response(
                    402,
                    json={"error": {"code": "QUOTA_EXCEEDED", "message": "Quota exceeded"}},
                )
            )
            result = await tools_build.run(client, 9999)

        assert result.get("isError") is True
        assert "app.flexorch.com" in result["error"]


# ===========================================================================
# Tool 5: search_documents
# ===========================================================================


class TestSearchDocuments:
    @pytest.mark.asyncio
    async def test_returns_results_and_total(self, client, mock_api):
        result = await tools_search.run(client, "invoice")
        assert result["total_results"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["score"] == 0.94
        assert result["results"][0]["dataset_id"] == 89
        assert result["query"] == "invoice"

    @pytest.mark.asyncio
    async def test_empty_query_returns_error(self, client, mock_api):
        result = await tools_search.run(client, "   ")
        assert result.get("isError") is True
        assert "empty" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_mode_returns_error(self, client, mock_api):
        result = await tools_search.run(client, "test", mode="magic")
        assert result.get("isError") is True
        assert "mode" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_top_k_clamped_to_max(self, client, mock_api):
        # Should not raise even with out-of-range top_k
        result = await tools_search.run(client, "invoice", top_k=999)
        assert "isError" not in result or result.get("isError") is not True

    @pytest.mark.asyncio
    async def test_plan_upgrade_error_propagates(self, client):
        with respx.mock(base_url=_BASE, assert_all_called=False) as router:
            router.post("/search").mock(
                return_value=httpx.Response(
                    403,
                    json={"error": {"code": "PLAN_UPGRADE_REQUIRED", "message": "Pro plan required"}},
                )
            )
            result = await tools_search.run(client, "test query", mode="semantic")

        assert result.get("isError") is True
        assert "Pro" in result["error"]


# ===========================================================================
# Tool 6: export_dataset
# ===========================================================================


class TestExportDataset:
    @pytest.mark.asyncio
    async def test_jsonl_export_returns_content(self, client, mock_api):
        result = await tools_export.run(client, 89, "jsonl")
        assert result["dataset_id"] == 89
        assert result["format"] == "jsonl"
        assert "FTR-2024-001" in result["content"]
        assert result["byte_count"] > 0
        assert result["filename"] == "q1-invoices.jsonl"

    @pytest.mark.asyncio
    async def test_csv_export_returns_content(self, client, mock_api):
        result = await tools_export.run(client, 89, "csv")
        assert "invoice_number" in result["content"]
        assert result["format"] == "csv"

    @pytest.mark.asyncio
    async def test_binary_format_returns_error(self, client, mock_api):
        result = await tools_export.run(client, 89, "parquet")
        assert result.get("isError") is True
        assert "binary" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_format_returns_error(self, client, mock_api):
        result = await tools_export.run(client, 89, "xlsx")
        assert result.get("isError") is True
        assert "Unsupported format" in result["error"]

    @pytest.mark.asyncio
    async def test_api_error_returns_error_dict(self, client):
        with respx.mock(base_url=_BASE, assert_all_called=False) as router:
            router.get("/datasets/9999/export/jsonl").mock(
                return_value=httpx.Response(
                    404,
                    json={"error": {"code": "NOT_FOUND", "message": "Dataset not found"}},
                )
            )
            result = await tools_export.run(client, 9999, "jsonl")

        assert result.get("isError") is True
        assert "not found" in result["error"].lower()

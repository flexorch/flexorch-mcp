from __future__ import annotations

FLEXORCH_ERRORS: dict[str, str] = {
    "QUOTA_EXCEEDED": (
        "Credit quota exceeded. Upgrade your FlexOrch plan at app.flexorch.com/settings"
    ),
    "TRIAL_EXPIRED": (
        "Trial period ended. Activate a paid plan at app.flexorch.com/settings to continue."
    ),
    "RATE_LIMIT_EXCEEDED": "Rate limit reached. Retry in {retry_after} seconds.",
    "UNSUPPORTED_FILE": (
        "Unsupported file type. Supported: PDF, DOCX, TXT, XLSX, HTML, XML, EML, JPG, PNG, TIFF"
    ),
    "PLAN_UPGRADE_REQUIRED": (
        "This feature requires a Pro plan or above. Upgrade at app.flexorch.com/settings"
    ),
    "INVALID_API_KEY": (
        "Invalid API key. Check your FLEXORCH_API_KEY environment variable."
    ),
    "UNAUTHORIZED": (
        "Authentication failed. Check your FLEXORCH_API_KEY environment variable."
    ),
    "FILE_TOO_LARGE": "File exceeds size limit. Max 50 MB.",
    "NOT_FOUND": (
        "Resource not found. Verify the job_id, execution_id, or dataset_id is correct."
    ),
    "PROCESSING_FAILED": (
        "Document processing failed. Check the file format and content, then retry."
    ),
    "VALIDATION_ERROR": (
        "Invalid request parameters. Check the values passed to this tool."
    ),
}

_DEFAULT_ERROR = "An error occurred. Visit app.flexorch.com for support."


def map_api_error(code: str, retry_after: int | None = None) -> str:
    template = FLEXORCH_ERRORS.get(code, _DEFAULT_ERROR)
    if code == "RATE_LIMIT_EXCEEDED" and retry_after is not None:
        return template.format(retry_after=retry_after)
    return template


class FlexOrchAPIError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 0,
        error_code: str = "",
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.retry_after = retry_after


class DownloadError(Exception):
    pass


class FileTooLargeError(Exception):
    pass

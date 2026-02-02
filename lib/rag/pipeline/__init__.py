"""Unified detection pipeline data models, types, and runner."""

from lib.rag.pipeline.models import (
    BlockClassification,
    ContentType,
    DetectionResult,
    DetectorScope,
    DocumentOutput,
)

__all__ = [
    "ContentType",
    "DetectorScope",
    "BlockClassification",
    "DetectionResult",
    "DocumentOutput",
    "run_document_pipeline",
]


def __getattr__(name: str):
    """Lazy import for runner to avoid circular imports."""
    if name == "run_document_pipeline":
        from lib.rag.pipeline.runner import run_document_pipeline

        return run_document_pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

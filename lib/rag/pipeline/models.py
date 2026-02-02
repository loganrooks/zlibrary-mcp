"""Data models for the unified detection pipeline.

Defines the contract between detectors, compositor, and writer.
All types use stdlib only (dataclasses, enum, typing, pathlib, json).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ContentType(Enum):
    """Classification of text block content."""

    BODY = "body"
    FOOTNOTE = "footnote"
    ENDNOTE = "endnote"
    MARGIN = "margin"
    HEADING = "heading"
    PAGE_NUMBER = "page_number"
    TOC = "toc"
    FRONT_MATTER = "front_matter"
    HEADER = "header"
    FOOTER = "footer"
    CITATION = "citation"


class DetectorScope(Enum):
    """Whether a detector operates on individual pages or the whole document."""

    PAGE = "page"
    DOCUMENT = "document"


@dataclass
class BlockClassification:
    """A classified text block with spatial and confidence information."""

    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    content_type: ContentType
    text: str
    confidence: float = 1.0
    detector_name: str = ""
    page_num: int = 0  # 1-indexed
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectionResult:
    """Output from a single detector run."""

    detector_name: str
    classifications: List[BlockClassification] = field(default_factory=list)
    page_num: int = 0  # 1-indexed, 0 for document-level
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentOutput:
    """Final processed document ready for output.

    Contains separated content streams and metadata.
    """

    body_text: str = ""
    footnotes: Optional[str] = None
    endnotes: Optional[str] = None
    citations: Optional[str] = None
    document_metadata: Optional[dict] = None
    processing_metadata: Optional[dict] = None

    def write_files(
        self, base_path: Path, output_format: str = "markdown"
    ) -> Dict[str, Path]:
        """Write document content to separate files.

        Args:
            base_path: Path to the source document (used for stem).
            output_format: Output format, currently only 'markdown'.

        Returns:
            Dict mapping content type name to written file path.
        """
        base_path = Path(base_path)
        stem = base_path.stem
        out_dir = base_path.parent
        ext = ".md" if output_format == "markdown" else ".txt"
        written: Dict[str, Path] = {}

        # Body text (always written)
        body_path = out_dir / f"{stem}{ext}"
        body_path.write_text(self.body_text, encoding="utf-8")
        written["body"] = body_path

        # Optional content streams
        for name, content in [
            ("footnotes", self.footnotes),
            ("endnotes", self.endnotes),
            ("citations", self.citations),
        ]:
            if content:
                p = out_dir / f"{stem}_{name}{ext}"
                p.write_text(content, encoding="utf-8")
                written[name] = p

        # Metadata (always written)
        meta = {
            "document_metadata": self.document_metadata,
            "processing_metadata": self.processing_metadata,
        }
        meta_path = out_dir / f"{stem}_meta.json"
        meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
        written["metadata"] = meta_path

        return written

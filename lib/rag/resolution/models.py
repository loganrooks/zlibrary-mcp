"""Data models for adaptive resolution DPI decisions."""

from dataclasses import dataclass, field


@dataclass
class DPIDecision:
    """Result of DPI analysis for a page or region."""

    dpi: int
    confidence: float  # 0.0-1.0
    reason: str
    font_size_pt: float
    estimated_pixel_height: float


@dataclass
class RegionDPI:
    """DPI decision for a specific region of a page."""

    bbox: tuple[float, float, float, float]
    dpi_decision: DPIDecision
    region_type: str


@dataclass
class PageAnalysis:
    """Font analysis results for a single page."""

    page_num: int
    dominant_size: float
    min_size: float
    max_size: float
    has_small_text: bool
    page_dpi: DPIDecision
    regions: list[RegionDPI] = field(default_factory=list)

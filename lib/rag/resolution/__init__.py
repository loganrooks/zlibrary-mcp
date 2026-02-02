"""Adaptive resolution pipeline for optimal DPI selection."""

from .analyzer import analyze_document_fonts, analyze_page_fonts, compute_optimal_dpi
from .models import DPIDecision, PageAnalysis, RegionDPI
from .renderer import AdaptiveRenderResult, render_page_adaptive, render_region

__all__ = [
    "AdaptiveRenderResult",
    "DPIDecision",
    "PageAnalysis",
    "RegionDPI",
    "compute_optimal_dpi",
    "analyze_page_fonts",
    "analyze_document_fonts",
    "render_page_adaptive",
    "render_region",
]

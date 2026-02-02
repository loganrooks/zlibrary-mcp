"""Adaptive resolution pipeline for optimal DPI selection."""

from .analyzer import analyze_document_fonts, analyze_page_fonts, compute_optimal_dpi
from .models import DPIDecision, PageAnalysis, RegionDPI

__all__ = [
    "DPIDecision",
    "PageAnalysis",
    "RegionDPI",
    "compute_optimal_dpi",
    "analyze_page_fonts",
    "analyze_document_fonts",
]

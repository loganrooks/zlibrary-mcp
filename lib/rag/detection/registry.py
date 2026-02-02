"""Detector registry with decorator-based registration and priority ordering.

Usage:
    @register_detector('footnote', priority=10, scope=DetectorScope.PAGE)
    def detect_footnotes(page, page_num, context):
        ...

    detectors = get_registered_detectors(scope=DetectorScope.PAGE)
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from lib.rag.pipeline.models import DetectorScope

_DETECTOR_REGISTRY: Dict[str, dict] = {}


def register_detector(
    name: str,
    priority: int = 50,
    scope: DetectorScope = DetectorScope.PAGE,
) -> Callable:
    """Decorator to register a detector function.

    Args:
        name: Unique detector name.
        priority: Execution priority (lower runs first).
        scope: PAGE for per-page detectors, DOCUMENT for whole-document.

    Returns:
        The original function, unmodified.

    Raises:
        ValueError: If a detector with the same name is already registered.
    """

    def decorator(func: Callable) -> Callable:
        if name in _DETECTOR_REGISTRY:
            raise ValueError(f"Detector '{name}' is already registered")
        _DETECTOR_REGISTRY[name] = {
            "func": func,
            "priority": priority,
            "scope": scope,
            "name": name,
        }
        return func

    return decorator


def get_registered_detectors(
    scope: Optional[DetectorScope] = None,
) -> List[Dict[str, Any]]:
    """Return registered detectors sorted by priority (ascending).

    Args:
        scope: If provided, filter to only detectors with this scope.

    Returns:
        List of detector entries sorted by priority (lower first).
    """
    entries = list(_DETECTOR_REGISTRY.values())
    if scope is not None:
        entries = [e for e in entries if e["scope"] == scope]
    return sorted(entries, key=lambda e: e["priority"])


def clear_registry() -> None:
    """Clear all registered detectors. For testing only."""
    _DETECTOR_REGISTRY.clear()

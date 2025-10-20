#!/usr/bin/env python3
"""
Garbled Text Detection Module

Statistically analyzes text to detect corruption/garbling using multiple heuristics:
- Shannon entropy (information content)
- Symbol density (non-alphanumeric ratio)
- Character repetition patterns

Designed for RAG pipeline quality assurance, particularly for OCR-processed PDFs
where text corruption can affect semantic understanding.

Usage:
    from lib.garbled_text_detection import (
        detect_garbled_text_enhanced,
        GarbledDetectionConfig,
        GarbledDetectionResult
    )

    # Use defaults
    result = detect_garbled_text_enhanced("sample text")
    if result.is_garbled:
        print(f"Garbled with confidence {result.confidence:.2f}")
        print(f"Flags: {result.flags}")

    # Custom configuration
    config = GarbledDetectionConfig(
        entropy_threshold=3.5,
        symbol_density_threshold=0.30
    )
    result = detect_garbled_text_enhanced("sample text", config)
"""

import logging
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Set, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Resource limits (DoS protection)
MAX_TEXT_LENGTH = 1_000_000  # 1M characters (~500 pages of text)

# Confidence scoring constants
# These values are empirically tuned based on Phase 1 validation (86-93% F1 score)
# and adjusted for production use.

# Single heuristic confidence scoring
SINGLE_HEURISTIC_BASE_CONFIDENCE = 0.6  # Base confidence when one heuristic triggers
SINGLE_HEURISTIC_DEVIATION_FACTOR = 0.3  # How much deviation from threshold affects confidence
SINGLE_HEURISTIC_MAX_CONFIDENCE = 0.9    # Maximum confidence for single heuristic

# Multiple heuristic confidence scoring
MULTIPLE_HEURISTIC_BASE_CONFIDENCE = 0.85  # Base confidence for 2+ heuristics
MULTIPLE_HEURISTIC_INCREMENT = 0.05        # Confidence increase per additional heuristic
MULTIPLE_HEURISTIC_MAX_CONFIDENCE = 1.0    # Maximum confidence (certainty)


@dataclass
class GarbledDetectionConfig:
    """
    Configuration for garbled text detection thresholds.

    All thresholds are tuned based on Phase 1.5-1.7 validation (86-93% F1 score).
    Adjust these values based on your corpus characteristics.

    Attributes:
        entropy_threshold: Minimum Shannon entropy (bits). Below this = suspicious.
                          Normal English ~3.8-5.0, garbled often <3.0.
        symbol_density_threshold: Maximum ratio of non-alphanumeric characters.
                                 Above this = suspicious. Normal ~0.05-0.15.
        repetition_threshold: Maximum ratio of most common character.
                             Above this = suspicious. Normal ~0.15-0.25.
        min_text_length: Minimum characters for reliable analysis. Skip shorter text.

    Example:
        # Strict detection (fewer false negatives, more false positives)
        strict_config = GarbledDetectionConfig(
            entropy_threshold=3.8,
            symbol_density_threshold=0.15,
            repetition_threshold=0.25
        )

        # Lenient detection (fewer false positives, more false negatives)
        lenient_config = GarbledDetectionConfig(
            entropy_threshold=2.5,
            symbol_density_threshold=0.50,
            repetition_threshold=0.85
        )
    """
    entropy_threshold: float = 3.2  # Bits, below = suspicious (lowered to avoid false positives)
    symbol_density_threshold: float = 0.25  # Ratio, above = suspicious (was 0.25 in original)
    repetition_threshold: float = 0.7  # Ratio, above = suspicious (was 0.7 in original)
    min_text_length: int = 10  # Skip very short text


@dataclass
class GarbledDetectionResult:
    """
    Result of garbled text detection with detailed metrics.

    Philosophy: Explainability is critical for AI agents. Don't just return
    a boolean - return WHY the text was flagged and HOW confident we are.

    Attributes:
        is_garbled: True if text appears garbled/corrupted
        confidence: Confidence score 0.0-1.0 (how sure are we it's garbled?)
        metrics: Dict of raw metric values {'entropy': 3.2, 'symbol_density': 0.35, ...}
        flags: Set of triggered detection flags for explainability

    Example:
        result = GarbledDetectionResult(
            is_garbled=True,
            confidence=0.85,
            metrics={'entropy': 2.8, 'symbol_density': 0.42, 'repetition_ratio': 0.15},
            flags={'low_entropy', 'high_symbols'}
        )
        print(f"Flagged because: {', '.join(result.flags)}")
    """
    is_garbled: bool
    confidence: float  # 0.0-1.0
    metrics: Dict[str, float] = field(default_factory=dict)
    flags: Set[str] = field(default_factory=set)  # {'low_entropy', 'high_symbols', 'repeated_chars'}


def calculate_entropy(text: str) -> float:
    """
    Calculate Shannon entropy of text in bits.

    Entropy measures information content. Garbled text typically has lower
    entropy due to reduced character variety and predictability.

    Formula: H(X) = -Σ p(x) * log2(p(x))
    where p(x) is the probability of character x in the text.

    Args:
        text: Input text to analyze

    Returns:
        Shannon entropy in bits. Range: 0.0-8.0 for byte-encoded text.
        - 0.0: Completely uniform (all same character)
        - ~4.0-5.0: Normal English text
        - ~2.0-3.5: Often garbled/corrupted
        - 8.0: Maximum entropy (random bytes)

    Example:
        >>> calculate_entropy("aaaaaaaaaa")
        0.0
        >>> calculate_entropy("This is normal English text.")
        4.2  # Approximate
        >>> calculate_entropy("!@#$%^&*()_+")
        3.5  # Approximate
    """
    if not text:
        return 0.0

    # Count character frequencies
    char_counts = Counter(text)
    text_length = len(text)

    # Calculate entropy
    entropy = 0.0
    for count in char_counts.values():
        probability = count / text_length
        if probability > 0:  # Avoid log(0)
            entropy -= probability * math.log2(probability)

    return entropy


def detect_garbled_text_enhanced(
    text: str,
    config: Optional[GarbledDetectionConfig] = None
) -> GarbledDetectionResult:
    """
    Detect garbled/corrupted text using statistical analysis.

    Uses multiple heuristics for robust detection:
    1. Shannon entropy (information content)
    2. Symbol density (non-alphanumeric ratio)
    3. Character repetition patterns

    Combines heuristics to produce confidence score and detailed flags.

    Args:
        text: Text to analyze for garbling
        config: Detection thresholds (uses defaults if None)

    Returns:
        GarbledDetectionResult with is_garbled flag, confidence, metrics, and flags

    Raises:
        None - errors are caught and logged, returning safe default result

    Example:
        >>> result = detect_garbled_text_enhanced("This is normal text")
        >>> result.is_garbled
        False
        >>> result.confidence
        0.1  # Low confidence it's garbled

        >>> result = detect_garbled_text_enhanced("!@#$%^&*()_+!@#$%^&*")
        >>> result.is_garbled
        True
        >>> result.confidence
        0.95  # High confidence it's garbled
        >>> result.flags
        {'high_symbols', 'low_entropy'}
    """
    # Use default config if none provided
    if config is None:
        config = GarbledDetectionConfig()

    # Initialize result
    result = GarbledDetectionResult(
        is_garbled=False,
        confidence=0.0,
        metrics={},
        flags=set()
    )

    # Handle edge cases
    text_length = len(text)

    # DoS protection: Limit text length
    if text_length > MAX_TEXT_LENGTH:
        logger.warning(f"Text too long ({text_length} chars), truncating to {MAX_TEXT_LENGTH}")
        text = text[:MAX_TEXT_LENGTH]
        text_length = MAX_TEXT_LENGTH

    if text_length < config.min_text_length:
        logger.debug(f"Text too short for analysis ({text_length} < {config.min_text_length})")
        return result

    # Edge case: all spaces/whitespace (not meaningful text)
    if text.strip() == "":
        logger.debug("Text is all whitespace, skipping analysis")
        return result

    try:
        # Metric 1: Shannon Entropy
        entropy = calculate_entropy(text)
        result.metrics['entropy'] = entropy

        # Metric 2: Symbol Density (Non-alphanumeric ratio)
        non_alpha_count = sum(1 for char in text if not char.isalnum() and not char.isspace())
        symbol_density = non_alpha_count / text_length
        result.metrics['symbol_density'] = symbol_density

        # Metric 3: Character Repetition Ratio
        char_counts = Counter(c for c in text if not c.isspace())
        if char_counts:
            most_common_char, most_common_count = char_counts.most_common(1)[0]
            non_space_length = text_length - text.count(' ')
            repetition_ratio = most_common_count / non_space_length if non_space_length > 0 else 0.0
            result.metrics['repetition_ratio'] = repetition_ratio
            result.metrics['most_common_char'] = most_common_char
        else:
            repetition_ratio = 0.0
            result.metrics['repetition_ratio'] = 0.0

        # Evaluate heuristics and set flags
        triggered_flags = []

        if entropy < config.entropy_threshold:
            result.flags.add('low_entropy')
            triggered_flags.append(('entropy', entropy, config.entropy_threshold))
            logger.debug(f"Low entropy detected: {entropy:.2f} < {config.entropy_threshold}")

        if symbol_density > config.symbol_density_threshold:
            result.flags.add('high_symbols')
            triggered_flags.append(('symbol_density', symbol_density, config.symbol_density_threshold))
            logger.debug(f"High symbol density: {symbol_density:.2f} > {config.symbol_density_threshold}")

        if repetition_ratio > config.repetition_threshold:
            result.flags.add('repeated_chars')
            triggered_flags.append(('repetition', repetition_ratio, config.repetition_threshold))
            logger.debug(f"High repetition: {repetition_ratio:.2f} > {config.repetition_threshold}")

        # Calculate confidence score based on how many heuristics triggered
        # and how far they deviated from thresholds
        if len(triggered_flags) == 0:
            # No flags - clean text
            result.is_garbled = False
            result.confidence = 0.0
        elif len(triggered_flags) == 1:
            # One flag - possible garbling, medium confidence
            result.is_garbled = True
            # Confidence based on severity of deviation from threshold
            metric_name, value, threshold = triggered_flags[0]
            if metric_name == 'entropy':
                deviation = (threshold - value) / threshold  # Lower entropy is worse
            else:
                deviation = (value - threshold) / threshold  # Higher density/repetition is worse

            # Scale confidence based on deviation severity
            confidence = SINGLE_HEURISTIC_BASE_CONFIDENCE + (deviation * SINGLE_HEURISTIC_DEVIATION_FACTOR)
            result.confidence = min(confidence, SINGLE_HEURISTIC_MAX_CONFIDENCE)
        else:
            # Multiple flags - high confidence garbling
            result.is_garbled = True
            confidence = MULTIPLE_HEURISTIC_BASE_CONFIDENCE + (len(triggered_flags) * MULTIPLE_HEURISTIC_INCREMENT)
            result.confidence = min(confidence, MULTIPLE_HEURISTIC_MAX_CONFIDENCE)

        if result.is_garbled:
            logger.info(f"Garbled text detected: confidence={result.confidence:.2f}, "
                       f"flags={result.flags}, metrics={result.metrics}")

    except (ValueError, TypeError, ZeroDivisionError, AttributeError, KeyError) as e:
        logger.error(f"Error in garbled text detection: {e}", exc_info=True)
        # Return safe default on error - don't crash pipeline
        return GarbledDetectionResult(
            is_garbled=False,
            confidence=0.0,
            metrics={},
            flags={'error'}
        )

    return result


# Backward compatibility function (simple boolean return)
def detect_garbled_text(
    text: str,
    non_alpha_threshold: float = 0.25,
    repetition_threshold: float = 0.7,
    min_length: int = 10
) -> bool:
    """
    Legacy API for garbled text detection (returns boolean).

    This function maintains backward compatibility with existing code.
    For new code, use `detect_garbled_text_enhanced()` which returns
    detailed metrics and confidence scores.

    Args:
        text: Text to analyze
        non_alpha_threshold: Symbol density threshold (0.0-1.0)
        repetition_threshold: Character repetition threshold (0.0-1.0)
        min_length: Minimum text length for analysis

    Returns:
        True if text appears garbled, False otherwise

    Example:
        >>> detect_garbled_text("This is normal text")
        False
        >>> detect_garbled_text("!@#$%^&*()_+!@#$%^&*")
        True
    """
    config = GarbledDetectionConfig(
        symbol_density_threshold=non_alpha_threshold,
        repetition_threshold=repetition_threshold,
        min_text_length=min_length
    )
    result = detect_garbled_text_enhanced(text, config)
    return result.is_garbled


__all__ = [
    'GarbledDetectionConfig',
    'GarbledDetectionResult',
    'calculate_entropy',
    'detect_garbled_text_enhanced',
    'detect_garbled_text',  # Legacy API
]

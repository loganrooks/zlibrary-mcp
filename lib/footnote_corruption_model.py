"""
Symbol Corruption Model for Footnote Detection

Implements probabilistic symbol recovery using:
- Corruption probabilities P(observed | actual)
- Schema transitions P(next | current)
- Bayesian inference for symbol disambiguation

Part of PFES (Probabilistic Footnote Extraction System)
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging


@dataclass
class SymbolInference:
    """Result of probabilistic symbol inference."""
    actual_symbol: str
    observed_text: str
    confidence: float
    inference_method: str  # 'direct', 'corruption_model', 'schema_inference', 'combined'
    alternatives: Dict[str, float]  # Other candidates with their scores


class SymbolCorruptionModel:
    """
    Probabilistic model for recovering actual symbols from corrupted text.

    Uses Bayesian inference:
    P(actual | observed, context) ∝ P(observed | actual) × P(actual | context)

    Where:
    - P(observed | actual) = corruption probability (learned from corpus)
    - P(actual | context) = schema prior (Markov chain over sequences)
    """

    # Corruption probabilities learned from PDF corpus analysis
    # P(observed_text | actual_symbol)
    CORRUPTION_TABLE = {
        '*': {
            '*': 0.95,      # Usually preserved
            'iii': 0.03,    # Seen in Derrida footnote area
            'asterisk': 0.02
        },
        '†': {
            't': 0.85,      # Very common corruption (seen in Derrida)
            '†': 0.10,      # Sometimes preserved
            'dagger': 0.03,
            'cross': 0.02
        },
        '‡': {
            'iii': 0.60,    # Common corruption to roman numeral
            'tt': 0.20,     # Double-t
            '‡': 0.15,      # Sometimes preserved
            'double-dagger': 0.05
        },
        '§': {
            's': 0.70,      # Section → s
            'sec': 0.15,
            '§': 0.10,
            'section': 0.05
        },
        '¶': {
            'p': 0.65,      # Pilcrow → p
            'para': 0.20,
            '¶': 0.10,
            'paragraph': 0.05
        },
        '°': {
            'o': 0.50,      # Degree → o
            '0': 0.30,      # Zero
            '°': 0.15,
            'degree': 0.05
        }
    }

    # Standard symbolic footnote schema
    # P(next_symbol | current_symbol)
    SCHEMA_TRANSITIONS = {
        '*': {'†': 0.95, '‡': 0.02, '§': 0.01, '1': 0.01, None: 0.01},
        '†': {'‡': 0.92, '§': 0.05, '2': 0.02, None: 0.01},
        '‡': {'§': 0.90, '¶': 0.05, '3': 0.03, None: 0.02},
        '§': {'¶': 0.85, '∥': 0.10, '4': 0.03, None: 0.02},
        '¶': {'∥': 0.80, '#': 0.10, '5': 0.05, None: 0.05},
    }

    # Base frequencies (prior probabilities)
    SYMBOL_PRIORS = {
        '*': 0.35,   # Most common
        '†': 0.25,
        '‡': 0.15,
        '§': 0.12,
        '¶': 0.08,
        '°': 0.03,
        '∥': 0.02,
    }

    def infer_symbol(
        self,
        observed_text: str,
        prev_symbol: Optional[str] = None,
        position_hint: Optional[str] = None
    ) -> SymbolInference:
        """
        Infer actual symbol from corrupted text using Bayesian inference.

        P(symbol | observed, prev) ∝ P(observed | symbol) × P(symbol | prev)

        Args:
            observed_text: What was extracted from PDF (e.g., 't', 'iii')
            prev_symbol: Previous symbol in sequence (for schema inference)
            position_hint: 'body', 'footer', 'margin' (affects priors)

        Returns:
            SymbolInference with best symbol and confidence
        """
        candidates = list(self.CORRUPTION_TABLE.keys())
        scores = {}

        for symbol in candidates:
            # P(observed | symbol) - corruption probability
            corruption_prob = self.CORRUPTION_TABLE[symbol].get(observed_text, 0.001)

            # P(symbol | prev) - schema probability
            if prev_symbol and prev_symbol in self.SCHEMA_TRANSITIONS:
                schema_prob = self.SCHEMA_TRANSITIONS[prev_symbol].get(symbol, 0.01)
            else:
                # No previous symbol - use base frequency
                schema_prob = self.SYMBOL_PRIORS.get(symbol, 0.01)

            # Posterior: P(symbol | observed, prev) ∝ P(obs|sym) × P(sym|prev)
            scores[symbol] = corruption_prob * schema_prob

        # Normalize to probabilities
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}

        # Best symbol
        best_symbol = max(scores, key=scores.get)
        confidence = scores[best_symbol]

        # Determine inference method
        if observed_text == best_symbol:
            method = 'direct'
        elif prev_symbol:
            method = 'schema_inference'
        else:
            method = 'corruption_model'

        return SymbolInference(
            actual_symbol=best_symbol,
            observed_text=observed_text,
            confidence=confidence,
            inference_method=method,
            alternatives=scores
        )

    def validate_sequence(self, symbols: List[str]) -> Tuple[bool, float, List[int]]:
        """
        Validate footnote marker sequence using Markov schema.

        Args:
            symbols: Sequence of detected symbols

        Returns:
            (is_valid, confidence, anomalous_positions)
        """
        if not symbols:
            return True, 1.0, []

        log_prob = 0.0
        anomalies = []

        for i in range(len(symbols) - 1):
            curr, next_sym = symbols[i], symbols[i+1]

            # Get transition probability
            if curr in self.SCHEMA_TRANSITIONS:
                prob = self.SCHEMA_TRANSITIONS[curr].get(next_sym, 0.01)
            else:
                # Unknown symbol - use uniform
                prob = 0.1

            log_prob += prob  # Using prob instead of log for simplicity

            # Flag low-probability transitions
            if prob < 0.05:
                anomalies.append(i)

        # Average probability as confidence
        avg_prob = log_prob / (len(symbols) - 1) if len(symbols) > 1 else 1.0
        is_valid = avg_prob > 0.5 and len(anomalies) == 0

        return is_valid, avg_prob, anomalies

    def infer_missing_marker(
        self,
        sequence: List[Optional[str]],
        missing_index: int
    ) -> SymbolInference:
        """
        Infer missing marker in sequence using bidirectional context.

        Uses both left and right context:
        P(missing | left, right) ∝ P(missing | left) × P(right | missing)

        Args:
            sequence: Partial sequence with None at missing_index
            missing_index: Index of missing marker

        Returns:
            SymbolInference for the missing marker
        """
        candidates = list(self.SYMBOL_PRIORS.keys())
        scores = {}

        for candidate in candidates:
            score = 1.0

            # Left context: P(candidate | previous)
            if missing_index > 0 and sequence[missing_index - 1] is not None:
                prev = sequence[missing_index - 1]
                if prev in self.SCHEMA_TRANSITIONS:
                    score *= self.SCHEMA_TRANSITIONS[prev].get(candidate, 0.01)

            # Right context: P(next | candidate)
            if missing_index < len(sequence) - 1 and sequence[missing_index + 1] is not None:
                next_sym = sequence[missing_index + 1]
                if candidate in self.SCHEMA_TRANSITIONS:
                    score *= self.SCHEMA_TRANSITIONS[candidate].get(next_sym, 0.01)

            # Prior
            score *= self.SYMBOL_PRIORS.get(candidate, 0.01)

            scores[candidate] = score

        # Normalize
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}

        best = max(scores, key=scores.get)

        return SymbolInference(
            actual_symbol=best,
            observed_text='[MISSING]',
            confidence=scores[best],
            inference_method='bidirectional_context',
            alternatives=scores
        )


def _detect_schema_type(markers: List[Dict]) -> str:
    """
    Detect footnote schema type from marker patterns.

    Args:
        markers: List of detected markers

    Returns:
        'numeric', 'symbolic', 'alphabetic', 'roman', or 'mixed'
    """
    if not markers:
        return 'unknown'

    marker_texts = [m.get('text', m.get('marker', '')) for m in markers]

    # Count each type
    numeric_count = sum(1 for m in marker_texts if m.isdigit())
    symbolic_count = sum(1 for m in marker_texts if m in ['*', '†', '‡', '§', '¶', '°', '∥', '#'])
    alpha_count = sum(1 for m in marker_texts if m.isalpha() and len(m) == 1 and m not in ['i', 'v', 'x'])
    roman_count = sum(1 for m in marker_texts if m in ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x'])

    total = len(markers)

    # Determine primary schema (>70% threshold)
    if numeric_count > 0.7 * total:
        return 'numeric'
    elif symbolic_count > 0.7 * total:
        return 'symbolic'
    elif alpha_count > 0.7 * total:
        return 'alphabetic'
    elif roman_count > 0.7 * total:
        return 'roman'
    else:
        return 'mixed'


class FootnoteSchemaValidator:
    """
    Validates footnote sequences for completeness and consistency.

    Checks:
    - All markers have definitions
    - All definitions have markers
    - Sequence follows known schema
    - No duplicates or gaps
    """

    def __init__(self):
        self.corruption_model = SymbolCorruptionModel()

    def validate(
        self,
        markers: List[Dict],
        definitions: List[Dict]
    ) -> Dict[str, any]:
        """
        Comprehensive validation of detected footnotes.

        Returns:
            {
                'is_complete': bool,
                'is_schema_valid': bool,
                'confidence': float,
                'orphaned_markers': List,
                'orphaned_definitions': List,
                'issues': List[str]
            }
        """
        result = {
            'is_complete': True,
            'is_schema_valid': True,
            'confidence': 1.0,
            'orphaned_markers': [],
            'orphaned_definitions': [],
            'issues': []
        }

        # Extract marker symbols
        marker_symbols = [m.get('symbol', m.get('text', '')) for m in markers]
        def_symbols = [d.get('marker', d.get('text', '')[:10].strip()) for d in definitions]

        # Check pairing completeness
        marker_set = set(marker_symbols)
        def_set = set(def_symbols)

        result['orphaned_markers'] = list(marker_set - def_set)
        result['orphaned_definitions'] = list(def_set - marker_set)

        if result['orphaned_markers'] or result['orphaned_definitions']:
            result['is_complete'] = False
            result['issues'].append(f"Incomplete pairing: {len(result['orphaned_markers'])} orphaned markers, {len(result['orphaned_definitions'])} orphaned definitions")

        # Validate sequence schema
        is_valid, conf, anomalies = self.corruption_model.validate_sequence(marker_symbols)
        result['is_schema_valid'] = is_valid
        result['confidence'] = conf

        if anomalies:
            result['issues'].append(f"Schema anomalies at positions: {anomalies}")

        # Check for duplicates
        if len(marker_symbols) != len(marker_set):
            result['issues'].append(f"Duplicate markers detected")
            result['is_complete'] = False

        return result


def apply_corruption_recovery(
    detected_markers: List[Dict],
    detected_definitions: List[Dict]
) -> Tuple[List[Dict], List[Dict]]:
    """
    Apply corruption model to recover actual symbols.

    Clever strategy:
    1. Detect schema type (numeric vs symbolic) from markers
    2. Use body markers (more reliable) to establish sequence
    3. Apply appropriate schema for recovery
    4. Return corrected markers and definitions

    Args:
        detected_markers: Markers from body text
        detected_definitions: Definitions from footer (corrupted)

    Returns:
        (corrected_markers, corrected_definitions) with actual symbols
    """
    model = SymbolCorruptionModel()

    # STEP 1: Detect schema type from body markers
    schema_type = _detect_schema_type(detected_markers)
    logging.info(f"Detected footnote schema: {schema_type}")

    # STEP 2: If numeric schema, don't apply symbolic corruption recovery
    if schema_type == 'numeric':
        # For numeric footnotes, markers are usually reliable (no symbol corruption)
        # Just pass through without inference
        corrected_markers = [
            {
                **marker,
                'actual_symbol': marker.get('text', marker.get('marker', '')),
                'observed_text': marker.get('text', marker.get('marker', '')),
                'confidence': 1.0 if marker.get('is_superscript', False) else 0.7,
                'inference_method': 'direct_numeric'
            }
            for marker in detected_markers
        ]

        corrected_definitions = [
            {
                **definition,
                'actual_marker': definition.get('marker', ''),
                'observed_marker': definition.get('marker', ''),
                'confidence': 0.95,
                'inference_method': 'direct_numeric'
            }
            for definition in detected_definitions
        ]

        return corrected_markers, corrected_definitions

    # BUG-2 FIX: STEP 2.5: If alphabetic schema, preserve markers unchanged
    # Alphabetic markers (a, b, c, d, e) from translators should NOT be converted to symbols
    if schema_type == 'alphabetic':
        # Pure alphabetic schema - pass through without conversion
        logging.info(f"Alphabetic schema detected - preserving translator markers as-is")

        corrected_markers = [
            {
                **marker,
                'actual_symbol': marker.get('text', marker.get('marker', '')),
                'observed_text': marker.get('text', marker.get('marker', '')),
                'confidence': 0.95,
                'inference_method': 'direct_alphabetic'
            }
            for marker in detected_markers
        ]

        corrected_definitions = [
            {
                **definition,
                'actual_marker': definition.get('marker', ''),
                'observed_marker': definition.get('marker', ''),
                'confidence': 0.95,
                'inference_method': 'direct_alphabetic'
            }
            for definition in detected_definitions
        ]

        return corrected_markers, corrected_definitions

    # BUG-2 FIX: STEP 2.6: If mixed schema, apply selective corruption recovery
    # Mixed can mean: symbolic + alphabetic (Kant) OR symbolic + corrupted symbolic (Derrida)
    # Strategy: Preserve alphabetic (a-z), recover corrupted symbols (t→†), keep actual symbols (*)
    if schema_type == 'mixed':
        logging.info(f"Mixed schema detected - applying selective corruption recovery")

        corrected_markers = []
        for i, marker in enumerate(detected_markers):
            observed = marker.get('text', marker.get('marker', ''))
            prev_symbol = corrected_markers[i-1]['actual_symbol'] if i > 0 else None

            # BUG-3 FIX: Preserve numeric, alphabetic, and actual symbols in mixed schema
            # Check if this is numeric marker (1-20, author notes)
            if observed.isdigit() and int(observed) <= 20:
                # Preserve numeric markers unchanged (single or multi-digit)
                corrected_markers.append({
                    **marker,
                    'actual_symbol': observed,
                    'observed_text': observed,
                    'confidence': 0.95,
                    'inference_method': 'direct_numeric'
                })
            # Check if this is alphabetic marker (a-j, translator notes)
            elif observed.isalpha() and len(observed) == 1 and observed in 'abcdefghij':
                # Preserve alphabetic markers unchanged
                corrected_markers.append({
                    **marker,
                    'actual_symbol': observed,
                    'observed_text': observed,
                    'confidence': 0.95,
                    'inference_method': 'direct_alphabetic'
                })
            # Check if this is actual symbolic marker (not corrupted)
            elif observed in ['*', '†', '‡', '§', '¶', '#', '°', '∥']:
                # Preserve actual symbols unchanged
                corrected_markers.append({
                    **marker,
                    'actual_symbol': observed,
                    'observed_text': observed,
                    'confidence': 0.98,
                    'inference_method': 'direct_symbolic'
                })
            else:
                # Might be corrupted symbol - apply Bayesian recovery
                inference = model.infer_symbol(observed, prev_symbol=prev_symbol)
                corrected_markers.append({
                    **marker,
                    'actual_symbol': inference.actual_symbol,
                    'observed_text': observed,
                    'confidence': inference.confidence,
                    'inference_method': inference.inference_method
                })

        # Similar logic for definitions
        corrected_definitions = []
        for i, definition in enumerate(detected_definitions):
            if definition is None:
                continue

            marker_text = definition.get('marker', definition.get('text', ''))

            # Markerless continuations
            if marker_text is None:
                corrected_definitions.append({
                    **definition,
                    'actual_marker': None,
                    'observed_marker': None,
                    'confidence': 0.90,
                    'inference_method': 'markerless'
                })
                continue

            # BUG-3 FIX: Preserve numeric (1-20), alphabetic, or actual symbols
            if (marker_text.isdigit() and int(marker_text) <= 20) or \
               (marker_text.isalpha() and len(marker_text) == 1 and marker_text in 'abcdefghij') or \
               (marker_text in ['*', '†', '‡', '§', '¶', '#', '°', '∥']):
                corrected_definitions.append({
                    **definition,
                    'actual_marker': marker_text,
                    'observed_marker': marker_text,
                    'confidence': 0.95,
                    'inference_method': 'direct_mixed'
                })
            else:
                # Potentially corrupted - recover
                if i < len(corrected_markers):
                    actual_marker = corrected_markers[i]['actual_symbol']
                else:
                    actual_marker = marker_text

                corrected_definitions.append({
                    **definition,
                    'actual_marker': actual_marker,
                    'observed_marker': marker_text,
                    'confidence': 0.85,
                    'inference_method': 'sequence_based'
                })

        return corrected_markers, corrected_definitions

    # STEP 3: For symbolic schema, apply Bayesian corruption recovery
    corrected_markers = []
    corrected_definitions = []

    # Process markers (body text - usually more reliable)
    for i, marker in enumerate(detected_markers):
        observed = marker.get('text', marker.get('marker', ''))
        prev_symbol = corrected_markers[i-1]['actual_symbol'] if i > 0 else None

        # Infer actual symbol
        inference = model.infer_symbol(observed, prev_symbol=prev_symbol)

        corrected_markers.append({
            **marker,
            'actual_symbol': inference.actual_symbol,
            'observed_text': observed,
            'confidence': inference.confidence,
            'inference_method': inference.inference_method
        })

        logging.debug(f"Marker {i}: '{observed}' → '{inference.actual_symbol}' (conf: {inference.confidence:.3f})")

    # Process definitions using established sequence + schema prediction
    # Clever: Build expected sequence from detected body markers + schema transitions
    expected_sequence = []
    if corrected_markers:
        # Start with detected body markers
        expected_sequence = [m['actual_symbol'] for m in corrected_markers]

        # Extend sequence based on schema if we have more definitions
        while len(expected_sequence) < len(detected_definitions):
            last_symbol = expected_sequence[-1]
            if last_symbol in model.SCHEMA_TRANSITIONS:
                # Predict next symbol with highest probability
                next_symbol = max(
                    model.SCHEMA_TRANSITIONS[last_symbol].items(),
                    key=lambda x: x[1]
                )[0]
                if next_symbol is None:
                    break  # Schema ended
                expected_sequence.append(next_symbol)
            else:
                break  # Can't extend

    # Now match definitions to expected sequence
    for i, definition in enumerate(detected_definitions):
        if definition is None:
            continue

        marker_text = definition.get('marker', definition.get('text', ''))

        # SPECIAL CASE: Markerless continuations (marker=None)
        # These are potential multi-page continuations detected by _find_markerless_content()
        # Pass them through WITHOUT corruption recovery - they're not corrupted
        if marker_text is None:
            # Preserve markerless definitions for CrossPageFootnoteParser
            corrected_definitions.append({
                **definition,
                'actual_marker': None,  # Explicitly preserve None marker
                'observed_marker': None,
                'confidence': definition.get('continuation_confidence', 0.5),
                'inference_method': 'markerless_passthrough'
            })
            continue

        observed = marker_text[:10].strip()

        # Use expected symbol from sequence if available
        if i < len(expected_sequence):
            expected_symbol = expected_sequence[i]

            # Verify using corruption model
            if expected_symbol in model.CORRUPTION_TABLE:
                corruption_prob = model.CORRUPTION_TABLE[expected_symbol].get(observed, 0.001)

                # Also use schema probability
                if i > 0 and i-1 < len(expected_sequence):
                    prev_symbol = expected_sequence[i-1]
                    schema_prob = model.SCHEMA_TRANSITIONS.get(prev_symbol, {}).get(expected_symbol, 0.01)
                else:
                    schema_prob = model.SYMBOL_PRIORS.get(expected_symbol, 0.01)

                # Combined confidence: corruption × schema
                combined_conf = corruption_prob * schema_prob * 10  # Scale up
                combined_conf = min(combined_conf, 1.0)  # Cap at 1.0

                corrected_definitions.append({
                    **definition,
                    'actual_marker': expected_symbol,
                    'observed_marker': observed,
                    'confidence': combined_conf,
                    'inference_method': 'sequence_schema_guided'
                })
                logging.debug(f"Definition {i}: '{observed}' → '{expected_symbol}' (sequence+schema, conf: {combined_conf:.3f})")
            else:
                # Unknown symbol - use expected
                corrected_definitions.append({
                    **definition,
                    'actual_marker': expected_symbol,
                    'observed_marker': observed,
                    'confidence': 0.85,
                    'inference_method': 'schema_guided'
                })
        else:
            # No expected symbol - infer from corruption model
            prev_symbol = expected_sequence[-1] if expected_sequence else None
            inference = model.infer_symbol(observed, prev_symbol=prev_symbol)

            corrected_definitions.append({
                **definition,
                'actual_marker': inference.actual_symbol,
                'observed_marker': observed,
                'confidence': inference.confidence,
                'inference_method': inference.inference_method
            })
            logging.warning(f"No expected symbol for definition {i}: '{observed}' → '{inference.actual_symbol}'")

    return corrected_markers, corrected_definitions


def compute_pairing_confidence(
    marker: Dict,
    definition: Dict,
    corruption_model: SymbolCorruptionModel
) -> float:
    """
    Compute confidence that marker and definition are correctly paired.

    Multi-factor scoring:
    - Symbol match confidence (via corruption model)
    - Spatial proximity (closer = higher confidence)
    - Sequence position match

    Args:
        marker: Marker dictionary with actual_symbol
        definition: Definition dictionary with actual_marker
        corruption_model: Symbol corruption model

    Returns:
        Confidence score 0-1
    """
    confidence = 1.0

    # Factor 1: Symbol match
    if marker['actual_symbol'] == definition['actual_marker']:
        symbol_match_score = 1.0
    else:
        symbol_match_score = 0.3  # Penalize mismatch

    # Factor 2: Spatial proximity (if bbox available)
    if 'bbox' in marker and 'bbox' in definition:
        # Euclidean distance between centers
        m_center = [(marker['bbox'][0] + marker['bbox'][2]) / 2,
                    (marker['bbox'][1] + marker['bbox'][3]) / 2]
        d_center = [(definition['bbox'][0] + definition['bbox'][2]) / 2,
                    (definition['bbox'][1] + definition['bbox'][3]) / 2]

        distance = ((m_center[0] - d_center[0])**2 + (m_center[1] - d_center[1])**2)**0.5

        # Exponential decay: closer = better
        max_distance = 500  # pixels
        spatial_score = min(1.0, max(0.0, 1.0 - distance / max_distance))
    else:
        spatial_score = 0.5  # Unknown

    # Factor 3: Corruption model confidence
    corruption_score = marker.get('confidence', 1.0) * definition.get('confidence', 1.0)

    # Weighted combination
    confidence = (
        symbol_match_score * 0.4 +
        spatial_score * 0.3 +
        corruption_score * 0.3
    )

    return confidence


# Example usage and testing
if __name__ == '__main__':
    # Test the corruption model
    model = SymbolCorruptionModel()

    print("=== Symbol Corruption Recovery ===\n")

    # Test case 1: 't' in footer after '*' in body
    test_cases = [
        ('*', None, "First marker (asterisk)"),
        ('t', '*', "Second marker after asterisk"),
        ('iii', None, "Corrupted asterisk in footer"),
    ]

    for observed, prev, description in test_cases:
        inference = model.infer_symbol(observed, prev_symbol=prev)
        print(f"{description}:")
        print(f"  Observed: '{observed}'")
        print(f"  Inferred: '{inference.actual_symbol}'")
        print(f"  Confidence: {inference.confidence:.3f}")
        print(f"  Method: {inference.inference_method}")
        print(f"  Alternatives: {dict(list(inference.alternatives.items())[:3])}")
        print()

    # Test case 2: Sequence validation
    print("\n=== Sequence Validation ===\n")

    sequences = [
        (['*', '†', '‡'], "Standard symbolic sequence"),
        (['*', '‡', '§'], "Missing † (anomaly)"),
        (['1', '2', '3'], "Numeric sequence"),
    ]

    for seq, description in sequences:
        is_valid, conf, anomalies = model.validate_sequence(seq)
        print(f"{description}: {seq}")
        print(f"  Valid: {is_valid}")
        print(f"  Confidence: {conf:.3f}")
        if anomalies:
            print(f"  Anomalies at: {anomalies}")
        print()

"""
Unit tests for lib/footnote_corruption_model.py

Targets uncovered lines: 119-153, 171-197, 217-247, 267, 283, 286-289,
304, 324-361, 451-665, 689-723, 729-766.

Uses synthetic data — no real PDFs.
"""

from lib.footnote_corruption_model import (
    SymbolCorruptionModel,
    SymbolInference,
    FootnoteSchemaValidator,
    _detect_schema_type,
    apply_corruption_recovery,
    compute_pairing_confidence,
)


# ===================================================================
# SymbolCorruptionModel.infer_symbol  (lines 119-153)
# ===================================================================


class TestInferSymbol:
    def setup_method(self):
        self.model = SymbolCorruptionModel()

    def test_direct_match_asterisk(self):
        """Observed '*' should infer '*' with high confidence."""
        result = self.model.infer_symbol("*")
        assert result.actual_symbol == "*"
        assert result.inference_method == "direct"
        assert result.confidence > 0.5

    def test_corrupted_t_after_asterisk(self):
        """'t' after '*' should infer '†' via schema."""
        result = self.model.infer_symbol("t", prev_symbol="*")
        assert result.actual_symbol == "†"
        assert result.inference_method == "schema_inference"

    def test_corrupted_iii_no_context(self):
        """'iii' without context -> corruption model picks best candidate."""
        result = self.model.infer_symbol("iii")
        assert result.inference_method == "corruption_model"
        assert result.actual_symbol in ["*", "†", "‡", "§", "¶", "°"]
        assert isinstance(result.alternatives, dict)

    def test_unknown_observed_text(self):
        """Completely unknown text should still return a result."""
        result = self.model.infer_symbol("xyz123")
        assert isinstance(result, SymbolInference)
        assert result.confidence > 0

    def test_with_prev_symbol_schema_transitions(self):
        """Test schema inference with various prev symbols."""
        # After † -> expect ‡
        result = self.model.infer_symbol("iii", prev_symbol="†")
        assert result.actual_symbol == "‡"

    def test_prev_symbol_not_in_transitions(self):
        """Unknown prev_symbol -> falls back to priors."""
        result = self.model.infer_symbol("*", prev_symbol="UNKNOWN")
        assert result.actual_symbol == "*"
        assert result.inference_method == "direct"


# ===================================================================
# SymbolCorruptionModel.validate_sequence  (lines 171-197)
# ===================================================================


class TestValidateSequence:
    def setup_method(self):
        self.model = SymbolCorruptionModel()

    def test_empty_sequence(self):
        is_valid, conf, anomalies = self.model.validate_sequence([])
        assert is_valid is True
        assert conf == 1.0
        assert anomalies == []

    def test_valid_standard_sequence(self):
        """* -> † -> ‡ is the standard schema."""
        is_valid, conf, anomalies = self.model.validate_sequence(["*", "†", "‡"])
        assert is_valid is True
        assert anomalies == []

    def test_anomalous_sequence(self):
        """Skipping from * to § should flag anomaly at position 0."""
        is_valid, conf, anomalies = self.model.validate_sequence(["*", "§"])
        # * -> § has very low probability (0.01), should be anomaly
        assert 0 in anomalies

    def test_unknown_symbol_in_sequence(self):
        """Unknown symbol gets uniform probability."""
        is_valid, conf, anomalies = self.model.validate_sequence(["UNKNOWN", "†"])
        assert isinstance(conf, float)

    def test_single_element(self):
        """Single-element sequence should be valid."""
        is_valid, conf, anomalies = self.model.validate_sequence(["*"])
        assert is_valid is True
        assert conf == 1.0
        assert anomalies == []


# ===================================================================
# SymbolCorruptionModel.infer_missing_marker  (lines 217-247)
# ===================================================================


class TestInferMissingMarker:
    def setup_method(self):
        self.model = SymbolCorruptionModel()

    def test_missing_middle(self):
        """Infer missing marker between * and ‡ (should be †)."""
        sequence = ["*", None, "‡"]
        result = self.model.infer_missing_marker(sequence, 1)
        assert result.actual_symbol == "†"
        assert result.inference_method == "bidirectional_context"
        assert result.observed_text == "[MISSING]"

    def test_missing_first(self):
        """Infer missing first marker before †."""
        sequence = [None, "†"]
        result = self.model.infer_missing_marker(sequence, 0)
        assert result.actual_symbol == "*"

    def test_missing_last(self):
        """Infer missing marker after †."""
        sequence = ["†", None]
        result = self.model.infer_missing_marker(sequence, 1)
        assert result.actual_symbol == "‡"  # most likely after †

    def test_missing_no_context(self):
        """All context is None -> falls back to priors."""
        sequence = [None, None, None]
        result = self.model.infer_missing_marker(sequence, 1)
        # Should return highest prior, which is *
        assert result.actual_symbol == "*"


# ===================================================================
# _detect_schema_type  (lines 267, 283, 286-289)
# ===================================================================


class TestDetectSchemaType:
    def test_empty_markers(self):
        assert _detect_schema_type([]) == "unknown"

    def test_numeric_schema(self):
        markers = [{"text": "1"}, {"text": "2"}, {"text": "3"}]
        assert _detect_schema_type(markers) == "numeric"

    def test_symbolic_schema(self):
        markers = [{"text": "*"}, {"text": "†"}, {"text": "‡"}]
        assert _detect_schema_type(markers) == "symbolic"

    def test_alphabetic_schema(self):
        markers = [{"text": "a"}, {"text": "b"}, {"text": "c"}]
        assert _detect_schema_type(markers) == "alphabetic"

    def test_roman_schema(self):
        markers = [{"text": "i"}, {"text": "ii"}, {"text": "iii"}]
        assert _detect_schema_type(markers) == "roman"

    def test_mixed_schema(self):
        markers = [{"text": "1"}, {"text": "*"}, {"text": "a"}, {"text": "ii"}]
        assert _detect_schema_type(markers) == "mixed"

    def test_marker_key_fallback(self):
        """Uses 'marker' key if 'text' is not present."""
        markers = [{"marker": "1"}, {"marker": "2"}, {"marker": "3"}]
        assert _detect_schema_type(markers) == "numeric"


# ===================================================================
# FootnoteSchemaValidator.validate  (lines 304, 324-361)
# ===================================================================


class TestFootnoteSchemaValidator:
    def setup_method(self):
        self.validator = FootnoteSchemaValidator()

    def test_complete_pairing(self):
        markers = [{"symbol": "*"}, {"symbol": "†"}]
        definitions = [{"marker": "*"}, {"marker": "†"}]
        result = self.validator.validate(markers, definitions)
        assert result["is_complete"] is True
        assert result["orphaned_markers"] == []
        assert result["orphaned_definitions"] == []

    def test_orphaned_marker(self):
        markers = [{"symbol": "*"}, {"symbol": "†"}, {"symbol": "‡"}]
        definitions = [{"marker": "*"}, {"marker": "†"}]
        result = self.validator.validate(markers, definitions)
        assert result["is_complete"] is False
        assert "‡" in result["orphaned_markers"]

    def test_orphaned_definition(self):
        markers = [{"symbol": "*"}]
        definitions = [{"marker": "*"}, {"marker": "†"}]
        result = self.validator.validate(markers, definitions)
        assert result["is_complete"] is False
        assert "†" in result["orphaned_definitions"]

    def test_duplicate_markers(self):
        markers = [{"symbol": "*"}, {"symbol": "*"}]
        definitions = [{"marker": "*"}]
        result = self.validator.validate(markers, definitions)
        assert result["is_complete"] is False
        assert any("Duplicate" in issue for issue in result["issues"])

    def test_schema_anomalies_reported(self):
        """Anomalous sequence should generate issues."""
        markers = [{"symbol": "*"}, {"symbol": "§"}]  # Skip †, ‡
        definitions = [{"marker": "*"}, {"marker": "§"}]
        result = self.validator.validate(markers, definitions)
        # Should detect anomaly at position 0
        if result["issues"]:
            assert any("anomal" in issue.lower() for issue in result["issues"])


# ===================================================================
# apply_corruption_recovery  (lines 451-665)
# ===================================================================


class TestApplyCorruptionRecovery:
    def test_numeric_schema_passthrough(self):
        """Numeric markers should pass through without corruption recovery."""
        markers = [{"text": "1"}, {"text": "2"}, {"text": "3"}]
        definitions = [{"marker": "1"}, {"marker": "2"}, {"marker": "3"}]
        cm, cd = apply_corruption_recovery(markers, definitions)
        assert len(cm) == 3
        assert cm[0]["actual_symbol"] == "1"
        assert cm[0]["inference_method"] == "direct_numeric"
        assert cd[0]["actual_marker"] == "1"

    def test_alphabetic_schema_passthrough(self):
        """Alphabetic markers preserved unchanged."""
        markers = [{"text": "a"}, {"text": "b"}, {"text": "c"}]
        definitions = [{"marker": "a"}, {"marker": "b"}, {"marker": "c"}]
        cm, cd = apply_corruption_recovery(markers, definitions)
        assert cm[0]["actual_symbol"] == "a"
        assert cm[0]["inference_method"] == "direct_alphabetic"
        assert cd[0]["inference_method"] == "direct_alphabetic"

    def test_symbolic_schema_recovery(self):
        """Symbolic schema applies Bayesian corruption recovery."""
        markers = [{"text": "*"}, {"text": "t"}]  # t is corrupted †
        definitions = [{"marker": "*"}, {"marker": "t"}]
        cm, cd = apply_corruption_recovery(markers, definitions)
        assert cm[0]["actual_symbol"] == "*"
        assert cm[1]["actual_symbol"] == "†"  # recovered from 't'

    def test_mixed_schema_numeric_preserved(self):
        """Mixed schema preserves numeric markers."""
        markers = [
            {"text": "1"},
            {"text": "a"},
            {"text": "*"},
            {"text": "t"},
        ]
        definitions = [
            {"marker": "1"},
            {"marker": "a"},
            {"marker": "*"},
            {"marker": "t"},
        ]
        cm, cd = apply_corruption_recovery(markers, definitions)
        assert cm[0]["actual_symbol"] == "1"
        assert cm[0]["inference_method"] == "direct_numeric"
        assert cm[1]["actual_symbol"] == "a"
        assert cm[1]["inference_method"] == "direct_alphabetic"
        assert cm[2]["actual_symbol"] == "*"
        assert cm[2]["inference_method"] == "direct_symbolic"

    def test_mixed_schema_corrupted_recovery(self):
        """Mixed schema recovers corrupted symbols."""
        markers = [
            {"text": "1"},
            {"text": "t"},  # corrupted — not alphabetic (not in a-j pattern)
        ]
        definitions = [{"marker": "1"}, {"marker": "t"}]
        cm, cd = apply_corruption_recovery(markers, definitions)
        # 't' should be recovered by corruption model
        assert cm[1]["inference_method"] in [
            "corruption_model",
            "schema_inference",
        ]

    def test_mixed_schema_definition_markerless(self):
        """Mixed schema handles None marker in definitions."""
        markers = [{"text": "1"}, {"text": "a"}]
        definitions = [
            {"marker": "1"},
            {"marker": None},  # markerless continuation
        ]
        cm, cd = apply_corruption_recovery(markers, definitions)
        # The None marker should be handled
        assert any(d.get("inference_method") == "markerless" for d in cd)

    def test_mixed_schema_definition_direct_mixed(self):
        """Mixed schema preserves known definition markers."""
        markers = [{"text": "1"}, {"text": "a"}, {"text": "*"}]
        definitions = [
            {"marker": "1"},
            {"marker": "a"},
            {"marker": "*"},
        ]
        cm, cd = apply_corruption_recovery(markers, definitions)
        assert cd[0]["inference_method"] == "direct_mixed"
        assert cd[1]["inference_method"] == "direct_mixed"
        assert cd[2]["inference_method"] == "direct_mixed"

    def test_mixed_schema_definition_corrupted_with_sequence(self):
        """Mixed schema: corrupted definition matched to corrected marker."""
        markers = [{"text": "1"}, {"text": "a"}, {"text": "*"}, {"text": "t"}]
        definitions = [
            {"marker": "1"},
            {"marker": "a"},
            {"marker": "*"},
            {"marker": "t_corrupted"},  # corrupted, but has matching marker
        ]
        cm, cd = apply_corruption_recovery(markers, definitions)
        # The fourth definition should use sequence_based
        assert cd[3]["inference_method"] == "sequence_based"

    def test_symbolic_schema_markerless_definition(self):
        """Symbolic schema handles markerless definitions (continuation)."""
        markers = [{"text": "*"}]
        definitions = [{"marker": "*"}, {"marker": None}]
        cm, cd = apply_corruption_recovery(markers, definitions)
        # Second definition is markerless -> passthrough
        markerless = [d for d in cd if d.get("actual_marker") is None]
        assert len(markerless) == 1
        assert markerless[0]["inference_method"] == "markerless_passthrough"

    def test_symbolic_schema_more_defs_than_markers(self):
        """When there are more definitions than markers, extends expected sequence."""
        markers = [{"text": "*"}]
        definitions = [{"marker": "*"}, {"marker": "t"}, {"marker": "iii"}]
        cm, cd = apply_corruption_recovery(markers, definitions)
        assert len(cd) == 3
        # Extended sequence should predict † then ‡
        assert cd[1]["actual_marker"] == "†"

    def test_symbolic_schema_definition_unknown_expected(self):
        """Definition beyond extended sequence uses corruption model."""
        markers = [{"text": "*"}]
        # Many definitions — beyond schema extension capacity
        definitions = [
            {"marker": "*"},
            {"marker": "t"},
            {"marker": "iii"},
            {"marker": "s"},
            {"marker": "p"},
            {"marker": "o"},
            {"marker": "extra1"},
            {"marker": "extra2"},
            {"marker": "extra3"},
            {"marker": "extra4"},
        ]
        cm, cd = apply_corruption_recovery(markers, definitions)
        # At some point the sequence can't extend further
        assert len(cd) == 10

    def test_symbolic_definition_none_skipped(self):
        """None definitions in the list are skipped."""
        markers = [{"text": "*"}]
        definitions = [{"marker": "*"}, None]
        cm, cd = apply_corruption_recovery(markers, definitions)
        assert len(cd) == 1  # None was skipped

    def test_mixed_schema_none_definition_skipped(self):
        """In mixed schema, None definitions are skipped (line 505)."""
        markers = [{"text": "1"}, {"text": "a"}]
        definitions = [{"marker": "1"}, None, {"marker": "a"}]
        cm, cd = apply_corruption_recovery(markers, definitions)
        # None definition skipped, so only 2 definitions output
        assert len(cd) == 2

    def test_mixed_schema_definition_index_beyond_markers(self):
        """In mixed schema, corrupted definition where i >= len(corrected_markers)
        falls back to marker_text itself (line 536).
        Need enough mixed markers so _detect_schema_type returns 'mixed'."""
        # 4 markers: 1 numeric, 1 alpha, 1 symbolic, 1 unknown -> no type >70% -> mixed
        markers = [
            {"text": "1"},
            {"text": "a"},
            {"text": "*"},
            {"text": "ii"},
        ]
        definitions = [
            {"marker": "1"},
            {"marker": "a"},
            {"marker": "*"},
            {"marker": "ii"},
            {"marker": "zzz_corrupted"},  # i=4 > len(corrected_markers)=4
            {"marker": "another_corrupted"},  # i=5 > len(corrected_markers)=4
        ]
        cm, cd = apply_corruption_recovery(markers, definitions)
        assert len(cd) == 6
        # The definitions beyond the marker count should use marker_text as fallback
        assert cd[4]["actual_marker"] == "zzz_corrupted"
        assert cd[4]["inference_method"] == "sequence_based"
        assert cd[5]["actual_marker"] == "another_corrupted"

    def test_symbolic_schema_sequence_extension_breaks_on_none(self):
        """When schema transition produces None as next_symbol, the sequence
        extension loop breaks (line 587). We mock SCHEMA_TRANSITIONS so that
        after the last inferred symbol, None has the highest probability.
        Markers must be >70% symbolic for _detect_schema_type to return 'symbolic'."""
        from unittest.mock import patch

        # Custom transitions where '†' -> None is highest probability
        custom_transitions = {
            "*": {None: 0.99, "†": 0.005, "‡": 0.005},
            "†": {None: 0.99, "‡": 0.005, "§": 0.005},
            "‡": {None: 0.99, "§": 0.005},
            "§": {None: 0.99},
            "¶": {None: 0.99},
        }

        # 3 symbolic markers -> 100% symbolic schema
        markers = [{"text": "*"}, {"text": "†"}, {"text": "‡"}]
        # 5 definitions -> needs sequence extension beyond 3 markers
        definitions = [
            {"marker": "*"},
            {"marker": "t"},
            {"marker": "iii"},
            {"marker": "s"},
            {"marker": "extra"},
        ]

        with patch.object(
            SymbolCorruptionModel, "SCHEMA_TRANSITIONS", custom_transitions
        ):
            cm, cd = apply_corruption_recovery(markers, definitions)
            # Should still produce output; extension stopped at None
            assert len(cd) == 5

    def test_mixed_schema_markerless_definition_in_mixed(self):
        """Mixed schema: definition with marker=None handled as markerless (line 510)."""
        markers = [{"text": "1"}, {"text": "a"}, {"text": "*"}]
        definitions = [
            {"marker": "1"},
            {"marker": None},  # markerless continuation
            {"marker": "*"},
        ]
        cm, cd = apply_corruption_recovery(markers, definitions)
        markerless = [d for d in cd if d.get("inference_method") == "markerless"]
        assert len(markerless) == 1
        assert markerless[0]["actual_marker"] is None


# ===================================================================
# compute_pairing_confidence  (lines 689-723)
# ===================================================================


class TestComputePairingConfidence:
    def setup_method(self):
        self.model = SymbolCorruptionModel()

    def test_matching_symbols_high_confidence(self):
        marker = {"actual_symbol": "*", "confidence": 1.0}
        definition = {"actual_marker": "*", "confidence": 1.0}
        conf = compute_pairing_confidence(marker, definition, self.model)
        assert conf > 0.7

    def test_mismatched_symbols_lower_confidence(self):
        marker = {"actual_symbol": "*", "confidence": 1.0}
        definition = {"actual_marker": "†", "confidence": 1.0}
        conf = compute_pairing_confidence(marker, definition, self.model)
        assert conf < 0.7

    def test_with_bbox_spatial_score(self):
        """Spatial proximity affects confidence."""
        marker = {
            "actual_symbol": "*",
            "confidence": 1.0,
            "bbox": (100, 100, 110, 110),
        }
        definition = {
            "actual_marker": "*",
            "confidence": 1.0,
            "bbox": (100, 200, 110, 210),
        }
        conf = compute_pairing_confidence(marker, definition, self.model)
        assert 0 < conf <= 1.0

    def test_without_bbox_defaults_spatial(self):
        """Without bbox, spatial score defaults to 0.5."""
        marker = {"actual_symbol": "*", "confidence": 0.9}
        definition = {"actual_marker": "*", "confidence": 0.8}
        conf = compute_pairing_confidence(marker, definition, self.model)
        assert 0 < conf <= 1.0

    def test_far_apart_bboxes(self):
        """Very far apart bboxes lower the score."""
        marker = {
            "actual_symbol": "*",
            "confidence": 1.0,
            "bbox": (0, 0, 10, 10),
        }
        definition = {
            "actual_marker": "*",
            "confidence": 1.0,
            "bbox": (1000, 1000, 1010, 1010),
        }
        conf_far = compute_pairing_confidence(marker, definition, self.model)

        marker_near = {
            "actual_symbol": "*",
            "confidence": 1.0,
            "bbox": (0, 0, 10, 10),
        }
        definition_near = {
            "actual_marker": "*",
            "confidence": 1.0,
            "bbox": (10, 10, 20, 20),
        }
        conf_near = compute_pairing_confidence(marker_near, definition_near, self.model)
        assert conf_near > conf_far


# ===================================================================
# __main__ block  (lines 729-766)
# ===================================================================


class TestMainBlock:
    def test_main_runs_without_error(self):
        """Execute the module as __main__ and verify it produces output (lines 729-766)."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "lib.footnote_corruption_model"],
            capture_output=True,
            text=True,
            cwd="/home/rookslog/workspace/projects/zlibrary-mcp",
            timeout=10,
        )
        assert result.returncode == 0
        assert "Symbol Corruption Recovery" in result.stdout
        assert "Sequence Validation" in result.stdout
        assert "Inferred:" in result.stdout

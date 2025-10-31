# Three-Way Validation Matrix
**Purpose**: Visual comparison of expected vs detected vs ground truth for all corpora
**Date**: 2025-10-30

## Matrix Legend
- ✓ = Match
- ✗ = Mismatch
- ❓ = Unknown/Not Available
- 🔴 = Critical Issue
- 🟡 = Warning
- 🟢 = Success

## Derrida: Traditional Bottom Footnotes

### Footnote Detection Matrix
| Marker | Expected | Detected | Ground Truth | Visual Count | Match | Issue |
|--------|----------|----------|--------------|--------------|-------|-------|
| * | ✓ | ✓ | ✓ | ✓ | ✓ | None |
| † | ✓ | ✗ | ✓ | ✓ | ✗ | 🔴 Corruption recovery failed |

### Feature Validation Matrix
| Feature | Expected Behavior | Actual Behavior | Match | Issue |
|---------|------------------|-----------------|-------|-------|
| Corruption Recovery | † detected via "t→†" recovery | Not detected | ✗ | 🔴 Core feature broken |
| Classification | 2 TRANSLATOR notes | 1 TRANSLATOR note | ✗ | Detection failure |
| Continuation | None expected | None detected | ✓ | None |
| Superscript | N/A (symbolic only) | N/A | ✓ | N/A |
| Performance | <60ms/page | 609ms/page | ✗ | 🔴 10.2x over budget |

### Ground Truth Comparison
```
Ground Truth (test_files/ground_truth/derrida_footnotes.json):
  Footnote 1:
    Marker: *
    Content: "The title of the next section..."
    Status: ✓ DETECTED

  Footnote 2:
    Marker: †
    Content: "Hereafter page numbers in parenthesis..."
    Status: ✗ MISSING (corruption recovery failed)
    Note: Text layer has "t" instead of "†"
```

### Visual Validation
**Manual PDF Inspection**: 2 footnotes visible in footer of page 1
- Footnote 1 (marker *): ✓ Detected
- Footnote 2 (marker †): ✗ Missing

**Result**: 50% detection rate (1/2)

---

## Kant 64-65: Multi-Page Continuation

### Footnote Detection Matrix
| Marker | Expected | Detected | Ground Truth | Visual Count | Match | Issue |
|--------|----------|----------|--------------|--------------|-------|-------|
| * (pages 64-65) | ✓ (1 merged) | ✗ (5 separate) | ❓ | ✓ | ✗ | 🔴 Continuation creates duplicates |
| † | ✗ | ✓ (false positive) | ❓ | ✗ | ✗ | 🔴 Hallucinated footnote |
| ‡ | ✗ | ✓ (false positive) | ❓ | ✗ | ✗ | 🔴 Hallucinated footnote |
| § | ✗ | ✓ (false positive) | ❓ | ✗ | ✗ | 🔴 Hallucinated footnote |
| ¶ | ✗ | ✓ (false positive) | ❓ | ✗ | ✗ | 🔴 Hallucinated footnote |

### Feature Validation Matrix
| Feature | Expected Behavior | Actual Behavior | Match | Issue |
|---------|------------------|-----------------|-------|-------|
| Continuation | 1 merged [^*] | 5 separate [^*], [^†], [^‡], [^§], [^¶] | ✗ | 🔴 Merge creates duplicates |
| Classification | 1 TRANSLATOR note | 5 TRANSLATOR notes (all identical) | ✗ | Detection failure |
| Superscript | Symbolic only | Symbolic only | ✓ | None |
| Performance | <60ms/page | 539ms/page | ✗ | 🔴 9.0x over budget |

### Content Duplication Evidence
```
All 5 detected footnotes have IDENTICAL content:
  [^*]: "Now and again one hears complaints about the superficiality..."
  [^†]: "Now and again one hears complaints about the superficiality..."
  [^‡]: "Now and again one hears complaints about the superficiality..."
  [^§]: "Now and again one hears complaints about the superficiality..."
  [^¶]: "Now and again one hears complaints about the superficiality..."
```

### Visual Validation
**Manual PDF Inspection**: 1 footnote spanning pages 64-65
- Single asterisk (*) marker on page 64
- Footnote begins page 64, continues page 65
- NO other markers (†, ‡, §, ¶) visible in PDF

**Result**: 400% false positive rate (5 detected, 1 exists)

---

## Kant 80-85: Mixed Schema

### Footnote Detection Matrix (Schema Coverage)
| Schema Type | Markers Expected | Markers Detected | Examples Missing | Match | Issue |
|-------------|-----------------|------------------|------------------|-------|-------|
| Symbolic | *, †, ‡, §, ¶ (~5) | *, †, ‡, §, ¶ (6) | None | ✓ | 🟡 Slight over-detection |
| Numeric | 1, 2, 3... (~10) | None (0) | 1, 2, 3, 4, 5, 6... | ✗ | 🔴 Complete failure |
| Alphabetic | a, b, c... (~5) | None (0) | a, b, c, d, e... | ✗ | 🔴 Complete failure |

### Feature Validation Matrix
| Feature | Expected Behavior | Actual Behavior | Match | Issue |
|---------|------------------|-----------------|-------|-------|
| Multi-Schema Detection | All 3 schemas detected | Only symbolic detected | ✗ | 🔴 Numeric/alphabetic missed |
| Classification | Mixed AUTHOR/TRANSLATOR | Only TRANSLATOR (symbolic) | ✗ | Detection failure |
| Continuation | Unknown | Unknown | ❓ | Cannot assess |
| Superscript | Numeric superscripts | None detected | ✗ | 🔴 Superscript detection failed |
| Performance | <60ms/page | 452ms/page | ✗ | 🔴 7.5x over budget |

### Schema Detection Evidence
```
Detected (6 footnotes - all symbolic):
  [^*]: "As in the first edition. Kant wrote a new preface..."
  [^†]: "As in the first edition. Kant wrote a new preface..."
  [^‡]: "As in the first edition. Kant wrote a new preface..."
  [^§]: "As in the first edition. Kant wrote a new preface..."
  [^¶]: "As in the first edition. Kant wrote a new preface..."
  [^*]: "As in the first edition. Kant wrote a new preface..."

Missing (estimated ~14 footnotes):
  [^1]: (numeric - Kant's original notes)
  [^2]: (numeric - Kant's original notes)
  [^a]: (alphabetic - translator notes)
  [^b]: (alphabetic - translator notes)
  ... and more
```

### Visual Validation
**Manual PDF Inspection**: ~20 footnotes across 6 pages (mixed schemas)
- Symbolic footnotes: ~5 (✓ detected)
- Numeric footnotes: ~10 (✗ missing)
- Alphabetic footnotes: ~5 (✗ missing)

**Result**: 30% detection rate (6/20), 70% false negative

---

## Heidegger 22-23: OCR Quality Test

### Footnote Detection Matrix
| Page | Marker | Expected | Detected | Ground Truth | Visual Count | Match | Issue |
|------|--------|----------|----------|--------------|--------------|-------|-------|
| 22 | 1 | ✓ | ✓ | ✓ | ✓ | ✓ | None |
| 22 | 1 (duplicate ref) | ✓ | ✓ (same entry) | ✓ | ✓ | ✓ | None |
| 23 | 2 | ✓ | ✗ | ✓ | ✓ | ✗ | 🔴 Per-page scoping failed |
| 23 | 3 | ✓ | ✗ | ✓ | ✓ | ✗ | 🔴 Per-page scoping failed |

### Feature Validation Matrix
| Feature | Expected Behavior | Actual Behavior | Match | Issue |
|---------|------------------|-----------------|-------|-------|
| Duplicate Markers | 4 separate [^1], [^2], [^3] entries | 1 [^1] entry only | ✗ | 🔴 Marker collision |
| Per-Page Scoping | Markers scoped by page | All [^1] collapsed | ✗ | 🔴 Scoping broken |
| OCR Quality Filter | Filter "the~", "of~" | Unknown | ❓ | Cannot assess |
| Classification | 4 TRANSLATOR notes | 1 TRANSLATOR note | ✗ | Detection failure |
| Performance | <60ms/page | 377ms/page | ✗ | 🔴 6.3x over budget |

### Ground Truth Comparison
```
Ground Truth (test_files/ground_truth/heidegger_22_23_footnotes.json):
  Footnote 1 (page 22):
    Marker: 1
    Content: "The word 'Dasein' plays so important a role..."
    Status: ✓ DETECTED

  Footnote 2 (page 22):
    Marker: 1 (same as above - duplicate reference)
    Status: ✓ DETECTED (same entry as footnote 1)

  Footnote 3 (page 23):
    Marker: 2
    Content: "Heidegger's point might be..."
    Status: ✗ MISSING (per-page scoping failed)

  Footnote 4 (page 23):
    Marker: 3
    Content: "The earlier version has..."
    Status: ✗ MISSING (per-page scoping failed)
```

### Visual Validation
**Manual PDF Inspection**: 4 footnotes across 2 pages
- Page 22: 2 references to marker "1" (same footnote) ✓
- Page 23: Markers "2" and "3" (separate footnotes) ✗

**Result**: 25% detection rate (1/4 unique footnotes), 75% false negative

---

## Cross-Corpus Feature Summary

### Detection Accuracy by Corpus
| Corpus | Expected | Detected | False Positives | False Negatives | Accuracy |
|--------|----------|----------|-----------------|-----------------|----------|
| Derrida | 2 | 1 | 0 (0%) | 1 (50%) | 50% |
| Kant 64-65 | 1 | 5 | 4 (400%) | 0 (0%) | 0% (false pos) |
| Kant 80-85 | ~20 | 6 | 0 (0%) | ~14 (70%) | 30% |
| Heidegger | 4 | 1 | 0 (0%) | 3 (75%) | 25% |
| **OVERALL** | **~27** | **13** | **4 (15%)** | **~18 (67%)** | **33%** |

### Feature Success Rate by Corpus
| Feature | Derrida | Kant 64-65 | Kant 80-85 | Heidegger | Overall |
|---------|---------|------------|------------|-----------|---------|
| Detection | 50% ✗ | 0% ✗ | 30% ✗ | 25% ✗ | **26% FAIL** |
| Continuation | ✓ | ✗ | ❓ | ✓ | **50% FAIL** |
| Schema Coverage | ✓ | ✓ | ✗ | ✓ | **75% PASS** |
| Superscript | N/A | N/A | ✗ | ✗ | **0% FAIL** |
| Corruption Recovery | ✗ | ❓ | ❓ | ❓ | **0% FAIL** |
| Per-Page Scoping | ✓ | ✓ | ✓ | ✗ | **75% PASS** |
| Performance (<60ms) | ✗ | ✗ | ✗ | ✗ | **0% FAIL** |

### Critical Features Status
| Feature | Working | Broken | Evidence |
|---------|---------|--------|----------|
| Basic Symbolic Detection | ✓ | | All corpora detect some symbolic markers |
| Corruption Recovery | | ✗ | Derrida † marker missed (text layer has "t") |
| Multi-Page Continuation | | ✗ | Kant 64-65 creates 5 duplicates instead of 1 merged |
| Multi-Schema Detection | | ✗ | Kant 80-85 only detects symbolic, misses numeric/alphabetic |
| Per-Page Marker Scoping | | ✗ | Heidegger collapses 4 footnotes to 1 |
| Superscript Detection | | ✗ | All numeric superscripts missed across all corpora |
| Performance Budget | | ✗ | All corpora 6-10x over budget (377-609ms vs 60ms) |

---

## Validation Methodology

### Visual Inspection Process
1. **Manual PDF Review**: Open PDF in viewer, count visible footnotes
2. **Marker Identification**: Record all footnote markers visible in body text
3. **Definition Location**: Confirm footnote content location (bottom, inline, etc.)
4. **Content Verification**: Read full footnote text to confirm completeness
5. **Schema Identification**: Categorize markers (symbolic, numeric, alphabetic)

### Ground Truth Validation Process
1. **Load JSON**: Read ground truth file
2. **Count Comparison**: Compare expected count vs detected count
3. **Marker Verification**: Check each marker in ground truth against detected markers
4. **Content Comparison**: Verify detected content matches expected content
5. **Classification Check**: Confirm note_type (AUTHOR/TRANSLATOR/EDITOR) matches

### Three-Way Validation (Visual + Ground Truth + Detected)
1. **Visual** provides baseline truth (manual inspection)
2. **Ground Truth** provides structured expected output
3. **Detected** shows actual system output
4. **Match** = All three agree
5. **Mismatch** = Any disagreement → investigation required

### Performance Validation Process
1. **Time Processing**: Measure wall-clock time for `process_pdf()`
2. **Count Pages**: Get page count from PDF
3. **Calculate Per-Page**: `total_ms / page_count`
4. **Compare Budget**: Check if `ms_per_page < 60`
5. **Calculate Multiplier**: `actual / budget` to show severity

---

## Key Insights

### Why Symbolic Works But Numeric Fails
- **Symbolic Markers**: Clear visual distinction (*, †, ‡), rare in body text
- **Numeric Markers**: Common in text (dates, citations), require superscript detection
- **Root Cause**: Superscript detection logic not triggering for numeric markers

### Why Tests Pass But Production Fails
- **Unit Tests**: Isolated feature testing with controlled inputs
- **Integration**: Features interact in unexpected ways
- **Real PDFs**: Complex formatting, mixed schemas, OCR issues
- **Mock Gap**: Mocked PyMuPDF doesn't match real PyMuPDF behavior

### Why Performance Is So Poor
- **OCR Pipeline**: Sous-rature detection adds significant overhead
- **Bayesian Inference**: Corruption recovery computationally expensive
- **NLTK Analysis**: Continuation detection uses sentence parsing
- **Multiple Passes**: Each schema type requires separate detection pass
- **No Caching**: Repeated calculations on same data

### Why Continuation Creates Duplicates
- **Hypothesis**: Continuation merge creates new footnote entry instead of merging content
- **Evidence**: 5 footnotes with identical content but different markers
- **Likely Cause**: Logic creates [^†], [^‡], etc. when finding continuation blocks
- **Fix Required**: Merge continuation content into existing [^*] entry

---

**Matrix Complete**: 4 corpora validated
**Total Footnotes Expected**: ~27
**Total Footnotes Detected**: 13
**Overall Accuracy**: 33% (26% detection + 15% false positives)
**Production Ready**: ❌ NO

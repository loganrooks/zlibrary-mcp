# Phase 12: Anna's Archive Integration - Research

**Researched:** 2026-02-02
**Domain:** Multi-source book search/download, API integration, fallback orchestration
**Confidence:** MEDIUM (API access requires donation; web scraping approach is well-documented)

## Summary

Anna's Archive has a JSON API, but it **requires a paid donation** to obtain an API key. There is no free tier. This directly conflicts with the phase's **hard constraint: free sources only**. However, there are two viable paths forward:

1. **Web scraping approach** (like SearXNG does) -- scrape Anna's Archive HTML search results. Free, no API key needed, but fragile and legally riskier.
2. **Library Genesis (LibGen) as the fallback source instead** -- LibGen has free, well-maintained Python libraries (`libgen-api-enhanced`) that provide search AND download with no API key. Anna's Archive itself is largely a search frontend over LibGen data. LibGen is a more direct, free, and stable integration target.

**Primary recommendation:** Use `libgen-api-enhanced` (Python, pip-installable, actively maintained as of Oct 2025) as the fallback source. It provides search by title/author, download link resolution, configurable mirrors, and covers fiction + non-fiction + comics + articles. This satisfies all go/no-go criteria (free, search + download, mitigatable instability via mirror config). The source abstraction layer should be generic enough that Anna's Archive web scraping or API could be added later.

## Go/No-Go Analysis

### Anna's Archive JSON API
| Criterion | Assessment | Status |
|-----------|-----------|--------|
| Free access | **NO** -- requires donation for API key | FAIL |
| Search capability | Yes (titles, authors, ISBN, MD5) | PASS |
| Download capability | Yes (with API key) | PASS |
| API stability | Multiple mirrors, domains change frequently | MEDIUM |
| Legal considerations | Jan 2026 preliminary injunction, domain suspensions | HIGH RISK |

**Verdict: NO-GO for JSON API** (violates free-only constraint)

### Anna's Archive Web Scraping
| Criterion | Assessment | Status |
|-----------|-----------|--------|
| Free access | Yes (public web pages) | PASS |
| Search capability | Yes (SearXNG proves it works) | PASS |
| Download capability | Uncertain -- download links may require membership | UNCLEAR |
| API stability | HTML structure changes break scrapers | LOW |
| Legal considerations | Same Jan 2026 injunction risk | HIGH RISK |

**Verdict: CONDITIONAL GO** (feasible but fragile and risky)

### Library Genesis (via libgen-api-enhanced)
| Criterion | Assessment | Status |
|-----------|-----------|--------|
| Free access | Yes -- fully free, no API key | PASS |
| Search capability | Yes -- title, author, default (multi-field) | PASS |
| Download capability | Yes -- resolved download links + Tor links | PASS |
| Stability | Configurable mirrors (.li, .bz, .gs, etc.) | MEDIUM |
| Legal considerations | Same shadow library concerns as Z-Library | MEDIUM RISK |
| Python library maturity | v1.2.4, Oct 2025, actively maintained | PASS |

**Verdict: GO** -- best fit for free-only constraint with search + download

### Recommendation Priority
1. **LibGen via `libgen-api-enhanced`** (primary recommendation)
2. **Anna's Archive web scraping** (future option, not for initial implementation)
3. **Open Library API** (legal, free, but no pirated content -- metadata only, limited downloads via controlled digital lending)

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| libgen-api-enhanced | 1.2.4 | LibGen search + download link resolution | Most complete free Python LibGen wrapper; supports fiction, non-fiction, comics, articles; configurable mirrors |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | (already in project) | HTTP requests for download | Already a project dependency; use for downloading resolved links |
| aiofiles | (already in project) | Async file writing | Already a project dependency |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| libgen-api-enhanced | libgen-api (original) | Original is simpler but lacks fiction search, fewer mirrors, less maintained |
| libgen-api-enhanced | libgen-api-modern | Modern has async support but smaller community, less battle-tested |
| libgen-api-enhanced | Anna's Archive scraping | Scraping is fragile, HTML changes break it; LibGen API is more stable |
| libgen-api-enhanced | archive_of_anna (JS) | Incomplete/undocumented, would need Node.js integration instead of Python |

**Installation:**
```bash
uv add libgen-api-enhanced
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── index.ts                    # Add `source` param to search tool schemas
├── lib/
│   ├── zlibrary-api.ts         # Existing Z-Library bridge (unchanged)
│   ├── source-router.ts        # NEW: Routes requests to correct source
│   └── fallback-manager.ts     # NEW: Fallback trigger logic + circuit breaker
lib/
├── python_bridge.py            # Add source routing to dispatch functions
├── libgen_adapter.py           # NEW: LibGen search/download via libgen-api-enhanced
├── source_adapter.py           # NEW: Abstract base class for source adapters
└── zlib_adapter.py             # NEW: Wrap existing EAPI calls in adapter interface
```

### Pattern 1: Source Adapter Interface (Python side)
**What:** Abstract base class defining search/download contract, with ZLib and LibGen implementations.
**When to use:** All source interactions go through adapters.
**Example:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class UnifiedBookResult:
    """Normalized book result across all sources."""
    title: str
    author: str
    year: Optional[str]
    language: Optional[str]
    extension: Optional[str]
    filesize: Optional[str]
    md5: Optional[str]
    source: str  # 'zlibrary' | 'libgen'
    source_id: Optional[str]  # Source-specific ID
    download_url: Optional[str]  # Resolved download link
    # Preserve source-specific extras
    extra: dict = None

class SourceAdapter(ABC):
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[UnifiedBookResult]:
        """Search for books. Returns normalized results."""
        pass

    @abstractmethod
    async def resolve_download(self, book: UnifiedBookResult) -> str:
        """Get download URL for a book result."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if source is currently reachable."""
        pass
```

### Pattern 2: Source Router (TypeScript side)
**What:** Determines which source to use based on `source` parameter and fallback logic.
**When to use:** Every search/download request.
**Example:**
```typescript
type SourceType = 'zlibrary' | 'libgen' | 'auto';

interface SourceRouterConfig {
  defaultSource: SourceType;  // from env var
  fallbackEnabled: boolean;   // from env var
  parallelMode: boolean;      // from env var
}

function resolveSource(requestedSource: SourceType, config: SourceRouterConfig): SourceType[] {
  if (requestedSource !== 'auto') return [requestedSource];
  if (config.parallelMode) return ['zlibrary', 'libgen'];
  return [config.defaultSource]; // fallback handled by error path
}
```

### Pattern 3: Fallback via Existing Circuit Breaker
**What:** Reuse existing `circuit-breaker.ts` and `retry-manager.ts` for fallback triggers.
**When to use:** When Z-Library call fails and `source` is `auto`.
**Example:**
```typescript
// In source-router.ts
async function searchWithFallback(query, params, config) {
  const primarySource = config.defaultSource === 'auto' ? 'zlibrary' : config.defaultSource;
  try {
    return await callSource(primarySource, query, params);
  } catch (error) {
    if (config.fallbackEnabled && isFallbackTrigger(error)) {
      const fallbackSource = primarySource === 'zlibrary' ? 'libgen' : 'zlibrary';
      return await callSource(fallbackSource, query, params);
    }
    throw error;
  }
}
```

### Anti-Patterns to Avoid
- **Mixing partial results from two sources in a single fallback:** Context decision says clean switch only. Never merge Z-Library partial results with LibGen results on fallback.
- **Creating separate MCP tools per source:** Context decision says use `source` parameter on existing tools.
- **Hardcoding mirror URLs:** Both Z-Library and LibGen have domain instability. Always use env var configuration.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LibGen search + download | Custom web scraper | `libgen-api-enhanced` | Handles mirror rotation, HTML parsing, download link resolution, multiple search topics |
| Result deduplication (parallel mode) | Custom dedup logic | MD5 hash comparison | LibGen and Z-Library books often share MD5 hashes; simple dict merge on MD5 |
| Download link resolution | Manual mirror page scraping | `libgen-api-enhanced` `resolve_direct_download_link()` | Handles mirror page parsing, fallback links |
| Retry/circuit-breaker | New retry system | Existing `retry-manager.ts` + `circuit-breaker.ts` | Already battle-tested in this codebase |

**Key insight:** The hardest part of LibGen integration is already solved by `libgen-api-enhanced`. The real work is the source abstraction layer and fallback orchestration, not the LibGen interaction itself.

## Common Pitfalls

### Pitfall 1: LibGen Mirror Instability
**What goes wrong:** Default mirror goes down, all searches fail.
**Why it happens:** LibGen regularly rotates/loses domains due to legal pressure.
**How to avoid:** Make mirror configurable via env var (`LIBGEN_MIRROR`). Default to `.li` but allow override. Log warning when mirror is unreachable.
**Warning signs:** Connection timeouts, HTTP 403/503 responses.

### Pitfall 2: Schema Mismatch Between Sources
**What goes wrong:** Z-Library returns different field names/structures than LibGen. Code assumes one schema.
**Why it happens:** Each source has its own data model.
**How to avoid:** Normalize ALL results into `UnifiedBookResult` at the adapter boundary. Never pass source-specific data structures above the adapter layer.
**Warning signs:** TypeError/KeyError in downstream code when switching sources.

### Pitfall 3: Download Source Inference
**What goes wrong:** User searches on Z-Library, gets results, tries to download. Code doesn't know which source the book came from.
**Why it happens:** Book results need to carry source metadata for download routing.
**How to avoid:** Always include `source` field in search results. Download function reads `source` from book metadata to route to correct adapter.
**Warning signs:** Download fails with "book not found" when using wrong source's download method.

### Pitfall 4: Rate Limiting Differences
**What goes wrong:** LibGen has different (often stricter) rate limits than Z-Library. Fallback floods LibGen.
**Why it happens:** No per-source rate limiting.
**How to avoid:** Add small delay between LibGen requests. `libgen-api-enhanced` already handles some of this, but add defensive delays for burst scenarios.
**Warning signs:** HTTP 429 or CAPTCHAs from LibGen mirrors.

### Pitfall 5: libgen-api-enhanced Is Synchronous
**What goes wrong:** Blocking the event loop in Python bridge.
**Why it happens:** `libgen-api-enhanced` uses synchronous `requests` library internally.
**How to avoid:** Run LibGen calls in `asyncio.to_thread()` or use `loop.run_in_executor()`. The Python bridge already uses asyncio, so wrap sync calls.
**Warning signs:** Slow responses, event loop blocking warnings.

## Code Examples

### LibGen Search via libgen-api-enhanced
```python
# Source: https://github.com/onurhanak/libgen-api-enhanced README
from libgen_api import LibgenSearch

s = LibgenSearch(mirror="li")  # Configurable mirror

# Search by title
results = s.search_title("Python Programming")

# Each result is a Book object with:
# - title, author, year, language, extension, filesize, md5
# - tor_download_link (prebuilt)
# - resolved via resolve_direct_download_link()

for book in results:
    print(f"{book.title} by {book.author} ({book.year}) [{book.extension}]")
    # Get direct download link
    link = book.resolve_direct_download_link()
```

### Wrapping Sync Library in Async Adapter
```python
import asyncio
from libgen_api import LibgenSearch

class LibgenAdapter(SourceAdapter):
    def __init__(self, mirror: str = "li"):
        self.mirror = mirror

    async def search(self, query: str, **kwargs) -> list:
        s = LibgenSearch(mirror=self.mirror)
        # Run synchronous search in thread pool
        results = await asyncio.to_thread(s.search_default, query)
        return [self._normalize(book) for book in results]

    def _normalize(self, book) -> UnifiedBookResult:
        return UnifiedBookResult(
            title=book.title,
            author=book.author,
            year=book.year,
            language=book.language,
            extension=book.extension,
            filesize=book.size,
            md5=book.md5,
            source='libgen',
            source_id=book.id,
            download_url=book.tor_download_link,
            extra={'publisher': book.publisher, 'pages': book.pages},
        )

    async def resolve_download(self, book: UnifiedBookResult) -> str:
        return await asyncio.to_thread(
            lambda: LibgenSearch(mirror=self.mirror)
                    ._resolve_from_md5(book.md5)
        )

    async def health_check(self) -> bool:
        try:
            results = await asyncio.to_thread(
                LibgenSearch(mirror=self.mirror).search_title, "test"
            )
            return results is not None
        except Exception:
            return False
```

### Environment Variables
```bash
# Source configuration
BOOK_SOURCE_DEFAULT=auto          # 'auto' | 'zlibrary' | 'libgen'
BOOK_SOURCE_FALLBACK_ENABLED=true # Enable fallback on primary failure
BOOK_SOURCE_PARALLEL=false        # Query both sources simultaneously

# LibGen configuration
LIBGEN_MIRROR=li                  # Mirror extension (li, bz, gs, etc.)

# Existing Z-Library config (unchanged)
ZLIBRARY_EMAIL=...
ZLIBRARY_PASSWORD=...
ZLIBRARY_MIRROR=...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Anna's Archive free web access | Donation-gated JSON API | ~2024-2025 | API key required for reliable programmatic access |
| Single LibGen mirror | Configurable mirrors with `.li` default | libgen-api-enhanced 1.2.4, Oct 2025 | Better resilience to domain changes |
| AsyncZlib (removed Phase 8) | EAPI client | Phase 8 completion | Clean adapter boundary possible |
| Direct API calls | Source adapter pattern | This phase | Enables multi-source with fallback |

**Deprecated/outdated:**
- Anna's Archive `.org` and `.se` domains (suspended Jan 2026 due to injunction)
- `libgen-api` original (fewer features, less maintained than enhanced fork)
- Web scraping Anna's Archive (fragile, injunction risk)

## Open Questions

1. **libgen-api-enhanced exact API for download resolution**
   - What we know: Library provides `resolve_direct_download_link()` and `tor_download_link`
   - What's unclear: Exact reliability of download resolution across mirrors; whether it handles CAPTCHA challenges
   - Recommendation: Test during plan 12-01 implementation; add retry/fallback to different mirror on download failure

2. **LibGen fiction vs non-fiction search**
   - What we know: `libgen-api-enhanced` supports `SearchTopic.FICTION` and `SearchTopic.LIBGEN` (non-fiction)
   - What's unclear: Whether default search covers both fiction and non-fiction, or needs separate calls
   - Recommendation: Test `search_default()` scope; may need to search both topics and merge

3. **Deduplication in parallel mode**
   - What we know: Many books exist on both Z-Library and LibGen with same MD5
   - What's unclear: How reliable MD5 matching is for dedup across sources
   - Recommendation: Use MD5 as primary dedup key; fall back to title+author fuzzy match

4. **Anna's Archive as future addition**
   - What we know: API requires donation; web scraping is fragile
   - What's unclear: Whether a minimal donation unlocks sufficient API access
   - Recommendation: Design adapter interface to support future Anna's Archive adapter; don't close the door

## Sources

### Primary (HIGH confidence)
- libgen-api-enhanced GitHub README -- search API, mirror config, download resolution
- SearXNG Anna's Archive engine source -- confirms no official API, documents HTML scraping approach
- annas-mcp GitHub -- confirms API key required for Anna's Archive JSON API

### Secondary (MEDIUM confidence)
- [Anna's Archive Wikipedia](https://en.wikipedia.org/wiki/Anna's_Archive) -- Jan 2026 injunction, domain suspensions
- [RapidAPI Anna's Archive](https://rapidapi.com/tribestick-tribestick-default/api/annas-archive-api) -- third-party wrapper exists but is paid
- [libgen-api-enhanced PyPI](https://pypi.org/project/libgen-api-enhanced/) -- v1.2.4, Oct 2025 release confirmed
- [SkyWork deep dive](https://skywork.ai/skypage/en/anna-archive-mcp-server-ai-engineer-dive/1980535272370720768) -- confirms donation required

### Tertiary (LOW confidence)
- [archive_of_anna GitHub](https://github.com/shetty-tejas/archive_of_anna) -- incomplete JS wrapper, TODO-heavy docs
- Various "alternatives" blog posts -- general landscape awareness

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM -- libgen-api-enhanced is well-documented but needs hands-on validation of download flow
- Architecture: HIGH -- source adapter pattern is well-understood; existing codebase has clear adapter boundaries (EAPI client)
- Pitfalls: MEDIUM -- based on domain experience with shadow library APIs, not direct testing

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (30 days -- LibGen mirrors may shift; legal landscape volatile)

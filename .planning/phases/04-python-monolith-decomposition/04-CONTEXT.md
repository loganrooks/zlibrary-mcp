# Phase 4: Python Monolith Decomposition - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Break `rag_processing.py` (4,968 lines) into domain modules under `lib/rag/`, with a thin facade at `rag_processing.py` that re-exports all 16 public API functions. All existing imports and tests must continue working unchanged. The Node.js-to-Python bridge must remain intact.

</domain>

<decisions>
## Implementation Decisions

### Module boundaries
- Claude determines the optimal module split based on code analysis (roadmap's 8-module suggestion is guidance, not a constraint)
- Cross-cutting code placement decided by dependency analysis
- 500-line limit per module (700 for footnotes) is a soft guideline — prefer clean boundaries over strict line counts
- Claude judges what light cleanup is safe during extraction

### Type hints & documentation
- Add type hints to the 16 public API functions exported through the facade
- Each new module gets a brief module-level docstring explaining its responsibility

### Migration strategy
- Claude determines incremental vs all-at-once approach and commit granularity based on code complexity
- Success criteria are authoritative: "no test file modifications" means the facade must cover all existing imports
- Claude analyzes what references `rag_processing.py` to determine if the filename must stay
- Docker/Dockerfile updates handled based on actual file structure (`lib/rag/` nested under `lib/`)

### Naming & structure
- Claude picks module naming style, directory depth (flat vs nested), and orchestrator module name based on Python conventions and code analysis
- Processor organization (single vs per-format) determined by actual code size and coupling

### Shared state & dependencies
- Circular dependencies resolved per case (extract shared code or lazy imports as appropriate)
- Module-level globals (regexes, caches) placed based on actual usage patterns
- Constants centralized or kept local based on sharing analysis

### Error handling & cleanup
- Existing exception types preserved — pure structural refactor
- Dynamic patterns assessed case-by-case for safety
- Per-module loggers following Python convention (`logging.getLogger(__name__)`)
- Import performance approach (eager vs lazy) determined by actual cost analysis
- Dead code identified but Claude uses judgment on preservation vs removal
- BUG-X FIX comments and DEBUG→logging conversion: Claude decides whether to handle during extraction or as separate pass

### Claude's Discretion
- Exact module split (names, count, boundaries)
- `__all__` usage pattern
- `__init__.py` re-export strategy
- Git history preservation approach (replace-in-place vs git mv)
- `py.typed` marker inclusion
- Monkey-patching/dynamic pattern handling

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User defers all technical decisions to Claude's analysis of the actual code.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-python-monolith-decomposition*
*Context gathered: 2026-01-29*

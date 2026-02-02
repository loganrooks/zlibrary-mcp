# Phase 8 Plan 3: Docker OpenCV + EAPI Improvements Summary

**One-liner:** opencv-python-headless for Docker builds + enriched booklist/full-text search EAPI fallbacks

## Completed Tasks

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Fix Docker opencv compilation (headless variant) | 089b925 | pyproject.toml, uv.lock, Dockerfile.test |
| 2 | Improve EAPI booklist and full-text search fallbacks | 9add7ee | lib/booklist_tools.py, lib/python_bridge.py, lib/enhanced_metadata.py |

## Changes Made

### Task 1: Docker OpenCV Fix
- Replaced `opencv-python` with `opencv-python-headless` in pyproject.toml
- Headless variant provides same cv2 API without GUI dependencies
- Pre-built manylinux wheels eliminate need for C compilation in Docker
- Removed `gcc` and `python3-dev` from Dockerfile.test (no longer needed)
- Docker image builds cleanly and is slimmer

### Task 2: EAPI Fallback Improvements
- **Booklist**: Top 5 results enriched with metadata (description, categories, rating) via `get_book_info`
- **Booklist**: All results tagged with `source: "topic_search_enriched"` for consumer clarity
- **Full-text search**: Multi-strategy fallback (exact phrase -> quoted query -> standard search)
- **Full-text search**: Results tagged with `search_type: "content_fallback"` and strategy used
- Both responses include informative notes explaining EAPI limitations

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| INFRA-OPENCV-HEADLESS | Use opencv-python-headless instead of opencv-python | MCP server is headless; GUI functions unused; eliminates Docker compilation issues |
| INFRA-DOCKER-SLIM | Remove gcc/python3-dev from Dockerfile.test | Headless wheels are pre-built; no compilation needed; smaller image |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- Docker builds clean without compilation errors
- `uv run pytest` passes (pre-existing failures unchanged)
- `npm test` passes (pre-existing failure unchanged)
- Booklist and full-text search responses include source/type markers

## Duration

~3 minutes

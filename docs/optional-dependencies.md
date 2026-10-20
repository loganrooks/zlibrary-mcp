# Python dependencies

The 2.0 server installs acquisition dependencies only. Text processing, OCR,
and their optional extras have been removed, not hidden behind a flag.

| Installation | Command | Includes |
|---|---|---|
| End user | `uv sync --no-dev` | Search, metadata, original-file download |
| Contributor | `bash setup-uv.sh` | Core plus test/lint tools in the dev group |
| Deployment | `bash setup-uv.sh --deploy` | Same core as end users |

Docker uses `uv sync --frozen --no-dev`. Contributor and CI suites collect without
processing libraries. `package = false` remains required for packed npm installs.

For older text workflows, see [migration](text-processing-migration.md). A future
text add-on is not shipped by this change.

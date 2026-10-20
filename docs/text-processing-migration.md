# Text-processing migration

## Acquisition-only 2.0

The 2.0 server searches catalogues, fetches metadata, and downloads original
files. Local text extraction, OCR, document-quality analysis, and their CLI
helpers are removed. This is a major-version break, not a default-off feature.
The operator chose to preserve the text implementation separately while the
acquisition server is reduced and repaired. The five-tool interface now replaces
all old registrations; see the [tool migration table](interface-migration.md).

`download` returns `path`, `bytes`, `reused`, `transfer_skipped`, `verified`, and
`record` (the acquisition sidecar path), not a processing bundle. Remove consumers
of `processed_file_path`, `metadata_file_path`, `footnotes_file_path`,
`endnotes_file_path`, `citations_file_path`, `output_files`, `stats`,
`content_types_produced`, and `processing_error` from new-download handling.

## Saved calls

- `process_document_for_rag` is absent from `tools/list`; calling it returns a
  typed `invalid_argument` migration error without provider contact.
- All old tool names are removed, including `download_book_to_file`. Search
  again and pass the chosen row's `ref` to `download`, not `bookDetails`.
- `process_for_rag` (including `false`), malformed flag values, and **any**
  `processed_output_format` are invalid MCP arguments before login, quota use,
  or transfer. Other unknown top-level arguments are also refused.
- The internal legacy API façade alone retains its earlier false no-op for
  non-MCP callers. It is not registered as a tool and is not a migration alias.
- The advertised `download` schema is closed (`additionalProperties: false`).
  Validating clients may reject saved processing arguments themselves; remove
  those fields from saved calls before sending them.

The `rag` and `scholar` install extras no longer exist. End users run
`bash setup-uv.sh --no-dev`; contributors run `bash setup-uv.sh`; deployments
run `bash setup-uv.sh --deploy` (the same acquisition core without dev tools).
The dev extra alias remains for compatibility; the dev group is preferred.

## Keep text processing isolated

Stay on a separate pinned **1.4.x** installation until a text add-on exists.
Published 1.4.0 installed processing dependencies in its base manifest; do not
expect its environment shape to match this candidate's former optional extras.
Do not upgrade the installation you still use to extract text in place. Keep
its dependencies, launch command, configuration, and output directories separate.
No text add-on ships in this change.

Downloaded books, old extracted text, and sidecars are left in place. Updating
an npm installation can replace its Python environment, so old outputs do not
imply the old engine remains runnable. Rollback means selecting the isolated
old installation, not copying a few modules into the new one.

## Preserved implementation and unresolved work

Preservation provided by the lead before removal:

- Branch `parked/text-processing` and immutable tag
  `parked-text-processing-2026-10`, both at `25fe05a`.
- Held optical work: tag `parked-pr240-optical-2026-10` (PR #240), separately
  preserved because it was not part of master.

Future text work should port reviewed pieces from that tree, not merge back
obsolete provider/authentication code wholesale. The real-document workflow and
quality criteria remain on the preserved tree.

The following failures move with their tests and are **not fixed** by removal;
see [issue #245](https://github.com/rookslog/zlibrary-mcp/issues/245):

| Preserved test | Unresolved finding |
|---|---|
| `test_garbled_performance.py::TestPerformance::test_detection_long_text_scales_linearly` | 15 ms timing budget |
| `test_garbled_performance.py::TestPerformance::test_page_detection_under_100ms` | 100 ms timing budget |
| `test_garbled_performance.py::TestScalability::test_large_region_acceptable` | 10 ms timing budget |
| `test_real_world_validation.py::TestRealWorldSousRature::test_derrida_sous_rature_detection` | scalar unpack error in detector; held repair |

## Verification boundary

The retained test suites must collect without processing libraries. The import
trap in `scripts/check_optional_imports.py --core-smoke` exercises fake-provider
search, metadata, and download with parked imports forbidden. SDK tests reject
saved options before any subprocess starts. These offline checks do not attest
to live provider availability or qualify a separately deployed reader. The
output-root guard is now in the acquisition path; deployment and publication
remain separate from source-level changes.

## Dropped processing environment settings

`RAG_QUALITY_STRATEGY` configured the 1.4.0 processing pipeline (for example,
`technical` instead of the default `hybrid`). It has no processing effect in
2.0 because that pipeline and its tools are absent. Keeping the variable does
not restore extraction or make a saved processing call valid. Keep processing
settings with the isolated pinned 1.4.x installation; do not rename them to
acquisition settings.

The source-checkout upgrade check exercises published npm 1.4.0, a packed
candidate, and a disposable in-place rollback. It prepares 1.4.0's NLTK data
before fencing runtime networking, downloads and processes a synthetic TXT
fixture, and checks the original, extracted text and metadata bytes across npm
replacement. It reports whether a package-local environment-choice canary was
replaced; it does not promise to preserve that environment. This rollback
experiment is not a supported text-restoration command and does not replace
the separate pinned installation recommendation above. See
[the check's instructions](../scripts/README.md#upgrade-and-rollback-check).

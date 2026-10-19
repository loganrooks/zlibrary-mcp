# Scripts

| Script | Use |
|---|---|
| `validate-python-bridge.js` | Asset validation (`npm run validate`) |
| `validate-readme-tools.sh` | Compare registrations with the README tool list |
| `check_upstream.py` | Source contract probes (`npm run doctor`) |
| `release-audit.mjs` | Release-record audit; requires Git history and GitHub access |
| `check_optional_imports.py --core-smoke` | Offline acquisition import trap |
| `get_venv_python_path.mjs` | Locate the project Python interpreter |

Text-processing CLI paths are removed. See
[migration](../docs/text-processing-migration.md). Scripts in `archive/` are
historical experiments, not runnable product features.

The npm package includes validation, upstream, and release-audit scripts.
Build/lint/test/rehearsal commands require a source checkout. The release audit
also needs that checkout's Git release records.

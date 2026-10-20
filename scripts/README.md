# Scripts

| Script | Use |
|---|---|
| `validate-python-bridge.js` | Asset validation (`npm run validate`) |
| `validate-readme-tools.sh` | Compare registrations with the README tool list |
| `check_upstream.py` | Source contract probes (`npm run doctor`) |
| `release-audit.mjs` | Release-record audit; requires Git history and GitHub access |
| `check_optional_imports.py --core-smoke` | Offline acquisition import trap |
| `get_venv_python_path.mjs` | Locate the project Python interpreter |
| `check-packed-artifact.mjs --offline-providers` | Clean disposable npm install and offline installed-bin smoke (source checkout only) |

Text-processing CLI paths are removed. See
[migration](../docs/text-processing-migration.md). Scripts in `archive/` are
historical experiments, not runnable product features.

The npm package includes validation, upstream, and release-audit scripts.
Build/lint/test/rehearsal commands require a source checkout. The release audit
also needs that checkout's Git release records.

## Packed install check

After `npm run build`, run:

```bash
node scripts/check-packed-artifact.mjs --offline-providers
```

Requires Node 22+, Python 3.10+, uv and tar. Packs once (without lifecycle
hooks), installs that tarball into an empty local prefix with install hooks
disabled, and runs the documented `bash setup-uv.sh --no-dev` in the installed
package. Registry access during dependency setup is expected. No global npm
install, publish, live doctor probes or user account configuration is used.
All disposable state is removed in `finally`.

Checks every bin plus doctor/validation/start/release-audit script target, the
installed Python bridge and package-local paths, then starts npm's actual bin
link from outside the source tree. Every stdout line must be JSON-RPC. The
2.0 names and argument names must match `__tests__/fixtures/tools-surface-v2.json`.
There is no 2.0 public local-file reader; the smoke uses `get_limits` local mode
and separately imports the installed bridge. Rehearsal Node/Python network fences
are tested, then runtime must produce zero egress attempts. This is not a live
source-health check or the full fake-provider acquisition journey.

Failure controls damage the tarball **before** installing it; each must exit 1:

```bash
node scripts/check-packed-artifact.mjs --offline-providers --control=missing-bridge
node scripts/check-packed-artifact.mjs --offline-providers --control=missing-script
```

The existing pack-check stays; a separate CI job runs this smoke on Ubuntu and
macOS within the rehearsal job's 15-minute budget.

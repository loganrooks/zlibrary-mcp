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

Requires Node 22+, Python 3.10+, uv, OpenSSL and tar. Packs once, installs that
tarball into an empty local prefix with install hooks disabled, and runs the
documented `bash setup-uv.sh --no-dev` in the installed package. Registry access
during dependency setup is expected. No global npm
install, publish, live doctor probes or user account configuration is used.
All disposable state is removed in `finally`.

Pack requests lifecycle scripts disabled with both `--ignore-scripts` and
`npm_config_ignore_scripts=true`; `HUSKY=0` also disables Husky's hook setup.
Some npm versions still invoke prepare and emit a Husky skip diagnostic despite
the flag. Tarball discovery therefore requires exactly one `.tgz` file in the
pack destination and never parses npm stdout as JSON. The check does not claim
that every npm version honors lifecycle-script suppression.

Checks every bin plus doctor/validation/start/release-audit script target, the
installed Python bridge and package-local paths, then starts npm's actual bin
link from outside the source tree. Every stdout line must be JSON-RPC. The
2.0 names and argument names must match `__tests__/fixtures/tools-surface-v2.json`.
The installed bin runs `search` → `get_book` → `download` → repeated `download`
against the existing rehearsal HTTPS fake for both credential-free LibGen and
synthetic-account Z-Library. It checks exact fixture bytes, SHA-256, output path,
and the complete `.acq.json` receipt. The repeated call must hit that receipt
without any additional fake-provider calls or quota spend, and must preserve
the artifact and receipt bytes. LibGen's initial acquisition includes a range
probe before the full stream; both requests are counted.

`Rehearsal.start()` supplies fake startup/certificates/cleanup, and its shared
`providerEnvironment()` supplies endpoints, trust and the Python fence. The
LibGen URL seam covers both requests-based search and httpx-based resolution
and streaming; production provider code is unchanged. Node/Python network
fences are tested, then runtime must produce zero non-loopback egress attempts.
Only the fake's exact loopback port is admitted. This is not a live-source
health check. All output, account state and fake-server state is disposable.

The first two controls damage the tarball **before** installing it. The third
allows search/details but makes the fake file endpoint return no bytes. Each
must exit 1:

```bash
node scripts/check-packed-artifact.mjs --offline-providers --control=missing-bridge
node scripts/check-packed-artifact.mjs --offline-providers --control=missing-script
node scripts/check-packed-artifact.mjs --offline-providers --control=drop-transfer
```

The existing pack-check stays; a separate CI job runs this smoke on Ubuntu and
macOS within the rehearsal job's 15-minute budget.

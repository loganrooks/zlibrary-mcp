# Offline built-server rehearsal

This candidate harness runs the real built Node server and Python bridge. Only the
EAPI service is fake. It uses a disposable, locally trusted HTTPS certificate,
synthetic credentials, temporary downloads, and the official SDK over stdio.
No installation, account, upstream service or ChatGPT messages are needed.

## Run

Requires the repository's existing Node dependencies, `.venv`, built `dist/`, and
`openssl` with `req -addext` support. Nothing is installed by this command.

```sh
npm run build
npm run test:rehearsal
```

The default is **master characterization**, with eight isolated expected failures:
login reuse, rejection refresh, four ambiguity/recovery login-count checks, and
two sentinel scans. Correlation, transfer, topology, outage behavior, TLS rejection,
and retry-budget checks must pass normally. An expected failure that starts passing
makes Jest fail, so a fixed server cannot silently keep using master expectations.

The command writes `test_output/rehearsal-manifest.json` (ignored by Git), including
source SHA, built-entrypoint hash, required/executed case counts, Node PIDs,
synthetic session epochs, endpoint counters, login attempts and successes, and
sentinel findings without values. Skipped, missing, duplicate or failed cases make
the aggregate exit nonzero. The default run has 20 required cases and takes less
than two minutes on the measured macOS environment.

To test another **already built** tree without editing it:

```sh
REHEARSAL_SERVER_ROOT=/absolute/path/to/tree \
REHEARSAL_EXPECT_REUSE=1 \
REHEARSAL_RESULT_FILE=/absolute/path/to/receipt.json \
npm run test:rehearsal
```

The selected tree's `.venv/bin/python` is used by both the fake and the real
bridge; the bridge locates its own venv through the unchanged product resolver.
`REHEARSAL_EXPECT_REUSE=1` makes all assertions ordinary assertions, including the
no-unprotected-sentinel checks.

## Cases

- S1: search → metadata → limits → exact TXT download → history.
- S2: five outstanding calls on **one SDK connection and one stable Node PID**;
  fake maximum-inflight count must exceed one; unique titles detect swapped replies.
- S3: two SDK connections, each with its own Node process and isolated state.
  This is not multiple chats sharing a backend.
- S4: five authentication failures open the existing shared breaker. A sixth
  EAPI call and local document-processing call are blocked without further HTTP;
  protocol tool listing still works. Alternate-source independence is not tested.
- S5: observed tool names and argument names; `tools-surface.json` is the initial
  observed snapshot, **not an approved 2.0 surface**. Set
  `REHEARSAL_SURFACE_FILE=/absolute/path.json` to capture the current target.
- E1: warm one identity, reject its cookie epoch, then five overlapping callers;
  one successful refresh is required on the session-reuse target.
- E2: warm one identity; inject timeout, wall, ambiguous operation 400, or
  `success:0` with populated user; recover; no additional login is allowed.
- E3: invalid login makes one attempt and zero successful logins with retries off.
- TLS control: removing `SSL_CERT_FILE` must reject the disposable certificate
  before any EAPI request reaches the fake.

The normal bridge deadline is 15 seconds, reduced to 6 seconds in ambiguity cases
so the timeout check is bounded. Retries are explicitly disabled; this is not a
measurement of default production retry settings. The runner deadline is 115 seconds.

## Negative controls

```sh
# Deliberately inject one skipped result. Must exit 1 (19/20 executed).
npm run test:rehearsal -- --self-test-skipped

# Remove usable cookies from login JSON. S1 itself must fail, not just the manifest.
REHEARSAL_DROP_COOKIES=1 node --experimental-vm-modules \
  node_modules/jest/bin/jest.js \
  --config __tests__/rehearsal/jest.config.js \
  --testPathPatterns rehearsal.test.js --testNamePattern '^S1 '
```

## Isolation and limitations

`sitecustomize.py` is loaded only by harness children via `PYTHONPATH`. It permits
only the fake's exact loopback address/port and local Unix sockets. A test-only
Node preloader blocks Node DNS/network connections and redirects legacy absolute
debug-file writes into each temporary home. Any detected outbound attempt writes
a trap that fails the scenario, even if product code catches the exception.
Children receive an allowlisted environment with no proxy or real credential
settings; Python bytecode writes are disabled. This is a language-level guard,
not an OS network namespace or defence against malicious native extensions.

Replies, captured Node/bridge error stderr, and scenario output files are scanned
for synthetic password, identity, cookie and CA-private-key sentinels. Protected
`session/eapi-session.json` files intentionally contain the synthetic identity and
cookies: their private mode is checked, their password absence is asserted, and
their count is reported separately. Generated CA material and these intended
session stores are not claimed to be secret-free output. All temporary state is
removed after the run. Master logs its cookie ID; the independent master sentinel
checks explicitly expose this known failure rather than hiding it in login checks.

No product source or TLS verification is changed. No live provider, tunnel, packed
installation, Linux CI, default retry policy, identity rotation, or alternate-source
search/download is qualified by this harness. The addendum's priority exception
leaves the alternate-source fixture for a separate slice.

## Format and lint

The repository normally ignores test files in formatter/linter discovery, so use
explicit overrides:

```sh
node node_modules/prettier/bin/prettier.cjs --ignore-path /dev/null --check '__tests__/rehearsal/*.{js,mjs,json}'
node node_modules/eslint/bin/eslint.js --no-ignore --config __tests__/rehearsal/eslint.config.js '__tests__/rehearsal/*.{js,mjs}'
.venv/bin/ruff format --check __tests__/rehearsal/*.py
.venv/bin/ruff check __tests__/rehearsal/*.py
```

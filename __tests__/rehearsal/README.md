# Offline built-server rehearsal

Runs the real built MCP server and Python bridge against a local HTTPS EAPI and
Library Genesis HTML fixture. Credentials and certificates are synthetic. No live
provider calls, account, ChatGPT messages, installation or global CA change.

## Run

Requires existing Node dependencies, `.venv`, `dist/`, and `openssl req -addext`.

```sh
npm run build
npm run test:rehearsal
```

Rehearsal is excluded from default Jest discovery. Its dedicated configuration has
a 30-second case deadline and serial suites; the runner bounds execution to 115
seconds plus a two-second shutdown grace. The manifest defaults to ignored
`test_output/rehearsal-manifest.json`; override with `REHEARSAL_RESULT_FILE`.

### Independent feature expectations

```sh
REHEARSAL_EXPECT=reuse,redaction,breaker npm run test:rehearsal
```

Omit a name until that feature's fix is expected:

- `reuse`: cold reuse, rejection single-flight, no additional login after ambiguity.
- `redaction`: no occurrence of the known cookie-ID authentication message in
  captured stderr or `client-N/logs/zlibrary_debug.log`.
- `breaker`: local document processing and Library Genesis search succeed while
  the EAPI breaker is open.

Absent features use isolated expected-failure assertions. Password, cookie-key,
CA-private-key, identity, and all other cookie-ID findings **always fail**. A known
authentication message cannot hide a new password or unrelated cookie-ID leak.
The lead's ruling treats the same known authentication message in captured stderr
and the debug file as one expected baseline defect, including quoted copies in
bridge errors. Every ID on an allowed line must belong to that message; other
sources and unrelated ID output fail. Both allowed locations must be zero when
`redaction` is enabled. `REHEARSAL_EXPECT_REUSE=1` remains a deprecated compatibility spelling
for `REHEARSAL_EXPECT=reuse,redaction`, not for breaker independence.

Another already-built target can be selected without editing it:

```sh
REHEARSAL_SERVER_ROOT=/absolute/path/to/tree \
REHEARSAL_EXPECT=reuse,redaction \
REHEARSAL_RESULT_FILE=/absolute/path/receipt.json npm run test:rehearsal
```

The target's own `.venv/bin/python` is used. A comparison tree is not assumed to
be frozen: SHA, full porcelain status, and deterministic hashes of **all files in
`dist/` and `lib/`** are captured before and after execution. Any difference or
unreadable end snapshot makes the aggregate nonzero. This is an endpoint check,
not a continuous filesystem lock or an atomic snapshot.

## Cases and receipts

There are 32 mandatory cases, including scanner/source-identity contracts. The
manifest records expected/executed counts, ordinary versus per-fix expected
outcomes, endpoint/login-attempt/login-success counts, fake cookie epochs, stable
Node PIDs, and categorized sentinel findings without their values. Missing,
skipped, duplicate and failed cases cannot produce a green aggregate.

- S1: search → metadata → quota → exact TXT download inside temp storage → history.
- S2: five outstanding calls over one SDK connection and one stable Node PID;
  distinct titles catch swapped responses, and fake max-inflight must exceed one.
- S3: two independent Node processes and isolated state, not several chats sharing
  one backend.
- S4: EAPI outage opens its breaker; protocol listing survives. Independent
  assertions require local document processing and Library Genesis search to work.
- S5: names/argument names equal `tools-surface.json`, an observed baseline, not an
  approved 2.0 surface. A deliberate surface change must update the snapshot.
- S6: healthy Library Genesis search goes through the real third-party parser,
  returns a hand-authored HTML record, and makes zero EAPI login attempts.
- E1–E3: overlapping refresh, four ambiguity/recovery cases, and invalid credentials
  within the explicit zero-retry budget. Master ambiguity counts reflect fresh
  per-call logins; they do not isolate retry-after-failure behavior.
- TLS: removing `SSL_CERT_FILE` rejects the certificate before EAPI dispatch.
- Contracts: a no-cookie search must get 401, stdin EOF must terminate the fake,
  and a PID mismatch must not prevent remaining client cleanup.

## Negative controls

```sh
# Synthetic controller results: these must both exit 1.
npm run test:rehearsal -- --self-test-skipped
npm run test:rehearsal -- --self-test-source-drift

# Selected S1 must itself fail after usable cookies are removed.
REHEARSAL_DROP_COOKIES=1 node --experimental-vm-modules \
  node_modules/jest/bin/jest.js --config __tests__/rehearsal/jest.config.js \
  --testPathPatterns rehearsal.test.js --testNamePattern '^S1 '
```

The focused scanner contract combines the known ID log with password, cookie-key
and CA-key mutations. All three remain unexpected even in master mode.

## Isolation and cleanup

The runner owns one temporary root for records, fake certificates and all child
state. It removes that root after normal execution, timeout, or handled termination.
The fake follows its owner's stdin and exits on EOF. Cleanup attempts every client
before reporting PID or close errors. Direct SIGKILL of the runner cannot execute
JavaScript cleanup; no OS-level teardown guarantee is claimed for that case.

Test-only Python startup guards permit the fake's exact local address/port and
Unix sockets. A Node preloader blocks Node DNS/network calls and redirects legacy
absolute debug writes into temporary homes. A recorded outbound attempt fails the
scenario even if product code catches its exception. These are language-level
fences, not an OS network namespace or malicious-native-code defence.

The Library Genesis seam rewrites only the three adapter mirror URLs, inside
`requests.Session.request`, to `/libgen/index.php` on the same HTTPS fake. It does
not replace the Node bridge, provider adapter or HTML parser. Preflight is disabled
only for those fixture-enabled scenarios; unrelated URLs remain fenced. Search
only is covered, not Library Genesis download resolution/transfer.

Replies, captured stderr and scenario files are scanned. Protected synthetic
`session/eapi-session.json` stores intentionally contain the fake identity/cookies;
private mode, exact synthetic values and absence of other secret fields are
checked separately. The generated CA/key and these intentional private stores are
not called secret-free output. No product TLS verification is disabled.

The CI matrix adds Ubuntu/macOS with Node 22 and uploads the manifest even on
failure. Hosted execution is pending the lead's draft PR. No local Node-22/Linux,
real tunnel, hosted connector, packed-install, live quota, identity-rotation, or
memory-only/no-disk acceptance is implied by a local run.

## Format and lint

```sh
node node_modules/prettier/bin/prettier.cjs --ignore-path /dev/null --check '__tests__/rehearsal/*.{js,mjs,json}'
node node_modules/eslint/bin/eslint.js '__tests__/rehearsal/*.{js,mjs}'
.venv/bin/ruff format --check __tests__/rehearsal/*.py
.venv/bin/ruff check __tests__/rehearsal/*.py
```

The root ESLint configuration now owns the rehearsal rules; all other existing
test exclusions remain unchanged.

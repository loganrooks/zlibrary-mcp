# Live pytest JUnit shapes

Recorded offline on 2026-10-20 using pytest 9.1.1 and the vendored EAPI decoder.
`cases.py` deliberately raises exceptions without contacting any provider. It is
named so ordinary pytest discovery does not collect these deliberate failures.

Generate in a scratch directory, using the existing project venv (no installs):

```bash
cp __tests__/python/fixtures/live-junit/cases.py /tmp/live-junit-cases.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -c /dev/null \
  /tmp/live-junit-cases.py --junitxml=/tmp/live-junit.xml -q
```

Exit 1 is expected. The checked-in XML removes suite timestamps/hostname and
durations, replaces the scratch source path with `<scratch>/cases.py`, and sets
the testcase class name to `offline_live_cases`. Exception message attributes
are unchanged. In particular, bare setup failures are
`failed on setup with "httpx.ConnectError"` and
`failed on setup with "httpx.ConnectTimeout"`, with no colon.

The classifier tests extract the real message attributes, then combine them
into focused reports. The original generation logs and raw XML are retained in
the fix296 lane scratch directory, alongside the first generation log, which records the initially omitted
httpx empty-string message argument and its subsequent correction.

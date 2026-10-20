"""Offline status/reporting contracts for the scheduled credentialed suite."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "classify_live_tests.py"
BLOCK_REASON = "blocked by the anti-bot wall on this runner's IP, not upstream drift"


@pytest.fixture(scope="module")
def classifier():
    spec = importlib.util.spec_from_file_location("classify_live_tests", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_report(tmp_path, problems=(), *, skipped=False):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite")
    case = ET.SubElement(suite, "testcase", name="test_contract")
    for tag, message in problems:
        ET.SubElement(case, tag, message=message).text = "traceback body"
    if skipped:
        ET.SubElement(case, "skipped")
    report = tmp_path / "live.xml"
    ET.ElementTree(root).write(report, encoding="unicode")
    return report


WALL = ("failure", "zlibrary.eapi.DiamWallError: HTTP 517 DiamWall block page")
CONNECT_SETUP = (
    "error",
    'failed on setup with "httpx.ConnectError: All connection attempts failed"',
)


@pytest.mark.parametrize("problem", [WALL, CONNECT_SETUP])
def test_blocked_only_is_not_failure(classifier, tmp_path, problem):
    result = classifier.classify(1, write_report(tmp_path, [problem]))
    assert result["status"] == "blocked"
    assert result["blocked"] is True
    assert BLOCK_REASON in result["detail"]


@pytest.mark.parametrize(
    "problem",
    [
        ("failure", "AssertionError: expected books to be a list"),
        ("failure", "KeyError: 'books'"),
        ("failure", "json.decoder.JSONDecodeError: Expecting value"),
        ("failure", "ValueError: parser regression"),
        ("failure", "httpx.ConnectError: connection during a test call"),
        ("error", 'failed on teardown with "httpx.ConnectError: connection"'),
        ("error", 'failed on setup with "KeyError: books"'),
        ("error", "collection failure: ImportError"),
        ("failure", "AssertionError: expected DiamWallError but parser regressed"),
        ("failure", "AssertionError: httpx.ConnectError appeared in a response"),
        ("failure", "ExceptionGroup: DiamWallError and KeyError"),
    ],
)
@pytest.mark.parametrize("alongside_wall", [False, True])
def test_real_failures_win_even_alongside_a_block(
    classifier, tmp_path, problem, alongside_wall
):
    problems = [problem, WALL] if alongside_wall else [problem]
    result = classifier.classify(1, write_report(tmp_path, problems))
    assert result["status"] == "failed"
    assert result["blocked"] is alongside_wall
    if alongside_wall:
        assert BLOCK_REASON in result["detail"]


def test_cause_in_traceback_does_not_hide_terminal_parser_error(classifier, tmp_path):
    report = write_report(tmp_path, [("failure", "KeyError: 'books'")])
    tree = ET.parse(report)
    tree.find(
        ".//failure"
    ).text = "zlibrary.eapi.DiamWallError: earlier cause\nKeyError: books"
    tree.write(report)
    assert classifier.classify(1, report)["status"] == "failed"


@pytest.mark.parametrize("exit_code", [2, 3, 4, 5, -9, 127])
def test_non_test_failure_exit_codes_cannot_be_hidden(classifier, tmp_path, exit_code):
    assert (
        classifier.classify(exit_code, write_report(tmp_path, [WALL]))["status"]
        == "failed"
    )


@pytest.mark.parametrize("content", [None, "", "<incomplete", "<testsuites/>"])
def test_missing_or_invalid_evidence_fails_closed(classifier, tmp_path, content):
    report = tmp_path / "invalid.xml"
    if content is not None:
        report.write_text(content)
    assert classifier.classify(1, report)["status"] == "failed"


def test_passing_suite(classifier, tmp_path):
    assert classifier.classify(0, write_report(tmp_path))["status"] == "passed"


def test_cli_emits_status_block_flag_and_summary(tmp_path):
    report = write_report(tmp_path, [CONNECT_SETUP])
    output = tmp_path / "github-output"
    summary = tmp_path / "summary"
    run = subprocess.run(
        [sys.executable, str(SCRIPT), "--exit-code", "1", "--junitxml", str(report)],
        env={
            **os.environ,
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(summary),
        },
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert "status=blocked\n" in output.read_text()
    assert "blocked=true\n" in output.read_text()
    assert BLOCK_REASON in summary.read_text()


def test_actual_pytest_reports_are_classified_offline(classifier, tmp_path):
    """Exercise pytest's real setup/call messages, not only hand-written XML."""
    source = tmp_path / "test_synthetic.py"
    source.write_text(
        "import pytest\nimport httpx\nfrom zlibrary.eapi import DiamWallError\n"
        "@pytest.fixture\ndef refused():\n    raise httpx.ConnectError('offline')\n"
        "def test_setup(refused):\n    pass\n"
        "def test_wall():\n    raise DiamWallError('HTTP 517 DiamWall block page')\n"
        "def test_drift():\n    assert 'books' in {'success': 1}\n"
    )
    report = tmp_path / "actual.xml"
    for selection, expected in [("not drift", "blocked"), ("", "failed")]:
        run = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-c",
                "/dev/null",
                str(source),
                "-k",
                selection,
                f"--junitxml={report}",
                "-q",
            ],
            env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
            capture_output=True,
            text=True,
        )
        assert run.returncode == 1, run.stdout + run.stderr
        result = classifier.classify(run.returncode, report)
        assert result["status"] == expected
        assert result["blocked"] is True


@pytest.fixture(scope="module")
def workflow():
    run = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            "import fs from 'node:fs'; import YAML from 'yaml'; "
            "console.log(JSON.stringify(YAML.parse(fs.readFileSync(process.argv[1], 'utf8'))));",
            str(ROOT / ".github/workflows/upstream-check.yml"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(run.stdout)


@pytest.mark.parametrize(
    "problems,expected",
    [([WALL], "blocked"), ([WALL, ("failure", "KeyError: books")], "failed")],
)
def test_workflow_live_step_classifies_and_retains_evidence(
    workflow, tmp_path, problems, expected
):
    report = write_report(tmp_path, problems)
    report = report.rename(tmp_path / "recorded.xml")
    output = tmp_path / "github-output"
    fake_uv = tmp_path / "uv"
    # Replace only the provider-facing pytest invocation. Run the production
    # classifier and the exact workflow shell, with the recorded pytest result.
    fake_uv.write_text(
        f"#!{sys.executable}\nimport os, sys, shutil\nfrom pathlib import Path\n"
        "if sys.argv[1:3] == ['run', 'pytest']:\n"
        "    shutil.copyfile(os.environ['SYNTHETIC_REPORT'], 'live.xml')\n"
        "    print('offline pytest log')\n    sys.exit(1)\n"
        "assert sys.argv[1:3] == ['run', 'python']\n"
        f"os.execv(sys.executable, [sys.executable, str(Path({str(ROOT)!r}) / sys.argv[3]), *sys.argv[4:]])\n"
    )
    fake_uv.chmod(0o755)
    step = next(
        s for s in workflow["jobs"]["live_tests"]["steps"] if s.get("id") == "live"
    )
    run = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "ZLIBRARY_EMAIL": "offline@example.test",
            "ZLIBRARY_PASSWORD": "offline",
            "ZLIB_BLOCKED": "false",
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
            "SYNTHETIC_REPORT": str(report),
        },
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert f"status={expected}\n" in output.read_text()
    assert "blocked=true\n" in output.read_text()
    assert "offline pytest log" in (tmp_path / "live.log").read_text()


@pytest.mark.parametrize("blocked,failed", [(True, False), (True, True), (False, True)])
def test_workflow_issue_gate_and_body(workflow, blocked, failed):
    # Execute the real report condition and github-script body against a local
    # GitHub API double: no credentials, requests, comments or issue writes.
    needs = {
        "reachability": {
            "result": "success",
            "outputs": {"failed": "false", "zlib_blocked": "false"},
        },
        "live_tests": {
            "result": "failure" if failed else "success",
            "outputs": {
                "status": "failed" if failed else "blocked",
                "blocked": str(blocked).lower(),
            },
        },
    }
    report = workflow["jobs"]["report"]
    step = report["steps"][0]
    # Resolve the actual env expressions for the contexts used by this job.
    env = {}
    for key, value in step["env"].items():
        if value.startswith("${{ needs."):
            parts = value.removeprefix("${{ ").removesuffix(" }}").split(".")
            resolved = {"needs": needs}
            for part in parts:
                resolved = resolved.get(part, "") if isinstance(resolved, dict) else ""
            env[key] = resolved
    runner = """
const fs = require('fs');
const data = JSON.parse(fs.readFileSync(0, 'utf8'));
const enabled = new Function('needs', 'github', 'always', 'return ' + data.condition)(data.needs, {event_name:'schedule'}, () => true);
let body = '';
const github = {rest: {issues: {
  listForRepo: async () => ({data: []}),
  create: async value => { body = value.body; },
}}};
const context = {serverUrl: 'https://github.example', repo: {owner:'example', repo:'offline'}, runId: 1};
Object.assign(process.env, data.env);
(async () => {
  if (enabled) await new (Object.getPrototypeOf(async function(){}).constructor)('github', 'context', data.script)(github, context);
  console.log(JSON.stringify({enabled, body}));
})().catch(error => { console.error(error); process.exit(1); });
"""
    run = subprocess.run(
        ["node", "-e", runner],
        input=json.dumps(
            {
                "condition": report["if"],
                "script": step["with"]["script"],
                "needs": needs,
                "env": env,
            }
        ),
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(run.stdout)
    assert result["enabled"] is failed
    if failed:
        assert (BLOCK_REASON in result["body"]) is blocked

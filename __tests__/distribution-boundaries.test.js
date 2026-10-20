/** Acquisition-only packaging and installation contracts. */

import { execFileSync, spawnSync } from 'child_process';
import {
  chmodSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'fs';
import os from 'os';
import path from 'path';
import { fileURLToPath } from 'url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

describe('distribution boundaries', () => {
  function runSetupUv(args, { pythonVersion = [3, 10], uvVersion = '0.8.22' } = {}) {
    const tempDir = mkdtempSync(path.join(os.tmpdir(), 'zlibrary-setup-uv-'));
    const binDir = path.join(tempDir, 'bin');
    const callLog = path.join(tempDir, 'uv-calls.log');

    try {
      mkdirSync(binDir, { recursive: true });
      const pythonStub = path.join(binDir, 'python3');
      const python = execFileSync('python3', ['-c', 'import sys; print(sys.executable)'], {
        encoding: 'utf8',
      }).trim();
      // Execute the script's real comparison with a controlled version tuple.
      writeFileSync(pythonStub, `#!${python}\nimport sys\nfrom collections import namedtuple\nsys.version_info = namedtuple('VersionInfo', 'major minor micro releaselevel serial')(${pythonVersion[0]}, ${pythonVersion[1]}, 0, 'final', 0)\ncode = sys.argv[2]\nsys.argv = ['-c', *sys.argv[3:]]\nexec(code)\n`);
      chmodSync(pythonStub, 0o755);

      // A runner without version-sort must still admit supported versions.
      const sortStub = path.join(binDir, 'sort');
      writeFileSync(sortStub, '#!/bin/sh\nprintf "sort: unsupported option -V\\n" >&2\nexit 2\n');
      chmodSync(sortStub, 0o755);

      const uvStub = path.join(binDir, 'uv');
      writeFileSync(
        uvStub,
        [
          '#!/bin/sh',
          `if [ "$1" = "--version" ]; then printf "uv ${uvVersion}\\n"; exit 0; fi`,
          'printf "%s\\n" "$*" >> "$UV_CALL_LOG"',
          'mkdir -p .venv/bin',
          'printf "#!/bin/sh\\nexit 0\\n" > .venv/bin/python',
          'chmod +x .venv/bin/python',
          '',
        ].join('\n'),
      );
      chmodSync(uvStub, 0o755);

      const result = spawnSync('bash', [path.join(projectRoot, 'setup-uv.sh'), ...args], {
        cwd: tempDir,
        encoding: 'utf8',
        env: {
          ...process.env,
          PATH: `${binDir}:${process.env.PATH}`,
          UV_CALL_LOG: callLog,
        },
      });

      return { ...result, calls: existsSync(callLog) ? readFileSync(callLog, 'utf8').trim() : '' };
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  }

  test('npm package includes the optional-dependency guide linked from the README', () => {
    const output = execFileSync(
      'npm',
      ['pack', '--dry-run', '--ignore-scripts', '--json'],
      {
        cwd: projectRoot,
        encoding: 'utf8',
        env: { ...process.env, npm_config_cache: '/tmp/zlibrary-mcp-npm-cache' },
      },
    );
    const [{ files }] = JSON.parse(output);

    expect(files.map(({ path: filePath }) => filePath)).toContain(
      'docs/optional-dependencies.md',
    );
  });

  test('Docker installs only acquisition dependencies', () => {
    const dockerfile = readFileSync(path.join(projectRoot, 'docker', 'Dockerfile'), 'utf8');

    expect(dockerfile).toMatch(/uv sync --frozen --no-dev/);
    expect(dockerfile).not.toMatch(/--all-extras/);
  });

  test('setup keeps end-user core separate from the contributor dev group', () => {
    expect(runSetupUv(['--no-dev'])).toMatchObject({ status: 0, calls: 'sync --no-dev' });
    // Contributor tools do not require a processing stack.
    expect(runSetupUv([])).toMatchObject({ status: 0, calls: 'sync --group dev' });
    // Deployment and end-user runtime dependencies match.
    expect(runSetupUv(['--deploy'])).toMatchObject({ status: 0, calls: 'sync --no-dev' });
  });

  test.each([[3, 10], [3, 15]])('setup admits Python %i.%i without sort -V', (major, minor) => {
    expect(runSetupUv(['--no-dev'], { pythonVersion: [major, minor], uvVersion: '0.4.27' }))
      .toMatchObject({ status: 0, calls: 'sync --no-dev' });
  });

  test('setup refuses Python 3.9 before dependency installation with the existing diagnostic', () => {
    const result = runSetupUv(['--no-dev'], { pythonVersion: [3, 9] });
    expect(result).toMatchObject({ status: 1, calls: '' });
    expect(result.stdout).toContain('Error: Python 3.10+ required, found 3.9');
  });

  test('setup refuses uv below 0.4.27 before syncing and retains its upgrade diagnostic', () => {
    const result = runSetupUv(['--no-dev'], { uvVersion: '0.4.26' });
    expect(result).toMatchObject({ status: 1, calls: '' });
    expect(result.stdout).toContain('Error: UV 0.4.27+ required (dev dependencies use PEP 735 [dependency-groups]), found 0.4.26');
    expect(result.stdout).toContain('Upgrade with: uv self update');
  });

  test('packed CI runs the documented core setup and rejects contributor packages', () => {
    const workflow = readFileSync(
      path.join(projectRoot, '.github', 'workflows', 'ci.yml'),
      'utf8',
    );

    expect(workflow).toMatch(
      /cd "\$EXTRACT\/package"[\s\S]*bash setup-uv\.sh --no-dev[\s\S]*importlib\.util\.find_spec\('pytest'\) is None/,
    );
    expect(workflow).not.toMatch(
      /cd "\$EXTRACT\/package"[\s\S]*\n\s+uv sync\s*(?:\n|$)/,
    );
  });

  test('runtime recovery instructions keep the core tier', () => {
    // Codex on #114: these two messages are the most likely path an npm user
    // takes when the server cannot start, and a bare `uv sync` there installs
    // the whole development group — defeating the boundary this PR builds, at
    // the exact moment the user is following instructions rather than choosing.
    const venvManager = readFileSync(
      path.join(projectRoot, 'src', 'lib', 'venv-manager.ts'),
      'utf8',
    );

    expect(venvManager).toContain('bash setup-uv.sh --no-dev');
    expect(venvManager).toContain('uv sync --no-dev');

    // Scoped to the two thrown messages, not to the file. A doc comment may
    // legitimately mention bare `uv sync` as the contributor variant; what must
    // not survive is an *instruction* that installs the dev group.
    const thrownLines = venvManager
      .split('\n')
      .filter((line) => /^\s*[`'].{0,8}uv sync/.test(line));
    expect(thrownLines.length).toBeGreaterThan(0);
    for (const line of thrownLines) {
      expect(line).toMatch(/uv sync --no-dev/);
    }
  });

  test('every documented setup produces the environment its own steps need', () => {
    // Codex on #114: three guides invoked a tier that could not run the very
    // next thing they told the reader to do. A setup script and the document
    // that calls it have to agree, or the instructions fail on a clean machine
    // at the step after the one that "worked".
    const setup = readFileSync(path.join(projectRoot, 'setup-uv.sh'), 'utf8');
    const contributing = readFileSync(path.join(projectRoot, 'CONTRIBUTING.md'), 'utf8');
    const deployment = readFileSync(
      path.join(projectRoot, 'docs', 'deployment', 'DEPLOYMENT_CHECKLIST.md'),
      'utf8',
    );
    const pkg = JSON.parse(
      readFileSync(path.join(projectRoot, 'package.json'), 'utf8'),
    );

    // Contributor default must match what the fast suite needs to collect.
    expect(setup).toContain('sync --group dev');
    expect(contributing).toMatch(/bash setup-uv\.sh\s*$/m);

    // Deployment has no processing extras.
    expect(setup).not.toMatch(/--extra (rag|scholar)/);
    expect(deployment).toContain('bash setup-uv.sh --deploy');

    // The health check is recommended to core installs; it must not sync dev.
    expect(pkg.scripts.doctor).toContain('uv run --no-dev');
  });

  test('end-user guides keep development tools out of core setup', () => {
    const systemWide = readFileSync(
      path.join(projectRoot, 'docs', 'installation', 'system-wide-setup.md'),
      'utf8',
    );
    const troubleshooting = readFileSync(
      path.join(projectRoot, 'docs', 'TROUBLESHOOTING.md'),
      'utf8',
    );

    expect(systemWide).toContain('bash setup-uv.sh --no-dev');
    expect(troubleshooting).toContain('uv sync --no-dev');
    expect(troubleshooting).not.toMatch(/--extra (rag|scholar)/);
    expect(troubleshooting).toContain('bash setup-uv.sh');
    expect(troubleshooting).not.toContain('uv sync --group dev`');
    expect(troubleshooting).not.toContain(
      'uv sync            # creates .venv/ and installs all Python dependencies',
    );
  });
});

import { jest, beforeEach, afterEach, expect, test } from '@jest/globals';

// Real API/retry/breaker; only interpreter lookup and the process boundary are fake.
// These catch reintroducing a shared scope, counting caller errors, and nested retries.
let api, errors, retry, runner;
let saved;
const envelope = (data) => [
  JSON.stringify({ content: [{ type: 'text', text: JSON.stringify(data) }] }),
];
const providerFailure = (details, type = 'SourceError', extra = {}) =>
  Object.assign(new Error('bridge exit'), {
    stderr: JSON.stringify({ error: 'fixture failure', type, details, ...extra }),
  });
const localBundle = { processed_file_path: '/tmp/fixture.txt' };

beforeEach(async () => {
  saved = { ...process.env };
  Object.assign(process.env, {
    ZLIBRARY_SESSION_MODE: 'per-call',
    RETRY_MAX_RETRIES: '0',
    RETRY_INITIAL_DELAY: '1',
    CIRCUIT_BREAKER_THRESHOLD: '5',
  });
  jest.resetModules();
  runner = jest.fn();
  jest.unstable_mockModule('../lib/venv-manager.js', () => ({
    getManagedPythonPath: async () => '/fake/python',
  }));
  jest.unstable_mockModule('../lib/python-runner.js', () => ({
    runPythonBridge: runner,
    LONG_BRIDGE_TIMEOUT_MS: 2400000,
  }));
  api = await import('../lib/zlibrary-api.js');
  errors = await import('../lib/errors.js');
  retry = await import('../lib/retry-manager.js');
});
afterEach(() => {
  process.env = saved;
});

async function fiveFailures(call, message = /fixture failure/) {
  for (let i = 0; i < 5; i++) await expect(call()).rejects.toThrow(message);
}

test('five LibGen outages open only the source-walk breaker; local and EAPI survive', async () => {
  runner.mockRejectedValue(providerFailure({ provider: 'libgen', reason: 'read_timeout' }));
  await fiveFailures(() => api.searchMultiSource({ query: 'x', source: 'libgen' }));
  await expect(api.searchMultiSource({ query: 'x', source: 'libgen' })).rejects.toThrow(/OPEN/);
  expect(runner).toHaveBeenCalledTimes(5);
  runner.mockResolvedValue(envelope(localBundle));
  await expect(api.processDocumentForRag({ filePath: '/tmp/fixture.txt' })).resolves.toEqual(
    localBundle,
  );
  runner.mockResolvedValue(envelope({ daily_limit: 10 }));
  await expect(api.getDownloadLimits()).resolves.toEqual({ daily_limit: 10 });
});

test('five EAPI 503 failures leave LibGen search, source download and local work usable', async () => {
  runner.mockRejectedValue(providerFailure(undefined, 'HTTPStatusError', { status_code: 503 }));
  await fiveFailures(() => api.getDownloadLimits());
  await expect(api.getDownloadLimits()).rejects.toThrow(/OPEN/);
  expect(runner).toHaveBeenCalledTimes(5);
  runner.mockResolvedValue(envelope({ books: [{ source: 'libgen' }] }));
  await expect(api.searchMultiSource({ query: 'x', source: 'libgen' })).resolves.toMatchObject({
    books: [{ source: 'libgen' }],
  });
  runner.mockResolvedValue(envelope({ file_path: '/tmp/book.pdf' }));
  await expect(
    api.downloadBookToFile({
      bookDetails: { source: 'libgen', md5: 'a'.repeat(32) },
      process_for_rag: false,
    }),
  ).resolves.toMatchObject({ file_path: '/tmp/book.pdf' });
  runner.mockResolvedValue(envelope(localBundle));
  await expect(api.processDocumentForRag({ filePath: '/tmp/fixture.txt' })).resolves.toEqual(
    localBundle,
  );
});

test('five missing-file errors cannot block a valid local document', async () => {
  runner.mockRejectedValue(providerFailure(undefined, 'FileNotFoundError'));
  await fiveFailures(() => api.processDocumentForRag({ filePath: '/tmp/missing.txt' }));
  runner.mockResolvedValue(envelope(localBundle));
  await expect(api.processDocumentForRag({ filePath: '/tmp/fixture.txt' })).resolves.toEqual(
    localBundle,
  );
  expect(runner).toHaveBeenCalledTimes(6);
});

test.each(['ReadTimeout', 'ConnectTimeout'])('typed EAPI %s opens only EAPI', async (type) => {
  runner.mockRejectedValue(providerFailure(undefined, type));
  await fiveFailures(() => api.getDownloadLimits());
  await expect(api.getDownloadLimits()).rejects.toThrow(/OPEN/);
  runner.mockResolvedValue(envelope(localBundle));
  await expect(api.processDocumentForRag({ filePath: '/tmp/fixture.txt' })).resolves.toEqual(
    localBundle,
  );
});

test.each([400, 401, 403, 404])('HTTP %i does not count despite outage words', async (status) => {
  runner.mockRejectedValue(providerFailure(undefined, 'HTTPStatusError', { status_code: status }));
  await fiveFailures(() => api.getDownloadLimits());
  runner.mockResolvedValue(envelope({ daily_limit: 10 }));
  await expect(api.getDownloadLimits()).resolves.toEqual({ daily_limit: 10 });
});

test.each(['ENOENT', 'EACCES', 'ENOEXEC'])('spawn %s neither retries nor counts', async (code) => {
  process.env.RETRY_MAX_RETRIES = '3';
  runner.mockImplementation(() => {
    throw new errors.BridgeSpawnError('fixture failure', code);
  });
  await fiveFailures(() => api.getDownloadLimits());
  runner.mockResolvedValue(envelope({ ok: true }));
  await expect(api.getDownloadLimits()).resolves.toEqual({ ok: true });
  expect(runner).toHaveBeenCalledTimes(6);
});

test.each(['EAGAIN', 'EMFILE', 'ENFILE'])('spawn %s retries and counts', async (code) => {
  process.env.RETRY_MAX_RETRIES = '1';
  runner.mockImplementation(() => {
    throw new errors.BridgeSpawnError('fixture failure', code);
  });
  await expect(api.getDownloadLimits()).rejects.toThrow('fixture failure');
  expect(runner).toHaveBeenCalledTimes(2);
  await expect(api.getDownloadLimits()).rejects.toThrow('fixture failure');
  await expect(api.getDownloadLimits()).rejects.toThrow(/OPEN/);
  expect(runner).toHaveBeenCalledTimes(5);
});

test.each(['aborted', 'signal', 'unknown', 'parse', 'auth', 'config'])(
  '%s failures do not poison a dependency',
  async (kind) => {
    const error = {
      aborted: new errors.BridgeTimeoutError('fixture failure', { reason: 'aborted' }),
      signal: new errors.BridgeKilledError('fixture failure', 'SIGKILL'),
      unknown: new Error('fixture failure: network connection timeout'),
      parse: new errors.PythonBridgeError('fixture failure', {}, false),
      auth: new errors.AuthenticationError('fixture failure'),
      config: providerFailure({
        failures: [{ reason: 'configuration_error' }, { reason: 'quota_exhausted' }],
      }),
    }[kind];
    runner.mockRejectedValue(error);
    await fiveFailures(() => api.getDownloadLimits());
    runner.mockResolvedValue(envelope({ ok: true }));
    await expect(api.getDownloadLimits()).resolves.toEqual({ ok: true });
  },
);

test('a full bridge deadline counts locally but never starts another process', async () => {
  process.env.RETRY_MAX_RETRIES = '3';
  runner.mockImplementation(() => {
    throw new errors.BridgeTimeoutError('fixture failure', { reason: 'timeout' });
  });
  await fiveFailures(() => api.processDocumentForRag({ filePath: '/tmp/fixture.txt' }));
  await expect(api.processDocumentForRag({ filePath: '/tmp/fixture.txt' })).rejects.toThrow(/OPEN/);
  expect(runner).toHaveBeenCalledTimes(5);
  runner.mockResolvedValue(envelope({ ok: true }));
  await expect(api.getDownloadLimits()).resolves.toEqual({ ok: true });
});

test.each(['stderr', 'stdout'])(
  'details read_timeout on %s gets exactly one runner call',
  async (channel) => {
    process.env.RETRY_MAX_RETRIES = '3';
    const details = { provider: 'libgen', reason: 'read_timeout' };
    if (channel === 'stderr') runner.mockRejectedValue(providerFailure(details));
    else
      runner.mockResolvedValue(
        envelope({ error: 'fixture failure', type: 'SourceError', details }),
      );
    const error = await api.searchMultiSource({ query: 'x', source: 'libgen' }).catch((e) => e);
    expect(error.context.details).toEqual(details);
    expect(error.retryable).toBe(false);
    expect(runner).toHaveBeenCalledTimes(1);
  },
);

test('mixed transient/permanent details count without a Node retry', async () => {
  process.env.RETRY_MAX_RETRIES = '3';
  const details = { failures: [{ reason: 'quota_exhausted' }, { reason: 'read_timeout' }] };
  runner.mockRejectedValue(providerFailure(details));
  await fiveFailures(() => api.searchMultiSource({ query: 'x' }));
  await expect(api.searchMultiSource({ query: 'x' })).rejects.toThrow(/OPEN/);
  expect(runner).toHaveBeenCalledTimes(5);
});

test('abort during backoff rejects within 50 ms and launches no retry', async () => {
  process.env.RETRY_MAX_RETRIES = '3';
  process.env.RETRY_INITIAL_DELAY = '10000';
  runner.mockImplementation(() => {
    throw new errors.NetworkError('fixture failure');
  });
  const controller = new AbortController();
  const call = api.searchMultiSource({ query: 'x' }, { signal: controller.signal });
  const rejection = expect(call).rejects.toMatchObject({ name: 'AbortError' });
  await new Promise((resolve) => setTimeout(resolve, 10));
  const started = performance.now();
  controller.abort();
  await rejection;
  expect(performance.now() - started).toBeLessThan(50);
  expect(runner).toHaveBeenCalledTimes(1);
});

test.each([null, {}, { reason: 'integrity_mismatch' }, { reason: 'read_timeout' }])(
  'details %j veto retry even with retryable=true',
  (details) => {
    expect(
      retry.isRetryableError({ code: 'PYTHON_ERROR', retryable: true, context: { details } }),
    ).toBe(false);
  },
);

test('untyped prose is not a transient-health verdict', () => {
  expect(
    retry.isRetryableError({ code: 'PYTHON_ERROR', message: 'network connection timeout' }),
  ).toBe(false);
});

// Wire errors need structured evidence after normalization, not message matching.
test('a typed network error remains retryable after the API wraps a non-ZLibrary error', async () => {
  process.env.RETRY_MAX_RETRIES = '1';
  runner
    .mockRejectedValueOnce(
      Object.assign(new Error('fixture transport failure'), { code: 'ECONNRESET' }),
    )
    .mockResolvedValueOnce(envelope({ ok: true }));
  await expect(api.searchMultiSource({ query: 'x' })).resolves.toEqual({ ok: true });
  expect(runner).toHaveBeenCalledTimes(2);
});

test('a typed login transport timeout counts as health evidence without an HTTP status', () => {
  expect(
    retry.isTransientDependencyError(
      new errors.PythonBridgeError(
        'upstream uncertainty',
        {
          reason: 'login_failed',
          loginStatus: null,
          pythonErrorType: 'ReadTimeout',
        },
        false,
      ),
    ),
  ).toBe(true);
});

test.each([
  [{ provider: 'libgen', reason: 'http_error', detail: 'HTTP 503' }, true],
  [{ provider: 'libgen', reason: 'http_error', status_code: 429 }, true],
  [{ provider: 'libgen', reason: 'http_error', detail: 'HTTP 401' }, false],
  [{ provider: 'libgen', reason: 'http_error' }, false],
  [{ provider: 'libgen', reason: 'tls_error' }, false],
  [{ provider: 'libgen', reason: 'unknown' }, false],
  [null, false],
])('details %j have health verdict %s but never retry', (details, health) => {
  const error = new errors.PythonBridgeError('opaque fixture error', { details }, false);
  expect(retry.isTransientDependencyError(error)).toBe(health);
  expect(retry.isRetryableError(error)).toBe(false);
});

test('bare Python ConnectError is ambiguous (including TLS/config) and cannot poison EAPI', async () => {
  process.env.RETRY_MAX_RETRIES = '3';
  runner.mockRejectedValue(providerFailure(undefined, 'ConnectError'));
  await fiveFailures(() => api.getDownloadLimits());
  runner.mockResolvedValue(envelope({ ok: true }));
  await expect(api.getDownloadLimits()).resolves.toEqual({ ok: true });
  expect(runner).toHaveBeenCalledTimes(6);
});

test.each([
  [503, true],
  [401, false],
])('login HTTP %i has health verdict %s', (loginStatus, health) => {
  expect(
    retry.isTransientDependencyError(
      new errors.PythonBridgeError(
        'login failed',
        {
          reason: 'login_failed',
          loginStatus,
          pythonErrorType: 'EAPIAuthenticationError',
        },
        false,
      ),
    ),
  ).toBe(health);
});

test('typed RemoteProtocolError is transient and retryable', () => {
  expect(
    retry.isRetryableError(
      new errors.PythonBridgeError('upstream protocol failure', {
        pythonErrorType: 'RemoteProtocolError',
      }),
    ),
  ).toBe(true);
});

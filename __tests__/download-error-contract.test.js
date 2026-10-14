import { jest, beforeEach, afterEach, test, expect } from '@jest/globals';

const runBridge = jest.fn();
jest.unstable_mockModule('../lib/python-runner.js', () => ({
  runPythonBridge: runBridge,
  LONG_BRIDGE_TIMEOUT_MS: 2400000,
}));

// Keep the compiled facade, environment resolution and real error classes.
const { downloadBookToFile } = await import('../dist/lib/zlibrary-api.js');
const { BridgeTimeoutError, AuthenticationError, PythonBridgeError } = await import('../dist/lib/errors.js');
const { isRetryableError } = await import('../dist/lib/retry-manager.js');
const args = { bookDetails: { id: '1', hash: 'offline' } };
let previousRetries;
let consoleSpy;
beforeEach(() => {
  runBridge.mockReset();
  previousRetries = process.env.RETRY_MAX_RETRIES;
  process.env.RETRY_MAX_RETRIES = '0';
  consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => {
  if (previousRetries === undefined) delete process.env.RETRY_MAX_RETRIES;
  else process.env.RETRY_MAX_RETRIES = previousRetries;
  consoleSpy.mockRestore();
});

for (const [name, makeError] of [
  ['timeout', () => new BridgeTimeoutError('budget elapsed', { reason: 'timeout' })],
  ['abort', () => new BridgeTimeoutError('caller cancelled', { reason: 'aborted' })],
  ['authentication', () => new AuthenticationError('rejected', { operation: 'download' })],
]) {
  test(`${name} retains the exact typed error and its retry classification`, async () => {
    // Mutation caught: constructing a generic PythonBridgeError in the facade.
    const original = makeError();
    original.cause = new Error('root cause');
    const { name: errorName, code, fatal, retryable, context, cause, stack } = original;
    runBridge.mockRejectedValueOnce(original);
    const promise = downloadBookToFile(args);
    await expect(promise).rejects.toThrow(); // Establish rejection before inspecting.
    const error = await promise.catch((value) => value);
    expect(error).toBe(original);
    expect(error).toBeInstanceOf(original.constructor);
    expect(error).toMatchObject({ name: errorName, code, fatal, retryable });
    expect(error.context).toBe(context);
    expect(error.cause).toBe(cause);
    expect(error.stack).toBe(stack);
    expect(error.message).toContain('Failed to download book:');
    expect(isRetryableError(error)).toBe(false);
  });
}

test('non-typed runner failures retain the existing generic bridge wrapper', async () => {
  const original = new Error('subprocess failed');
  runBridge.mockRejectedValueOnce(original);
  const promise = downloadBookToFile(args);
  await expect(promise).rejects.toThrow();
  const error = await promise.catch((value) => value);
  expect(error).toBeInstanceOf(PythonBridgeError);
  expect(error.code).toBe('PYTHON_ERROR');
  expect(error.context.originalError).toBe(original);
});

for (const [name, payload, process_for_rag] of [
  ['successful', { file_path: '/offline/book.pdf' }, false],
  ['partial processing', {
    file_path: '/offline/book.pdf', processed_file_path: null,
    processing_error: 'processing unavailable', output_files: {}, content_types_produced: [],
  }, true],
]) {
  test(`${name} download payload is unchanged`, async () => {
    runBridge.mockResolvedValueOnce([JSON.stringify({
      content: [{ type: 'text', text: JSON.stringify(payload) }],
    })]);
    await expect(downloadBookToFile({ ...args, process_for_rag })).resolves.toEqual(payload);
  });
}

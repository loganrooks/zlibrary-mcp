import { expect, jest, test } from '@jest/globals';
import { AcquisitionTools } from '../dist/lib/acquisition-tools.js';
import { ErrorEnvelopeSchema } from '../dist/lib/tool-errors.js';

const env = { ZLIBRARY_EMAIL: 'offline@example.invalid', ZLIBRARY_PASSWORD: 'offline' };

for (const operation of ['search', 'get_history']) {
  test.each([0, -1, 1.5, 51])(
    `${operation}: invalid limit %s explains how to repair it without a provider call`,
    async (limit) => {
      const invoke = jest.fn();
      const args =
        operation === 'search' ? { query: 'book', sources: ['zlibrary'], limit } : { limit };
      const result = await new AcquisitionTools(invoke, env).call(operation, args);
      expect(invoke).not.toHaveBeenCalled();
      expect(ErrorEnvelopeSchema.safeParse(result).success).toBe(true);
      expect(result.error).toMatchObject({
        code: 'invalid_argument',
        operation,
        retry: 'no',
        attempts: [],
        detail: { reason: 'schema', fields: ['limit'] },
      });
      expect(result.error.recovery).toMatch(/limit.*integer from 1 to 50/i);
      expect(result.error.recovery).toMatch(/default 10/i);
      expect(result.error.recovery).toMatch(/pag(?:e|ing).*cursor/i);
    },
  );
}

test.each([
  [
    'search',
    { query: 5 },
    'Use snake_case arguments; count becomes limit and source order is sources.',
  ],
  [
    'get_history',
    { source: 'unknown' },
    'Use snake_case arguments; count becomes limit and source order is sources.',
  ],
  [
    'download',
    { ref: 5 },
    'Pass ref, optional output_dir and filename only; text processing was removed in 2.0.',
  ],
])('%s: other schema failures retain their recovery', async (operation, args, recovery) => {
  const invoke = jest.fn();
  const result = await new AcquisitionTools(invoke, env).call(operation, args);
  expect(invoke).not.toHaveBeenCalled();
  expect(result.error.code).toBe('invalid_argument');
  expect(result.error.recovery).toBe(recovery);
});

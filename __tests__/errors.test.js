import { jest, describe, test, expect } from '@jest/globals';
import {
  ZLibraryError,
  NetworkError,
  AuthenticationError,
  DomainError,
  PythonBridgeError,
  TimeoutError,
} from '../dist/lib/errors.js';

describe('Error Classes', () => {

  describe('ZLibraryError', () => {
    test('should create instance with all properties', () => {
      const ctx = { operation: 'search' };
      const err = new ZLibraryError('test error', 'TEST_CODE', ctx, false, true);

      expect(err).toBeInstanceOf(Error);
      expect(err).toBeInstanceOf(ZLibraryError);
      expect(err.name).toBe('ZLibraryError');
      expect(err.message).toBe('test error');
      expect(err.code).toBe('TEST_CODE');
      expect(err.context).toEqual(ctx);
      expect(err.retryable).toBe(false);
      expect(err.fatal).toBe(true);
      expect(err.stack).toBeDefined();
    });

    test('should default retryable to true and fatal to false', () => {
      const err = new ZLibraryError('msg', 'CODE');
      expect(err.retryable).toBe(true);
      expect(err.fatal).toBe(false);
    });

    describe('fromError()', () => {
      test('should return the same instance if already a ZLibraryError', () => {
        const original = new ZLibraryError('original', 'ORIG');
        const result = ZLibraryError.fromError(original, { extra: 'data' });
        expect(result).toBe(original);
      });

      test('should wrap a plain Error into ZLibraryError with UNKNOWN_ERROR code', () => {
        const plain = new Error('plain error');
        const result = ZLibraryError.fromError(plain, { operation: 'test' });

        expect(result).toBeInstanceOf(ZLibraryError);
        expect(result.message).toBe('plain error');
        expect(result.code).toBe('UNKNOWN_ERROR');
        expect(result.retryable).toBe(true);
        expect(result.context.operation).toBe('test');
        expect(result.context.originalError).toBe(plain);
        expect(result.context.stack).toBe(plain.stack);
        expect(result.context.timestamp).toBeDefined();
      });

      test('should use error.code if present', () => {
        const err = new Error('auth fail');
        err.code = 'AUTH_ERROR';
        const result = ZLibraryError.fromError(err);

        expect(result.code).toBe('AUTH_ERROR');
        expect(result.retryable).toBe(false); // AUTH_ERROR is non-retryable
      });

      test('should mark FORBIDDEN errors as non-retryable', () => {
        const err = new Error('forbidden');
        err.code = 'FORBIDDEN';
        const result = ZLibraryError.fromError(err);
        expect(result.retryable).toBe(false);
      });

      test('should mark INVALID_INPUT errors as non-retryable', () => {
        const err = new Error('bad input');
        err.code = 'INVALID_INPUT';
        const result = ZLibraryError.fromError(err);
        expect(result.retryable).toBe(false);
      });

      test('should mark VALIDATION_ERROR errors as non-retryable', () => {
        const err = new Error('validation');
        err.code = 'VALIDATION_ERROR';
        const result = ZLibraryError.fromError(err);
        expect(result.retryable).toBe(false);
      });

      test('should mark other coded errors as retryable', () => {
        const err = new Error('timeout');
        err.code = 'TIMEOUT';
        const result = ZLibraryError.fromError(err);
        expect(result.retryable).toBe(true);
      });

      test('should handle string error input', () => {
        const result = ZLibraryError.fromError('string error');
        expect(result).toBeInstanceOf(ZLibraryError);
        expect(result.code).toBe('UNKNOWN_ERROR');
      });

      test('should handle error without message', () => {
        const result = ZLibraryError.fromError({});
        expect(result).toBeInstanceOf(ZLibraryError);
        expect(result.message).toBe('[object Object]');
      });
    });

    describe('toJSON()', () => {
      test('should return a JSON-serializable object with all fields', () => {
        const ctx = { operation: 'download' };
        const err = new ZLibraryError('json test', 'JSON_CODE', ctx, false, true);
        const json = err.toJSON();

        expect(json).toEqual({
          name: 'ZLibraryError',
          message: 'json test',
          code: 'JSON_CODE',
          context: ctx,
          retryable: false,
          fatal: true,
          stack: expect.any(String),
        });
      });

      test('should be serializable with JSON.stringify', () => {
        const err = new ZLibraryError('serialize test', 'SER_CODE');
        const serialized = JSON.stringify(err.toJSON());
        const parsed = JSON.parse(serialized);
        expect(parsed.name).toBe('ZLibraryError');
        expect(parsed.message).toBe('serialize test');
        expect(parsed.code).toBe('SER_CODE');
      });
    });
  });

  describe('NetworkError', () => {
    test('should create with correct defaults', () => {
      const ctx = { url: 'http://example.com' };
      const err = new NetworkError('connection failed', ctx);

      expect(err).toBeInstanceOf(ZLibraryError);
      expect(err).toBeInstanceOf(NetworkError);
      expect(err.name).toBe('NetworkError');
      expect(err.code).toBe('NETWORK_ERROR');
      expect(err.retryable).toBe(true);
      expect(err.fatal).toBe(false);
      expect(err.context).toEqual(ctx);
    });

    test('should work without context', () => {
      const err = new NetworkError('no context');
      expect(err.message).toBe('no context');
      expect(err.context).toBeUndefined();
    });
  });

  describe('AuthenticationError', () => {
    test('should create with correct defaults', () => {
      const err = new AuthenticationError('bad credentials', { user: 'test' });

      expect(err).toBeInstanceOf(ZLibraryError);
      expect(err).toBeInstanceOf(AuthenticationError);
      expect(err.name).toBe('AuthenticationError');
      expect(err.code).toBe('AUTH_ERROR');
      expect(err.retryable).toBe(false);
      expect(err.fatal).toBe(true);
    });
  });

  describe('DomainError', () => {
    test('should create with correct defaults', () => {
      const err = new DomainError('domain unavailable', { domain: 'z-lib.org' });

      expect(err).toBeInstanceOf(ZLibraryError);
      expect(err).toBeInstanceOf(DomainError);
      expect(err.name).toBe('DomainError');
      expect(err.code).toBe('DOMAIN_ERROR');
      expect(err.retryable).toBe(true);
      expect(err.fatal).toBe(false);
    });
  });

  describe('PythonBridgeError', () => {
    test('should create with default retryable=true', () => {
      const err = new PythonBridgeError('bridge failed');

      expect(err).toBeInstanceOf(ZLibraryError);
      expect(err.name).toBe('PythonBridgeError');
      expect(err.code).toBe('PYTHON_ERROR');
      expect(err.retryable).toBe(true);
      expect(err.fatal).toBe(false);
    });

    test('should accept retryable=false', () => {
      const err = new PythonBridgeError('parse error', { raw: 'bad data' }, false);
      expect(err.retryable).toBe(false);
    });
  });

  describe('TimeoutError', () => {
    test('should create with correct defaults', () => {
      const err = new TimeoutError('operation timed out', { timeout: 30000 });

      expect(err).toBeInstanceOf(ZLibraryError);
      expect(err).toBeInstanceOf(TimeoutError);
      expect(err.name).toBe('TimeoutError');
      expect(err.code).toBe('TIMEOUT');
      expect(err.retryable).toBe(true);
      expect(err.fatal).toBe(false);
      expect(err.context).toEqual({ timeout: 30000 });
    });
  });
});

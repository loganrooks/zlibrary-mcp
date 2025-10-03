import { jest, describe, test, expect, beforeEach } from '@jest/globals';

// Import from compiled dist directory
let CircuitBreaker;

describe('Circuit Breaker', () => {
  beforeEach(async () => {
    jest.resetModules();
    jest.clearAllMocks();
    const module = await import('../dist/lib/circuit-breaker.js');
    CircuitBreaker = module.CircuitBreaker;
  });

  describe('State Management', () => {
    test('should start in CLOSED state', () => {
      const breaker = new CircuitBreaker();
      expect(breaker.getState()).toBe('CLOSED');
      expect(breaker.getFailureCount()).toBe(0);
    });

    test('should execute operation successfully when CLOSED', async () => {
      const breaker = new CircuitBreaker();
      const operation = jest.fn().mockResolvedValue('success');

      const result = await breaker.execute(operation);

      expect(result).toBe('success');
      expect(breaker.getState()).toBe('CLOSED');
      expect(operation).toHaveBeenCalledTimes(1);
    });

    test('should open circuit after threshold failures', async () => {
      const breaker = new CircuitBreaker({ threshold: 3 });
      const operation = jest.fn().mockRejectedValue(new Error('Failure'));

      // Trigger failures up to threshold
      for (let i = 0; i < 3; i++) {
        try {
          await breaker.execute(operation);
        } catch (e) {
          // Expected failures
        }
      }

      expect(breaker.getState()).toBe('OPEN');
      expect(breaker.getFailureCount()).toBe(3);
    });

    test('should reject operations when OPEN', async () => {
      const breaker = new CircuitBreaker({ threshold: 2 });
      const operation = jest.fn().mockRejectedValue(new Error('Failure'));

      // Trigger failures to open circuit
      for (let i = 0; i < 2; i++) {
        try {
          await breaker.execute(operation);
        } catch (e) {
          // Expected failures
        }
      }

      expect(breaker.getState()).toBe('OPEN');

      // Next operation should be rejected immediately
      await expect(breaker.execute(operation)).rejects.toThrow('Circuit breaker is OPEN');

      // Operation should not have been called
      expect(operation).toHaveBeenCalledTimes(2); // Only the initial failures
    });

    test('should transition to HALF_OPEN after timeout', async () => {
      const breaker = new CircuitBreaker({
        threshold: 2,
        timeout: 100 // Short timeout for testing
      });
      const failOp = jest.fn().mockRejectedValue(new Error('Failure'));
      const successOp = jest.fn().mockResolvedValue('success');

      // Open the circuit
      for (let i = 0; i < 2; i++) {
        try {
          await breaker.execute(failOp);
        } catch (e) {
          // Expected
        }
      }

      expect(breaker.getState()).toBe('OPEN');

      // Wait for timeout
      await new Promise(resolve => setTimeout(resolve, 150));

      // Next execute should transition to HALF_OPEN and try the operation
      const result = await breaker.execute(successOp);

      expect(result).toBe('success');
      expect(breaker.getState()).toBe('CLOSED'); // Success closes the circuit
      expect(successOp).toHaveBeenCalledTimes(1);
    });

    test('should reset to CLOSED on successful operation', async () => {
      const breaker = new CircuitBreaker({ threshold: 3 });
      const failOp = jest.fn().mockRejectedValue(new Error('Failure'));
      const successOp = jest.fn().mockResolvedValue('success');

      // Trigger some failures (but not enough to open)
      try {
        await breaker.execute(failOp);
      } catch (e) {
        // Expected
      }

      expect(breaker.getFailureCount()).toBe(1);

      // Successful operation should reset counter
      await breaker.execute(successOp);

      expect(breaker.getState()).toBe('CLOSED');
      expect(breaker.getFailureCount()).toBe(0);
    });
  });

  describe('Failure Tracking', () => {
    test('should track failure count correctly', async () => {
      const breaker = new CircuitBreaker({ threshold: 5 });
      const operation = jest.fn().mockRejectedValue(new Error('Failure'));

      for (let i = 1; i <= 3; i++) {
        try {
          await breaker.execute(operation);
        } catch (e) {
          // Expected
        }
        expect(breaker.getFailureCount()).toBe(i);
      }
    });

    test('should not exceed threshold count', async () => {
      const breaker = new CircuitBreaker({ threshold: 3 });
      const operation = jest.fn().mockRejectedValue(new Error('Failure'));

      // Trigger more failures than threshold
      for (let i = 0; i < 5; i++) {
        try {
          await breaker.execute(operation);
        } catch (e) {
          // Expected (may be circuit open error)
        }
      }

      // Circuit should be open, count at threshold
      expect(breaker.getState()).toBe('OPEN');
      expect(breaker.getFailureCount()).toBe(3);
    });
  });

  describe('Manual Reset', () => {
    test('should allow manual reset to CLOSED state', async () => {
      const breaker = new CircuitBreaker({ threshold: 2 });
      const operation = jest.fn().mockRejectedValue(new Error('Failure'));

      // Open the circuit
      for (let i = 0; i < 2; i++) {
        try {
          await breaker.execute(operation);
        } catch (e) {
          // Expected
        }
      }

      expect(breaker.getState()).toBe('OPEN');

      // Manual reset
      breaker.reset();

      expect(breaker.getState()).toBe('CLOSED');
      expect(breaker.getFailureCount()).toBe(0);
    });
  });

  describe('State Change Callback', () => {
    test('should call onStateChange callback on state transitions', async () => {
      const onStateChange = jest.fn();
      const breaker = new CircuitBreaker({
        threshold: 2,
        onStateChange
      });
      const failOp = jest.fn().mockRejectedValue(new Error('Failure'));
      const successOp = jest.fn().mockResolvedValue('success');

      // Trigger failures to open circuit
      for (let i = 0; i < 2; i++) {
        try {
          await breaker.execute(failOp);
        } catch (e) {
          // Expected
        }
      }

      expect(onStateChange).toHaveBeenCalledWith('CLOSED', 'OPEN');

      // Success should close circuit
      breaker.reset();
      await breaker.execute(successOp);

      expect(onStateChange).toHaveBeenCalledWith('OPEN', 'CLOSED');
    });

    test('should not call onStateChange if state does not change', async () => {
      const onStateChange = jest.fn();
      const breaker = new CircuitBreaker({
        threshold: 3,
        onStateChange
      });
      const failOp = jest.fn().mockRejectedValue(new Error('Failure'));

      // Single failure should not change state
      try {
        await breaker.execute(failOp);
      } catch (e) {
        // Expected
      }

      expect(breaker.getState()).toBe('CLOSED');
      expect(onStateChange).not.toHaveBeenCalled();
    });
  });

  describe('Configuration', () => {
    test('should use custom threshold', async () => {
      const breaker = new CircuitBreaker({ threshold: 1 });
      const operation = jest.fn().mockRejectedValue(new Error('Failure'));

      try {
        await breaker.execute(operation);
      } catch (e) {
        // Expected
      }

      expect(breaker.getState()).toBe('OPEN'); // Opened after just 1 failure
    });

    test('should use custom timeout', async () => {
      const breaker = new CircuitBreaker({
        threshold: 1,
        timeout: 50
      });
      const failOp = jest.fn().mockRejectedValue(new Error('Failure'));
      const successOp = jest.fn().mockResolvedValue('success');

      // Open circuit
      try {
        await breaker.execute(failOp);
      } catch (e) {
        // Expected
      }

      expect(breaker.getState()).toBe('OPEN');

      // Wait for custom timeout
      await new Promise(resolve => setTimeout(resolve, 60));

      // Should transition to HALF_OPEN
      await breaker.execute(successOp);

      expect(breaker.getState()).toBe('CLOSED');
    });
  });
});

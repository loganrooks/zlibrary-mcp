/**
 * Circuit Breaker pattern implementation for Z-Library MCP
 * Implements the pattern from .claude/PATTERNS.md
 * Prevents cascading failures by opening circuit after repeated failures
 */

export type CircuitState = 'CLOSED' | 'OPEN' | 'HALF_OPEN';

export interface CircuitBreakerOptions {
  threshold?: number;
  timeout?: number;
  onStateChange?: (oldState: CircuitState, newState: CircuitState) => void;
}

export class CircuitBreaker {
  private failureCount = 0;
  private lastFailureTime: number | null = null;
  private state: CircuitState = 'CLOSED';
  private readonly threshold: number;
  private readonly timeout: number;
  private readonly onStateChange?: (oldState: CircuitState, newState: CircuitState) => void;

  constructor(options: CircuitBreakerOptions = {}) {
    this.threshold = options.threshold ?? 5;
    this.timeout = options.timeout ?? 60000;
    this.onStateChange = options.onStateChange;
  }

  /**
   * Execute an operation through the circuit breaker
   * @param operation - The async operation to execute
   * @returns Promise resolving with the operation result
   * @throws Error if circuit is OPEN or operation fails
   */
  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state === 'OPEN') {
      if (this.lastFailureTime && Date.now() - this.lastFailureTime > this.timeout) {
        this.transitionTo('HALF_OPEN');
      } else {
        throw new Error('Circuit breaker is OPEN');
      }
    }

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  /**
   * Get current circuit breaker state
   */
  getState(): CircuitState {
    return this.state;
  }

  /**
   * Get current failure count
   */
  getFailureCount(): number {
    return this.failureCount;
  }

  /**
   * Manually reset the circuit breaker to CLOSED state
   */
  reset(): void {
    this.failureCount = 0;
    this.lastFailureTime = null;
    this.transitionTo('CLOSED');
  }

  private onSuccess(): void {
    this.failureCount = 0;
    this.transitionTo('CLOSED');
  }

  private onFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();

    if (this.failureCount >= this.threshold) {
      this.transitionTo('OPEN');
      console.error('Circuit breaker opened due to repeated failures', {
        failureCount: this.failureCount,
        threshold: this.threshold,
        lastFailureTime: new Date(this.lastFailureTime).toISOString()
      });
    }
  }

  private transitionTo(newState: CircuitState): void {
    if (this.state !== newState) {
      const oldState = this.state;
      this.state = newState;

      console.log(`Circuit breaker state transition: ${oldState} -> ${newState}`);

      if (this.onStateChange) {
        this.onStateChange(oldState, newState);
      }
    }
  }
}

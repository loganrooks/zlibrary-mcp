import { BridgeTimeoutError, PythonBridgeError } from './errors.js';

export interface EapiSession {
  identity: string;
  generation: number;
  domain: string;
  remix_userid: string;
  remix_userkey: string;
}
export interface SessionInput extends Partial<EapiSession> {
  generation: number;
  identity: string;
  action: 'login' | 'validate' | 'operation';
  authRetry?: boolean;
}
export function getSessionMode(): 'memory' | 'per-call' {
  const mode = process.env.ZLIBRARY_SESSION_MODE ?? 'memory';
  if (mode !== 'memory' && mode !== 'per-call')
    throw new Error('ZLIBRARY_SESSION_MODE must be memory or per-call');
  return mode;
}
function milliseconds(name: string, fallback: number): number {
  const value = Number(process.env[name]);
  return Number.isSafeInteger(value) && value > 0 && value <= 2147483647 ? value : fallback;
}
export function needsEapi(functionName: string, args: Record<string, any>): boolean {
  if (functionName === 'process_document' || functionName === 'search_multi_source') return false;
  return (
    functionName !== 'download_book' ||
    !['libgen', 'annas', 'annas_archive'].includes(
      String(args.book_details?.source || '').toLowerCase(),
    )
  );
}
export function authRejected(generation: number, token: string): PythonBridgeError {
  return new PythonBridgeError(token, { reason: 'auth_rejected', generation }, false);
}

/** One server owns one active account/session, never a disk record or account pool. */
export class EapiSessionOwner {
  private identity?: string;
  private generation = 0;
  private session?: EapiSession;
  private tail: Promise<unknown> = Promise.resolve();
  private lastUse = 0;
  private loginAttempts = new Map<string, number>();

  generationFor(identity: string): number {
    if (identity !== this.identity) {
      this.identity = identity;
      this.session = undefined;
      this.generation++;
    }
    return this.generation;
  }
  get(identity: string): EapiSession | undefined {
    return identity === this.identity ? this.session : undefined;
  }
  consume(update: any, identity: string, expected: number): void {
    if (
      identity !== this.identity ||
      expected !== this.generation ||
      update?.generation !== expected ||
      update?.identity !== identity
    )
      return;
    if (
      !['domain', 'remix_userid', 'remix_userkey'].every(
        (key) => typeof update[key] === 'string' && update[key],
      )
    )
      return;
    if (
      this.session &&
      ['domain', 'remix_userid', 'remix_userkey'].every(
        (key) => update[key] === this.session![key as keyof EapiSession],
      )
    )
      return;
    this.session = {
      identity,
      generation: ++this.generation,
      domain: update.domain,
      remix_userid: update.remix_userid,
      remix_userkey: update.remix_userkey,
    };
  }
  reject(identity: string, expected: number): void {
    if (identity === this.identity && expected === this.generation) {
      this.session = undefined;
      this.generation++;
    }
  }
  run<T>(
    identity: string,
    invoke: (input: SessionInput, signal?: AbortSignal) => Promise<T>,
    options: { signal?: AbortSignal; timeoutMs?: number } = {},
  ): Promise<T> {
    const budget =
      Number.isSafeInteger(options.timeoutMs) &&
      options.timeoutMs! > 0 &&
      options.timeoutMs! <= 2147483647
        ? options.timeoutMs!
        : milliseconds('PYTHON_BRIDGE_TIMEOUT', 240000);
    const timeout = AbortSignal.timeout(budget);
    const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout;
    const deadlineError = () =>
      new BridgeTimeoutError(
        timeout.aborted ? 'EAPI call deadline exceeded' : 'EAPI call aborted',
        { reason: timeout.aborted ? 'timeout' : 'aborted' },
      );
    let active = false;
    const execute = async () => {
      if (signal.aborted) throw deadlineError();
      active = true;
      this.generationFor(identity);
      const input = (action: SessionInput['action'], authRetry = false): SessionInput => ({
        ...this.get(identity),
        identity,
        generation: this.generation,
        action,
        authRetry,
      });
      const acquire = async (authRetry = false) => {
        const previous = this.loginAttempts.get(identity);
        const cooldown = milliseconds('ZLIBRARY_SESSION_LOGIN_COOLDOWN_MS', 180000);
        if (previous !== undefined && Date.now() - previous < cooldown)
          throw new PythonBridgeError(
            'EAPI login cooldown active; try again later',
            { reason: 'auth_backoff' },
            false,
          );
        this.loginAttempts.set(identity, Date.now());
        await invoke(input('login', authRetry), signal);
        if (signal.aborted) throw deadlineError();
        if (!this.get(identity))
          throw new PythonBridgeError('Login returned no valid private session', {}, false);
        this.lastUse = Date.now();
      };
      if (!this.get(identity)) await acquire();
      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          if (signal.aborted) throw deadlineError();
          if (Date.now() - this.lastUse >= milliseconds('ZLIBRARY_SESSION_IDLE_MS', 300000))
            await invoke(input('validate', attempt > 0), signal);
          if (signal.aborted) throw deadlineError();
          const result = await invoke(input('operation', attempt > 0), signal);
          if (signal.aborted) throw deadlineError();
          this.lastUse = Date.now();
          return result;
        } catch (error: any) {
          if (signal.aborted) throw deadlineError();
          if (error?.context?.reason !== 'auth_rejected') throw error;
          this.reject(identity, error.context.generation);
          if (attempt) throw error;
          if (!this.get(identity)) await acquire(true);
        }
      }
      throw new Error('Unreachable EAPI session state');
    };
    const predecessor = this.tail.catch(() => {});
    const operation = predecessor.then(execute);
    const result = new Promise<T>((resolve, reject) => {
      const abort = () => {
        if (active && identity === this.identity) {
          // Preserve uncertain cookies, but fence any late child update/rejection.
          this.generation++;
          if (this.session) this.session = { ...this.session, generation: this.generation };
        }
        reject(deadlineError());
      };
      signal.addEventListener('abort', abort, { once: true });
      if (signal.aborted) abort();
      void operation.then(resolve, reject).finally(() => {
        active = false;
        signal.removeEventListener('abort', abort);
      });
    });
    // The flight ends on the caller's deadline even if a broken child ignores abort.
    // A timed-out queued waiter must not let later callers overtake its leader.
    this.tail = predecessor
      .then(() => result)
      .then(
        () => {},
        () => {},
      );
    return result;
  }
}

/** Never retain subprocess environments or private input in public diagnostics. */
export function sanitizeSessionError(error: any, secrets: string[]): void {
  const seen = new WeakSet<object>();
  function visit(value: any): void {
    if (!value || typeof value !== 'object' || seen.has(value)) return;
    seen.add(value);
    for (const key of Object.getOwnPropertyNames(value)) {
      if (['env', 'stdout', 'sessionInput', '_eapi_session', 'ZLIBRARY_EAPI_SESSION'].includes(key))
        delete value[key];
      else if (typeof value[key] === 'string') {
        for (const secret of secrets.filter(Boolean))
          value[key] = value[key].split(secret).join('[redacted]');
      } else visit(value[key]);
    }
  }
  visit(error);
}

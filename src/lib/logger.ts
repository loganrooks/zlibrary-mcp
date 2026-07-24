/**
 * Structured logger that writes exclusively to stderr.
 *
 * WHY THIS EXISTS
 * ---------------
 * This server speaks MCP over the stdio transport. In that transport stdout is
 * the JSON-RPC channel: the specification requires that a server MUST NOT write
 * anything to stdout that is not a valid, newline-delimited MCP message. A
 * single stray `console.log` corrupts the stream, and strict clients respond by
 * dropping the connection ("server disconnected").
 *
 * Every diagnostic in this codebase therefore goes to stderr, which MCP clients
 * capture for logs and never parse as protocol traffic.
 *
 * Verbosity is controlled with LOG_LEVEL: silent | error | warn | info | debug
 * (default: info). Per-request argument tracing lives at `debug` so that normal
 * operation does not echo user queries into client logs.
 */

export type LogLevel = 'silent' | 'error' | 'warn' | 'info' | 'debug';

const LEVEL_ORDER: Record<LogLevel, number> = {
  silent: 0,
  error: 1,
  warn: 2,
  info: 3,
  debug: 4,
};

const DEFAULT_LEVEL: LogLevel = 'info';

function resolveLevel(): LogLevel {
  const raw = (process.env.LOG_LEVEL ?? '').trim().toLowerCase();
  return raw in LEVEL_ORDER ? (raw as LogLevel) : DEFAULT_LEVEL;
}

function write(level: Exclude<LogLevel, 'silent'>, args: unknown[]): void {
  if (LEVEL_ORDER[resolveLevel()] < LEVEL_ORDER[level]) return;
  const prefix = `[${new Date().toISOString()}] [${level}]`;
  // Always stderr — see the module docstring.
  console.error(prefix, ...args);
}

export const logger = {
  error: (...args: unknown[]): void => write('error', args),
  warn: (...args: unknown[]): void => write('warn', args),
  info: (...args: unknown[]): void => write('info', args),
  debug: (...args: unknown[]): void => write('debug', args),
  /** Exposed for tests and for callers that want to skip expensive formatting. */
  isEnabled: (level: Exclude<LogLevel, 'silent'>): boolean =>
    LEVEL_ORDER[resolveLevel()] >= LEVEL_ORDER[level],
};

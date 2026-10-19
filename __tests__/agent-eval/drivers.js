import { spawn, execFileSync } from 'node:child_process';
import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { here } from './server.js';

export const driverPins = {
  claude: { binary: 'claude', version: '2.1.303', model: 'claude-opus-5-5', effort: 'high' },
  codex: { binary: 'codex', version: '0.162.1', model: 'gpt-6.1-sol', effort: 'high' },
};
export function parseEvents(text) {
  return text
    .split('\n')
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return { unparsed: line };
      }
    });
}
export function usageFrom(driver, events) {
  if (driver === 'codex') {
    const usages = events.filter((e) => e.type === 'turn.completed').map((e) => e.usage);
    if (!usages.length)
      throw new Error('missing Codex turn.completed usage; do not substitute estimates');
    for (const u of usages)
      for (const k of ['input_tokens', 'cached_input_tokens', 'output_tokens']) {
        if (!Number.isFinite(u?.[k]) || u[k] < 0) throw new Error('incomplete Codex usage: ' + k);
      }
    const sum = (k) => usages.reduce((n, u) => n + (u[k] ?? 0), 0);
    const input = sum('input_tokens'),
      cached = sum('cached_input_tokens');
    return {
      inputTotal: input,
      inputUncached: input - cached,
      inputCacheRead: cached,
      inputCacheWrite: usages.some((u) => 'cache_write_input_tokens' in u)
        ? sum('cache_write_input_tokens')
        : null,
      output: sum('output_tokens'),
      outputCached: null,
      outputUncached: sum('output_tokens'),
      cacheFirstRequest: null,
      source: 'turn.completed.usage',
    };
  }
  const result = events.findLast((e) => e.type === 'result');
  if (!result?.usage) throw new Error('missing Claude result.usage; do not substitute estimates');
  for (const k of [
    'input_tokens',
    'output_tokens',
    'cache_read_input_tokens',
    'cache_creation_input_tokens',
  ]) {
    if (!Number.isFinite(result.usage[k]) || result.usage[k] < 0)
      throw new Error('incomplete Claude usage: ' + k);
  }
  const u = result.usage,
    read = u.cache_read_input_tokens ?? 0,
    write = u.cache_creation_input_tokens ?? 0;
  const first = events.find((e) => e.type === 'assistant' && e.message?.usage)?.message.usage;
  return {
    inputTotal: u.input_tokens + read + write,
    inputUncached: u.input_tokens,
    inputCacheRead: read,
    inputCacheWrite: write,
    output: u.output_tokens,
    outputCached: null,
    outputUncached: u.output_tokens,
    cacheFirstRequest: first?.cache_read_input_tokens ?? null,
    source: 'result.usage',
  };
}
export function finalFrom(driver, events) {
  if (driver === 'codex')
    return events
      .filter((e) => e.type === 'item.completed' && e.item?.type === 'agent_message')
      .map((e) => e.item.text)
      .join('\n');
  return events.findLast((e) => e.type === 'result')?.result ?? '';
}
export function sessionFrom(driver, events) {
  return driver === 'codex'
    ? events.find((e) => e.type === 'thread.started')?.thread_id
    : events.find((e) => e.session_id)?.session_id;
}
export function commandFor({
  driver,
  directory,
  socketPath,
  toolSearch = false,
  session,
  nonce,
  model,
}) {
  const pin = driverPins[driver];
  if (driver === 'claude') {
    const args = [
      '-p',
      '--model',
      model ?? pin.model,
      '--effort',
      pin.effort,
      '--output-format',
      'stream-json',
      '--verbose',
      '--setting-sources',
      '',
      '--strict-mcp-config',
      '--mcp-config',
      path.join(directory, 'mcp.json'),
      '--tools',
      toolSearch ? 'ToolSearch' : '',
      '--allowedTools',
      'mcp__books__*',
      ...(toolSearch ? ['ToolSearch'] : []),
      '--permission-mode',
      'dontAsk',
      '--disable-slash-commands',
      '--system-prompt',
      `Evaluation ${nonce}. Use the provided book tools only. Do not use shell, files, web, or other agents.`,
      ...(session ? ['--resume', session] : ['--session-id', randomUUID()]),
    ];
    return {
      binary: pin.binary,
      args,
      env: { ENABLE_TOOL_SEARCH: String(toolSearch), MCP_CONNECTION_NONBLOCKING: '0' },
      unsetEnv: [
        'DISABLE_PROMPT_CACHING',
        'DISABLE_PROMPT_CACHING_OPUS',
        'DISABLE_PROMPT_CACHING_SONNET',
        'DISABLE_PROMPT_CACHING_FABLE',
        'DISABLE_PROMPT_CACHING_HAIKU',
      ],
      caching:
        'enabled (unset every DISABLE_PROMPT_CACHING* override); provider cache is not forcibly flushed',
    };
  }
  const config = [
    ['model_reasoning_effort', pin.effort],
    ['approval_policy', 'never'],
    ['sandbox_mode', 'read-only'],
    ['web_search', 'disabled'],
    ['mcp_servers.books.command', process.execPath],
    ['mcp_servers.books.args', [path.join(here, 'proxy.mjs'), socketPath]],
    ['mcp_servers.books.required', true],
    [
      'developer_instructions',
      `Evaluation ${nonce}. Use only the books MCP tools. Do not run commands, read files, use web, or delegate.`,
    ],
  ];
  const args = [
    'exec',
    ...(session ? ['resume'] : []),
    '--ignore-user-config',
    '--ignore-rules',
    '--skip-git-repo-check',
    '--json',
    '--model',
    model ?? pin.model,
    '--disable',
    'code_mode_tool_search',
    '--disable',
    'code_mode',
    '--disable',
    'multi_agent',
    '--disable',
    'memories',
    '--disable',
    'plugins',
    '--disable',
    'shell_tool',
    ...config.flatMap(([key, value]) => ['-c', `${key}=${JSON.stringify(value)}`]),
    ...(session ? [session] : []),
  ];
  return {
    binary: pin.binary,
    args,
    env: {},
    unsetEnv: [],
    caching: 'provider default; no supported CLI cache-off/flush flag found',
    toolSearch:
      'code_mode_tool_search disabled; retired tool_search switch deliberately not passed',
  };
}
export async function runDriver(command, prompt, directory) {
  const current = execFileSync(command.binary, ['--version'], { encoding: 'utf8' }).trim();
  const driver = command.binary,
    pin = driverPins[driver];
  if (!current.split(/\s+/).includes(pin.version))
    throw new Error(`CLI version mismatch: ${current}; expected ${pin.version}`);
  const env = { ...process.env, ...command.env };
  for (const name of command.unsetEnv) delete env[name];
  const child = spawn(command.binary, [...command.args, prompt], {
    cwd: directory,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stdout = '',
    stderr = '';
  child.stdout.on('data', (d) => (stdout += d));
  child.stderr.on('data', (d) => (stderr += d));
  let killTimer;
  const timer = setTimeout(() => {
    child.kill('SIGTERM');
    killTimer = setTimeout(() => child.kill('SIGKILL'), 2000);
  }, 300000);
  let code;
  try {
    code = await new Promise((resolve, reject) => {
      child.once('error', reject);
      child.once('exit', resolve);
    });
  } finally {
    clearTimeout(timer);
    clearTimeout(killTimer);
  }
  await writeFile(path.join(directory, 'last-driver.jsonl'), stdout);
  await writeFile(path.join(directory, 'last-driver.stderr'), stderr);
  if (code !== 0) throw new Error(`${driver} exited ${code}; inspect preserved raw output`);
  const events = parseEvents(stdout);
  if (
    events.some(
      (e) => e.type === 'turn.failed' || e.type === 'error' || (e.type === 'result' && e.is_error),
    )
  )
    throw new Error('driver reported an error');
  return {
    version: current,
    events,
    usage: usageFrom(driver, events),
    final: finalFrom(driver, events),
    session: sessionFrom(driver, events),
  };
}

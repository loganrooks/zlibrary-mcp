import { createHash } from 'node:crypto';

// Source groups and limits are documented in driver-environment.md. This records
// the effective launch environment, NOT settings/auth file contents or resolved
// provider state. Never inspect a secret-bearing value, even to hash it.
export const environmentPolicy = {
  codex: {
    values: ['HOME', 'CODEX_HOME', 'OPENAI_BASE_URL', 'CODEX_OSS_BASE_URL', 'CODEX_OSS_PORT'],
    presence: ['OPENAI_API_KEY', 'CODEX_API_KEY'],
  },
  claude: {
    values: [
      'HOME',
      'CLAUDE_CONFIG_DIR',
      'ANTHROPIC_BASE_URL',
      'ANTHROPIC_MODEL',
      'ANTHROPIC_DEFAULT_OPUS_MODEL',
      'ANTHROPIC_DEFAULT_SONNET_MODEL',
      'ANTHROPIC_DEFAULT_HAIKU_MODEL',
      'ANTHROPIC_SMALL_FAST_MODEL',
      'ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION',
      'CLAUDE_CODE_EFFORT_LEVEL',
      'MAX_THINKING_TOKENS',
      'CLAUDE_CODE_MAX_OUTPUT_TOKENS',
      'CLAUDE_CODE_USE_BEDROCK',
      'CLAUDE_CODE_USE_MANTLE',
      'AWS_REGION',
      'AWS_DEFAULT_REGION',
      'AWS_PROFILE',
      'AWS_CONFIG_FILE',
      'AWS_SHARED_CREDENTIALS_FILE',
      'ANTHROPIC_BEDROCK_BASE_URL',
      'ANTHROPIC_BEDROCK_MANTLE_BASE_URL',
      'ANTHROPIC_BEDROCK_REGION_PREFIX',
      'ANTHROPIC_BEDROCK_SERVICE_TIER',
      'CLAUDE_CODE_USE_VERTEX',
      'ANTHROPIC_VERTEX_BASE_URL',
      'ANTHROPIC_VERTEX_PROJECT_ID',
      'CLOUD_ML_REGION',
      'CLAUDE_CODE_USE_FOUNDRY',
      'ANTHROPIC_FOUNDRY_BASE_URL',
      'ANTHROPIC_FOUNDRY_RESOURCE',
      'ENABLE_TOOL_SEARCH',
      'DISABLE_PROMPT_CACHING',
      'DISABLE_PROMPT_CACHING_OPUS',
      'DISABLE_PROMPT_CACHING_SONNET',
      'DISABLE_PROMPT_CACHING_HAIKU',
      'ENABLE_PROMPT_CACHING_1H',
      'CLAUDE_CODE_PROMPT_CACHE_TTL',
    ],
    presence: [
      'ANTHROPIC_API_KEY',
      'ANTHROPIC_AUTH_TOKEN',
      'ANTHROPIC_CUSTOM_HEADERS',
      'CLAUDE_CODE_OAUTH_TOKEN',
      'CLAUDE_CODE_OAUTH_REFRESH_TOKEN',
      'AWS_ACCESS_KEY_ID',
      'AWS_SECRET_ACCESS_KEY',
      'AWS_SESSION_TOKEN',
      'AWS_BEARER_TOKEN_BEDROCK',
      'ANTHROPIC_FOUNDRY_API_KEY',
      'ANTHROPIC_FOUNDRY_AUTH_TOKEN',
    ],
  },
};
const stable = (value) =>
  JSON.stringify(value, (_key, v) =>
    v && typeof v === 'object' && !Array.isArray(v)
      ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b)))
      : v,
  );
const hash = (value) => createHash('sha256').update(stable(value)).digest('hex');
const has = (env, key) => Object.hasOwn(env, key);
export function driverEnvironmentRecord(driver, env) {
  const policy = environmentPolicy[driver];
  if (!policy) throw new Error('unsupported driver environment policy');
  const values = Object.fromEntries(
    policy.values.map((key) => {
      const value = has(env, key) ? env[key] : null;
      if (value !== null && typeof value !== 'string')
        throw new Error('invalid driver environment key ' + key);
      // Endpoint credentials may not be serialized as routing values. Refuse
      // userinfo/query/fragment endpoints, without echoing any part of the value.
      if (value && key.endsWith('BASE_URL')) {
        let url;
        try {
          url = new URL(value);
        } catch {
          throw new Error('invalid driver endpoint key ' + key);
        }
        if (url.username || url.password || url.search || url.hash)
          throw new Error('credential-capable driver endpoint refused: ' + key);
      }
      return [key, value];
    }),
  );
  const presence = Object.fromEntries(policy.presence.map((key) => [key, has(env, key)]));
  const record = { version: 1, driver, values, presence };
  return { ...record, sha256: hash(record) };
}
export function driverEnvironmentErrors(record, driver) {
  try {
    if (!record || record.version !== 1 || record.driver !== driver) throw new Error();
    const policy = environmentPolicy[driver];
    if (
      !policy ||
      stable(Object.keys(record).sort()) !==
        stable(['version', 'driver', 'values', 'presence', 'sha256'].sort())
    )
      throw new Error();
    for (const kind of ['values', 'presence']) {
      if (stable(Object.keys(record[kind]).sort()) !== stable([...policy[kind]].sort()))
        throw new Error();
      if (
        Object.values(record[kind]).some((v) =>
          kind === 'presence' ? typeof v !== 'boolean' : v !== null && typeof v !== 'string',
        )
      )
        throw new Error();
    }
    const env = {
      ...Object.fromEntries(Object.entries(record.values).filter(([, v]) => v !== null)),
      ...Object.fromEntries(
        Object.entries(record.presence)
          .filter(([, v]) => v)
          .map(([key]) => [key, '']),
      ),
    };
    if (stable(driverEnvironmentRecord(driver, env)) !== stable(record)) throw new Error();
    return [];
  } catch {
    return ['missing/invalid driver environment record'];
  }
}

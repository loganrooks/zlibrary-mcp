# Driver launch-environment identity

`driver-environment.js` records the effective environment **after** the existing
inherit/merge/unset recipe, without changing that recipe. Each measured row and
the cell summary carry the same versioned record and canonical SHA-256. Admission
recomputes the digest and requires the exact policy keys/types; comparison identity
includes the digest. A missing, tampered or drifting record is not measured evidence.
Unset value keys are `null`; unset presence keys are `false` (an explicitly empty
secret key is still present). Only designated nonsecret values enter the digest.
Secret values are neither inspected by the recorder nor hashed nor serialized.
Endpoint URLs with userinfo, query or fragment are refused with a key-only error
before serialization, because those fields could contain credentials.

## Key inventory and primary sources

The following groups enumerate **every** policy key. Sources were read on
2026-10-20, without running either CLI. Current docs are not a proof that every
listed switch affects the pinned binary; recording conservative documented keys
also prevents silently pairing runs when their effect is version-dependent.

### Codex

- Values `HOME`, `CODEX_HOME`: [advanced configuration, Config and state locations](https://learn.chatgpt.com/docs/config-file/config-advanced#config-and-state-locations)
  specifies the `CODEX_HOME` location and home-directory default. `HOME` binds the
  inherited home underlying that default; this is not a config-content hash.
- Values `CODEX_OSS_BASE_URL`, `CODEX_OSS_PORT`: [pinned 0.162.1 source, create_oss_provider](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/model-provider-info/src/lib.rs)
  reads both experimental OSS routing overrides.
- Value `OPENAI_BASE_URL`: [CLI maintainer's documented environment override](https://github.com/openai/codex/issues/11698).
  **Legacy/conservative:** current configuration docs prefer the `openai_base_url`
  config key; its environment effect was not confirmed in the inspected 0.162.1
  config/provider modules. It is recorded, not asserted effective.
- Presence `OPENAI_API_KEY`: [authentication, Sign in with an API key](https://learn.chatgpt.com/docs/auth#sign-in-with-an-api-key).
- Presence `CODEX_API_KEY`: [pinned exec source, bootstrap-auth comment and enable_codex_api_key_env](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/exec/src/lib.rs).

### Claude Code

- Values `HOME`, `CLAUDE_CONFIG_DIR`: [environment reference, configuration directory](https://code.claude.com/docs/en/env-vars#variables)
  documents the home-directory default and its override.
- Values `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`,
  `CLAUDE_CODE_EFFORT_LEVEL`, `MAX_THINKING_TOKENS`,
  `CLAUDE_CODE_MAX_OUTPUT_TOKENS`, `ENABLE_TOOL_SEARCH`,
  `DISABLE_PROMPT_CACHING`, `DISABLE_PROMPT_CACHING_OPUS`,
  `DISABLE_PROMPT_CACHING_SONNET`, `DISABLE_PROMPT_CACHING_HAIKU`,
  `ENABLE_PROMPT_CACHING_1H`, `CLAUDE_CODE_PROMPT_CACHE_TTL`:
  [environment reference, Variables and Precedence](https://code.claude.com/docs/en/env-vars).
- Values `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`,
  `ANTHROPIC_DEFAULT_HAIKU_MODEL`: [Foundry, Pin model versions](https://code.claude.com/docs/en/microsoft-foundry#4-pin-model-versions).
- Values `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_MANTLE`, `AWS_REGION`,
  `AWS_DEFAULT_REGION`, `AWS_PROFILE`, `AWS_CONFIG_FILE`,
  `AWS_SHARED_CREDENTIALS_FILE`, `ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION`,
  `ANTHROPIC_BEDROCK_BASE_URL`, `ANTHROPIC_BEDROCK_MANTLE_BASE_URL`,
  `ANTHROPIC_BEDROCK_REGION_PREFIX`, `ANTHROPIC_BEDROCK_SERVICE_TIER`:
  [Bedrock configuration, region precedence and Mantle](https://code.claude.com/docs/en/amazon-bedrock).
  File-path variables bind paths only; the recorder never opens those files.
- Values `CLAUDE_CODE_USE_VERTEX`, `ANTHROPIC_VERTEX_BASE_URL`,
  `ANTHROPIC_VERTEX_PROJECT_ID`, `CLOUD_ML_REGION`:
  [Google Cloud, Configure Claude Code](https://code.claude.com/docs/en/google-vertex-ai#4-configure-claude-code).
- Values `CLAUDE_CODE_USE_FOUNDRY`, `ANTHROPIC_FOUNDRY_BASE_URL`,
  `ANTHROPIC_FOUNDRY_RESOURCE`: [Foundry, Configure Claude Code](https://code.claude.com/docs/en/microsoft-foundry#3-configure-claude-code).
- Presence `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`,
  `ANTHROPIC_CUSTOM_HEADERS`, `CLAUDE_CODE_OAUTH_TOKEN`,
  `CLAUDE_CODE_OAUTH_REFRESH_TOKEN`: [environment reference, Variables](https://code.claude.com/docs/en/env-vars#variables).
  Custom headers are secret-capable, even if a particular header only affects routing.
- Presence `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`,
  `AWS_BEARER_TOKEN_BEDROCK`: [Bedrock, Configure AWS credentials](https://code.claude.com/docs/en/amazon-bedrock#2-configure-aws-credentials).
- Presence `ANTHROPIC_FOUNDRY_API_KEY`, `ANTHROPIC_FOUNDRY_AUTH_TOKEN`:
  [Foundry authentication](https://code.claude.com/docs/en/microsoft-foundry#2-configure-azure-credentials).

## Limits / unconfirmed candidates

This is a bounded launch-environment identity, **not** full effective-driver
configuration, authentication/account identity, resolved model identity or a
hermetic driver attestation. Stable paths do not attest stable file contents.
Settings/managed configuration can override inherited environment. Original user,
project and auth configuration contents must not be read by this recorder.
Credential rotation with unchanged presence intentionally does not change identity.

`CODEX_CONFIG`, `CODEX_CONFIG_OVERRIDES`, `CODEX_MODEL`, `CODEX_PROFILE` were not
confirmed as Codex environment overrides in the inspected documentation or pinned
config/exec/provider source; they are not invented policy keys. Documented Codex
`--config` and profile flags are command/config surfaces, not those environment
names. The command recipe already records its explicit overrides.
`OPENAI_BASE_URL` has the legacy qualification above. Arbitrary provider-specific
`env_key`/`env_http_headers`, per-model `VERTEX_REGION_CLAUDE_*`, proxy/CA settings,
wrapper-specific variables, and future switches are not exhaustively bound here.
Those require a separately reviewed policy extension before claiming their
effective configuration is comparable. No inference that unlisted keys are ignored
by a CLI is made. These limits must accompany any later model result.

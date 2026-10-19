import { tasks, arms } from './tasks.js';
import { createUsageTracker } from './drivers.js';
export const receiptSchemaVersion = 2;
export const measuredStatus = 'measured; report comparison before deciding';
export const stable = (value) =>
  JSON.stringify(value, (_k, v) =>
    v && typeof v === 'object' && !Array.isArray(v)
      ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b)))
      : v,
  );
const nonnegative = (v) => Number.isSafeInteger(v) && v >= 0;
const finite = nonnegative;
const versionMatches = (raw, version) =>
  typeof raw === 'string' && raw.split(/\s+/).includes(version);
export function comparisonSettings(r) {
  return stable({
    driver: r.driver,
    driverVersion: r.driverVersion,
    settings: r.settings,
    baselinePin: r.baselinePin,
  });
}
export function cellIdentity(r) {
  return stable({
    comparison: comparisonSettings(r),
    arm: r.arm,
    sha: r.build?.sha,
    trees: r.build?.source?.trees,
    tools: r.build?.tools,
  });
}
export function admitReceipt(r) {
  try {
    return checkReceipt(r);
  } catch (error) {
    return { eligible: false, reasons: ['malformed receipt: ' + error.message] };
  }
}
function checkReceipt(r) {
  const reasons = [];
  const fail = (m) => reasons.push(m);
  if (r.schemaVersion !== receiptSchemaVersion) fail('unsupported/legacy receipt schema');
  if (r.status !== measuredStatus) fail('receipt did not complete measured successfully');
  if (r.sourceStable !== true) fail('source integrity not stable');
  if (r.fencePassed !== true) fail('network fence not established');
  if (
    r.error ||
    r.failure ||
    r.fenceError ||
    r.nonEvaluationToolFailure ||
    r.sourceError ||
    r.cleanupError ||
    r.driverError
  )
    fail('receipt carries a failure');
  const s = r.settings ?? {},
    arm = arms.find((a) => a.id === r.arm?.id);
  if (!arm || stable(arm) !== stable(r.arm)) fail('unknown/inconsistent interface arm');
  if (!['codex', 'claude'].includes(r.driver) || s.binary !== r.driver) fail('inconsistent driver');
  for (const key of ['version', 'model', 'effort', 'temperature', 'cell', 'defaultOrderEnv'])
    if (typeof s[key] !== 'string' || !s[key]) fail('missing fixed setting ' + key);
  if (typeof s.toolSearch !== 'boolean' || (r.driver === 'codex' && s.toolSearch))
    fail('invalid tool-search setting');
  if (s.repetitions !== 5) fail('exact five replicates required');
  if (!Number.isSafeInteger(s.warmRuns) || s.warmRuns < 1) fail('invalid warm episode count');
  if (!versionMatches(r.driverVersion, s.version)) fail('receipt CLI version mismatch');
  if (!/^[a-f0-9]{40}$/.test(r.build?.sha ?? '') || r.build?.source?.sha !== r.build.sha)
    fail('missing/inconsistent build SHA');
  if (
    !/^[a-f0-9]{40}$/.test(r.baselinePin ?? '') ||
    (r.arm?.build === 'A' && r.build?.sha !== r.baselinePin)
  )
    fail('baseline pin mismatch');
  for (const key of ['dist', 'lib', 'vendoredZlibrary'])
    if (!/^[a-f0-9]{64}$/.test(r.build?.source?.trees?.[key]?.sha256 ?? ''))
      fail('missing build tree ' + key);
  if (!nonnegative(r.build?.tools?.serializedCharacters) || !nonnegative(r.build?.tools?.count))
    fail('missing tool-list measurement');
  const expectedCount = r.arm?.build === 'A' ? 12 : r.arm?.history ? 5 : 4;
  if (r.build?.tools?.count !== expectedCount) fail('tool count inconsistent with arm');
  const results = Array.isArray(r.results) ? r.results : [];
  const count = tasks.length * 5 * (1 + s.warmRuns);
  if (results.length !== count) fail('incomplete exact task/run/phase grid');
  const keys = new Set(),
    sessions = new Map();
  for (const x of results) {
    const key = `${x.run}/${x.phaseIndex}/${x.task}`;
    if (keys.has(key)) fail('duplicate grid position ' + key);
    keys.add(key);
    if (
      !Number.isInteger(x.run) ||
      x.run < 0 ||
      x.run >= 5 ||
      !Number.isInteger(x.phaseIndex) ||
      x.phaseIndex < 0 ||
      x.phaseIndex > s.warmRuns ||
      !tasks.some((t) => t.id === x.task) ||
      x.phase !== (x.phaseIndex === 0 ? 'cold' : 'warm')
    )
      fail('invalid grid position ' + key);
    if (typeof x.session !== 'string' || !x.session) fail('missing session ' + key);
    if (sessions.has(x.run) && sessions.get(x.run) !== x.session)
      fail('unexpected session change ' + key);
    sessions.set(x.run, x.session);
    if (x.driverVersion !== r.driverVersion) fail('task CLI mismatch ' + key);
    if (x.requestedModel !== s.model) fail('task requested model mismatch ' + key);
    if (x.driverError || x.nonEvaluationToolFailure || x.fenceError)
      fail('task driver/fence failure ' + key);
    if (
      (x.events ?? []).some(
        (e) =>
          e.type === 'turn.failed' ||
          e.type === 'error' ||
          (e.type === 'result' && e.is_error) ||
          (e.type === 'item.completed' &&
            ['command_execution', 'web_search', 'file_change'].includes(e.item?.type)),
      )
    )
      fail('driver event failure ' + key);
    if (!Array.isArray(x.trace) || x.trace.some((c) => c.unaccounted))
      fail('missing/unaccounted attempt trace ' + key);
    if (!Array.isArray(x.providerEvents)) fail('missing provider telemetry ' + key);
    if (
      !x.attemptCoverage ||
      !Array.isArray(x.attemptCoverage.unavailable) ||
      x.attemptCoverage.unavailable.length
    )
      fail('incomplete driver attempt telemetry ' + key);
    for (const field of ['wrongDecisions', 'invalidCalls', 'refUnavailable', 'calls', 'quotaSpent'])
      if (!nonnegative(x[field])) fail('missing/non-integer metric ' + field + ' ' + key);
    if (x.calls !== x.trace?.length) fail('attempt count inconsistent ' + key);
    if (
      typeof x.success !== 'boolean' ||
      typeof x.pathCorrect !== 'boolean' ||
      !['correct', 'incorrect', 'not-required'].includes(x.answer?.status)
    )
      fail('unscored/invalid answer ' + key);
    if (
      x.pathCorrect !== (x.wrongDecisions === 0) ||
      x.success !== (x.pathCorrect && ['correct', 'not-required'].includes(x.answer?.status))
    )
      fail('inconsistent correctness fields ' + key);
    const u = x.usage;
    for (const field of [
      'inputTotal',
      'inputUncached',
      'inputCacheRead',
      'output',
      'outputUncached',
    ])
      if (!finite(u?.[field])) fail('incomplete/negative usage ' + field + ' ' + key);
    if (u?.inputCacheWrite !== null && !finite(u?.inputCacheWrite))
      fail('missing/negative cache-write usage ' + key);
    if (u?.outputCached !== null || u?.outputUncached !== u?.output)
      fail('invalid output usage split ' + key);
    if (
      u &&
      u.inputTotal !==
        u.inputUncached + u.inputCacheRead + (r.driver === 'claude' ? (u.inputCacheWrite ?? 0) : 0)
    )
      fail('inconsistent input usage split ' + key);
    if (u?.cacheFirstRequest !== null && !finite(u?.cacheFirstRequest))
      fail('invalid first-request cache evidence ' + key);
    if (
      r.driver === 'codex' &&
      (u?.scope !== 'session-delta' || u.cacheFirstRequest !== null || u.session !== x.session)
    )
      fail('Codex usage not normalized / cold scope unknown ' + key);
    if (r.driver === 'claude' && u?.scope !== 'invocation')
      fail('unexpected Claude usage scope ' + key);
  }
  // Exact count + unique in-range positions cover the finite configured grid.
  if (new Set(sessions.values()).size !== 5)
    fail('replicates must have distinct session identities');
  if (r.driver === 'codex' && reasons.length === 0) {
    for (let run = 0; run < 5; run++) {
      const tracker = createUsageTracker('codex', { version: s.version });
      const ordered = results
        .filter((x) => x.run === run)
        .sort(
          (a, b) =>
            a.phaseIndex - b.phaseIndex ||
            tasks.findIndex((t) => t.id === a.task) - tasks.findIndex((t) => t.id === b.task),
        );
      try {
        for (const x of ordered) {
          const recomputed = tracker.consume(
            {
              scope: 'session-cumulative',
              rawCounters: x.usage.rawCounters,
              rawSnapshots: x.usage.rawSnapshots,
              cacheFirstRequest: null,
            },
            x.session,
          );
          for (const field of [
            'inputTotal',
            'inputUncached',
            'inputCacheRead',
            'inputCacheWrite',
            'output',
            'outputUncached',
            'previousCounters',
          ])
            if (stable(recomputed[field]) !== stable(x.usage[field]))
              throw new Error('raw/delta mismatch');
        }
      } catch (e) {
        fail('Codex cumulative receipt invalid: ' + e.message);
      }
    }
  }
  return { eligible: reasons.length === 0, reasons: [...new Set(reasons)] };
}

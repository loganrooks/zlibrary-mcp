const common = (row) => !['T5', 'T6', 'T10'].includes(row.task);
export function distribution(values) {
  const v = [...values].sort((a, b) => a - b),
    n = v.length;
  return n
    ? {
        median: n % 2 ? v[(n - 1) / 2] : (v[n / 2 - 1] + v[n / 2]) / 2,
        min: v[0],
        max: v[n - 1],
        n,
      }
    : null;
}
export function summarize(receipts) {
  const groups = {};
  for (const r of receipts) {
    if (r.status?.startsWith('self-test') || r.status?.startsWith('dry-run')) continue;
    const key = `${r.driver}/${r.settings.toolSearch ? 'search-on' : 'search-off'}/${r.arm.id}`;
    const g = (groups[key] ??= {
      driver: r.driver,
      toolSearch: r.settings.toolSearch,
      arm: r.arm,
      tools: r.build?.tools,
      warmRuns: r.settings.warmRuns,
      phases: {},
      absoluteViolations: [],
      historyCalls: 0,
      coldEvidence: [],
    });
    for (const x of r.results ?? []) {
      if (x.phase === 'cold' && x.task === 'T1')
        g.coldEvidence.push(
          x.usage?.cacheFirstRequest === 0
            ? 'no first-request read observed'
            : x.usage?.cacheFirstRequest > 0
              ? 'cache hit'
              : 'unknown',
        );
      g.historyCalls += (x.trace ?? []).filter((c) => c.name === 'get_history').length;
      if (r.arm.build === 'B') {
        if (['T2', 'T4', 'T5', 'T7', 'T11'].includes(x.task) && x.quotaSpent !== 0)
          g.absoluteViolations.push(`${x.task}: quota spent ${x.quotaSpent}`);
        if (x.refUnavailable)
          g.absoluteViolations.push(
            `${x.task}: ref_unavailable (inspect arguments for hallucination)`,
          );
      }
      const phase = (g.phases[x.phase] ??= { runs: {}, perTask: {} });
      const run = (phase.runs[x.run] ??= {
        wrongDecisions: 0,
        inputTotal: 0,
        output: 0,
        successes: 0,
        tasks: 0,
        quotaSpent: 0,
        usageComplete: true,
      });
      const list = (phase.perTask[x.task] ??= []);
      list.push({
        success: x.success,
        wrongDecisions: x.wrongDecisions,
        inputTotal: x.usage?.inputTotal,
        quotaSpent: x.quotaSpent,
      });
      if (common(x)) {
        run.wrongDecisions += x.wrongDecisions;
        run.inputTotal += x.usage?.inputTotal ?? 0;
        run.output += x.usage?.output ?? 0;
        run.successes += Number(x.success);
        run.tasks++;
        run.usageComplete &&= !!x.usage;
      }
      run.quotaSpent += x.quotaSpent;
    }
    if (r.arm.build === 'B' && !(g.tools?.serializedCharacters < 6500))
      g.absoluteViolations.push('tools/list is not under 6500 characters');
  }
  for (const g of Object.values(groups))
    for (const phase of Object.values(g.phases)) {
      phase.totals = Object.fromEntries(
        ['wrongDecisions', 'inputTotal', 'output', 'successes', 'quotaSpent'].map((k) => [
          k,
          distribution(Object.values(phase.runs).map((r) => r[k])),
        ]),
      );
      for (const [task, rows] of Object.entries(phase.perTask))
        phase.perTask[task] = {
          success: distribution(rows.map((x) => Number(x.success))),
          wrongDecisions: distribution(rows.map((x) => x.wrongDecisions)),
        };
    }
  const comparisons = [];
  for (const [key, b] of Object.entries(groups).filter(([, g]) => g.arm.build === 'B')) {
    const a = groups[`${b.driver}/${b.toolSearch ? 'search-on' : 'search-off'}/A`];
    if (!a) {
      comparisons.push({ key, status: 'inconclusive: missing matching A' });
      continue;
    }
    const checks = [];
    for (const phase of ['cold', 'warm']) {
      const ap = a.phases[phase],
        bp = b.phases[phase];
      if (!ap || !bp) {
        checks.push({ phase, inconclusive: 'missing phase' });
        continue;
      }
      const valid =
        Object.values(ap.runs).every(
          (x) => x.usageComplete && x.tasks === 9 * (phase === 'warm' ? a.warmRuns : 1),
        ) &&
        Object.values(bp.runs).every(
          (x) => x.usageComplete && x.tasks === 9 * (phase === 'warm' ? b.warmRuns : 1),
        );
      const n = ap.totals.inputTotal.n >= 5 && bp.totals.inputTotal.n >= 5;
      checks.push({
        phase,
        valid,
        atLeastFiveRuns: n,
        wrongDecisionsAtMostHalf:
          bp.totals.wrongDecisions.median <= 0.5 * ap.totals.wrongDecisions.median,
        inputAtMost60Percent: bp.totals.inputTotal.median <= 0.6 * ap.totals.inputTotal.median,
        successAtLeastA: bp.totals.successes.median >= ap.totals.successes.median,
        perTask: Object.fromEntries(
          tasksInCommon(ap, bp).map((t) => [
            t,
            {
              successAtLeastA: bp.perTask[t].success.median >= ap.perTask[t].success.median,
              zeroWhereAZero:
                ap.perTask[t].wrongDecisions.median !== 0 ||
                bp.perTask[t].wrongDecisions.median === 0,
            },
          ]),
        ),
      });
    }
    const coldEligible =
      a.coldEvidence.length >= 5 &&
      b.coldEvidence.length >= 5 &&
      [...a.coldEvidence, ...b.coldEvidence].every((x) => x === 'no first-request read observed');
    const allChecks =
      checks.length === 2 &&
      checks.every(
        (c) =>
          !c.inconclusive &&
          c.valid &&
          c.atLeastFiveRuns &&
          c.wrongDecisionsAtMostHalf &&
          c.inputAtMost60Percent &&
          c.successAtLeastA &&
          Object.values(c.perTask).every((t) => t.successAtLeastA && t.zeroWhereAZero),
      );
    comparisons.push({
      key,
      status: !coldEligible
        ? 'inconclusive: strict cold-cache eligibility not established'
        : allChecks && !b.absoluteViolations.length
          ? 'bar met'
          : 'bar not met',
      checks,
      coldEligible,
      absoluteViolations: b.absoluteViolations,
    });
  }
  return {
    groups,
    comparisons,
    historyDecision: Object.values(groups)
      .filter((g) => g.arm.build === 'B' && g.arm.history)
      .some((g) => g.historyCalls > 0)
      ? 'retain: get_history used in history-enabled arm'
      : 'not established: absence of calls is meaningful only after complete enabled matrix',
    exclusions: ['T5', 'T6', 'T10'],
    note: 'Medians and min/max spread; warm totals sum all warm episodes per replicate. No fabricated token counts. Strict cold uncertainty prevents a success claim.',
  };
}
function tasksInCommon(a, b) {
  return Object.keys(a.perTask).filter((t) => !['T5', 'T6', 'T10'].includes(t) && b.perTask[t]);
}

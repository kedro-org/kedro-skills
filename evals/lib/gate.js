// Pass/fail gate for eval runs. Baseline results show what a skill fixes, so
// they are reported but never fail the run; only with-skill results do.
//
// Usage: node evals/lib/gate.js <promptfoo -o output.json>...
// Exits 1 if any with-skill result failed or errored, or if a file has no
// with-skill results (a wrong label would otherwise pass silently).

const fs = require('node:fs');

const GATED = 'with-skill';
const ERROR = 2; // promptfoo ResultFailureReason.ERROR

function gate(results) {
  const gated = results.filter((r) => r.prompt.label === GATED);
  const failed = gated.filter((r) => !r.success);
  const baselineErrors = results.filter(
    (r) => r.prompt.label !== GATED && r.failureReason === ERROR,
  );
  const baselinePassed = results.filter((r) => r.prompt.label !== GATED && r.success);
  return { gated, failed, baselineErrors, baselinePassed };
}

const describe = (r) => `${r.testCase.description} [${r.provider.id}]`;

function main(files) {
  let ok = true;
  for (const file of files) {
    const { results } = JSON.parse(fs.readFileSync(file, 'utf8')).results;
    const { gated, failed, baselineErrors, baselinePassed } = gate(results);
    console.log(`\n${file}: ${gated.length - failed.length}/${gated.length} ${GATED} passed`);
    if (gated.length === 0) {
      console.log(`  no results labelled "${GATED}"`);
      ok = false;
    }
    for (const r of failed) {
      const kind = r.failureReason === ERROR ? 'ERROR' : 'FAIL';
      console.log(`  ${kind} ${describe(r)}`);
    }
    for (const r of baselineErrors) console.log(`  warning: baseline errored: ${describe(r)}`);
    if (baselinePassed.length > 0) {
      console.log(`  note: ${baselinePassed.length} baseline result(s) passed without the skill`);
    }
    if (failed.length > 0) ok = false;
  }
  return ok;
}

if (require.main === module) {
  const files = process.argv.slice(2);
  if (files.length === 0) {
    console.error('Usage: node evals/lib/gate.js <results.json>...');
    process.exit(2);
  }
  process.exit(main(files) ? 0 : 1);
}

module.exports = { gate };

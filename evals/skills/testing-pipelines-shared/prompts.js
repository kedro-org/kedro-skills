// Prompt functions for compare.yaml, which runs both testing-pipelines
// variants in one eval so they appear as side-by-side columns. Each function
// builds the same messages as prompts/with-skill.json, with a different skill.

const fs = require('node:fs');
const path = require('node:path');

// Reuse the system text from the shared baseline prompt so the variants and
// the baseline stay in sync. The file is a Nunjucks template, not JSON, so
// only the first "content" string is parsed.
const baseline = fs.readFileSync(path.join(__dirname, '../../prompts/baseline.json'), 'utf8');
const SYSTEM = JSON.parse(baseline.match(/"content":\s*("(?:[^"\\]|\\.)*")/)[1]);

const messages = (skill, vars) => [
  { role: 'system', content: `${SYSTEM}\n\nFollow this skill guidance:\n\n${skill}` },
  { role: 'user', content: `Project files:\n\n${vars.project_context}\n\nTask: ${vars.task}` },
];

module.exports = {
  raw: ({ vars }) => messages(vars.skill_raw, vars),
  skillCreator: ({ vars }) => messages(vars.skill_creator, vars),
  // Iteration 1 snapshots (docs/skill-creation-comparison/v1/), to check that
  // the iteration 2 fixes improve on them.
  rawV1: ({ vars }) => messages(vars.skill_raw_v1, vars),
  skillCreatorV1: ({ vars }) => messages(vars.skill_creator_v1, vars),
};

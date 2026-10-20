// Prompt functions for the explain-project suite. The skill answers questions
// in prose and starts with commands (a version check, then asking before it
// loads project code), so the shared code-change prompts do not fit. Each test
// sets a `mode` var:
//
//   explain   no tools; answer in the chat. Tests the skill's file-only
//             fallback ("Without the snapshot").
//   commands  first turn with a shell. The model lists the commands it would
//             run itself in ```run blocks and stops. Tests the order of its
//             first moves: version check, consent, never running the pipeline.
//   code      the shared code-change prompt, for tasks the skill must stay out of.
//
// The with-skill and baseline functions differ only in the skill guidance.

const fs = require('node:fs');
const path = require('node:path');

// The code-change system text is the shared baseline prompt's, so it stays in
// sync. The file is a Nunjucks template, not JSON, so only the first "content"
// string is parsed.
const baseline = fs.readFileSync(path.join(__dirname, '../../prompts/baseline.json'), 'utf8');
const CODE = JSON.parse(baseline.match(/"content":\s*("(?:[^"\\]|\\.)*")/)[1]);

const ASSISTANT = 'You are an AI coding assistant working in a Kedro project.';

const SYSTEM = {
  explain:
    `${ASSISTANT} In this conversation you cannot run commands, read files beyond ` +
    'those shown, or fetch URLs. Answer the user in the chat.',
  commands:
    `${ASSISTANT} You have a shell open in the project root, and this is your first ` +
    'turn: you have not run anything yet. To run a command yourself, put it in a ' +
    'fenced code block with the language `run` (```run), one command per block, in ' +
    'the order you would run them; you will see their output in the next message, so ' +
    'stop after them and do not invent their output. Commands you only show the user, ' +
    'for them to run, go in ordinary ```bash blocks. If you would ask the user ' +
    'something first, ask it. If you need no command, answer directly.',
  code: CODE,
};

function messages(vars, skill) {
  const mode = vars.mode || 'explain';
  if (!(mode in SYSTEM)) throw new Error(`Unknown mode ${JSON.stringify(mode)}`);
  const system = skill ? `${SYSTEM[mode]}\n\nFollow this skill guidance:\n\n${skill}` : SYSTEM[mode];
  return [
    { role: 'system', content: system },
    { role: 'user', content: `Project files:\n\n${vars.project_context}\n\nTask: ${vars.task}` },
  ];
}

module.exports = {
  withSkill: ({ vars }) => messages(vars, vars.skill_content),
  baseline: ({ vars }) => messages(vars, null),
  SYSTEM,
};

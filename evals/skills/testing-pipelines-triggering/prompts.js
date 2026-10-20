// Prompt functions for promptfooconfig.yaml. Each one shows the model the
// installed skills with their descriptions, the way an agent sees them, and
// asks which skill it would load for the request. Only the testing-pipelines
// description changes between variants; the other skills are the competition.

const fs = require('node:fs');
const path = require('node:path');

const { others, variants } = JSON.parse(
  fs.readFileSync(path.join(__dirname, 'descriptions.json'), 'utf8'),
);

const picker = (variant, request) => {
  const skills = { ...others, 'testing-pipelines': variants[variant] };
  const list = Object.entries(skills)
    .map(([id, description]) => `- ${id}: ${description}`)
    .join('\n');
  return [
    {
      role: 'system',
      content:
        'You are an AI coding assistant working in a Kedro project. These skills are installed. ' +
        'Each one is listed with its description:\n\n' +
        list +
        '\n\nFor the user request, reply with only the id of each skill you would load, ' +
        'separated by commas, or `none` if no skill applies. Do not add anything else.',
    },
    { role: 'user', content: request },
  ];
};

module.exports = {
  raw: ({ vars }) => picker('raw', vars.request),
  skillCreator: ({ vars }) => picker('skill-creator', vars.request),
  // Iteration 1 descriptions, for before/after.
  rawV1: ({ vars }) => picker('raw-v1', vars.request),
  skillCreatorV1: ({ vars }) => picker('skill-creator-v1', vars.request),
};

// Deterministic trigger check: did the reply name the testing skill?
// Expected "trigger" means it should be named; "none" means it should not.
module.exports.triggers = (output, context) => {
  const named = /testing-pipelines/.test(output);
  return context.vars.expect === 'trigger' ? named : !named;
};

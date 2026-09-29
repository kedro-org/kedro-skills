// Deterministic checks for the parameters-and-config skill. Each one maps to a
// rule in skills/parameters-and-config/SKILL.md and only inspects code blocks.

const { forbid, isPython } = require('../../lib/blocks.js');

// "The only config loader": ConfigLoader and TemplatedConfigLoader were removed
// in 0.19. \b does not match inside "OmegaConfigLoader", so that stays allowed.
function noRemovedConfigLoaders(output) {
  return forbid(output, /\b(Templated)?ConfigLoader\b/, isPython, 'removed ConfigLoader/TemplatedConfigLoader');
}

// "the params: prefix": a parameter passed as a bare node input is looked up
// as a dataset.
function noBareParamInput(output) {
  return forbid(
    output,
    /inputs\s*=\s*(\[[^\]]*)?["']fit_intercept["']/,
    isPython,
    'fit_intercept passed as a node input without the params: prefix',
  );
}

// "Loading credentials from environment variables": oc.env is enabled only for
// credentials files by default.
function noOcEnvOutsideCredentials(output) {
  return forbid(
    output,
    /\$\{\s*oc\.env\s*:/,
    (b) => /(parameters|catalog|globals)[^/]*\.ya?ml$/.test(b.path || ''),
    'oc.env in a parameters, catalog or globals file',
  );
}

// "Credentials": never in conf/base/, which is version-controlled.
function noCredentialsInBase(output) {
  return forbid(
    output,
    /hunter2|password\s*:/i,
    (b) => /(^|\/)conf\/base\//.test(b.path || ''),
    'credentials under conf/base/',
  );
}

// "Parameter validation": Pydantic v2+ only.
function noPydanticV1(output) {
  return forbid(
    output,
    /@validator\b|\.parse_obj\(|from pydantic\.v1\b|class Config\s*:/,
    isPython,
    'Pydantic v1 API',
  );
}

module.exports = {
  noRemovedConfigLoaders,
  noBareParamInput,
  noOcEnvOutsideCredentials,
  noCredentialsInBase,
  noPydanticV1,
};

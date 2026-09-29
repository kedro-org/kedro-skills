// Helpers for assertions that inspect the code a model proposes, not its prose.
//
// Prompts ask the model to precede each fenced code block with `File: <path>`.
// Checking only code blocks means a model that *explains* why a pattern is
// wrong does not fail an assertion that forbids that pattern.

const FENCE = /^```([\w.+-]*)[^\n]*\n([\s\S]*?)^```/gm;
// Markdown wrappers (`code`, **bold**) around the path are skipped; underscores
// are kept because paths like src/eval_project/ contain them.
const FILE_LINE = /File:\s*[`*]*([^\s`*]+)/g;
// Models often ignore the `File:` instruction and label blocks with headings
// such as `#### conf/base/parameters.yml`, so fall back to any path-like token.
const PATH_TOKEN = /[\w.-]+(?:\/[\w.-]+)*\.(?:py|ya?ml|toml|txt|json|cfg)\b/g;

const lastMatch = (text, re, group) => {
  let found = null;
  for (const m of text.matchAll(re)) found = m[group];
  return found;
};

// Some models put the label in a fence of its own, followed by the real block.
const LABEL_ONLY = /^\s*File:\s*[`*]*([^\s`*]+)[`*]*\s*$/;
// Others put it in a comment on the block's first line: `# conf/base/x.yml`.
const COMMENT_LABEL = new RegExp(
  String.raw`^\s*(?:#|//)\s*(?:File:\s*)?(${PATH_TOKEN.source})\s*\n`,
);

// Returns [{ path, lang, code }]. `path` is, in order of preference: the last
// `File:` line between the previous block and this one, a label-only block
// just before, a path comment on the block's first line, the last path-like
// token in the text before the block, or null. The prose fallback is last
// because it can pick up a file the model only mentioned in passing.
function codeBlocks(output) {
  const blocks = [];
  let lastEnd = 0;
  let labelPath = null;
  for (const match of output.matchAll(FENCE)) {
    const between = output.slice(lastEnd, match.index);
    lastEnd = match.index + match[0].length;
    const label = match[2].match(LABEL_ONLY);
    if (label) {
      labelPath = label[1];
      continue;
    }
    const comment = match[2].match(COMMENT_LABEL);
    const path =
      lastMatch(between, FILE_LINE, 1) ||
      labelPath ||
      (comment && comment[1]) ||
      lastMatch(between, PATH_TOKEN, 0);
    labelPath = null;
    blocks.push({ path, lang: match[1].toLowerCase(), code: match[2] });
  }
  return blocks;
}

// Fails if any block selected by `where` matches `pattern`.
function forbid(output, pattern, where, what) {
  const hits = codeBlocks(output).filter((b) => where(b) && pattern.test(b.code));
  if (hits.length === 0) {
    return { pass: true, score: 1, reason: `No ${what}` };
  }
  const paths = hits.map((b) => b.path || '<unlabelled block>').join(', ');
  return { pass: false, score: 0, reason: `Found ${what} in ${paths}` };
}

const isPython = (b) => b.lang === 'python' || b.lang === 'py' || /\.py$/.test(b.path || '');

module.exports = { codeBlocks, forbid, isPython };

# Writing a skill by hand vs. with skill-creator

An experiment run while authoring the `testing-pipelines` skill (2026-10-09).
The same skill was written twice from the same verified facts:

| Variant | How it was written |
|---|---|
| [`testing-pipelines-raw`](../../skills/testing-pipelines-raw/SKILL.md) | By hand, following the house style of the existing skills (`parameters-and-config`) |
| [`testing-pipelines-skill-creator`](../../skills/testing-pipelines-skill-creator/SKILL.md) | Through the `skill-creator` skill's workflow: its writing guide, then its eval loop |

Both variants ship in this branch so they can be installed and tried side by side.

## TL;DR

- **Both skills help, and by the same amount.** With either skill, 5/5 tasks passed on
  the first try and 25/25 graded checks passed. Without a skill, 2/5 passed on the first
  try and 23/25 checks passed. The no-skill runs failed on exactly the gotchas the skills
  document.
- **Round 1 tied; rounds 2 and 3 favoured raw on score, but not on substance.** Round 1
  (Sonnet agents, A/B) scored 25/25 for both. Round 2 (promptfoo, gpt-4o and gpt-5.5)
  scored 13/26 for raw and 10/26 for skill-creator, or 2 vs 1 on code alone. After both
  skills were fixed from round 2's failures, round 3 scored 25/26 and 23/26; on code
  alone, 25/26 each. Round 4 tied at 23/26 on different tests, and after the eval's own
  bugs were fixed, both passed every assertion in round 5. All rounds were run at n=1.
- **The value of skill-creator was its process, not its prose.** Its eval loop (with-skill
  vs. baseline runs, graded) is what produced the evidence above. Hand-writing the skill
  had no equivalent step.
- **Neither authoring method caught the wrong claims.** Running the skills' snippets
  under pytest caught one wrong fact before either version shipped. Two more got
  through both eval rounds: a `# WRONG` comment in the hand-written version whose prose
  did not match what its test proved, found by reading the versions side by side, and
  the fact-sheet claim that a misspelled env silently falls back to base config, which
  both versions repeated, found while verifying the iteration 2 fixes.

## Conclusion

**The rules a skill is built on matter more than how it is written.** Two skills in
different styles, built on the same verified rules and improved with the same eval
feedback, ended up equivalent. In more detail, a skill's quality came from three things,
in this order:

1. **A verified set of rules.** Two of the three wrong claims came from the shared fact
   sheet (intermediates stay in the catalog, caught before either skill shipped; a
   misspelled env falls back to base config, which both skills repeated). The third was
   the hand-written version's own `# WRONG` comment, whose wording did not match what its
   test proved. Neither writing method prevented any of them; running code against
   Kedro, and comparing the prose with what the tests proved, caught them. Without the
   rules, the no-skill baseline scored 0/26 in every promptfoo round.
2. **Guidance for when a request contradicts the rules.** In round 2 both skills already
   had correct rules and still scored 10-13/26: the models knew the rule and followed the
   user's wrong premise anyway. Telling the model to write the correct version and say
   why fixed most of it. That guidance is not a fact, and only testing showed it was
   needed.
3. **An eval loop, with the evals themselves checked.** The loop found the gaps. From
   round 3 on, most failures were the eval (judge errors, rubric wording, an over-strict
   code check), not the skills. Anything a code check can decide should not be left to
   the judge model.

Writing style came last. skill-creator's real contribution was its eval loop, which the
promptfoo harness in `evals/` now provides for any skill.

Limits: one run per cell; the same author wrote both variants; both were pasted into
the prompt, so triggering (where skill-creator's "pushy" description could still matter)
was never tested; and the shared fact sheet means this compares writing styles, not
research methods.

## Method

1. **Shared fact sheet ([facts.md](facts.md)).** Each claim was verified against Kedro
   1.7.0 with a pytest in a fresh spaceflights project
   ([verification/test_facts.py](verification/test_facts.py), 20 tests). Both variants
   used only these facts.
2. **Raw variant.** Written by hand. Its code snippets were run under pytest
   ([verification/test_raw_snippets.py](verification/test_raw_snippets.py)). That run
   showed that one fact-sheet claim was wrong (see "Findings about the process").
3. **skill-creator variant.** Written by following `skill-creator`. That means its
   writing guide (explain the *why*, avoid all-caps MUSTs, a "pushy" description), then
   its eval loop: test prompts, with-skill and baseline subagent runs, grading, and a
   benchmark. Snippets verified in
   [verification/test_skill_creator_snippets.py](verification/test_skill_creator_snippets.py).
4. **A/B test ([ab-test/](ab-test/)).** Five realistic prompts ([evals.json](ab-test/evals.json)).
   Each was run by a fresh Sonnet 5.5 subagent in its own copy of the spaceflights
   project, under three arms: `skill_creator`, `raw` and `no_skill`. Outputs were graded
   by [grade.py](ab-test/grade.py), which re-runs the agent's tests under pytest and
   checks the code for specific Kedro patterns.

## Results

### Outcomes

| Task | What it probes | skill_creator | raw | no_skill |
|---|---|---|---|---|
| `ds-pipeline-metrics` | runner returns datasets (`.load()`) | 4/4 · first try | 4/4 · first try | 4/4 · first try |
| `inspect-intermediate-xtrain` | intermediates released after run | 4/4 · first try | 4/4 · first try | 4/4 · first try ¹ |
| `smoke-runtime-params` | `bootstrap_project`, nested `runtime_params` | 5/5 · first try | 5/5 · first try | 5/5 · **1 failed run** ² |
| `unit-test-preprocess-nodes` | call node functions directly | 3/3 · first try | 3/3 · first try | 3/3 · first try |
| `fix-legacy-test` | removed APIs, `.load()`, `params:` | 9/9 · first try | 9/9 · first try | **7/9 · 2 failed runs** ³ |
| **Total** | | **25/25 · 5/5** | **25/25 · 5/5** | **23/25 · 2/5** |

¹ Passed, but read the runner source to discover that intermediates are released, then
captured `X_train` with a hook built on a private Kedro helper
(`kedro.framework.hooks._create_hook_manager`). Both skill arms used the documented
approach, `pipeline.to_outputs("X_train")`.
² First run used `runtime_params={"model_options.test_size": 0.3}` and failed with
`assert 0.2 == 0.3`, because dotted keys are not expanded through the Python API.
³ First run: `ImportError: cannot import name 'load_context'`. Second:
`TypeError: 'MemoryDataset' object is not subscriptable`. The final code still used the
deprecated `pipeline_name=` and a cwd-dependent `Path.cwd()`.

### Cost

| | skill_creator | raw | no_skill |
|---|---|---|---|
| Median time per task | 32.9 s | 33.8 s | 47.5 s ⁴ |
| Median tokens per task | 38.7k | 37.6k | 36.2k ⁴ |

⁴ n=4: one no-skill run lost its usage numbers to an API error after it had finished.
Reading the skill costs about 1–2k tokens. The time saved comes from not having to debug.

### Static comparison

| | raw | skill_creator |
|---|---|---|
| Length | 211 lines, 883 words | 202 lines, 1014 words |
| Code blocks | 10 | 7 |
| Headings | 6 sections + 4 subsections | 6 sections + 2 subsections, numbered by test layer |
| Style | Example-led: `# WRONG` / `# Correct` pairs, a cheat-sheet of removed APIs | Explanation-led: says *why* each behaviour matters, "Don't write / Write" table |
| All-caps MUST/NEVER | 0 | 0 |
| Description | 4 lines, factual | 8 lines, "pushy" (lists trigger phrasings) |
| Shows a `conftest.py` with the fixtures its examples use | ✅ | ❌ (examples use fixtures it never defines) |
| Mentions `MemoryDataset` copying DataFrames | ❌ | ✅ |
| Mentions `session.run()` also returns datasets | ❌ | ✅ |
| Explains *why* `bootstrap_project` is needed | ❌ (states it) | ✅ |
| Covers every other fact in the fact sheet | ✅ | ✅ |

### Round 2: promptfoo suite

2026-10-13, branch `test-skills`. 13 shared tests, one per verified fact, in
`evals/skills/testing-pipelines-shared/`. Each test leads the user to ask for the wrong
thing and checks the answer with deterministic JS on code blocks plus an llm-rubric.
Suites for the two variants live at
`evals/skills/testing-pipelines-raw/` and
`evals/skills/testing-pipelines-skill-creator/`.

Single-turn, no tools: the skill text was pasted into the system prompt. Triggering and
description were therefore still not tested. Models: openai `gpt-4o` (temperature 0) and
`gpt-5.5`. Judge: `gpt-4o-mini`. One run per cell.

| Model | raw | skill_creator | no_skill |
|---|---|---|---|
| gpt-4o | 7/13 | 6/13 | 0/13 |
| gpt-5.5 | 6/13 | 4/13 | 0/13 |
| **Total** | **13/26** | **10/26** | **0/26** |

Every baseline run failed. The raw variant scored higher overall; the gap on code alone
was 2 vs 1.

- **Env file replaces top-level keys** — raw wins on gpt-5.5 (substance). The
  skill-creator answer wrote a test-env file with only `test_size`, dropping
  `random_state` and `features`.
- **Share fixtures via `conftest.py`** — raw wins on gpt-4o (substance). The
  skill-creator answer duplicated fixtures in both files.
- **Fixtures not provided by Kedro** — raw wins on gpt-5.5 (wording). JS checks passed;
  the rubric failed it for not explaining the change.
- **Replace `load_context`** — raw wins on gpt-4o (wording). JS checks passed; the rubric
  failed it for not explaining the change.
- **Read run outputs with `.load()`** — skill-creator wins on gpt-4o (substance). The raw
  answer indexed `result["metrics"]["r2_score"]`.

Shared failures: with either variant, the model followed the user's wrong premise (bare
`model_options` catalog key and `catalog.load("X_train")` after a full run on gpt-4o;
`pipeline_name=` kept and `KedroSession` in a unit test on gpt-5.5; misspelled env not
corrected ⁵). `MemoryDataset` copying failed everywhere, even though skill-creator mentions
it. gpt-5.5 produced code-only answers, so rubrics requiring explanation failed correct
code (nested `runtime_params`, `load_context` rewrite); whether to make explanations
optional is undecided. The judge made one wrong verdict (said a correct gpt-5.5
`load_context` test was missing).

Caveats: n=1 per cell; the 3-test gap is within run-to-run noise. Two of raw's wins were
rubric-wording failures, not code errors. Why raw scored higher is not established.

⁵ This test is not valid. Its rubric expected the model to say that a misspelled env
silently falls back to base config, which is false (see finding 3). It failed in all four
with-skill cells, so it does not change the gap between the variants. It has been replaced
by "Assert that the test env's values took effect".

### Iteration 2 (2026-10-13)

Both skills were fixed from the round 2 failures. The iteration 1 versions are kept in
[v1/](v1/), and [skill-diff.md](skill-diff.md) refers to them.

The most common round 2 failure was the model doing what a request with an outdated
assumption asked for. Both skills now say what to do then: write the Kedro 1.x version
and add one sentence on what changed and why.

| Fix | raw (by hand, house style) | skill-creator (its "Improving the skill" step) |
|---|---|---|
| Outdated requests | New table: asked for / write instead / why (9 rows) | New section explaining why a test built on an old assumption fails or passes for the wrong reason, and why the one-sentence explanation matters |
| `# WRONG` runner comment | Fixed to the real `TypeError` | Was already correct |
| Unit tests | Build small frames by hand; no session for data | Explains why loading real data through a session is not a unit test |
| `MemoryDataset` copying | Added (v1 lacked it) | Made actionable: no `.copy()` needed through the catalog; direct calls do mutate |
| Misspelled env | Corrected: empty params with a warning, then `MissingConfigException` | Same correction |
| Asserting the env took effect | New snippet: check `load_context().params` before `run()` | Same snippet |
| Env parameters file replaces keys | New `# WRONG` / `# Correct` YAML pair | New full-key YAML example, with the `KeyError: 'features'` it prevents |
| `tests/conftest.py` example | Was already there | Added, with the fixtures its pipeline example uses (v1 used undefined ones) |
| Length | 211 → 263 lines | 202 → 278 lines |

skill-creator's loop was adapted: the feedback came from the promptfoo results rather
than its review viewer, and the re-run uses the promptfoo suite rather than subagent runs.

Every new snippet, `# WRONG` lines included, runs under pytest against Kedro 1.7.0:
43 tests pass (20 facts, 12 raw, 11 skill-creator). `make test` and lint pass.

`evals/skills/testing-pipelines-shared/compare.yaml` now has five columns:
`with-skill:raw` and `with-skill:skill-creator` (iteration 2, gated), `v1:raw` and
`v1:skill-creator` (iteration 1, reported only) and `baseline`.

### Round 3: iteration 2 on the promptfoo suite (2026-10-13)

The two per-variant suites, same models and judge as round 2 (`gpt-4o`, `gpt-5.5`;
judge `gpt-4o-mini`), with the replaced env test. One run per cell.

| Model | raw | skill-creator | no skill |
|---|---|---|---|
| gpt-4o | 12/13 | 10/13 | 0/13 |
| gpt-5.5 | 13/13 | 13/13 | 0/13 |
| **Total** | **25/26** (round 2: 13/26) | **23/26** (round 2: 10/26) | **0/26** |

Both variants improved by about the same amount. The three remaining with-skill failures
were all on gpt-4o:

- **Assert that the test env's values took effect:** failed for both variants. The
  answers wrote a correct full-key env file but no assertion on the loaded value. A real
  failure, and the only one left.
- **An env parameters file replaces whole top-level keys (skill-creator):** a judge
  error. The answer has the full `model_options` block; the judge said it did not. This
  is the second wrong verdict from `gpt-4o-mini`.
- **Replace load_context and context.run (skill-creator):** a wording failure. The answer
  replaced the old APIs and said they come from older Kedro, but did not say the existing
  test is broken, which the rubric asks for.

So on what the code does, the variants tie at 25/26. Raw's 2-point lead is one judge error
and one wording requirement.

### Iteration 3 (2026-10-13)

Small fixes aimed at round 3's remaining failures, same methods as before.

| Failure | raw (by hand) | skill-creator (its "Improving the skill" step) |
|---|---|---|
| No check that the test env took effect (both, gpt-4o) | Two new table rows: "if it runs, the config was used" and "a new test in the style of an old `load_context` one"; the env bullet now says to assert in every test that sets `env=` or `runtime_params`, even if asked not to | Added "if the run passes, the test config was used" to the list of wrong assumptions, and explained why: it is how a test-config test ends up checking production config |
| Did not say the existing `load_context` test is broken (skill-creator, gpt-4o) | Covered by the new table row (raw had passed) | New paragraph: when a request points at existing code that uses removed APIs, say it is already broken and fix it too, or the user finds out from CI |
| Env-file answer marked wrong (skill-creator, gpt-4o) | n/a | Nothing to fix: judge error |

No new code snippets, so the 43 verification tests still cover everything. raw is now
266 lines, skill-creator 287. Iteration 2 was not snapshotted separately; this table is
the full diff from it. Round 4 has not been run.

**Token use.** In the suite totals, skill-creator's run used fewer completion tokens
(19,128 against 21,884). That difference comes from the baseline, not the skills: two of
raw's baseline answers were not cached and were regenerated, while all of
skill-creator's came from the cache. Counting only the with-skill answers, skill-creator
used slightly more: about 3k more prompt tokens across the 26 calls, because its skill is
longer (10.8k against 9.7k characters), and about the same output.

### Round 4: iteration 3 on the promptfoo suite (2026-10-13)

The two per-variant suites, same models and judge as round 3 (`gpt-4o`, `gpt-5.5`; judge `gpt-4o-mini`), with the iteration 3 skills and `--no-cache`. One run per cell.

| Model | raw | skill-creator |
|---|---|---|
| gpt-4o | 11/13 | 10/13 |
| gpt-5.5 | 12/13 | 13/13 |
| **Total** | **23/26** | **23/26** |

Same count, different tests:

| Test | Model | Variant | Kind |
|---|---|---|---|
| An env parameters file replaces whole top-level keys | gpt-4o | raw | judge error (full `model_options` block is in the answer) |
| An env parameters file replaces whole top-level keys | gpt-5.5 | raw | judge error (same) |
| Replace load_context and context.run | gpt-4o | raw | rubric wording (said the APIs are "not available in Kedro 1.x" and rewrote the old test) |
| Register parameters under the literal params: key | gpt-4o | skill-creator | real: registered bare `"model_options"` as asked |
| Expose an intermediate instead of loading it after the run | gpt-4o | skill-creator | real: full run then `catalog.load("X_train")`, plus a `Pipeline(outputs=["X_train"])` edit that does not keep it |
| Replace load_context and context.run | gpt-4o | skill-creator | rubric wording (said the old test "is not compatible with Kedro 1.x" and rewrote it) |

On code alone: raw 26/26, skill-creator 24/26. Both of skill-creator's real failures passed in round 3, and iteration 3 did not touch those sections, so this is run-to-run variance (gpt-4o at temperature 0 is not deterministic; n=1). The env-file test has now produced three wrong verdicts from `gpt-4o-mini` (one in round 3, two here), four wrong verdicts in total plus the two borderline wording calls above.

### Iteration 4 (2026-10-13)

**Eval fixes** (shared tests, so they apply to both variants equally). The judge kept deciding things a code check can decide:

- Env-file test: new JS check `writesFullEnvBlock` (a YAML block whose `model_options` has `test_size`, `random_state` and `features`); the rubric now judges only the explanation.
- load_context test: new JS check `rewritesOldTest` (the block defining `test_data_processing_runs` also uses `KedroSession.create`, directly or through a helper); the rubric now asks only that the answer says `load_context` / `context.run` don't exist or work in 1.x, and writes the new-style test.

Re-grading round 4's answers with the new JS checks: all 8 pass. `make eval-test`: 32 pass.

**Skill fixes**, same methods:

| | raw (by hand) | skill-creator (its "Improving the skill" step) |
|---|---|---|
| Change | none: its round 4 failures were all grading | Generalized from the two real failures, where gpt-4o followed a reason the user gave: a new paragraph in "When the request itself is out of date" says assumptions often arrive with a reason attached, that a reason is the same assumption stated more confidently, and to correct the reason. The params paragraph adds "The prefix is not just pipeline syntax: it is part of the dataset name the runner looks up"; the intermediates paragraph adds "even though `X_train` was written during the run". |
| Lines | 266 | 295 |

No new snippets, so the 43 verification tests still cover both; `make test` passes (152). Round 5 not run yet.

### Round 5: iteration 4, gpt-4o + Kimi (2026-10-13)

gpt-5.5 was dropped for token cost (reasoning tokens made it the most expensive provider) and `moonshot:kimi-k2.7-code` added, so this round starts a new series and is not comparable with rounds 1-4. Judge still `gpt-4o-mini`. One run per cell.

raw passed every test on both models. skill-creator failed one: "Unit-test a node without a session" on Kimi. That was a check bug. The answer wrote the session-free unit test the task wanted *and* a separate `KedroSession` smoke test in `tests/test_run.py` for the realistic-data goal (also passing a `.copy()` because the node mutates its input). The rubric passed it; `noKedroMachineryInUnitTest` failed it because it rejected `KedroSession` in any block. raw's Kimi answer only mentioned the smoke test in prose, so it never tripped the check.

Fix: the check now requires a block that calls `preprocess_companies` without a session, runner or catalog, and forbids those only in the unit-test module (`test_nodes.py`). Regrading round 5 with it: every with-skill answer passes for both variants on both models; every baseline answer still fails. **Both skills pass every assertion.** `make eval-test`: 32 pass.

Of the failures since round 3, most were the eval (judge errors, rubric wording, this check), not the skills.

## Findings about the process

These came out of the experiment, not out of the comparison itself.

1. **Verifying facts is not enough. Verify the snippets.** The fact sheet's first draft
   said intermediates stay loadable after a run. Its evidence test only checked
   `"X_train" in catalog`, which is true. Running the raw skill's snippet showed that
   `catalog.load("X_train")` actually raises. Without that run, both variants would have
   shipped the wrong claim.
2. **The hand-written version shipped a wrong claim anyway.** Its `# WRONG` example
   (`v1/raw:L81`) says indexing the runner result "compares a MemoryDataset with a dict,
   always fails". Kedro 1.7.0 actually raises
   `TypeError: 'MemoryDataset' object is not subscriptable`. The skill-creator version
   describes the failure correctly. The advice (call `.load()`) is right in both, and the
   error did not cost raw any eval points. It survived the fact sheet, the snippet tests
   and both eval rounds, and was only found while writing
   [skill-diff.md](skill-diff.md) on 2026-10-13. Its snippet test did run the `# WRONG`
   line and asserted `TypeError`, so the behaviour was checked. Nobody compared the
   comment's wording with what the test proved. The lesson is to check that a snippet's
   comments and prose say what its test proves, not only that the code behaves. Fixed in
   iteration 2. One caveat on the comparison: skill-creator's version was written second,
   by the same author, so it is not evidence that the method avoids such errors.
3. **A third wrong fact: a misspelled env.** `facts.md` 10b said a non-existent `env` is
   accepted silently, and both skills said Kedro then uses base config. On Kedro 1.7.0,
   `KedroSession.create(env="tset")` and `load_context()` do not raise, but the
   parameters come back empty with only a `UserWarning`, and `session.run()` raises
   `MissingConfigException`. The evidence test only checked that `load_context()` does
   not raise: the same blind spot as the X_train claim in finding 1. Found 2026-10-13
   while verifying the iteration 2 fixes. `facts.md`, its test and both skills are
   corrected, and the round 2 test built on the claim was replaced.
4. **The A/B test confirmed the facts that matter most.** The no-skill runs failed on
   `.load()`, dotted `runtime_params` and `load_context`, all non-obvious entries in the
   fact sheet. They did *not* fail on node unit tests, which supports the roadmap's worry
   that part of this skill overlaps with generic pytest knowledge.
5. **Two tasks did not discriminate.** `unit-test-preprocess-nodes` and
   `ds-pipeline-metrics` passed in every arm. For the second, the spaceflights starter
   ships a pipeline test the agent can copy. A future eval suite should drop or harden them.
6. **skill-creator's defaults need adapting for this repo:**
   - Its default workspace goes next to the skill directory, which here is inside
     `skills/`, and that directory ships in the wheel. The workspace was kept outside the repo.
   - Its benchmark aggregator compares two configurations, not three, and expects an
     `eval-N/<config>/run-N/` layout.
   - Its "pushy description" advice produced a description containing `": "`. The Cursor
     and Copilot renderers write `description:` unquoted, so that broke their YAML
     frontmatter. The description was reworded to avoid the colon. The renderer bug is
     real and is tracked separately.
7. **The runs were flaky for infrastructure reasons.** On Opus 5.5, 11 of 15 runs were
   stopped by API safeguard errors that had nothing to do with the task. The whole set
   was re-run on Sonnet 5.5, where 2 of 15 were hit: one was retried, and one had already
   finished its work. The four Opus runs that did finish agree with the Sonnet results,
   but they are not counted.

## Caveats

- **n = 1 per cell.** Five tasks, one run each. Differences between the two skill arms
  are well inside run-to-run noise.
- **Same author.** One model wrote both variants, the raw one first. The skill-creator
  version was written knowing the raw one, so this compares authoring *workflows*, not
  independent authors.
- **Ceiling effect.** Both skill arms scored 25/25, so the test set cannot rank one
  above the other. The prompts were built to separate "skill" from "no skill", not one
  skill from another. None of them targets a fact only one variant covers, such as
  `conftest.py` fixtures, a silently missing env, or an env file replacing whole keys.
- **Triggering was not tested.** Every with-skill run was handed the skill's path, so
  each description's job, getting the skill loaded at all, never came into play.
  skill-creator's longer, "pushy" description is its most distinctive output, and this
  test cannot see it.
- **Shared facts.** Both variants were written from the same verified fact sheet, which
  was most of the work. The experiment compares how the facts were *written up*, not
  how they were *found*.
- **Sonnet subagents.** Results may differ with other models or IDEs.
- **One iteration.** skill-creator's loop expects a human review of outputs and a second
  iteration. Its description-optimisation step (`run_loop.py`, which needs `claude -p`)
  has not been run.

## Files

```
facts.md                          shared, verified fact sheet
skill-diff.md                     side-by-side record of how the two SKILL.md files differ
skills.diff                       raw unified diff of the two SKILL.md files
v1/                               iteration 1 SKILL.md files, as evaluated in rounds 1 and 2
verification/
  test_facts.py                   evidence for facts.md (20 tests)
  test_raw_snippets.py            raw variant's snippets under pytest
  conftest_raw.py                 fixtures used by the raw snippet tests
  test_skill_creator_snippets.py  skill-creator variant's snippets under pytest
ab-test/
  evals.json                      the five prompts
  grade.py                        grader (re-runs tests + pattern checks)
  legacy_test_fixture.py          the broken file given to fix-legacy-test
  runs/<task>/<arm>/              agent output, grading.json, timing.json, summary.md
```

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
- **On this test set, the authoring method made no measurable difference to outcomes.**
  The variants differ in style (examples vs. explanation) and in a few facts each one
  covers, not in how well agents did with them.
- **The value of skill-creator was its process, not its prose.** Its eval loop (with-skill
  vs. baseline runs, graded) is what produced the evidence above. Hand-writing the skill
  had no equivalent step.
- **The step that caught a wrong claim was neither.** It was running the skill's own code
  snippets under pytest.

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

## Findings about the process

These came out of the experiment, not out of the comparison itself.

1. **Verifying facts is not enough. Verify the snippets.** The fact sheet's first draft
   said intermediates stay loadable after a run. Its evidence test only checked
   `"X_train" in catalog`, which is true. Running the raw skill's snippet showed that
   `catalog.load("X_train")` actually raises. Without that run, both variants would have
   shipped the wrong claim.
2. **The A/B test confirmed the facts that matter most.** The no-skill runs failed on
   `.load()`, dotted `runtime_params` and `load_context`, all non-obvious entries in the
   fact sheet. They did *not* fail on node unit tests, which supports the roadmap's worry
   that part of this skill overlaps with generic pytest knowledge.
3. **Two tasks did not discriminate.** `unit-test-preprocess-nodes` and
   `ds-pipeline-metrics` passed in every arm. For the second, the spaceflights starter
   ships a pipeline test the agent can copy. A future eval suite should drop or harden them.
4. **skill-creator's defaults need adapting for this repo:**
   - Its default workspace goes next to the skill directory, which here is inside
     `skills/`, and that directory ships in the wheel. The workspace was kept outside the repo.
   - Its benchmark aggregator compares two configurations, not three, and expects an
     `eval-N/<config>/run-N/` layout.
   - Its "pushy description" advice produced a description containing `": "`. The Cursor
     and Copilot renderers write `description:` unquoted, so that broke their YAML
     frontmatter. The description was reworded to avoid the colon. The renderer bug is
     real and is tracked separately.
5. **The runs were flaky for infrastructure reasons.** On Opus 5.5, 11 of 15 runs were
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

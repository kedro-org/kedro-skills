---
name: kedro-quality-check
description: >-
  Evaluate a Kedro project against the rules in this skill's kedro-rules.md,
  grouped into functional appropriateness, performance efficiency and
  maintainability. Writes the verdicts to kedro-quality-check/results.json and
  builds kedro-quality-check/dashboard.html. Use when asked to review, check, score
  or audit a Kedro pipeline, evaluate it against kedro-rules.md, or build the
  quality dashboard.
---

# Kedro quality check

Files named in this skill (`kedro-rules.md`, `scripts/...`) are relative to this skill's folder, the one containing this `SKILL.md`. Run the scripts from the project root, replacing `<skill folder>` below with that folder's path.

Evaluate the project, record verdicts as JSON, then build a dashboard from that JSON. You judge;
you do not fix code, rules or config while reviewing.

## The three groups

| Group key | Question it answers |
|---|---|
| `functional_appropriateness` | Has it solved the problem in an appropriate way, including the right Kedro patterns? |
| `performance_efficiency` | Does it perform efficiently without unnecessary overhead? |
| `maintainability` | Is it modular, understandable, testable and easy to change? |

## 1. Load the rules

Read `kedro-rules.md` in this skill's folder (next to this `SKILL.md`), or the rules file the user points to. Each `##` section is one
criterion with a *Good pattern* and an *Anti-pattern* list. Assign sections to groups like this:

| kedro-rules.md section | Group | id |
|---|---|---|
| Kedro version and APIs | functional_appropriateness | FA-01 |
| Data catalog | functional_appropriateness | FA-02 |
| Configuration and parameters | functional_appropriateness | FA-03 |
| Credentials, security and sensitive data | functional_appropriateness | FA-04 |
| Data validation | functional_appropriateness | FA-05 |
| Node design | maintainability | MA-01 |
| Pipeline design and modularity | maintainability | MA-02 |
| Code style and linting | maintainability | MA-03 |
| Hooks and logging | maintainability | MA-04 |
| Docs and visualisation | maintainability | MA-05 |

If the rules file has other sections, place each in the group whose question fits best and take
the next free id. If a section is missing from the file, skip it and say so in your summary.

`performance_efficiency` normally has no section in kedro-rules.md. Use these skill-defined criteria and
set `source` to `skill-defined` so the reader knows they did not come from the rules file:

| id | Criterion | Good pattern | Anti-pattern |
|---|---|---|---|
| PE-01 | Nodes avoid redundant copies and repeated computation | One conversion per column, no copy of a frame that is not mutated | Same transform done in two nodes, `.copy()` of inputs that are only read |
| PE-02 | Data operations are vectorised | pandas/numpy column operations | `iterrows`, row-wise `apply`, Python loops over rows |
| PE-03 | Dataset types suit the data | Parquet or typed formats for large tables, pickle only for models | CSV for intermediates that lose dtypes and need re-parsing, pickled DataFrames |
| PE-04 | No unnecessary I/O or unused inputs | Every node input is used, every write goes through the catalog | Extra file writes in nodes, inputs loaded but never read |

Scale matters: judge against the data size the project documents, and say so when the overhead is
real but harmless at that size.

## 2. Inspect and judge

For each criterion:

1. Read the code it concerns (`src/**/nodes.py`, `pipeline.py`, `pipeline_registry.py`,
   `settings.py`, `conf/**`, `pyproject.toml`, `requirements.txt`, `README.md`, `.gitignore`,
   tests, CI and pre-commit files). Do not judge from file names or the README alone.
2. Decide a status:
   - `pass`: the good patterns are clearly present and no anti-pattern is.
   - `mixed`: the main intent is met but a minor anti-pattern or gap remains. Say which.
   - `fail`: an anti-pattern is present, a required good pattern is missing, or there is not
     enough evidence either way.
3. Judge the code as it is now, not plans or TODOs. Be strict and consistent.
4. `message` is one or two sentences: what is wrong (or right) and where.
5. `evidence` lists `path:line` locations (or a path for a missing file). Open each one and confirm
   the line number is right before you record it.
6. A criterion needing a git history or running code you cannot see (for example "nothing
   committed") gets a caveat in `message` instead of a guess.

## 3. Write `kedro-quality-check/results.json`

Create the `kedro-quality-check/` folder in the project root if needed. Valid JSON only:

```json
{
  "project": "insurance_fraud_detection",
  "rules_source": "kedro-rules.md",
  "evaluated_at": "2026-11-09T12:00:00Z",
  "groups": {
    "functional_appropriateness": {
      "label": "Functional appropriateness",
      "question": "Has it solved the problem in an appropriate way, including the right Kedro patterns?",
      "criteria": [
        {
          "id": "FA-02",
          "title": "Data catalog",
          "source": "kedro-rules.md: Data catalog",
          "status": "fail",
          "message": "A node writes model_input.csv to a hard-coded path instead of returning it.",
          "evidence": ["src/pkg/pipelines/data_processing/nodes.py:61"]
        }
      ]
    },
    "performance_efficiency": { "label": "...", "question": "...", "criteria": [] },
    "maintainability": { "label": "...", "question": "...", "criteria": [] }
  }
}
```

All three groups must be present, with the labels and questions from the table above.
`evaluated_at` is the current UTC time. If the file already exists, replace it entirely.

## 4. Build the dashboard

```sh
python3 <skill folder>/scripts/build_dashboard.py \
    kedro-quality-check/results.json kedro-quality-check/dashboard.html
```

The script uses only the standard library, validates the JSON (it exits with a message on a bad
status, missing field or missing group), computes per-group and overall scores, and writes a
self-contained HTML file. Pass `--open` to open it in the browser. Score is
`(pass + 0.5 * mixed) / total`. Do not edit the HTML by hand; fix the JSON and rebuild.

## 5. Gate (optional, for CI)

```sh
python3 <skill folder>/scripts/gate.py kedro-quality-check/results.json \
    --min-score 40 --baseline baseline/results.json --markdown kedro-quality-check/comment.md
```

Exit code 0 means the gate passed, 1 means it failed, 2 means bad input. `--min-score` sets a floor
on the overall score. `--baseline` is the `results.json` from the target branch: the gate fails if
any criterion got worse (pass to mixed or fail, mixed to fail) or if a new criterion fails.
Improvements never fail it. A missing baseline file is skipped with a warning, so the first run
on a branch passes. `--markdown` writes a summary you can post as a PR comment. The gate only
reads the JSON; it does not run the review.

## 6. Automate in CI (only when asked)

When the user wants the gate to run on every pull request, set it up from the template
`templates/kedro-quality-gate.yml` in this skill's folder. Do this only on request.

1. Copy it to `.github/workflows/kedro-quality-gate.yml`. Never overwrite an existing file of that
   name without asking.
2. Adjust `MIN_SCORE`, the Python version and `SKILL_DIR` to the project. `SKILL_DIR` is
   `.agents/skills/kedro-quality-check`, which exists whatever IDE the skill was installed for.
3. Tell the user what it does: it runs `scripts/gate.py` on the committed
   `kedro-quality-check/results.json`, compares it with the target branch's copy and comments on
   the pull request. It does not run the review, so `results.json` must be committed with each
   change. Offer to run the review and commit it now.

## 7. Report

Give the user a short summary: the overall score, pass / mixed / fail counts per group, the
highest-impact failures, and anything you were unsure about. Name the paths of `results.json` and
`dashboard.html`. Mention any criteria that were skill-defined rather than from the rules file.

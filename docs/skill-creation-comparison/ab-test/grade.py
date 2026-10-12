"""Grade A/B runs for the testing-pipelines skill comparison.

Usage: python grade.py <iteration_dir>
Writes grading.json into every <eval>/<arm>/ run dir.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

PY = "<scratch>/spaceflights/.venv/bin/python"

TARGETS = {
    "ds-pipeline-metrics": None,  # any new/changed file under tests/pipelines/data_science
    "inspect-intermediate-xtrain": "tests/pipelines/data_science/test_split_output.py",
    "smoke-runtime-params": "tests/test_smoke.py",
    "unit-test-preprocess-nodes": "tests/pipelines/data_processing/test_nodes.py",
    "fix-legacy-test": "tests/test_legacy.py",
}


def code_of(text: str) -> str:
    """Strip comments and docstrings so assertions look at code, not prose."""
    text = re.sub(r'"""[\s\S]*?"""', "", text)
    text = re.sub(r"'''[\s\S]*?'''", "", text)
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def run_pytest(project: Path, rel: list[str]) -> tuple[bool, str]:
    r = subprocess.run(
        [PY, "-m", "pytest", "-o", "addopts=", "-q", "-p", "no:cacheprovider", *rel],
        cwd=project, capture_output=True, text=True, timeout=600,
    )
    last = [l for l in r.stdout.strip().splitlines() if l.strip()][-1:] or [""]
    return r.returncode == 0, last[0]


def checks(eval_name: str, src: str) -> list[tuple[str, bool, str]]:
    c = code_of(src)
    has = lambda p: re.search(p, c) is not None  # noqa: E731
    out = []
    if eval_name == "ds-pipeline-metrics":
        out += [
            ("Runs the pipeline in memory (SequentialRunner, no KedroSession)",
             has(r"SequentialRunner") and not has(r"KedroSession"), ""),
            ("Registers the parameters under the literal 'params:model_options' key",
             has(r"[\"']params:model_options[\"']"), ""),
            ("Reads metrics through .load() or catalog.load, not by indexing the run result",
             has(r"\.load\(") , ""),
        ]
    elif eval_name == "inspect-intermediate-xtrain":
        sliced = has(r"to_outputs\(|only_nodes\(|to_nodes\(|from_nodes\(")
        hook = has(r"after_node_run|hook_impl|HOOKS")
        out += [
            ("Makes X_train observable (slice so it is an output, or a hook), not catalog.load after a full run",
             sliced or hook, "slice" if sliced else ("hook" if hook else "")),
            ("Compares X_train columns with model_options features",
             has(r"columns") and has(r"features"), ""),
            ("Runs in memory (no KedroSession)", not has(r"KedroSession"), ""),
        ]
    elif eval_name == "smoke-runtime-params":
        out += [
            ("Calls bootstrap_project before KedroSession.create",
             has(r"bootstrap_project\(") and c.find("bootstrap_project(") < c.find("KedroSession.create"), ""),
            ("Passes runtime_params as a nested dict (no dotted key)",
             has(r"runtime_params") and not has(r"[\"']model_options\.test_size[\"']\s*:"), ""),
            ("Uses pipeline_names= (not the deprecated pipeline_name=)",
             has(r"pipeline_names\s*=") and not has(r"pipeline_name\s*="), ""),
            ("Asserts that 0.3 took effect", has(r"0\.3"), ""),
        ]
    elif eval_name == "unit-test-preprocess-nodes":
        out += [
            ("Calls both node functions directly",
             has(r"preprocess_companies\(") and has(r"preprocess_shuttles\("), ""),
            ("No Kedro machinery (no KedroSession/SequentialRunner/DataCatalog)",
             not has(r"KedroSession|SequentialRunner|DataCatalog"), ""),
        ]
    elif eval_name == "fix-legacy-test":
        out += [
            ("Removes load_context / context.run",
             not has(r"load_context|context\.run\("), ""),
            ("Smoke part uses bootstrap_project + KedroSession",
             has(r"bootstrap_project\(") and has(r"KedroSession"), ""),
            ("Reads metrics with .load()", has(r"\.load\("), ""),
            ("Registers 'params:model_options'", has(r"[\"']params:model_options[\"']"), ""),
            ("Keeps both original checks (2 test functions)",
             len(re.findall(r"^def test_|^    def test_", c, re.M)) >= 2, ""),
            ("Keeps the mae < 1 assertion", has(r"mae[\"']\]\s*<\s*1"), ""),
            ("Uses pipeline_names= (not the deprecated pipeline_name=)",
             has(r"pipeline_names\s*=") and not has(r"pipeline_name\s*="), ""),
            ("Project path does not depend on cwd (no Path.cwd())", not has(r"Path\.cwd\(\)"), ""),
        ]
    return out


def main(it: Path) -> None:
    for eval_dir in sorted(p for p in it.iterdir() if p.is_dir()):
        name = eval_dir.name
        for run in sorted(p for p in eval_dir.iterdir() if p.is_dir()):
            project, outputs = run / "project", run / "outputs"
            files = sorted(str(p.relative_to(outputs)) for p in outputs.rglob("test_*.py"))
            target = TARGETS[name]
            if target:
                files = [f for f in files if f == target] or ([target] if (project / target).exists() else [])
            exp = []
            if not files:
                exp.append({"text": "Produced the requested test file", "passed": False, "evidence": "no file"})
            else:
                ok, line = run_pytest(project, files)
                exp.append({"text": "Tests pass under pytest", "passed": ok, "evidence": line})
                src = "\n".join((project / f).read_text() for f in files)
                for text, passed, ev in checks(name, src):
                    exp.append({"text": text, "passed": bool(passed), "evidence": ev or ", ".join(files)})
            n = sum(e["passed"] for e in exp)
            (run / "grading.json").write_text(json.dumps({
                "expectations": exp,
                "summary": {"passed": n, "failed": len(exp) - n, "total": len(exp),
                            "pass_rate": round(n / len(exp), 3)},
            }, indent=2))
            print(f"{name:30s} {run.name:14s} {n}/{len(exp)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))

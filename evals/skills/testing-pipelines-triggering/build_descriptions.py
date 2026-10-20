"""Write descriptions.json: the skill descriptions the triggering suite shows the model.

Other skills come from registry.yaml (what gets installed). The two testing-pipelines
variants come from their installed SKILL.md frontmatter (the same text). The iteration 1
variants come from docs/skill-creation-comparison/v1/. Run from anywhere:
    python3 evals/skills/testing-pipelines-triggering/build_descriptions.py
"""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    block = text.split("---", 2)[1]
    return yaml.safe_load(block)


def one_line(text):
    return " ".join(text.split())


registry = yaml.safe_load((ROOT / "registry.yaml").read_text(encoding="utf-8"))
others = {
    s["id"]: one_line(s["description"])
    for s in registry["skills"]
    if not s["id"].startswith("testing-pipelines")
}

current = {
    "raw": frontmatter(ROOT / "skills/testing-pipelines-raw/SKILL.md")["description"],
    "skill-creator": frontmatter(ROOT / "skills/testing-pipelines-skill-creator/SKILL.md")["description"],
}
v1 = {
    "raw": frontmatter(ROOT / "docs/skill-creation-comparison/v1/testing-pipelines-raw.md")["description"],
    "skill-creator": frontmatter(ROOT / "docs/skill-creation-comparison/v1/testing-pipelines-skill-creator.md")["description"],
}

out = {
    "others": others,
    "variants": {
        "raw": one_line(current["raw"]),
        "skill-creator": one_line(current["skill-creator"]),
        "raw-v1": one_line(v1["raw"]),
        "skill-creator-v1": one_line(v1["skill-creator"]),
    },
}
dest = Path(__file__).with_name("descriptions.json")
dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(f"wrote {dest} ({len(others)} other skills, {len(out['variants'])} variants)")

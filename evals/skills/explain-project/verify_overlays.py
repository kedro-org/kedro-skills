"""Apply each explain-project overlay to the fixture and load it with Kedro.

Evidence that the overlays behave the way tests.yaml claims. Not run by CI.
Prints what each project registers, resolves and fails on:

    uvx --from kedro==1.7.0 --with "kedro-datasets[pandas-csvdataset,pandas-exceldataset,\
pandas-parquetdataset,plotly-plotlydataset,plotly-jsondataset,matplotlib-matplotlibdataset]" \
        --with kedro-viz==12.5.0 --with scikit-learn --with seaborn \
        python -I evals/skills/explain-project/verify_overlays.py .

Last run 2026-10-15 (Kedro 1.7.0, kedro-datasets 9.6.0, kedro-viz 12.5.0):
- stock: metrics not in the catalog (MemoryDataset).
- broken-import: feature_engineering missing from the registry, import warning.
- namespaced: active.regressor and candidate.regressor not in the catalog.
- local-params: model_options == {'test_size': 0.3}.
- tracking-leftover: settings.py fails (ModuleNotFoundError for
  kedro_viz.integrations.kedro.sqlite_store); without it, the metrics entry
  raises DatasetError.
"""
import shutil, sys, tempfile, warnings, importlib, traceback
from pathlib import Path

REPO = Path(sys.argv[1]); FIX = REPO / "evals/fixture/project"
OVL = REPO / "evals/skills/explain-project/overlays"

def build(name):
    d = Path(tempfile.mkdtemp()) / "proj"
    shutil.copytree(FIX, d)
    if name:
        shutil.copytree(OVL / name, d, dirs_exist_ok=True)
    (d / "conf/local").mkdir(exist_ok=True)
    return d

def session(d):
    from kedro.framework.startup import bootstrap_project
    from kedro.framework.session import KedroSession
    for m in [m for m in sys.modules if m.startswith("eval_project")]: del sys.modules[m]
    bootstrap_project(d)
    return KedroSession.create(project_path=d)

def run(name, fn):
    print(f"\n== {name}")
    try: fn(build(name))
    except Exception as e: print("  EXC", type(e).__name__, str(e).splitlines()[0][:200])

def broken(d):
    from kedro.framework.project import pipelines
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        session(d)
        names = sorted(pipelines.keys())
    print("  pipelines:", names)
    print("  warnings:", [str(x.message).splitlines()[0][:120] for x in w if "importing" in str(x.message)])

def namespaced(d):
    from kedro.framework.project import pipelines
    ctx = session(d).load_context()
    ds = pipelines["data_science"]
    print("  outputs:", sorted(ds.outputs()))
    print("  regressor-ish datasets:", sorted(x for x in ds.datasets() if "regressor" in x))
    cat = ctx.catalog
    for n in ("regressor", "active.regressor", "candidate.regressor"):
        print(f"  {n}: in catalog config ->", n in cat, type(cat.get(n)).__name__ if n in cat else "-")
    print("  params keys:", sorted(ctx.params))

def local_params(d):
    ctx = session(d).load_context()
    print("  model_options:", ctx.params["model_options"])

def tracking(d):
    try:
        session(d)
    except Exception as e:
        print("  session EXC:", type(e).__name__, str(e).splitlines()[0][:160])
    # Without the SQLiteStore line, does the catalog entry fail?
    s = d / "src/eval_project/settings.py"
    s.write_text("\n".join(l for l in s.read_text().splitlines() if "SQLiteStore" not in l and "SESSION_STORE" not in l))
    ctx = session(d).load_context()
    try:
        ctx.catalog.get("metrics")
        print("  metrics dataset created OK")
    except Exception as e:
        print("  catalog EXC:", type(e).__name__, str(e).splitlines()[0][:160])

def stock(d):
    from kedro.framework.project import pipelines
    ctx = session(d).load_context()
    print("  metrics in catalog:", "metrics" in ctx.catalog, "| default pipelines:", sorted(pipelines))

run(None, stock); run("broken-import", broken); run("namespaced", namespaced)
run("local-params", local_params); run("tracking-leftover", tracking)

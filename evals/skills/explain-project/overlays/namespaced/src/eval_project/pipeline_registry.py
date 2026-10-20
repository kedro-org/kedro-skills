"""Project pipelines."""

from kedro.pipeline import Pipeline

from eval_project.pipelines import data_processing, data_science, reporting


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines.

    The data science pipeline is trained twice: the model in production
    ("active") and a challenger with different settings ("candidate").

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    ds = data_science.create_pipeline()
    active = Pipeline(ds, namespace="active", inputs={"model_input_table"})
    candidate = Pipeline(ds, namespace="candidate", inputs={"model_input_table"})
    pipelines = {
        "data_processing": data_processing.create_pipeline(),
        "data_science": active + candidate,
        "reporting": reporting.create_pipeline(),
    }
    pipelines["__default__"] = sum(pipelines.values())
    return pipelines

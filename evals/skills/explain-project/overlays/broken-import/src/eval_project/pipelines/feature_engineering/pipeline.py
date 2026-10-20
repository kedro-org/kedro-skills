from kedro.pipeline import Node, Pipeline

from .nodes import add_rating_features


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=add_rating_features,
                inputs="model_input_table",
                outputs="model_input_table_with_features",
                name="add_rating_features_node",
            ),
        ]
    )

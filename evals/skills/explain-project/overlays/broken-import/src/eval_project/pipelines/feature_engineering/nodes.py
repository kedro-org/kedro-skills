import pandas as pd
from category_encoders import TargetEncoder


def add_rating_features(model_input_table: pd.DataFrame) -> pd.DataFrame:
    """Target-encodes the company location and adds it as a feature."""
    encoder = TargetEncoder(cols=["company_location"])
    encoded = encoder.fit_transform(model_input_table, model_input_table["price"])
    return model_input_table.assign(company_location_encoded=encoded["company_location"])

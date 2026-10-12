import pandas as pd
import pytest


@pytest.fixture
def model_input_table():
    return pd.DataFrame({"engines": [1, 2, 3, 4, 5], "crew": [4, 5, 6, 7, 8],
                         "passenger_capacity": [5, 6, 7, 8, 9],
                         "price": [120, 290, 30, 40, 50]})


@pytest.fixture
def model_options():
    return {"test_size": 0.2, "random_state": 3,
            "features": ["engines", "passenger_capacity", "crew"]}

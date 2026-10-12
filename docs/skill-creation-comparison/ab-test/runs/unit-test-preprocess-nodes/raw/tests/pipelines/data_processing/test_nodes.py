import pandas as pd
import pytest

from spaceflights.pipelines.data_processing.nodes import (
    preprocess_companies,
    preprocess_shuttles,
)


@pytest.fixture
def raw_companies():
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "company_rating": ["100%", "67%", "0%"],
            "iata_approved": ["t", "f", "t"],
        }
    )


@pytest.fixture
def raw_shuttles():
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "d_check_complete": ["t", "f", "f"],
            "moon_clearance_complete": ["f", "f", "t"],
            "price": ["$1,325.0", "$100.5", "$12,000.0"],
        }
    )


def test_preprocess_companies_converts_rating_to_float(raw_companies):
    result = preprocess_companies(raw_companies)

    assert result["company_rating"].dtype == float
    assert result["company_rating"].tolist() == pytest.approx([1.0, 0.67, 0.0])


def test_preprocess_companies_converts_iata_approved_to_bool(raw_companies):
    result = preprocess_companies(raw_companies)

    assert result["iata_approved"].dtype == bool
    assert result["iata_approved"].tolist() == [True, False, True]


def test_preprocess_companies_keeps_other_columns(raw_companies):
    result = preprocess_companies(raw_companies)

    assert list(result.columns) == ["id", "company_rating", "iata_approved"]
    assert result["id"].tolist() == [1, 2, 3]


def test_preprocess_shuttles_converts_price_to_float(raw_shuttles):
    result = preprocess_shuttles(raw_shuttles)

    assert result["price"].dtype == float
    assert result["price"].tolist() == pytest.approx([1325.0, 100.5, 12000.0])


def test_preprocess_shuttles_converts_flags_to_bool(raw_shuttles):
    result = preprocess_shuttles(raw_shuttles)

    assert result["d_check_complete"].dtype == bool
    assert result["moon_clearance_complete"].dtype == bool
    assert result["d_check_complete"].tolist() == [True, False, False]
    assert result["moon_clearance_complete"].tolist() == [False, False, True]


def test_preprocess_shuttles_keeps_other_columns(raw_shuttles):
    result = preprocess_shuttles(raw_shuttles)

    assert list(result.columns) == [
        "id",
        "d_check_complete",
        "moon_clearance_complete",
        "price",
    ]
    assert result["id"].tolist() == [1, 2, 3]

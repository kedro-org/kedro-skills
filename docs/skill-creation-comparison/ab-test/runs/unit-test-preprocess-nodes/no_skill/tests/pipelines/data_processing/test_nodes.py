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
            "price": ["$1,000.00", "$25.50", "$1,234,567.00"],
            "d_check_complete": ["t", "f", "f"],
            "moon_clearance_complete": ["f", "f", "t"],
        }
    )


def test_preprocess_companies_rating_is_float_fraction(raw_companies):
    result = preprocess_companies(raw_companies.copy())
    assert result["company_rating"].dtype == float
    assert result["company_rating"].tolist() == pytest.approx([1.0, 0.67, 0.0])


def test_preprocess_companies_iata_approved_is_bool(raw_companies):
    result = preprocess_companies(raw_companies.copy())
    assert result["iata_approved"].dtype == bool
    assert result["iata_approved"].tolist() == [True, False, True]


def test_preprocess_companies_preserves_other_columns_and_rows(raw_companies):
    result = preprocess_companies(raw_companies.copy())
    assert list(result.columns) == list(raw_companies.columns)
    assert result["id"].tolist() == [1, 2, 3]


def test_preprocess_companies_unexpected_flag_is_false():
    df = pd.DataFrame(
        {"company_rating": ["50%"], "iata_approved": ["yes"]}
    )
    assert preprocess_companies(df)["iata_approved"].tolist() == [False]


def test_preprocess_companies_invalid_rating_raises():
    df = pd.DataFrame({"company_rating": ["abc"], "iata_approved": ["t"]})
    with pytest.raises(ValueError):
        preprocess_companies(df)


def test_preprocess_shuttles_price_is_float(raw_shuttles):
    result = preprocess_shuttles(raw_shuttles.copy())
    assert result["price"].dtype == float
    assert result["price"].tolist() == pytest.approx([1000.0, 25.5, 1234567.0])


def test_preprocess_shuttles_boolean_columns(raw_shuttles):
    result = preprocess_shuttles(raw_shuttles.copy())
    assert result["d_check_complete"].dtype == bool
    assert result["moon_clearance_complete"].dtype == bool
    assert result["d_check_complete"].tolist() == [True, False, False]
    assert result["moon_clearance_complete"].tolist() == [False, False, True]


def test_preprocess_shuttles_preserves_other_columns_and_rows(raw_shuttles):
    result = preprocess_shuttles(raw_shuttles.copy())
    assert list(result.columns) == list(raw_shuttles.columns)
    assert result["id"].tolist() == [1, 2, 3]


def test_preprocess_shuttles_invalid_price_raises():
    df = pd.DataFrame(
        {
            "price": ["free"],
            "d_check_complete": ["t"],
            "moon_clearance_complete": ["t"],
        }
    )
    with pytest.raises(ValueError):
        preprocess_shuttles(df)

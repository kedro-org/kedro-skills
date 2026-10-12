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
            "company_location": ["Chile", "Peru", "Togo"],
        }
    )


@pytest.fixture
def raw_shuttles():
    return pd.DataFrame(
        {
            "id": [10, 11, 12],
            "price": ["$1,325.00", "$100.50", "$12"],
            "d_check_complete": ["t", "f", "f"],
            "moon_clearance_complete": ["f", "t", "f"],
            "engines": [1.0, 2.0, 3.0],
        }
    )


def test_preprocess_companies_parses_rating_as_fraction(raw_companies):
    result = preprocess_companies(raw_companies)

    assert result["company_rating"].dtype == float
    assert result["company_rating"].tolist() == pytest.approx([1.0, 0.67, 0.0])


def test_preprocess_companies_converts_iata_approved_to_bool(raw_companies):
    result = preprocess_companies(raw_companies)

    assert result["iata_approved"].dtype == bool
    assert result["iata_approved"].tolist() == [True, False, True]


def test_preprocess_companies_leaves_other_columns_and_rows_unchanged(raw_companies):
    other = raw_companies[["id", "company_location"]].copy()

    result = preprocess_companies(raw_companies)

    assert list(result.columns) == list(raw_companies.columns)
    pd.testing.assert_frame_equal(result[["id", "company_location"]], other)


def test_preprocess_companies_treats_non_t_values_as_false():
    df = pd.DataFrame(
        {"company_rating": ["50%", "50%", "50%"], "iata_approved": ["T", "", "yes"]}
    )

    result = preprocess_companies(df)

    assert result["iata_approved"].tolist() == [False, False, False]


def test_preprocess_companies_rejects_malformed_rating():
    df = pd.DataFrame({"company_rating": ["n/a"], "iata_approved": ["t"]})

    with pytest.raises(ValueError):
        preprocess_companies(df)


def test_preprocess_shuttles_parses_price_as_float(raw_shuttles):
    result = preprocess_shuttles(raw_shuttles)

    assert result["price"].dtype == float
    assert result["price"].tolist() == pytest.approx([1325.0, 100.5, 12.0])


def test_preprocess_shuttles_converts_checks_to_bool(raw_shuttles):
    result = preprocess_shuttles(raw_shuttles)

    assert result["d_check_complete"].dtype == bool
    assert result["moon_clearance_complete"].dtype == bool
    assert result["d_check_complete"].tolist() == [True, False, False]
    assert result["moon_clearance_complete"].tolist() == [False, True, False]


def test_preprocess_shuttles_leaves_other_columns_unchanged(raw_shuttles):
    other = raw_shuttles[["id", "engines"]].copy()

    result = preprocess_shuttles(raw_shuttles)

    assert list(result.columns) == list(raw_shuttles.columns)
    pd.testing.assert_frame_equal(result[["id", "engines"]], other)


def test_preprocess_shuttles_rejects_malformed_price():
    df = pd.DataFrame(
        {"price": ["free"], "d_check_complete": ["t"], "moon_clearance_complete": ["t"]}
    )

    with pytest.raises(ValueError):
        preprocess_shuttles(df)

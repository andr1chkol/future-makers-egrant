import pytest

from tests.conftest import validate_test_database_url


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://localhost/egrant_test",
        "postgresql+psycopg://localhost/egrant_test_final_assembly",
    ],
)
def test_disposable_postgresql_database_is_accepted(url):
    validate_test_database_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://localhost/demo_data",
        "postgresql+psycopg://localhost/demo_data?application_name=/egrant_test",
        "postgresql+psycopg://localhost/egrant_test?dbname=demo_data",
        "postgresql+psycopg://localhost/egrant_test?service=demo_data",
        "postgresql+psycopg://localhost/egrant_test?options=-csearch_path%3Dother",
        "sqlite:///egrant_test",
    ],
)
def test_destructive_fixture_rejects_ambiguous_or_non_test_targets(url):
    with pytest.raises(ValueError, match="isolated PostgreSQL"):
        validate_test_database_url(url)

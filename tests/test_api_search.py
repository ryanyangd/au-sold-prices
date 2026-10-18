import pytest

from au_sold_prices.api.search import escape_like, normalise_query


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("12 Example Street", "12 example st"),
        ("  12   EXAMPLE   st,  ", "12 example st"),
        ("Unit 3, 12 Sample Road", "3/12 sample rd"),
        ("u3/12 sample road", "3/12 sample rd"),
        ("apartment 5 20 grand avenue", "5/20 grand ave"),
        ("12 example st NSW", "12 example st"),
        ("5 Park Boulevarde", "5 park bvd"),
        ("14 sample crescent exampleville", "14 sample cres exampleville"),
    ],
)
def test_normalise_query(raw, expected):
    assert normalise_query(raw) == expected


def test_normalise_query_truncates():
    assert len(normalise_query("a" * 500)) == 100


def test_escape_like():
    assert escape_like(r"50%_\x") == r"50\%\_\\x"

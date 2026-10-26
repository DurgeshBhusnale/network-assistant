import pytest

from app.imports.normalise import split_name


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("priya nair", "Priya Nair"),
        ("PRIYA NAIR", "Priya Nair"),  # caps lock: whole name upper
        ("Priya NAIR", "Priya NAIR"),  # deliberate mixed input is kept
        ("A.K. Sharma", "A.K. Sharma"),  # initials survive
        ("Rahul from IBM", "Rahul From IBM"),
        ("Priya E2E", "Priya E2E"),
        ("McDonald", "McDonald"),
        ("  ravi   kumar ", "Ravi Kumar"),
        ("प्रिया नायर", "प्रिया नायर"),
    ],
)
def test_split_name_casing(raw: str, expected: str) -> None:
    result = split_name(raw)
    assert result is not None
    assert result[0] == expected


def test_split_name_first_last() -> None:
    assert split_name(None, "ANIL", "kapoor") == ("Anil Kapoor", "Anil", "Kapoor")
    assert split_name("Priya Nair") == ("Priya Nair", "Priya", "Nair")
    assert split_name("   ") is None

import pytest
from app.domain.services import clamp_rating

def test_clamp_rating_valid():
    assert clamp_rating(1) == 1
    assert clamp_rating(5) == 5

def test_clamp_rating_none():
    assert clamp_rating(None) is None

def test_clamp_rating_out_of_range():
    with pytest.raises(ValueError):
        clamp_rating(0)
    with pytest.raises(ValueError):
        clamp_rating(6)

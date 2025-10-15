from src.dash_system.recommender import probability_correct


def test_probability_correct_monotonicity():
    low = probability_correct(-2.0, 0.5)
    mid = probability_correct(0.0, 0.5)
    high = probability_correct(2.0, 0.5)

    assert 0.0 < low < mid < high < 1.0

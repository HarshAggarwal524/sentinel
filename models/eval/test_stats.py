from stats import compute_avg_and_stddev


def test_empty_list_returns_none():
    avg, stddev = compute_avg_and_stddev([])
    assert avg is None
    assert stddev is None


def test_single_value_has_zero_stddev():
    avg, stddev = compute_avg_and_stddev([42.0])
    assert avg == 42.0
    assert stddev == 0.0


def test_known_average():
    avg, stddev = compute_avg_and_stddev([10.0, 20.0, 30.0])
    assert avg == 20.0
    assert stddev > 0  # values vary, so spread should be non-zero


def test_identical_values_have_zero_stddev():
    avg, stddev = compute_avg_and_stddev([5.0, 5.0, 5.0])
    assert avg == 5.0
    assert stddev == 0.0
import numpy as np
import pytest
from plate_dependence import effective_sample_size, equicorrelated_mean_se, leave_one_plate_out

def test_independent_limit():
    assert effective_sample_size(15, 0) == 15
    assert equicorrelated_mean_se([1., 2., 3.], 0) == pytest.approx(np.std([1,2,3], ddof=1)/np.sqrt(3))

def test_perfect_correlation_limit():
    assert effective_sample_size(15, 1) == 1

def test_positive_correlation_increases_se():
    x = [0., 0.2, -0.1, 0.3, 0.4]
    assert equicorrelated_mean_se(x, 0.3) > equicorrelated_mean_se(x, 0)

def test_one_plate_is_unidentifiable():
    with pytest.raises(ValueError, match='single plate'):
        leave_one_plate_out([1., 2., 3.], [266, 266, 266])

def test_leave_plate_out():
    assert leave_one_plate_out([1, 3, 5, 7], [1, 1, 2, 2]) == {'1': 6., '2': 2.}

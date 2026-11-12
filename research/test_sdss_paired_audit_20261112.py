import numpy as np
import pytest
from research.sdss_paired_audit_20261112 import paired_bootstrap, leave_one_spectrum_out, exact_signflip_pvalues, holm_adjust

def test_bootstrap_seed_and_shape():
    x=np.array([[1.,2.],[3.,4.],[5.,6.]])
    a=paired_bootstrap(x,draws=200,seed=9)
    np.testing.assert_array_equal(a,paired_bootstrap(x,draws=200,seed=9))
    assert a.shape==(3,2)

def test_loo():
    np.testing.assert_allclose(leave_one_spectrum_out([[1,2],[3,4],[5,6]]),[[4,5],[3,4],[2,3]])

def test_exact_signflip():
    assert exact_signflip_pvalues([[1],[1],[1],[1]])[0]==pytest.approx(.125)
    assert exact_signflip_pvalues([[1],[-1]])[0]==pytest.approx(1)

def test_holm_monotone():
    np.testing.assert_allclose(holm_adjust([.04,.01,.03]),[.06,.03,.06])

def test_reject_invalid():
    with pytest.raises(ValueError):
        paired_bootstrap([[1,np.nan],[2,3]])
    with pytest.raises(ValueError):
        exact_signflip_pvalues(np.ones((19,1)))

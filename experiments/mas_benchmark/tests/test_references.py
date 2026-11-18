import pytest

from mas_benchmark import validation as V


@pytest.mark.parametrize('check', [V.tan_frozen_convergence, V.pcca_noncooperating, V.pcca_matches_central,
                                   V.risk_ratio_shares])
def test_reference_claims(check):
    for r in check():
        assert r['passed'], r


def test_swaps():
    for r in V.swaps():
        if r['method'] == 'Tan' and not r['passed']:
            pytest.xfail('Tan outside its Assumption 3 (local Slater): ' + r['note'])
        assert r['passed'], r

"""
Étape 1.D.1 : impôt de sortie par enveloppe, calculé à partir du régime.

Les attendus sont recalculés à la main à partir des paramètres du régime (taux,
abattement, seuil) lus dans le fichier, pas recopiés : un changement de
millésime ne casse pas le test, une erreur de formule le casse.
"""

import numpy as np
import pytest

from investment_calculator.tax_regime import load_regime
from investment_calculator.wrapper_tax import liquidation_tax


@pytest.fixture(scope='module')
def regime():
    return load_regime('FR', 2026)


def _rule(regime, wrapper, **context):
    return regime.select_withdrawal_rule(wrapper, **context)


def test_cto_taxes_gain_at_flat_tax(regime):
    res = liquidation_tax(regime, 'cto', contributions=100_000, final_value=[150_000, 80_000],
                          holding_years=10)
    rate = regime.flat_tax_income_rate + regime.social_rate
    assert res.gain.tolist() == [50_000, 0]
    assert res.total_tax[0] == pytest.approx(50_000 * rate)
    assert res.net_value.tolist() == pytest.approx([150_000 - 50_000 * rate, 80_000])


def test_pea_after_five_years_pays_only_social(regime):
    res = liquidation_tax(regime, 'pea', contributions=100_000, final_value=150_000,
                          holding_years=6)
    assert res.income_tax[0] == 0.0
    assert res.social_tax[0] == pytest.approx(50_000 * regime.social_rate)


def test_pea_before_five_years_pays_both(regime):
    res = liquidation_tax(regime, 'pea', contributions=100_000, final_value=150_000,
                          holding_years=3)
    rule = _rule(regime, 'pea', holding_years=3)
    assert res.income_tax[0] == pytest.approx(50_000 * rule['income_tax_rate'])
    assert res.social_tax[0] > 0


def test_livret_a_is_exempt(regime):
    res = liquidation_tax(regime, 'livret_a', contributions=20_000, final_value=24_000,
                          holding_years=5)
    assert res.total_tax[0] == 0.0
    assert res.net_value[0] == 24_000


def test_assurance_vie_allowance_and_reduced_rate(regime):
    rule = _rule(regime, 'assurance_vie', holding_years=10, premiums_paid=100_000)
    allowance = rule['allowance']['amount_single']
    res = liquidation_tax(regime, 'assurance_vie', contributions=100_000, final_value=150_000,
                          holding_years=10)
    assert res.income_tax[0] == pytest.approx((50_000 - allowance) * rule['income_tax_rate'])
    assert res.social_tax[0] == pytest.approx(50_000 * regime.social_rate)


def test_assurance_vie_couple_doubles_the_allowance(regime):
    single = liquidation_tax(regime, 'assurance_vie', contributions=100_000,
                             final_value=150_000, holding_years=10)
    couple = liquidation_tax(regime, 'assurance_vie', contributions=100_000,
                             final_value=150_000, holding_years=10, couple=True)
    rule = _rule(regime, 'assurance_vie', holding_years=10, premiums_paid=100_000)
    extra = rule['allowance']['amount_single'] * rule['income_tax_rate']
    assert single.income_tax[0] - couple.income_tax[0] == pytest.approx(extra)


def test_assurance_vie_premiums_above_threshold_split_the_gain(regime):
    low = _rule(regime, 'assurance_vie', holding_years=10, premiums_paid=1)
    high = _rule(regime, 'assurance_vie', holding_years=10, premiums_paid=10**9)
    threshold = low['when']['premiums_paid']['lte']
    contributions, final = 2 * threshold, 2 * threshold + 100_000
    res = liquidation_tax(regime, 'assurance_vie', contributions=contributions,
                          final_value=final, holding_years=10)
    allowance = low['allowance']['amount_single']
    # moitié de la plus-value sous le seuil (taux réduit), moitié au-delà ; l'abattement
    # s'impute d'abord sur la fraction au taux réduit.
    expected = (50_000 - allowance) * low['income_tax_rate'] + 50_000 * high['income_tax_rate']
    assert res.income_tax[0] == pytest.approx(expected)


def test_assurance_vie_before_eight_years_is_taxed_without_allowance(regime):
    res = liquidation_tax(regime, 'assurance_vie', contributions=100_000, final_value=150_000,
                          holding_years=5)
    rule = _rule(regime, 'assurance_vie', holding_years=5, premiums_paid=100_000)
    assert 'allowance' not in rule
    assert res.income_tax[0] == pytest.approx(50_000 * rule['income_tax_rate'])


@pytest.mark.parametrize('wrapper', ['per', 'immobilier_direct'])
def test_unsupported_wrappers_are_refused_explicitly(regime, wrapper):
    with pytest.raises(NotImplementedError, match=wrapper):
        liquidation_tax(regime, wrapper, contributions=1, final_value=2, holding_years=10)


def test_negative_inputs_are_refused(regime):
    with pytest.raises(ValueError, match='positifs'):
        liquidation_tax(regime, 'cto', contributions=-1, final_value=1, holding_years=1)
    with pytest.raises(ValueError, match='négative'):
        liquidation_tax(regime, 'cto', contributions=1, final_value=-1, holding_years=1)


def test_net_value_never_exceeds_final_value_and_tax_grows_with_gain(regime):
    values = np.linspace(0, 400_000, 81)
    for wrapper in ('cto', 'pea', 'assurance_vie', 'livret_a'):
        res = liquidation_tax(regime, wrapper, contributions=100_000, final_value=values,
                              holding_years=10)
        assert (res.net_value <= values + 1e-9).all()
        assert (np.diff(res.total_tax) >= -1e-9).all()
        assert (np.diff(res.net_value) >= -1e-9).all()

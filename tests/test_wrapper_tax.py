"""
Étape 1.D.1 : impôt de sortie par enveloppe, calculé à partir du régime.

Les attendus sont recalculés à la main à partir des paramètres du régime (taux,
abattement, seuil) lus dans le fichier, pas recopiés : un changement de
millésime ne casse pas le test, une erreur de formule le casse.
"""

import numpy as np
import pytest

from investment_calculator.tax_regime import load_regime
from investment_calculator.wrapper_tax import (
    RealEstateLot,
    liquidation_tax,
    real_estate_liquidation_tax,
)


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


# --------------------------------------------------------------------------- #
# Plus-values immobilières : lots, abattements, surtaxe
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("years, income, social", [
    (5, 0.0, 0.0),
    (6, 0.06, 0.0165),
    (21, 0.96, 0.264),
    (22, 1.0, 0.28),
    (23, 1.0, 0.37),
    (30, 1.0, 1.0),
    (6.9, 0.06, 0.0165),
])
def test_abattement_pour_duree_de_detention_suit_le_bofip(regime, years, income, social):
    """BOI-RFPI-PVI-20-20, § 60 et § 70 : seules les années révolues comptent."""
    assert regime.real_estate_holding_allowance(years, against='income_tax') == pytest.approx(
        income
    )
    assert regime.real_estate_holding_allowance(
        years, against='social_contributions'
    ) == pytest.approx(social)


def test_cession_immobiliere_chaque_lot_a_son_abattement(regime):
    rule = _rule(regime, 'immobilier_direct', holding_years=0)
    ir_rate, ps_rate = rule['income_tax_rate'], regime.resolve_social_rate(rule)
    lots = [RealEstateLot(10_000, 20_000.0, 25), RealEstateLot(10_000, 20_000.0, 3)]
    res = real_estate_liquidation_tax(regime, 'immobilier_direct', lots)
    social_25 = 1.0 - regime.real_estate_holding_allowance(25, against='social_contributions')
    # Le lot de 25 ans est exonéré d'impôt sur le revenu ; celui de 3 ans n'a aucun abattement.
    assert res.income_tax[0] == pytest.approx(10_000 * ir_rate)
    assert res.social_tax[0] == pytest.approx(10_000 * ps_rate * (1 + social_25))
    assert res.gain[0] == 20_000
    assert res.net_value[0] == pytest.approx(40_000 - res.total_tax[0])


def test_cession_immobiliere_moins_value_d_un_lot_non_imputee(regime):
    lots = [RealEstateLot(10_000, 15_000.0, 2), RealEstateLot(10_000, 5_000.0, 2)]
    res = real_estate_liquidation_tax(regime, 'immobilier_direct', lots)
    assert res.gain[0] == 5_000


def test_cession_immobiliere_surtaxe_seuil_par_conjoint(regime):
    """BOI-RFPI-TPVIE-20, § 40 : le seuil de 50 000 € s'apprécie par conjoint."""
    rule = _rule(regime, 'immobilier_direct', holding_years=0)
    lots = [RealEstateLot(0, 100_000.0, 1)]
    seul = real_estate_liquidation_tax(regime, 'immobilier_direct', lots)
    couple = real_estate_liquidation_tax(regime, 'immobilier_direct', lots, couple=True)
    assert seul.income_tax[0] == pytest.approx(
        100_000 * rule['income_tax_rate'] + regime.real_estate_surtax_due(100_000)
    )
    assert couple.income_tax[0] == pytest.approx(100_000 * rule['income_tax_rate']), (
        "Pour un couple, chaque conjoint a 50 000 € de plus-value : pas de surtaxe."
    )


def test_cession_immobiliere_par_scenario(regime):
    res = real_estate_liquidation_tax(
        regime, 'immobilier_direct', [RealEstateLot(100_000, np.array([200_000.0, 90_000.0]), 10)]
    )
    assert res.gain.tolist() == [100_000, 0]
    assert res.total_tax[1] == 0.0
    assert res.net_value[1] == 90_000


def test_cession_immobiliere_sans_lot_refusee(regime):
    with pytest.raises(ValueError, match="Aucun lot"):
        real_estate_liquidation_tax(regime, 'immobilier_direct', [])

"""
Impôt de sortie par enveloppe, calculé à partir du régime fiscal.

Pour une enveloppe donnée, le module liquide l'intégralité de la position à
l'horizon : il sélectionne la règle de retrait du régime selon la durée de
détention et l'encours de primes, puis applique son taux d'impôt sur le revenu,
son taux social et son éventuel abattement à la plus-value. Aucun taux ni seuil
ne figure ici : tout vient du fichier ``tax_regimes/*.json`` (ADR 0001).

Périmètre
---------
Enveloppes prises en charge : celles dont la base imposable est la plus-value
(``gain_only`` ou ``proportional_gain``) et dont le taux est un nombre ou le
renvoi ``flat_tax`` : CTO, PEA, assurance-vie, Livret A. Les autres lèvent une
``NotImplementedError`` explicite plutôt qu'un zéro silencieux :

- ``per`` : déduction à l'entrée et imposition au barème de la totalité de la
  sortie, qui dépendent du revenu du foyer ;
- ``immobilier_direct`` : sa cession relève de :func:`real_estate_liquidation_tax`,
  qui calcule la plus-value lot par lot avec les abattements pour durée de
  détention et la surtaxe. Les revenus fonciers annuels ne sont pas dans ce module.

Choix de modélisation (à faire valider par un fiscaliste)
---------------------------------------------------------
- Liquidation totale à l'horizon, en une fois ; la durée de détention est celle
  de l'ouverture de l'enveloppe, pas du dernier versement.
- Une moins-value ne donne ni impôt ni crédit : elle n'est pas imputée sur
  d'autres gains.
- Assurance-vie : quand les primes dépassent le seuil de la règle, la plus-value
  est répartie au prorata des primes sous le seuil (règle réduite) et au-delà
  (règle suivante). L'abattement annuel s'impute d'abord sur la fraction taxée
  au taux le plus bas, hypothèse prudente (elle donne l'impôt le plus élevé).
- L'abattement ne porte que sur l'impôt sur le revenu, jamais sur les
  prélèvements sociaux.
- L'impôt annuel sur les revenus distribués (dividendes, coupons) d'une
  enveloppe imposée au fil de l'eau n'est pas dans ce module.
"""

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from investment_calculator.tax_regime import TaxRegime, _condition_holds

logger = logging.getLogger(__name__)

SUPPORTED_BASES = ("gain_only", "proportional_gain")


@dataclass(frozen=True)
class LiquidationResult:
    """
    Résultat d'une liquidation, un élément par valeur finale.

    Attributes:
        gain: plus-value imposable (valeur finale moins versements, plancher 0).
        income_tax: impôt sur le revenu dû à la sortie.
        social_tax: prélèvements sociaux dus à la sortie.
        net_value: valeur finale moins les deux impôts.
    """

    gain: np.ndarray
    income_tax: np.ndarray
    social_tax: np.ndarray
    net_value: np.ndarray

    @property
    def total_tax(self) -> np.ndarray:
        return self.income_tax + self.social_tax


def _check_supported(regime: TaxRegime, wrapper_id: str, rule: dict[str, Any]) -> None:
    base = rule.get("taxable_base")
    rate = rule.get("income_tax_rate")
    annual = regime.wrapper(wrapper_id).get("growth_taxed_annually")
    if base not in SUPPORTED_BASES or rate == "progressive" or annual:
        raise NotImplementedError(
            f"L'impôt de sortie de l'enveloppe {wrapper_id!r} (régime {regime.id}) n'est pas "
            f"modélisé : base {base!r}, taux {rate!r}, imposition annuelle {annual!r}. "
            "Seules les enveloppes imposées sur la plus-value à taux fixe le sont "
            "(cto, pea, assurance_vie, livret_a). "
            "Retirez cette enveloppe des enveloppes ouvrables, ou attendez son modèle."
        )


def _income_allowance(rule: dict[str, Any], couple: bool) -> float:
    allowance = rule.get("allowance")
    if not allowance:
        return 0.0
    if allowance.get("against") != "income_tax" or allowance.get("period") != "annual":
        raise NotImplementedError(
            f"Abattement non géré : {allowance}. Seul un abattement annuel contre l'impôt "
            "sur le revenu est modélisé."
        )
    return float(allowance["amount_couple" if couple else "amount_single"])


def liquidation_tax(
    regime: TaxRegime,
    wrapper_id: str,
    *,
    contributions: float,
    final_value: np.ndarray | float,
    holding_years: float,
    couple: bool = False,
    cost_basis: np.ndarray | float | None = None,
) -> LiquidationResult:
    """
    Impôt dû à la liquidation totale d'une enveloppe.

    Args:
        regime: régime fiscal.
        wrapper_id: identifiant de l'enveloppe (``cto``, ``pea``, ...).
        contributions: versements cumulés dans l'enveloppe, en euros (≥ 0).
        final_value: valeur de l'enveloppe à l'horizon, par scénario.
        holding_years: années écoulées depuis l'ouverture de l'enveloppe.
        couple: foyer imposé en couple (abattement de l'assurance-vie doublé).
        cost_basis: prix de revient, par scénario, quand il diffère des versements
            (revenus déjà imposés puis réinvestis dans un CTO). Par défaut, les
            versements. Le seuil de primes de l'assurance-vie reste celui des versements.

    Raises:
        ValueError: versements négatifs ou valeur finale négative.
        NotImplementedError: enveloppe hors périmètre (voir le module).
    """
    if contributions < 0:
        raise ValueError(
            f"Les versements doivent être positifs ou nuls (reçu {contributions}). "
            "Passez la somme des versements, sans les retraits."
        )
    value = np.atleast_1d(np.asarray(final_value, dtype=float))
    if (value < 0).any():
        raise ValueError(
            "La valeur finale d'une enveloppe ne peut pas être négative : "
            "vérifiez la simulation du patrimoine."
        )
    basis = contributions if cost_basis is None else np.asarray(cost_basis, dtype=float)
    gain = np.clip(value - basis, 0.0, None)

    first = regime.select_withdrawal_rule(
        wrapper_id, holding_years=holding_years, premiums_paid=contributions
    )
    _check_supported(regime, wrapper_id, first)

    # Part de la plus-value soumise à chaque règle : au-dessus du seuil de primes d'une règle
    # réduite (assurance-vie), la fraction sous le seuil relève de cette règle, le reste de `first`.
    tranches: list[tuple[float, dict[str, Any]]] = [(1.0, first)]
    for rule in regime.wrapper(wrapper_id).get("withdrawal_rules") or []:
        cap = (rule.get("when") or {}).get("premiums_paid", {}).get("lte")
        if cap is None or contributions <= cap:
            continue
        duration_only = {k: v for k, v in rule["when"].items() if k != "premiums_paid"}
        if _condition_holds(duration_only, {"holding_years": holding_years}):
            _check_supported(regime, wrapper_id, rule)
            low_share = cap / contributions
            tranches = [(low_share, rule), (1.0 - low_share, first)]
            break

    income_tax = np.zeros_like(gain)
    social_tax = np.zeros_like(gain)
    allowance = max(_income_allowance(rule, couple) for _, rule in tranches)
    allowance_left = np.full_like(gain, allowance)

    # Abattement imputé d'abord sur la fraction au taux d'impôt le plus bas (hypothèse prudente).
    ordered = sorted(
        tranches, key=lambda t: float(regime.resolve_income_tax_rate(t[1], taxable_amount=1.0))
    )
    for share, rule in ordered:
        part = gain * share
        base = np.clip(part - allowance_left, 0.0, None)
        allowance_left = np.clip(allowance_left - part, 0.0, None)
        income_tax += base * regime.resolve_income_tax_rate(rule, taxable_amount=1.0)
        social_tax += part * regime.resolve_social_rate(rule)

    net = value - income_tax - social_tax
    return LiquidationResult(gain=gain, income_tax=income_tax, social_tax=social_tax, net_value=net)


@dataclass(frozen=True)
class RealEstateLot:
    """
    Un lot de parts acquis à une même date, vendu à l'horizon.

    Attributes:
        cost: prix d'acquisition, frais d'acquisition réels compris (commission
            de souscription d'une SCPI), en euros.
        value: prix de cession, par scénario.
        holding_years: années écoulées entre l'acquisition et la cession.
    """

    cost: float
    value: np.ndarray | float
    holding_years: float


def real_estate_liquidation_tax(
    regime: TaxRegime,
    wrapper_id: str,
    lots: list[RealEstateLot],
    *,
    couple: bool = False,
) -> LiquidationResult:
    """
    Impôt dû à la cession de biens ou de parts soumis au régime des plus-values
    immobilières (``immobilier_direct``, parts de SCPI détenues en direct).

    Chaque lot a sa propre durée de détention (BOI-RFPI-SPI-20, § 30 et § 40) :
    sa plus-value reçoit l'abattement de son ancienneté, séparément pour
    l'impôt sur le revenu et pour les prélèvements sociaux. L'impôt sur le
    revenu applique le taux de la règle de retrait de l'enveloppe ; les
    prélèvements sociaux, son taux social. La surtaxe sur les plus-values
    élevées porte sur la plus-value totale de la cession, après abattement ;
    elle est comptée dans ``income_tax``. Pour un couple, son seuil s'apprécie
    par conjoint, sur la moitié de la plus-value (BOI-RFPI-TPVIE-20, § 40 et § 50).

    Choix de modélisation (à faire valider) : la moins-value d'un lot ne
    s'impute pas sur la plus-value des autres lots.

    Raises:
        ValueError: aucun lot, prix d'acquisition ou valeur négatifs.
        NotImplementedError: le régime ne décrit pas les abattements ou la surtaxe.
    """
    if not lots:
        raise ValueError(
            "Aucun lot à céder : passez au moins un lot (prix d'acquisition, valeur, ancienneté)."
        )
    rule = regime.select_withdrawal_rule(wrapper_id, holding_years=max(
        lot.holding_years for lot in lots
    ))
    if rule.get("taxable_base") != "gain_only" or rule.get("income_tax_rate") == "progressive":
        raise NotImplementedError(
            f"L'enveloppe {wrapper_id!r} (régime {regime.id}) n'est pas imposée sur la "
            f"plus-value à taux fixe : base {rule.get('taxable_base')!r}, taux "
            f"{rule.get('income_tax_rate')!r}. Utilisez liquidation_tax pour cette enveloppe."
        )
    income_rate = regime.resolve_income_tax_rate(rule, taxable_amount=1.0)
    social_rate = regime.resolve_social_rate(rule)

    values = [np.atleast_1d(np.asarray(lot.value, dtype=float)) for lot in lots]
    total_value = np.zeros(max(v.size for v in values))
    total_gain = np.zeros_like(total_value)
    income_base = np.zeros_like(total_value)
    social_tax = np.zeros_like(total_value)
    for lot, value in zip(lots, values, strict=True):
        if lot.cost < 0 or (value < 0).any():
            raise ValueError(
                f"Lot de {lot.holding_years} ans : prix d'acquisition et valeur doivent être "
                f"positifs (reçu {lot.cost}). Vérifiez la simulation du patrimoine."
            )
        gain = np.clip(value - lot.cost, 0.0, None)
        income_allowance = regime.real_estate_holding_allowance(
            lot.holding_years, against="income_tax"
        )
        social_allowance = regime.real_estate_holding_allowance(
            lot.holding_years, against="social_contributions"
        )
        total_value = total_value + value
        total_gain = total_gain + gain
        income_base = income_base + gain * (1.0 - income_allowance)
        social_tax = social_tax + gain * (1.0 - social_allowance) * social_rate

    sellers = 2 if couple else 1
    surtax = np.array([sellers * regime.real_estate_surtax_due(g / sellers) for g in income_base])
    income_tax = income_base * income_rate + surtax
    net = total_value - income_tax - social_tax
    return LiquidationResult(
        gain=total_gain, income_tax=income_tax, social_tax=social_tax, net_value=net
    )

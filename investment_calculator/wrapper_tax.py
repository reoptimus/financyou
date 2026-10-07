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
- ``immobilier_direct`` : revenus fonciers annuels et abattements pour durée de
  détention, non portés par ce calcul.

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
    gain = np.clip(value - contributions, 0.0, None)

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


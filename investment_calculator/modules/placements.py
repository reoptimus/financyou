"""
Module GSE+ : les placements accessibles à un foyer, avant impôt.

Chaque placement du catalogue (:mod:`investment_calculator.placement_catalog`)
est construit à partir des scénarios du GSE (module ``scenario_generator``) :
un rendement annuel par scénario et par année, **net des frais annuels du
placement et avant tout impôt**. L'impôt, qui dépend de l'utilisateur et de la
durée de détention, est l'affaire de GSE++.

Les frais d'entrée ne sont pas dans ces rendements : ils portent sur chaque
versement, pas sur une année de détention. Ils sont exposés à part
(:func:`entry_fee_rates`).

Équivalent R : ``legacy/R_scripts/Produits_placements.R``. Voir
``docs/adr/0002-le-placement-est-l-unite-d-optimisation.md``.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from investment_calculator.placement_catalog import PlacementCatalog

logger = logging.getLogger(__name__)

__all__ = ["UnsourcedValueError", "build_gross_placements", "entry_fee_rates"]

INDEX_COLUMNS = ("scenario_id", "time_period")


class UnsourcedValueError(ValueError):
    """Un paramètre nécessaire au calcul vaut ``null`` dans le catalogue."""


def _required(value: Any, placement_id: str, name: str) -> float:
    """Refuse une valeur non sourcée plutôt que de la remplacer par un défaut."""
    if value is None:
        raise UnsourcedValueError(
            f"Le placement {placement_id!r} n'a pas de valeur pour {name} dans le "
            f"catalogue : elle n'est pas encore sourcée. Renseignez-la dans "
            f"placement_catalogs/<catalogue>.json, ou retirez ce placement du calcul."
        )
    return float(value)


def _after_fee(returns: np.ndarray, annual_fee: float) -> np.ndarray:
    """Rendement après des frais prélevés sur l'encours de fin d'année : (1 + r)(1 - f) - 1."""
    # Écrit r - f(1 + r) pour que des frais nuls rendent r à l'identique.
    result: np.ndarray = returns - annual_fee * (1.0 + returns)
    return result


def _smoothed_euro_fund(
    placement: dict[str, Any], scenarios: pd.DataFrame, annual_fee: float
) -> np.ndarray:
    """
    Fonds en euros lissé : le rendement servi suit le rendement comptable d'un
    portefeuille obligataire dont une fraction ``1 / renewal_years`` est
    renouvelée chaque année au taux de référence du GSE.

    Rendement du portefeuille : ``y(t) = y(t-1) + (r(t) - y(t-1)) / renewal_years``,
    avec ``y(-1) = initial_yield``. Rendement servi :
    ``max(pass_through × y(t), floor_rate)``, puis frais de gestion. Les lignes
    sont supposées annuelles, comme partout dans GSE+.
    """
    support = placement["support"]
    pid = placement["id"]
    pass_through = _required(support["pass_through"], pid, "support.pass_through")
    floor = _required(support["floor_rate"], pid, "support.floor_rate")
    initial_yield = _required(support["initial_yield"], pid, "support.initial_yield")
    renewal_years = _required(support["renewal_years"], pid, "support.renewal_years")
    if renewal_years < 1.0:
        raise ValueError(
            f"Le placement {pid!r} a renewal_years = {renewal_years} : il faut au moins "
            f"1 an (1 = tout le portefeuille est renouvelé chaque année, sans lissage)."
        )

    # Récurrence dans l'ordre du temps de chaque scénario, quel que soit l'ordre
    # des lignes reçues ; le résultat est rendu dans l'ordre d'origine.
    order = np.lexsort((
        scenarios["time_period"].to_numpy(dtype=float),
        pd.factorize(scenarios["scenario_id"])[0],
    ))
    ids = scenarios["scenario_id"].to_numpy()[order]
    reference = scenarios[support["reference_series"]].to_numpy(dtype=float)[order]
    portfolio_yield = np.empty_like(reference)
    previous = initial_yield
    for i, rate in enumerate(reference):
        if i > 0 and ids[i] != ids[i - 1]:
            previous = initial_yield
        previous = previous + (rate - previous) / renewal_years
        portfolio_yield[i] = previous

    served = np.maximum(pass_through * portfolio_yield, floor)
    result = np.empty_like(served)
    result[order] = _after_fee(served, annual_fee)
    return result


def _support_returns(
    placement: dict[str, Any], scenarios: pd.DataFrame, annual_fee: float
) -> np.ndarray:
    """Rendement annuel du support, net des frais annuels, pour chaque ligne des scénarios."""
    support = placement["support"]
    pid = placement["id"]
    model = support["model"]

    if model == "gse_series":
        gross = scenarios[support["series"]].to_numpy(dtype=float)
        result: np.ndarray = _after_fee(gross, annual_fee)
        return result

    if model == "euro_fund":
        # Rendement servi = part du rendement de référence, jamais sous le
        # plancher, puis frais de gestion : le capital est garanti hors frais.
        pass_through = _required(support["pass_through"], pid, "support.pass_through")
        floor = _required(support["floor_rate"], pid, "support.floor_rate")
        reference = scenarios[support["reference_series"]].to_numpy(dtype=float)
        served = np.maximum(pass_through * reference, floor)
        result = _after_fee(served, annual_fee)
        return result

    if model == "euro_fund_smoothed":
        return _smoothed_euro_fund(placement, scenarios, annual_fee)

    if model == "regulated_rate":
        # Arrêté du 27 janvier 2021 : moyenne pondérée du taux court et de
        # l'inflation, arrondie au pas le plus proche (vers le haut à égalité),
        # jamais sous le plancher. Taux net de frais : les frais annuels s'appliquent.
        step = float(support["rounding_step"])
        raw = (
            float(support["short_rate_weight"]) * scenarios["interest_rate"].to_numpy(dtype=float)
            + float(support["inflation_weight"]) * scenarios["inflation"].to_numpy(dtype=float)
        )
        rounded = np.floor(raw / step + 0.5 + 1e-9) * step
        rate = np.maximum(rounded, float(support["floor_rate"]))
        result = _after_fee(rate, annual_fee)
        return result

    raise NotImplementedError(
        f"Modèle de support {model!r} (placement {pid!r}) non pris en charge par GSE+. "
        f"Modèles pris en charge : gse_series, euro_fund, euro_fund_smoothed, "
        f"regulated_rate."
    )


def build_gross_placements(
    scenarios: pd.DataFrame,
    catalog: PlacementCatalog,
    placement_ids: list[str] | None = None,
) -> pd.DataFrame:
    """
    Construire GSE+ : le rendement annuel de chaque placement, avant impôt.

    Args:
        scenarios: scénarios du GSE, une ligne par (scénario, année), avec les
            colonnes ``scenario_id`` et ``time_period`` et les séries citées par
            le catalogue.
        catalog: catalogue des placements.
        placement_ids: placements à construire ; tous ceux du catalogue par défaut.

    Returns:
        Un tableau indexé par (``scenario_id``, ``time_period``), une colonne par
        placement : rendement annuel net des frais annuels, avant impôt.

    Raises:
        UnsourcedValueError: un paramètre nécessaire vaut ``null`` dans le catalogue.
        ValueError: une colonne nécessaire manque dans les scénarios.
    """
    ids = placement_ids if placement_ids is not None else catalog.placement_ids
    missing_index = [c for c in INDEX_COLUMNS if c not in scenarios.columns]
    if missing_index:
        raise ValueError(
            f"Les scénarios n'ont pas les colonnes {missing_index}. Utilisez la sortie "
            f"'scenarios' de scenario_generator.ScenarioGenerator.generate."
        )

    columns: dict[str, np.ndarray] = {}
    for pid in ids:
        placement = catalog.placement(pid)
        needed = _series_needed(placement)
        absent = [c for c in needed if c not in scenarios.columns]
        if absent:
            raise ValueError(
                f"Le placement {pid!r} a besoin des séries {absent}, absentes des "
                f"scénarios (colonnes : {list(scenarios.columns)})."
            )
        annual_fee = _required(placement["fees"]["annual_rate"], pid, "fees.annual_rate")
        columns[pid] = _support_returns(placement, scenarios, annual_fee)

    index = pd.MultiIndex.from_frame(scenarios[list(INDEX_COLUMNS)])
    result = pd.DataFrame(columns, index=index)
    logger.info(
        "GSE+ construit : %d placement(s) sur %d lignes de scénarios (catalogue %s)",
        len(ids), len(result), catalog.id,
    )
    return result


def entry_fee_rates(
    catalog: PlacementCatalog, placement_ids: list[str] | None = None
) -> dict[str, float]:
    """Frais d'entrée de chaque placement, en fraction du versement."""
    ids = placement_ids if placement_ids is not None else catalog.placement_ids
    return {
        pid: _required(catalog.placement(pid)["fees"]["entry_rate"], pid, "fees.entry_rate")
        for pid in ids
    }


def _series_needed(placement: dict[str, Any]) -> list[str]:
    support = placement["support"]
    if support["model"] == "gse_series":
        return [str(support["series"])]
    if support["model"] in ("euro_fund", "euro_fund_smoothed"):
        return [str(support["reference_series"])]
    if support["model"] == "regulated_rate":
        return ["interest_rate", "inflation"]
    return []

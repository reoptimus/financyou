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


def _time_order(scenarios: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """
    Ordre des lignes qui parcourt chaque scénario dans l'ordre du temps, et
    marqueur des lignes qui ouvrent un nouveau scénario dans cet ordre.

    Les modèles à mémoire (portefeuille renouvelé, provision) suivent cet ordre,
    quel que soit l'ordre des lignes reçues ; leur résultat est rendu dans
    l'ordre d'origine par ``result[order] = ...``.
    """
    order = np.lexsort((
        scenarios["time_period"].to_numpy(dtype=float),
        pd.factorize(scenarios["scenario_id"])[0],
    ))
    ids = scenarios["scenario_id"].to_numpy()[order]
    starts = np.ones(len(ids), dtype=bool)
    starts[1:] = ids[1:] != ids[:-1]
    return order, starts


def _book_yield(
    reference: np.ndarray,
    starts: np.ndarray,
    initial_yield: float,
    renewal_years: float,
    placement_id: str,
) -> np.ndarray:
    """
    Rendement comptable d'un portefeuille obligataire dont une fraction
    ``1 / renewal_years`` est réinvestie chaque année au taux de référence :
    ``y(t) = y(t-1) + (r(t) - y(t-1)) / renewal_years``, avec ``y(-1) = initial_yield``.
    Les tableaux sont dans l'ordre de :func:`_time_order`.
    """
    if renewal_years < 1.0:
        raise ValueError(
            f"Le placement {placement_id!r} a renewal_years = {renewal_years} : il faut "
            f"au moins 1 an (1 = tout le portefeuille est renouvelé chaque année, sans "
            f"lissage)."
        )
    portfolio_yield = np.empty_like(reference)
    previous = initial_yield
    for i, rate in enumerate(reference):
        if starts[i]:
            previous = initial_yield
        previous = previous + (rate - previous) / renewal_years
        portfolio_yield[i] = previous
    return portfolio_yield


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

    order, starts = _time_order(scenarios)
    reference = scenarios[support["reference_series"]].to_numpy(dtype=float)[order]
    portfolio_yield = _book_yield(reference, starts, initial_yield, renewal_years, pid)

    served = np.maximum(pass_through * portfolio_yield, floor)
    result: np.ndarray = np.empty_like(served)
    result[order] = _after_fee(served, annual_fee)
    return result


def _general_account_euro_fund(
    placement: dict[str, Any], scenarios: pd.DataFrame, annual_fee: float
) -> np.ndarray:
    """
    Fonds en euros adossé à l'actif général de l'assureur, lissé par la
    provision pour participation aux bénéfices (PPB).

    Chaque année :

    1. rendement de l'actif ``a(t)`` = somme pondérée des actifs du support :
       une série du GSE (valeur de marché) ou un portefeuille obligataire en
       valeur comptable (:func:`_book_yield`) ;
    2. réserve disponible ``B(t) = P(t-1) + pass_through × a(t)``, avec
       ``P(-1) = initial_rate`` (stock de PPB en fraction de l'encours) ;
    3. taux servi ``s(t) = max(B(t) / release_divisor, floor_rate)`` ;
    4. provision restante ``P(t) = max(B(t) - s(t), 0)`` : la provision n'est
       jamais négative, l'assureur absorbe ce qu'elle ne couvre pas (capital
       garanti) ;
    5. frais de gestion puis marge de l'assureur, prélevés comme des frais sur
       l'encours.

    La provision est exprimée en fraction de l'encours, sans tenir compte de la
    croissance de l'encours d'une année sur l'autre.
    """
    support = placement["support"]
    pid = placement["id"]
    pass_through = _required(support["pass_through"], pid, "support.pass_through")
    floor = _required(support["floor_rate"], pid, "support.floor_rate")
    margin = _required(support["insurer_margin"], pid, "support.insurer_margin")
    reserve = support["profit_sharing_reserve"]
    initial_reserve = _required(
        reserve["initial_rate"], pid, "support.profit_sharing_reserve.initial_rate"
    )
    divisor = _required(
        reserve["release_divisor"], pid, "support.profit_sharing_reserve.release_divisor"
    )
    if divisor < 1.0:
        raise ValueError(
            f"Le placement {pid!r} a release_divisor = {divisor} : il faut au moins 1 "
            f"(1 = toute la provision est servie chaque année, sans lissage)."
        )

    order, starts = _time_order(scenarios)
    asset_return = np.zeros(len(order))
    total_weight = 0.0
    for k, asset in enumerate(support["assets"]):
        name = f"support.assets[{k}]"
        weight = _required(asset["weight"], pid, f"{name}.weight")
        total_weight += weight
        if asset["kind"] == "gse_series":
            returns = scenarios[asset["series"]].to_numpy(dtype=float)[order]
        else:  # book_bonds, seule autre valeur admise par le schéma
            reference = scenarios[asset["reference_series"]].to_numpy(dtype=float)[order]
            returns = _book_yield(
                reference,
                starts,
                _required(asset["initial_yield"], pid, f"{name}.initial_yield"),
                _required(asset["renewal_years"], pid, f"{name}.renewal_years"),
                pid,
            )
        asset_return += weight * returns
    if abs(total_weight - 1.0) > 1e-9:
        raise ValueError(
            f"Les poids de l'actif général du placement {pid!r} font {total_weight:.6g} "
            f"au lieu de 1. Corrigez support.assets[].weight dans le catalogue."
        )

    served = np.empty_like(asset_return)
    provision = initial_reserve
    for i, a in enumerate(asset_return):
        if starts[i]:
            provision = initial_reserve
        available = provision + pass_through * a
        served[i] = max(available / divisor, floor)
        provision = max(available - served[i], 0.0)

    result: np.ndarray = np.empty_like(served)
    result[order] = _after_fee(served, annual_fee + margin)
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

    if model == "euro_fund_general_account":
        return _general_account_euro_fund(placement, scenarios, annual_fee)

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
        f"euro_fund_general_account, regulated_rate."
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
    if support["model"] == "euro_fund_general_account":
        return sorted({
            str(asset["series"] if asset["kind"] == "gse_series" else asset["reference_series"])
            for asset in support["assets"]
        })
    if support["model"] == "regulated_rate":
        return ["interest_rate", "inflation"]
    return []

"""
Calage de la dynamique immobilière (a, σ) sur l'indice INSEE des prix des logements anciens.

Usage :
    python examples/calibrate_real_estate_insee.py chemin/vers/serie_bdm.csv [--start 2000] [--end 2025]

Entrée : l'export CSV de la Banque de données macroéconomiques de l'INSEE pour
la série trimestrielle « Indice des prix des logements anciens, France » (page
https://www.insee.fr/fr/statistiques/8745266). Le fichier BDM est séparé par des
points-virgules ; seules les lignes dont la première colonne est une période
trimestrielle (``2025-T2`` ou ``2025-Q2``) sont lues, les en-têtes sont ignorés.

Sortie : deux estimations de (a, σ), affichées côte à côte.

1. Méthode des moments du modèle codé (``calibrate_from_returns``, pas 0,25) :
   autocorrélation et variance des rendements trimestriels telles que
   ``RealEstateModel`` les produit.
2. AR(1) sur le rendement instantané : le rendement trimestriel annualisé est
   vu comme un processus d'Ornstein-Uhlenbeck observé tous les trimestres,
   ``a = −ln(φ)/dt`` et ``σ = sd(résidus)/dt · √(2a/(1−φ²))``.

La vol long terme affichée est σ/a. Aucune valeur n'est écrite dans les
hypothèses de marché par ce script : il ne fait que mesurer.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import numpy as np

from investment_calculator.stochastic_models.real_estate import calibrate_from_returns

QUARTER = re.compile(r"^\s*(\d{4})-[TQ]([1-4])\s*$")
DT = 0.25


def read_bdm_quarterly(path: Path) -> list[tuple[int, int, float]]:
    """Lit un export BDM trimestriel ; renvoie (année, trimestre, valeur) triés."""
    rows: list[tuple[int, int, float]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for record in csv.reader(handle, delimiter=";"):
            if len(record) < 2:
                continue
            match = QUARTER.match(record[0])
            if not match:
                continue
            raw = record[1].strip().replace(",", ".")
            try:
                value = float(raw)
            except ValueError:
                continue  # valeur manquante ou non numérique (« n.d. ») : ignorée
            rows.append((int(match.group(1)), int(match.group(2)), value))
    if not rows:
        raise ValueError(
            f"Aucune ligne trimestrielle lue dans {path} : la première colonne doit "
            "contenir des périodes du type 2025-T2. Vérifiez qu'il s'agit bien de "
            "l'export CSV BDM de la série trimestrielle."
        )
    rows.sort()
    for (y0, q0, _), (y1, q1, _) in zip(rows, rows[1:]):
        if (y1 * 4 + q1) - (y0 * 4 + q0) != 1:
            raise ValueError(
                f"Trou dans la série entre {y0}-T{q0} et {y1}-T{q1} : fournir une "
                "série trimestrielle continue."
            )
    return rows


def ar1_instantaneous(log_returns: np.ndarray, dt: float) -> tuple[float, float]:
    """AR(1) des rendements trimestriels, lu comme un OU sur le rendement instantané."""
    phi, intercept = np.polyfit(log_returns[:-1], log_returns[1:], 1)
    if not 0 < phi < 1:
        raise ValueError(f"Coefficient AR(1) de {phi:.3f} : hors de ]0, 1[, pas de retour à la moyenne.")
    residuals = log_returns[1:] - (phi * log_returns[:-1] + intercept)
    a = -np.log(phi) / dt
    sigma = residuals.std(ddof=2) / dt * np.sqrt(2 * a / (1 - phi**2))
    return float(a), float(sigma)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("csv", type=Path)
    parser.add_argument("--start", type=int, default=2000, help="première année incluse")
    parser.add_argument("--end", type=int, default=2025, help="dernière année incluse")
    args = parser.parse_args(argv)

    rows = [r for r in read_bdm_quarterly(args.csv) if args.start <= r[0] <= args.end]
    levels = np.array([r[2] for r in rows])
    log_returns = np.diff(np.log(levels))
    print(f"Série : {rows[0][0]}-T{rows[0][1]} à {rows[-1][0]}-T{rows[-1][1]}, "
          f"{len(levels)} points, {len(log_returns)} rendements trimestriels")
    centered = log_returns - log_returns.mean()
    rho = centered[1:] @ centered[:-1] / (centered @ centered)
    print(f"Autocorrélation d'ordre 1 des rendements trimestriels : {rho:.3f}")
    print(f"Rendement annualisé moyen : {log_returns.mean() / DT:.2%}")

    for label, estimate in (
        ("Moments du modèle codé", lambda: calibrate_from_returns(log_returns, DT)),
        ("AR(1) rendement instantané", lambda: ar1_instantaneous(log_returns, DT)),
    ):
        try:
            a, sigma = estimate()
        except ValueError as error:
            print(f"{label} : échec ({error})")
            continue
        print(f"{label} : a = {a:.3f}, σ = {sigma:.2%}, vol long terme σ/a = {sigma / a:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

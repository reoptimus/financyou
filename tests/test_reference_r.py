"""
Les traductions fidèles de ``tests/reference_r`` reproduisent le vrai R.

``tests/reference_r/r_outputs.json`` contient les sorties des scripts R de
``legacy/R_Financyou``, exécutés par ``tests/reference_r/generate_r_outputs.R``.
Ces tests comparent chaque traduction à ces sorties. Le R n'est pas nécessaire
pour les exécuter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from tests.reference_r.assembl_invest import r_assembl_invest
from tests.reference_r.exp_finance import r_cumulative_capital, r_exp_proj_hist
from tests.reference_r.striping import r_stripping

R_OUTPUTS: dict[str, Any] = json.loads(
    (Path(__file__).parent / "reference_r" / "r_outputs.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", R_OUTPUTS["exp_proj_hist"]["cases"], ids=str)
def test_exp_proj_hist_translation_matches_r(case: dict[str, Any]) -> None:
    horiz = R_OUTPUTS["exp_proj_hist"]["horiz"]
    start, mdebut, mvers, duree, msortie = case["input"]
    ours = r_exp_proj_hist(horiz, int(start), mdebut, mvers, duree, msortie)
    np.testing.assert_allclose(ours, case["output"])


def test_exp_fin_cumulative_translation_matches_r() -> None:
    spec = R_OUTPUTS["exp_fin"]
    horiz = spec["horiz"]
    cases = R_OUTPUTS["exp_proj_hist"]["cases"][:6]
    rows = np.vstack([np.asarray(c["output"], dtype=float) for c in cases])
    ours = r_cumulative_capital(rows, horiz, spec["sal_net"], spec["epar"])
    np.testing.assert_allclose(ours, spec["output"])


@pytest.mark.parametrize(
    "case", R_OUTPUTS["stripping"]["cases"], ids=lambda c: str(c["input"][:4])
)
def test_stripping_translation_matches_r(case: dict[str, Any]) -> None:
    pas_e = R_OUTPUTS["stripping"]["pas_e"]
    curve = np.asarray(case["input"], dtype=float)
    if "error" in case:
        # R : « subscript out of bounds » ; la traduction lève l'erreur d'indice équivalente.
        with pytest.raises(IndexError):
            r_stripping(pas_e, curve)
        return
    np.testing.assert_allclose(r_stripping(pas_e, curve), np.asarray(case["output"]), rtol=1e-12)


def test_assembl_invest_translation_matches_r() -> None:
    case = R_OUTPUTS["assembl_invest"]
    horiz = case["horiz"]
    soltot = np.zeros((3, horiz, horiz))
    for d, w in case["weights"].items():
        soltot[:, int(d) - 1, :] = np.asarray(w, dtype=float)[:, None]
    ours = r_assembl_invest(
        soltot, np.asarray(case["tr1"], dtype=float), np.asarray(case["capital"]), horiz
    )
    expected = np.asarray(case["output"], dtype=float)  # "NaN" du R lu comme nan
    np.testing.assert_allclose(ours, expected, equal_nan=True)


def test_fct_flux_ir_translation_matches_r() -> None:
    from investment_calculator.tax_regime import load_regime
    from tests.reference_r.imp_ir import r_fct_flux_ir

    case = R_OUTPUTS["imp_ir"]
    brackets = load_regime("FR", 2026).document["income_tax"]["brackets"]
    tab_ir = [(float(b["lower"]), float(b["rate"])) for b in brackets]
    np.testing.assert_allclose(
        r_fct_flux_ir(np.asarray(case["qf"], dtype=float), tab_ir), case["output"], atol=1e-9
    )


@pytest.mark.parametrize("case", R_OUTPUTS["crd_flux"], ids=str)
def test_flux_crd_translation_matches_r(case: dict[str, Any]) -> None:
    from tests.reference_r.crd_flux import r_flux_crd

    principal, interest = r_flux_crd(case["horiz"], case["annuite"], case["taux"], case["an_rest"])
    np.testing.assert_array_equal(principal, case["principal"])
    np.testing.assert_array_equal(interest, case["interest"])

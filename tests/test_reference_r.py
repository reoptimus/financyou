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

from tests.reference_r.exp_finance import r_cumulative_capital, r_exp_proj_hist

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


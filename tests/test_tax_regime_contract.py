"""
Contrat d'architecture : la fiscalité est une donnée d'entrée du modèle.

Ce fichier contient deux familles de tests.

1. Des tests fonctionnels sur le chargeur de régimes
   (:mod:`investment_calculator.tax_regime`).

2. Un **test de garde** qui inspecte l'arbre syntaxique du moteur fiscal et
   fait échouer la CI dès qu'un taux, un seuil ou un abattement réapparaît en
   dur dans le code. C'est ce test qui rend la décision d'architecture
   exécutoire plutôt que déclarative : sans lui, la première urgence ramènerait
   une constante dans le moteur et personne ne s'en apercevrait.

Voir ``docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md``.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from investment_calculator.tax_regime import (
    ENV_REGIME_PATH,
    PACKAGE_REGIME_DIR,
    SCHEMA_PATH,
    DraftRegimeError,
    RegimeNotFoundError,
    TaxRegime,
    apply_brackets,
    list_regimes,
    load_regime,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
TAX_ENGINE = REPO_ROOT / "investment_calculator" / "modules" / "tax_engine.py"

#: Régime minimal, valide selon le schéma, utilisé pour tester le MÉCANISME de
#: refus des brouillons sans dépendre du statut d'un régime livré (fr-2026 est
#: aujourd'hui validated, et il est le seul régime du paquet depuis le retrait
#: de us-2026/uk-2026 — voir docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md).
_REGIME_JOUET = {
    "schema_version": "0.1",
    "id": "zz-2026",
    "country": {"code": "ZZ", "name": "Zzedland"},
    "fiscal_year": 2026,
    "currency": "EUR",
    "status": "draft",
    "known_gaps": ["Régime jouet, pour les tests uniquement."],
    "social_contributions": {"investment_income": {"rate": 0.1}},
    "income_tax": {"mode": "flat", "flat_rate": 0.2},
    "wrappers": [
        {"id": "cto", "label": "Compte-titres", "tax_treatment": "taxable"}
    ],
}


@pytest.fixture
def regime_jouet_brouillon(tmp_path, monkeypatch):
    """Dépose un régime brouillon minimal dans un répertoire pointé par FINANCYOU_TAX_REGIMES."""
    (tmp_path / "zz-2026.json").write_text(json.dumps(_REGIME_JOUET), encoding="utf-8")
    monkeypatch.setenv(ENV_REGIME_PATH, str(tmp_path))
    return "ZZ", 2026


# --------------------------------------------------------------------------- #
# 1. Inventaire et validité des régimes livrés
# --------------------------------------------------------------------------- #

def _regime_files() -> list[Path]:
    return sorted(
        p
        for p in PACKAGE_REGIME_DIR.glob("*.json")
        if p.name != "schema.json" and not p.name.startswith("_")
    )


def test_le_schema_est_un_json_schema_valide():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)


def test_des_regimes_sont_livres():
    assert _regime_files(), (
        "Aucun régime fiscal livré. Le produit ne peut alors proposer aucun pays."
    )


@pytest.mark.parametrize("path", _regime_files(), ids=lambda p: p.stem)
def test_chaque_regime_livre_est_valide(path: Path):
    """Chaque fichier livré doit passer le schéma ET les contrôles sémantiques."""
    country = path.stem.split("-")[0]
    year = int(path.stem.split("-")[1])
    regime = load_regime(country, year, allow_draft=True)
    assert isinstance(regime, TaxRegime)
    assert regime.id == path.stem
    assert regime.wrapper_ids, "Un régime sans enveloppe ne permet aucun calcul."


@pytest.mark.parametrize("path", _regime_files(), ids=lambda p: p.stem)
def test_un_regime_brouillon_declare_ses_lacunes(path: Path):
    """
    Un brouillon doit dire ce qu'il ne sait pas faire.

    Une lacune déclarée est arbitrable ; une lacune silencieuse produit un
    chiffre faux que personne ne remet en question.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    if document["status"] == "draft":
        assert document.get("known_gaps"), (
            f"{path.name} est un brouillon sans known_gaps : il faut énoncer "
            f"explicitement ce qui n'est pas modélisé."
        )


@pytest.mark.parametrize("path", _regime_files(), ids=lambda p: p.stem)
def test_un_regime_valide_est_source_et_signe(path: Path):
    """
    Le passage au statut ``validated`` impose des sources et un validateur humain.

    Un agent peut rédiger un régime, il ne peut pas se porter garant de ses
    valeurs : le champ ``validated_by`` nomme une personne.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    if document["status"] != "validated":
        return
    validation = document.get("validation", {})
    assert validation.get("validated_by"), f"{path.name} : validated_by est obligatoire."
    assert validation.get("golden_cases"), f"{path.name} : golden_cases est obligatoire."
    assert document.get("sources"), f"{path.name} : au moins une source officielle est requise."


# --------------------------------------------------------------------------- #
# 2. Comportement du chargeur
# --------------------------------------------------------------------------- #

def test_un_brouillon_est_refuse_par_defaut(regime_jouet_brouillon):
    """La protection centrale : un chiffre non validé ne peut pas atteindre un utilisateur."""
    country, year = regime_jouet_brouillon
    with pytest.raises(DraftRegimeError) as excinfo:
        load_regime(country, year)
    assert "draft" in str(excinfo.value)


def test_un_brouillon_est_chargeable_explicitement(regime_jouet_brouillon):
    country, year = regime_jouet_brouillon
    regime = load_regime(country, year, allow_draft=True)
    assert regime.country_code == country
    assert regime.is_draft


def test_un_pays_inconnu_leve_une_erreur_explicite():
    with pytest.raises(RegimeNotFoundError) as excinfo:
        load_regime("ZZ", allow_draft=True)
    message = str(excinfo.value)
    assert "Disponibles" in message, "L'erreur doit lister ce qui existe."
    assert "schema.json" in message, "L'erreur doit dire comment ajouter un régime."


def test_le_millesime_le_plus_recent_est_choisi_par_defaut():
    regime = load_regime("FR", allow_draft=True)
    annees = [r.fiscal_year for r in list_regimes() if r.country_code == "FR"]
    assert regime.fiscal_year == max(annees)


def test_l_inventaire_est_la_source_des_pays_proposes():
    """
    La liste des pays offerts à l'utilisateur se déduit des fichiers présents.

    Ajouter un pays doit être une opération de données, jamais une modification
    de code.
    """
    inventaire = list_regimes()
    assert {r.country_code for r in inventaire} >= {"FR"}
    assert all(r.path.exists() for r in inventaire)


def test_seuls_les_regimes_valides_sont_utilisables():
    utilisables = list_regimes(include_draft=False)
    assert all(r.is_usable for r in utilisables)


# --------------------------------------------------------------------------- #
# 3. Sémantique des règles
# --------------------------------------------------------------------------- #

def test_le_bareme_est_marginal_et_non_cumulatif():
    bareme = [
        {"lower": 0, "upper": 100, "rate": 0.0},
        {"lower": 100, "upper": 200, "rate": 0.10},
        {"lower": 200, "upper": None, "rate": 0.20},
    ]
    assert apply_brackets(50, bareme) == 0.0
    assert apply_brackets(150, bareme) == pytest.approx(5.0)
    assert apply_brackets(200, bareme) == pytest.approx(10.0)
    assert apply_brackets(300, bareme) == pytest.approx(30.0)
    assert apply_brackets(-10, bareme) == 0.0


def test_le_prelevement_forfaitaire_ne_double_compte_pas_les_contributions_sociales():
    """
    Régression du défaut le plus coûteux de l'ancien moteur.

    L'ancien code appliquait 30 % puis ajoutait 17,2 % par-dessus, portant le
    taux à 47,2 %. Le taux global doit être exactement 30 %.
    """
    fr = load_regime("FR", 2026, allow_draft=True)
    assert fr.flat_tax_income_rate == pytest.approx(0.128)
    assert fr.social_rate == pytest.approx(0.172)
    assert fr.flat_tax_total_rate() == pytest.approx(0.30)
    assert fr.flat_tax_total_rate() < fr.flat_tax_income_rate + 2 * fr.social_rate


def test_le_quotient_familial_reduit_l_impot():
    fr = load_regime("FR", 2026, allow_draft=True)
    seul = fr.income_tax_due(60000, shares=1.0)
    couple = fr.income_tax_due(60000, shares=2.0)
    assert couple < seul, "Le quotient familial doit alléger l'impôt à revenu égal."
    assert fr.income_tax_due(0) == 0.0


def test_le_plafonnement_du_quotient_limite_l_avantage_des_enfants():
    """
    Cas général du plafonnement (CGI art. 197 I-2°) : au-delà d'un certain
    revenu, l'avantage procuré par les parts d'enfants est plafonné à un
    montant par demi-part, pas illimité.
    """
    fr = load_regime("FR", 2026, allow_draft=True)
    revenu = 300_000
    sans_enfants = fr.income_tax_due(revenu, shares=2.0)
    avec_plafonnement = fr.income_tax_due(revenu, shares=3.0, dependent_shares=1.0)
    sans_plafonnement = fr.income_tax_due(revenu, shares=3.0)

    assert avec_plafonnement > sans_plafonnement, (
        "Le plafonnement doit renchérir l'impôt par rapport au quotient plein, "
        "à ce niveau de revenu où l'avantage dépasse le plafond."
    )
    avantage_plafonne = sans_enfants - avec_plafonnement
    plafond = fr.document["income_tax"]["household_quotient"]["cap_per_half_share"]
    # dependent_shares=1.0 équivaut à deux demi-parts (2 enfants à 0.5 part chacun).
    assert avantage_plafonne == pytest.approx(2 * plafond)


def test_l_appel_sans_dependent_shares_reste_retrocompatible():
    """dependent_shares est optionnel : l'appel historique doit produire le même résultat."""
    fr = load_regime("FR", 2026, allow_draft=True)
    assert fr.income_tax_due(60_000, shares=2.0) == pytest.approx(4_207.98, abs=0.01)


def test_la_cehr_double_ses_seuils_pour_un_couple():
    """La CEHR (art. 223 sexies CGI) : mêmes taux, seuils doublés pour un couple."""
    fr = load_regime("FR", 2026, allow_draft=True)
    celibataire = fr.surtax_due(600_000, married=False)
    couple = fr.surtax_due(600_000, married=True)
    assert celibataire > couple > 0, (
        "À RFR égal, un couple doit payer moins de CEHR qu'une personne seule : "
        "ses seuils sont doublés."
    )
    assert fr.surtax_due(200_000, married=False) == 0.0, "Sous 250 000 €, la CEHR n'est pas due."


def test_l_impot_sur_la_fortune_respecte_son_seuil():
    fr = load_regime("FR", 2026, allow_draft=True)
    assert fr.wealth_tax_due(1_000_000) == 0.0
    assert fr.wealth_tax_due(2_000_000) > 0.0


def test_la_regle_de_retrait_depend_de_la_duree_de_detention():
    fr = load_regime("FR", 2026, allow_draft=True)
    apres = fr.select_withdrawal_rule("pea", holding_years=6)
    avant = fr.select_withdrawal_rule("pea", holding_years=2)
    assert fr.resolve_income_tax_rate(apres, taxable_amount=10_000) == 0.0
    assert fr.resolve_income_tax_rate(avant, taxable_amount=10_000) > 0.0
    # Les prélèvements sociaux restent dus dans les deux cas.
    assert fr.resolve_social_rate(apres) == pytest.approx(fr.social_rate)


def test_un_critere_non_renseigne_retombe_sur_la_regle_par_defaut():
    """
    Ne jamais présumer d'un contexte inconnu.

    Sans durée de détention, on applique la règle sans condition plutôt que la
    plus favorable.
    """
    fr = load_regime("FR", 2026, allow_draft=True)
    regle = fr.select_withdrawal_rule("pea")
    assert regle.get("when") is None


def test_les_enveloppes_portent_leurs_contraintes_d_actifs():
    """Contrainte destinée à l'optimiseur : un PEA ne peut pas tout détenir."""
    fr = load_regime("FR", 2026, allow_draft=True)
    assert "pea" in fr.eligible_wrappers("equity_eu")
    assert "pea" not in fr.eligible_wrappers("real_estate")
    assert fr.wrapper("pea")["contribution_limit"] == 150_000


def test_l_absence_de_plafond_s_ecrit_null_et_non_infini():
    """
    ``float('inf')`` traverse mal le JSON et se propage en NaN dans les calculs.

    Le schéma impose ``null``, et aucun régime ne doit contenir d'infini.
    """
    for path in _regime_files():
        texte = path.read_text(encoding="utf-8")
        assert "Infinity" not in texte, f"{path.name} contient un infini JSON non standard."


# --------------------------------------------------------------------------- #
# 4. Test de garde : aucun paramètre fiscal en dur dans le moteur
# --------------------------------------------------------------------------- #

#: Littéraux tolérés dans ``tax_engine.py``, avec la raison et l'échéance de
#: leur disparition. Toute nouvelle valeur non listée ici fait échouer la CI.
#: Clé : ``"<fonction>:<valeur>"``.
LITTERAUX_TOLERES: dict[str, str] = {
    # Les hypothèses de marché (rendement du dividende, répartition
    # loyer/appréciation, part réalisée annuellement) ont déménagé à l'étape
    # 1.A.6 dans investment_calculator/market_assumptions/ ; elles ne sont
    # plus des littéraux de ce fichier et n'ont donc plus leur place ici.
    # Garde-fous numériques, sans contenu fiscal.
    "_calculate_after_tax_scenarios:0.01": "epsilon de division, pas un taux",
    "_calculate_tax_tables:0.001": "epsilon de division, pas un taux",
    # Allocation par défaut d'une fonction de commodité : c'est une entrée
    # d'exemple, pas une règle d'imposition.
    "apply_taxes_simple:0.7": "allocation par défaut de la fonction de commodité",
    "apply_taxes_simple:0.8": "allocation par défaut de la fonction de commodité",
    "apply_taxes_simple:0.5": "allocation par défaut de la fonction de commodité",
    "apply_taxes_simple:0.4": "allocation par défaut de la fonction de commodité",
    "apply_taxes_simple:0.2": "allocation par défaut de la fonction de commodité",
    "apply_taxes_simple:0.1": "allocation par défaut de la fonction de commodité",
}


def _litteraux_suspects(path: Path) -> list[tuple[str, float | int, int, str]]:
    """
    Repérer les littéraux numériques ressemblant à un paramètre fiscal.

    Sont suspects : tout flottant strictement compris entre 0 et 1 (un taux),
    et tout entier supérieur ou égal à 1000 (un seuil ou un plafond).
    """
    source = path.read_text(encoding="utf-8")
    lignes = source.splitlines()
    arbre = ast.parse(source)

    portee: dict[int, str] = {}
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.FunctionDef | ast.AsyncFunctionDef):
            fin = getattr(noeud, "end_lineno", noeud.lineno)
            for ligne in range(noeud.lineno, fin + 1):
                portee[ligne] = noeud.name

    suspects: list[tuple[str, float | int, int, str]] = []
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Constant):
            continue
        valeur = noeud.value
        if isinstance(valeur, bool) or not isinstance(valeur, int | float):
            continue
        est_taux = isinstance(valeur, float) and 0.0 < valeur < 1.0
        est_seuil = isinstance(valeur, int) and valeur >= 1000
        if not (est_taux or est_seuil):
            continue
        fonction = portee.get(noeud.lineno, "<module>")
        suspects.append(
            (f"{fonction}:{valeur}", valeur, noeud.lineno, lignes[noeud.lineno - 1].strip())
        )
    return suspects


def test_aucun_parametre_fiscal_en_dur_dans_le_moteur():
    """
    GARDE D'ARCHITECTURE.

    Si ce test échoue, c'est qu'un taux, un seuil ou un abattement a été écrit
    dans ``tax_engine.py``. La correction n'est pas d'allonger la liste des
    tolérances : c'est de déplacer la valeur dans le régime fiscal du pays
    concerné, sous ``investment_calculator/tax_regimes/``.

    La liste des tolérances ne doit que se réduire au fil des étapes.
    """
    inconnus = [
        (cle, ligne, code)
        for cle, _valeur, ligne, code in _litteraux_suspects(TAX_ENGINE)
        if cle not in LITTERAUX_TOLERES
    ]
    if inconnus:
        details = "\n".join(
            f"    ligne {ligne} — {cle}\n        {code}" for cle, ligne, code in inconnus
        )
        pytest.fail(
            "Paramètre fiscal codé en dur dans tax_engine.py :\n"
            f"{details}\n\n"
            "La fiscalité est une donnée d'entrée du modèle. Déplacez cette valeur "
            "dans investment_calculator/tax_regimes/<pays>-<millésime>.json plutôt "
            "que de l'ajouter à LITTERAUX_TOLERES. Voir "
            "docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md."
        )


def test_la_dette_de_litteraux_ne_grossit_pas():
    """La liste des tolérances est un plafond, pas un budget à consommer."""
    presents = {cle for cle, _v, _l, _c in _litteraux_suspects(TAX_ENGINE)}
    obsoletes = set(LITTERAUX_TOLERES) - presents
    assert not obsoletes, (
        "Ces tolérances ne correspondent plus à aucune valeur du moteur ; "
        f"retirez-les de LITTERAUX_TOLERES : {sorted(obsoletes)}"
    )


def test_aucune_juridiction_en_dur_dans_le_moteur():
    """
    Les valeurs héritées vivent dans un fichier de données, plus dans le code.

    Ce test empêche la réintroduction d'un dictionnaire de presets en Python.
    """
    source = TAX_ENGINE.read_text(encoding="utf-8")
    arbre = ast.parse(source)
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Dict):
            continue
        cles = {
            k.value
            for k in noeud.keys
            if isinstance(k, ast.Constant) and isinstance(k.value, str)
        }
        if len({"US", "FR", "UK", "DE", "CA"} & cles) >= 2:
            pytest.fail(
                f"Un dictionnaire indexé par juridiction est réapparu dans "
                f"tax_engine.py (ligne {noeud.lineno}). Les régimes vivent dans "
                f"investment_calculator/tax_regimes/."
            )


def test_taxconfigpreset_a_disparu():
    """
    Fin de la transition (étape 1.A.5) : TaxConfigPreset et son fichier de
    valeurs gelées devaient disparaître une fois le moteur branché sur les
    régimes. Ce test échoue si quelqu'un les réintroduit.
    """
    from investment_calculator.modules import tax_engine

    assert not hasattr(tax_engine, "TaxConfigPreset"), (
        "TaxConfigPreset devait disparaître à la fin de l'étape 1.A ; voir "
        "docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md."
    )
    legacy_path = REPO_ROOT / "investment_calculator" / "tax_regimes" / "_legacy_presets.json"
    assert not legacy_path.exists(), (
        "_legacy_presets.json devait être supprimé avec TaxConfigPreset."
    )


def test_le_moteur_consomme_directement_un_regime():
    """Le pont vers l'ancien moteur passe par TaxRegime, pas par un preset."""
    from investment_calculator.modules import tax_engine

    config = tax_engine._default_tax_config()
    assert config["jurisdiction"] == "FR"
    assert config["social_charges"] == 0.172
    assert config["wealth_tax"]["threshold"] == 1_300_000

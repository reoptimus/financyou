"""
Régimes fiscaux — chargement, validation et interrogation.

PRINCIPE STRUCTURANT DU PROJET
------------------------------
La fiscalité est une **donnée d'entrée du modèle**, pas une règle codée dans le
moteur. Elle varie par pays et par millésime, elle change plus vite que le code,
et elle engage la responsabilité de celui qui la publie. Elle vit donc dans des
documents JSON validés par un schéma (``tax_regimes/schema.json``), au même titre
qu'un profil utilisateur ou qu'un jeu d'hypothèses de marché.

Conséquences pratiques :

* aucun taux, seuil, abattement ou plafond ne doit apparaître en dur dans
  ``investment_calculator/modules/tax_engine.py`` — un test de garde
  (``tests/test_tax_regime_contract.py``) fait échouer la CI si c'est le cas ;
* ajouter un pays consiste à déposer un fichier JSON, jamais à modifier du code ;
* un exploitant peut fournir ses propres régimes sans toucher au paquet, via la
  variable d'environnement ``FINANCYOU_TAX_REGIMES`` ;
* un régime au statut ``draft`` est refusé par défaut, pour qu'un chiffre non
  vérifié ne puisse pas atteindre un utilisateur par inadvertance.

Ce module ne calcule pas l'impôt : il donne accès aux règles. Le calcul est la
responsabilité du moteur fiscal, qui les consomme.

Exemple
-------
>>> from investment_calculator.tax_regime import list_regimes
>>> sorted(r.id for r in list_regimes())
['fr-2026']
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "ENV_REGIME_PATH",
    "PACKAGE_REGIME_DIR",
    "SCHEMA_PATH",
    "DraftRegimeError",
    "RegimeDescriptor",
    "RegimeNotFoundError",
    "RegimeValidationError",
    "TaxRegime",
    "TaxRegimeError",
    "apply_brackets",
    "list_regimes",
    "load_regime",
    "search_paths",
]


PACKAGE_REGIME_DIR = Path(__file__).parent / "tax_regimes"
SCHEMA_PATH = PACKAGE_REGIME_DIR / "schema.json"

#: Variable d'environnement listant des répertoires supplémentaires de régimes,
#: séparés par ``os.pathsep``. Ils sont prioritaires sur ceux du paquet, ce qui
#: permet à un exploitant de corriger un millésime sans publier une version.
ENV_REGIME_PATH = "FINANCYOU_TAX_REGIMES"


# --------------------------------------------------------------------------- #
# Erreurs
# --------------------------------------------------------------------------- #

class TaxRegimeError(Exception):
    """Erreur générique liée à un régime fiscal."""


class RegimeNotFoundError(TaxRegimeError):
    """Aucun régime ne correspond au pays et au millésime demandés."""


class RegimeValidationError(TaxRegimeError):
    """Le document ne respecte pas le schéma des régimes fiscaux."""


class DraftRegimeError(TaxRegimeError):
    """
    Le régime demandé est au statut ``draft`` et n'a pas été explicitement autorisé.

    Un régime brouillon contient des valeurs qui n'ont pas été confrontées à des
    cas d'or. Le charger sans le vouloir reviendrait à présenter à un utilisateur
    des montants dont personne ne répond.
    """


# --------------------------------------------------------------------------- #
# Découverte
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class RegimeDescriptor:
    """Carte d'identité d'un régime, lisible sans charger tout le document."""

    id: str
    country_code: str
    country_name: str
    fiscal_year: int
    currency: str
    status: str
    path: Path

    @property
    def is_usable(self) -> bool:
        """Vrai si le régime peut être servi à un utilisateur final."""
        return self.status == "validated"


def search_paths() -> list[Path]:
    """
    Répertoires où chercher des régimes, du plus prioritaire au moins prioritaire.

    Les répertoires déclarés dans ``FINANCYOU_TAX_REGIMES`` passent avant ceux
    embarqués dans le paquet.
    """
    paths: list[Path] = []
    raw = os.environ.get(ENV_REGIME_PATH, "")
    for chunk in raw.split(os.pathsep):
        chunk = chunk.strip()
        if not chunk:
            continue
        candidate = Path(chunk).expanduser()
        if candidate.is_dir():
            paths.append(candidate)
        else:
            logger.warning(
                "%s référence un répertoire inexistant, ignoré : %s", ENV_REGIME_PATH, chunk
            )
    paths.append(PACKAGE_REGIME_DIR)
    return paths


def list_regimes(*, include_draft: bool = True) -> list[RegimeDescriptor]:
    """
    Inventorier les régimes disponibles.

    C'est la source de vérité pour l'interface : la liste des pays proposés à
    l'utilisateur se déduit des fichiers présents, jamais d'une énumération
    figée dans le code.
    """
    seen: dict[str, RegimeDescriptor] = {}
    for directory in search_paths():
        for path in sorted(directory.glob("*.json")):
            if path.name == "schema.json":
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Régime illisible, ignoré : %s (%s)", path, exc)
                continue
            regime_id = raw.get("id")
            if not isinstance(regime_id, str) or regime_id in seen:
                continue
            try:
                country = raw["country"]
                descriptor = RegimeDescriptor(
                    id=regime_id,
                    country_code=country["code"],
                    country_name=country["name"],
                    fiscal_year=int(raw["fiscal_year"]),
                    currency=raw["currency"],
                    status=raw["status"],
                    path=path,
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Régime incomplet, ignoré : %s (%s)", path, exc)
                continue
            seen[regime_id] = descriptor

    regimes = list(seen.values())
    if not include_draft:
        regimes = [r for r in regimes if r.is_usable]
    return sorted(regimes, key=lambda r: (r.country_code, -r.fiscal_year))


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=1)
def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validate(document: dict[str, Any], origin: Path) -> None:
    """Valider le document contre le schéma, plus quelques règles inexprimables en JSON Schema."""
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - dépendance déclarée
        raise RegimeValidationError(
            "jsonschema est requis pour valider les régimes fiscaux. "
            "Installez-le avec : pip install jsonschema"
        ) from exc

    validator = jsonschema.Draft202012Validator(_load_schema())
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        details = "\n".join(
            f"  - {'/'.join(str(p) for p in err.path) or '<racine>'} : {err.message}"
            for err in errors[:10]
        )
        more = f"\n  ... et {len(errors) - 10} autre(s)" if len(errors) > 10 else ""
        raise RegimeValidationError(
            f"Le régime {origin} ne respecte pas le schéma :\n{details}{more}"
        )

    _validate_semantics(document, origin)


def _validate_semantics(document: dict[str, Any], origin: Path) -> None:
    """
    Contrôles que le schéma JSON ne peut pas exprimer.

    Ces règles existent parce que chacune correspond à une erreur qui a
    réellement été commise dans la version précédente du moteur.
    """
    problems: list[str] = []

    expected_id = f"{document['country']['code'].lower()}-{document['fiscal_year']}"
    if document["id"] != expected_id and not document["id"].startswith(
        document["id"].split("-")[0]
    ):
        problems.append(f"id {document['id']!r} incohérent avec le pays et le millésime")

    income_tax = document["income_tax"]
    mode = income_tax["mode"]
    if mode == "progressive" and not income_tax.get("brackets"):
        problems.append("income_tax.mode vaut 'progressive' mais aucune tranche n'est fournie")
    if mode == "flat" and income_tax.get("flat_rate") is None:
        problems.append("income_tax.mode vaut 'flat' mais flat_rate est absent")

    for label, brackets in _iter_bracket_sets(document):
        problems.extend(f"{label} : {msg}" for msg in _check_brackets(brackets))

    # Piège du double comptage : le taux forfaitaire porte déjà sa part sociale.
    flat = document.get("flat_tax", {})
    if flat.get("enabled"):
        total = flat.get("income_tax_rate", 0.0) + flat.get("social_rate", 0.0)
        if total > 1.0:
            problems.append(
                f"flat_tax : la somme income_tax_rate + social_rate vaut {total:.3f}, "
                "ce qui dépasse 100 %"
            )

    seen_wrappers: set[str] = set()
    for wrapper in document["wrappers"]:
        if wrapper["id"] in seen_wrappers:
            problems.append(f"enveloppe {wrapper['id']!r} déclarée deux fois")
        seen_wrappers.add(wrapper["id"])
        rules = wrapper.get("withdrawal_rules") or []
        if rules and any(r.get("when") for r in rules) and rules[-1].get("when"):
            problems.append(
                f"enveloppe {wrapper['id']!r} : la dernière règle de retrait porte une "
                "condition, aucun cas par défaut n'est donc garanti"
            )

    if problems:
        details = "\n".join(f"  - {p}" for p in problems)
        raise RegimeValidationError(f"Le régime {origin} est incohérent :\n{details}")


def _iter_bracket_sets(document: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    sets: list[tuple[str, list[dict[str, Any]]]] = []
    if document["income_tax"].get("brackets"):
        sets.append(("income_tax.brackets", document["income_tax"]["brackets"]))
    for surtax in document["income_tax"].get("surtaxes", []):
        sets.append((f"surtaxe {surtax['label']!r}", surtax["brackets"]))
    wealth = document.get("wealth_tax", {})
    if wealth.get("brackets"):
        sets.append(("wealth_tax.brackets", wealth["brackets"]))
    real_estate = document.get("capital_gains", {}).get("real_estate", {})
    if real_estate.get("surtax_brackets"):
        sets.append(("capital_gains.real_estate.surtax_brackets", real_estate["surtax_brackets"]))
    return sets


def _check_brackets(brackets: list[dict[str, Any]]) -> list[str]:
    """Vérifier qu'un barème est ordonné, contigu et ouvert sur sa dernière tranche."""
    problems: list[str] = []
    previous_upper: float = 0.0
    for index, bracket in enumerate(brackets):
        lower = float(bracket.get("lower", 0.0))
        upper = bracket.get("upper")
        if abs(lower - previous_upper) > 1e-9:
            problems.append(
                f"tranche {index} : la borne basse {lower} ne prolonge pas la tranche "
                f"précédente qui s'arrête à {previous_upper}"
            )
        if upper is None:
            if index != len(brackets) - 1:
                problems.append(f"tranche {index} : seule la dernière tranche peut être ouverte")
            previous_upper = float("inf")
            continue
        if float(upper) <= lower:
            problems.append(f"tranche {index} : borne haute {upper} inférieure ou égale à {lower}")
        previous_upper = float(upper)
    if brackets and brackets[-1].get("upper") is not None:
        problems.append("la dernière tranche doit être ouverte (upper à null)")
    return problems


# --------------------------------------------------------------------------- #
# Barèmes
# --------------------------------------------------------------------------- #

def apply_brackets(amount: float, brackets: list[dict[str, Any]]) -> float:
    """
    Appliquer un barème par tranches à un montant.

    Le calcul est marginal : chaque tranche n'impose que la fraction du montant
    qu'elle recouvre. Un montant négatif ne produit aucun impôt.

    >>> bareme = [
    ...     {"lower": 0, "upper": 100, "rate": 0.0},
    ...     {"lower": 100, "upper": 200, "rate": 0.10},
    ...     {"lower": 200, "upper": None, "rate": 0.20},
    ... ]
    >>> apply_brackets(150, bareme)
    5.0
    >>> apply_brackets(300, bareme)
    30.0
    """
    if amount <= 0:
        return 0.0
    total = 0.0
    for bracket in brackets:
        lower = float(bracket.get("lower", 0.0))
        upper_raw = bracket.get("upper")
        upper = float("inf") if upper_raw is None else float(upper_raw)
        if amount <= lower:
            break
        taxable = min(amount, upper) - lower
        if taxable > 0:
            total += taxable * float(bracket["rate"])
    return total


# --------------------------------------------------------------------------- #
# Le régime lui-même
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class TaxRegime:
    """
    Un régime fiscal chargé et validé.

    L'objet est immuable : deux exécutions du même scénario avec le même régime
    produisent nécessairement le même résultat, ce qui est la condition pour
    pouvoir rejouer une simulation archivée.
    """

    document: dict[str, Any] = field(repr=False)
    source: Path

    # -- identité ----------------------------------------------------------- #

    @property
    def id(self) -> str:
        return str(self.document["id"])

    @property
    def country_code(self) -> str:
        return str(self.document["country"]["code"])

    @property
    def country_name(self) -> str:
        return str(self.document["country"]["name"])

    @property
    def fiscal_year(self) -> int:
        return int(self.document["fiscal_year"])

    @property
    def currency(self) -> str:
        return str(self.document["currency"])

    @property
    def status(self) -> str:
        return str(self.document["status"])

    @property
    def is_draft(self) -> bool:
        return self.status == "draft"

    @property
    def known_gaps(self) -> list[str]:
        """Ce que le régime ne modélise pas, tel que déclaré par son auteur."""
        return list(self.document.get("known_gaps", []))

    # -- règles ------------------------------------------------------------- #

    @property
    def social_rate(self) -> float:
        """Taux des contributions sociales sur les revenus du capital."""
        return float(self.document["social_contributions"]["investment_income"]["rate"])

    @property
    def flat_tax_enabled(self) -> bool:
        return bool(self.document.get("flat_tax", {}).get("enabled", False))

    @property
    def flat_tax_income_rate(self) -> float:
        """
        Part « impôt sur le revenu » du prélèvement forfaitaire, hors part sociale.

        À ne jamais additionner avec :attr:`social_rate` sans passer par
        :meth:`flat_tax_total_rate` — c'est précisément le double comptage qui
        portait le taux français à 47,2 % au lieu de 30 % dans la version
        précédente du moteur.
        """
        return float(self.document.get("flat_tax", {}).get("income_tax_rate", 0.0))

    def flat_tax_total_rate(self) -> float:
        """Taux global du prélèvement forfaitaire, part sociale comprise."""
        flat = self.document.get("flat_tax", {})
        if not flat.get("enabled"):
            raise TaxRegimeError(
                f"Le régime {self.id} ne prévoit pas de prélèvement forfaitaire."
            )
        return float(flat.get("income_tax_rate", 0.0)) + float(flat.get("social_rate", 0.0))

    def income_tax_due(
        self, taxable_income: float, *, shares: float = 1.0, dependent_shares: float = 0.0
    ) -> float:
        """
        Impôt sur le revenu dû pour un revenu imposable donné.

        ``shares`` est le nombre de parts total du foyer lorsque le régime
        pratique le quotient familial ; il est ignoré sinon. ``dependent_shares``
        est la fraction de ``shares`` attribuable aux personnes à charge
        (enfants), par opposition aux parts de base du foyer (1 pour un
        célibataire, 2 pour un couple) : elle sert à appliquer le
        plafonnement général de l'avantage du quotient familial
        (``household_quotient.cap_per_half_share``), quand le régime en
        prévoit un.

        Ne modélise que le cas général du plafonnement (CGI art. 197 I-2°).
        Les cas particuliers (parent isolé, veuf avec enfant à charge, garde
        alternée au quart de part, invalides) portent des plafonds ou des
        réductions complémentaires distincts, non modélisés ici — voir les
        ``known_gaps`` du régime.
        """
        income_tax = self.document["income_tax"]
        mode = income_tax["mode"]
        if mode == "none":
            return 0.0
        if mode == "flat":
            return max(0.0, taxable_income) * float(income_tax["flat_rate"])

        quotient = income_tax.get("household_quotient", {})
        effective_shares = shares if quotient.get("enabled") else 1.0
        if effective_shares <= 0:
            raise ValueError("Le nombre de parts doit être strictement positif.")
        per_share = taxable_income / effective_shares
        tax_with_full_quotient = apply_brackets(per_share, income_tax["brackets"]) * effective_shares

        cap = quotient.get("cap_per_half_share")
        if not quotient.get("enabled") or not cap or dependent_shares <= 0:
            return tax_with_full_quotient

        base_shares = effective_shares - dependent_shares
        if base_shares <= 0:
            raise ValueError(
                "dependent_shares ne peut pas atteindre ni dépasser le nombre total de parts."
            )
        per_base_share = taxable_income / base_shares
        tax_at_base_shares = apply_brackets(per_base_share, income_tax["brackets"]) * base_shares

        advantage = tax_at_base_shares - tax_with_full_quotient
        if advantage <= 0:
            return tax_with_full_quotient
        max_advantage = (dependent_shares / 0.5) * float(cap)
        return tax_at_base_shares - min(advantage, max_advantage)

    def surtax_due(self, taxable_amount: float, *, married: bool = False) -> float:
        """
        Total des contributions additionnelles sur le revenu (``income_tax.surtaxes``),
        par exemple la contribution exceptionnelle sur les hauts revenus (CEHR).

        ``taxable_amount`` est l'assiette de la contribution (le revenu
        fiscal de référence pour la CEHR) : elle n'est jamais divisée par le
        nombre de parts, contrairement à l'impôt sur le revenu — ces
        contributions ne pratiquent pas le quotient familial. ``married``
        double les seuils du barème quand le régime le prévoit
        (``threshold_multiplier_married``).
        """
        total = 0.0
        for surtax in self.document["income_tax"].get("surtaxes", []):
            multiplier = float(surtax.get("threshold_multiplier_married", 1.0)) if married else 1.0
            brackets = surtax["brackets"]
            if multiplier != 1.0:
                brackets = [
                    {
                        **bracket,
                        "lower": float(bracket.get("lower", 0.0)) * multiplier,
                        "upper": None if bracket.get("upper") is None else float(bracket["upper"]) * multiplier,
                    }
                    for bracket in brackets
                ]
            total += apply_brackets(taxable_amount, brackets)
        return total

    def wealth_tax_due(self, net_taxable_wealth: float) -> float:
        """
        Impôt sur la fortune dû.

        Zéro si le régime n'en prévoit pas, ou si le seuil n'est pas atteint.
        """
        wealth = self.document.get("wealth_tax", {})
        if not wealth.get("enabled"):
            return 0.0
        threshold = float(wealth.get("threshold", 0.0))
        if net_taxable_wealth < threshold:
            return 0.0
        brackets = wealth.get("brackets")
        if not brackets:
            raise TaxRegimeError(
                f"Le régime {self.id} active l'impôt sur la fortune sans fournir de barème."
            )
        return apply_brackets(net_taxable_wealth, brackets)

    # -- pont vers l'ancien moteur de scénarios ------------------------------ #

    def to_scenario_tax_config(self, *, reference_household_income: float) -> dict[str, Any]:
        """
        Traduire ce régime dans la forme historique attendue par
        :class:`investment_calculator.modules.tax_engine.TaxEngine`.

        C'est un pont vers un moteur plus grossier qu'un régime, pas une
        nouvelle vérité fiscale : ``TaxEngine`` raisonne par grande catégorie
        de compte (taxable / tax_deferred / tax_free) et par classe d'actif,
        pas par enveloppe ni par barème progressif complet. Ce que ce pont
        fait, précisément :

        * ``dividend_tax_rate``, ``interest_tax_rate`` et ``capital_gains_rate``
          reçoivent la part *impôt sur le revenu* du prélèvement forfaitaire
          (:attr:`flat_tax_income_rate`), jamais son taux global. C'est
          exactement le point qui portait le taux français à 47,2 % au lieu
          de 30 % dans l'ancien moteur : celui-ci ajoute ``social_charges``
          par-dessus, et additionner un taux déjà global aurait recompté les
          prélèvements sociaux une seconde fois.
        * ``income_tax_rate`` (utilisé par le moteur pour les revenus fonciers,
          imposés au barème et non au forfait) reçoit un taux moyen obtenu en
          divisant :meth:`income_tax_due` à ``reference_household_income`` par
          ce revenu. ``reference_household_income`` n'est pas une donnée du
          régime : c'est un revenu de foyer choisi par l'appelant pour réduire
          un barème progressif à un taux unique, faute de connaître le revenu
          réel du foyer simulé à ce stade du calcul — une hypothèse de
          modélisation du moteur de scénarios, pas une règle fiscale (voir
          ``investment_calculator/modules/tax_engine.py`` et
          ``docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md``,
          section « ce qui n'est pas de la fiscalité »).
        * ``wealth_tax.rate`` reçoit le taux marginal de la première tranche
          non nulle du barème IFI : ``TaxEngine`` ne sait pas appliquer un
          barème par tranches, seulement un taux unique au-delà d'un seuil.

        Cette méthode ne couvre donc qu'une fraction de ce qu'un régime peut
        exprimer (aucune règle par enveloppe, aucun quotient familial, aucune
        CEHR). Elle existe pour que ``TaxEngine`` cesse de lire
        ``_legacy_presets.json`` ; elle ne prétend pas remplacer le calcul par
        enveloppe que porte le reste de ce module.
        """
        if reference_household_income <= 0:
            raise ValueError("reference_household_income doit être strictement positif.")

        if self.flat_tax_enabled:
            capital_income_rate = self.flat_tax_income_rate
        else:
            capital_income_rate = (
                self.income_tax_due(reference_household_income) / reference_household_income
            )

        earned_income_rate = (
            self.income_tax_due(reference_household_income) / reference_household_income
        )

        wealth = self.document.get("wealth_tax", {})
        wealth_rate = 0.0
        for bracket in wealth.get("brackets", []) or []:
            if float(bracket["rate"]) > 0:
                wealth_rate = float(bracket["rate"])
                break

        return {
            "jurisdiction": self.country_code,
            "account_types": {
                "taxable": {
                    "income_tax_rate": earned_income_rate,
                    "capital_gains_rate": capital_income_rate,
                    "dividend_tax_rate": capital_income_rate,
                    "interest_tax_rate": capital_income_rate,
                },
                "tax_deferred": {
                    "contribution_deduction": True,
                    "withdrawal_tax_rate": earned_income_rate,
                },
                "tax_free": {
                    "contribution_limit": None,
                    "age_restrictions": {},
                },
            },
            "social_charges": self.social_rate,
            "wealth_tax": {
                "enabled": bool(wealth.get("enabled", False)),
                "threshold": float(wealth.get("threshold", 0.0)),
                "rate": wealth_rate,
            },
        }

    # -- enveloppes --------------------------------------------------------- #

    @property
    def wrapper_ids(self) -> list[str]:
        return [str(w["id"]) for w in self.document["wrappers"]]

    def wrapper(self, wrapper_id: str) -> dict[str, Any]:
        """Récupérer une enveloppe par son identifiant."""
        for candidate in self.document["wrappers"]:
            if candidate["id"] == wrapper_id:
                return dict(candidate)
        raise KeyError(
            f"Enveloppe {wrapper_id!r} inconnue dans le régime {self.id}. "
            f"Disponibles : {', '.join(self.wrapper_ids)}"
        )

    def eligible_wrappers(self, asset_class: str) -> list[str]:
        """
        Enveloppes pouvant détenir une classe d'actifs donnée.

        Cette contrainte est destinée à l'optimiseur : un PEA ne peut pas
        accueillir n'importe quel actif, et l'ignorer produit des allocations
        irréalisables.
        """
        return [
            str(w["id"])
            for w in self.document["wrappers"]
            if asset_class in (w.get("eligible_assets") or [])
        ]

    def select_withdrawal_rule(
        self,
        wrapper_id: str,
        *,
        holding_years: float | None = None,
        age: float | None = None,
        premiums_paid: float | None = None,
        account_value: float | None = None,
        exit_form: str | None = None,
    ) -> dict[str, Any]:
        """
        Sélectionner la règle de retrait applicable, la première dont la condition est satisfaite.

        Une condition portant sur un critère non renseigné n'est jamais
        satisfaite : mieux vaut retomber sur la règle par défaut que présumer
        d'un contexte inconnu.
        """
        context: dict[str, float | str | None] = {
            "holding_years": holding_years,
            "age": age,
            "premiums_paid": premiums_paid,
            "account_value": account_value,
            "exit_form": exit_form,
        }
        wrapper = self.wrapper(wrapper_id)
        rules = wrapper.get("withdrawal_rules") or []
        for rule in rules:
            if _condition_holds(rule.get("when"), context):
                return dict(rule)
        raise TaxRegimeError(
            f"Aucune règle de retrait applicable pour l'enveloppe {wrapper_id!r} "
            f"du régime {self.id} dans le contexte {context}."
        )

    def resolve_income_tax_rate(
        self, rule: dict[str, Any], *, taxable_amount: float, shares: float = 1.0
    ) -> float:
        """
        Convertir le champ ``income_tax_rate`` d'une règle en taux effectif.

        La valeur peut être un taux, ou l'un des renvois ``"flat_tax"`` et
        ``"progressive"``, auquel cas le taux effectif est déduit du régime.
        """
        spec = rule.get("income_tax_rate", 0.0)
        if isinstance(spec, int | float):
            return float(spec)
        if spec == "flat_tax":
            return self.flat_tax_income_rate
        if spec == "progressive":
            if taxable_amount <= 0:
                return 0.0
            return self.income_tax_due(taxable_amount, shares=shares) / taxable_amount
        raise TaxRegimeError(f"Renvoi de taux inconnu : {spec!r}")

    def resolve_social_rate(self, rule: dict[str, Any]) -> float:
        """Convertir le champ ``social_rate`` d'une règle en taux effectif."""
        spec = rule.get("social_rate", "none")
        if isinstance(spec, int | float):
            return float(spec)
        if spec == "standard":
            return self.social_rate
        if spec == "none":
            return 0.0
        raise TaxRegimeError(f"Renvoi de taux social inconnu : {spec!r}")


def _condition_holds(
    condition: dict[str, Any] | None, context: dict[str, float | str | None]
) -> bool:
    """Une condition absente vaut « toujours vrai » ; un critère non renseigné vaut « faux »."""
    if not condition:
        return True
    for key, requirement in condition.items():
        value = context.get(key)
        if value is None:
            return False
        if key == "exit_form":
            if requirement != "any" and value != requirement:
                return False
            continue
        numeric = float(value)  # type: ignore[arg-type]
        if "lt" in requirement and not numeric < requirement["lt"]:
            return False
        if "lte" in requirement and not numeric <= requirement["lte"]:
            return False
        if "gt" in requirement and not numeric > requirement["gt"]:
            return False
        if "gte" in requirement and not numeric >= requirement["gte"]:
            return False
    return True


# --------------------------------------------------------------------------- #
# Chargement
# --------------------------------------------------------------------------- #

def load_regime(
    country: str,
    fiscal_year: int | None = None,
    *,
    allow_draft: bool = False,
) -> TaxRegime:
    """
    Charger le régime fiscal d'un pays.

    Args:
        country: code pays ISO 3166-1 alpha-2, ou identifiant complet du régime
            tel que ``"fr-2026"``.
        fiscal_year: millésime. Si omis, le millésime le plus récent disponible.
        allow_draft: autorise le chargement d'un régime au statut ``draft``.
            Réservé aux tests et au travail de mise au point ; jamais en
            production, où un chiffre non validé ne doit pas atteindre un
            utilisateur.

    Raises:
        RegimeNotFoundError: aucun fichier ne correspond.
        RegimeValidationError: le document existe mais est invalide.
        DraftRegimeError: le régime est un brouillon et ``allow_draft`` est faux.
    """
    descriptor = _find_descriptor(country, fiscal_year)

    if descriptor.status == "draft" and not allow_draft:
        raise DraftRegimeError(
            f"Le régime {descriptor.id} est au statut 'draft' : ses valeurs n'ont pas "
            f"été confrontées à des cas d'or et ne doivent pas être présentées à un "
            f"utilisateur. Passez allow_draft=True pour l'utiliser en développement, "
            f"ou faites-le valider (voir "
            f"docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md)."
        )
    if descriptor.status == "deprecated":
        logger.warning(
            "Régime %s marqué 'deprecated' : il n'est conservé que pour rejouer "
            "des simulations archivées.",
            descriptor.id,
        )

    document = json.loads(descriptor.path.read_text(encoding="utf-8"))
    document.pop("$schema", None)
    _validate(document, descriptor.path)

    logger.info(
        "Régime fiscal chargé : %s (%s %d, statut %s, %d enveloppe(s))",
        descriptor.id,
        descriptor.country_code,
        descriptor.fiscal_year,
        descriptor.status,
        len(document["wrappers"]),
    )
    return TaxRegime(document=document, source=descriptor.path)


def _find_descriptor(country: str, fiscal_year: int | None) -> RegimeDescriptor:
    available = list_regimes()
    if not available:
        raise RegimeNotFoundError(
            f"Aucun régime fiscal trouvé. Répertoires explorés : "
            f"{', '.join(str(p) for p in search_paths())}"
        )

    token = country.strip().lower()
    if "-" in token:
        matches = [r for r in available if r.id == token]
    else:
        matches = [r for r in available if r.country_code.lower() == token]
        if not matches:
            # Tolérance : l'identifiant peut différer du code ISO (uk pour GB).
            matches = [r for r in available if r.id.split("-")[0] == token]

    if fiscal_year is not None:
        matches = [r for r in matches if r.fiscal_year == fiscal_year]

    if not matches:
        inventory = ", ".join(f"{r.id} ({r.status})" for r in available)
        wanted = f"{country}" + (f" millésime {fiscal_year}" if fiscal_year else "")
        raise RegimeNotFoundError(
            f"Aucun régime fiscal pour {wanted}. Disponibles : {inventory}. "
            f"Pour en ajouter un, déposez un fichier JSON conforme à "
            f"{SCHEMA_PATH.name} dans un répertoire de {ENV_REGIME_PATH} ou dans "
            f"{PACKAGE_REGIME_DIR}."
        )

    return max(matches, key=lambda r: r.fiscal_year)

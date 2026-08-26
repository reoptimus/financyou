# Conventions de contribution — FinancYou

Ce fichier s'adresse autant aux agents qu'aux personnes. Il est lu avant toute
modification du dépôt.

## Ce que fait ce projet, et ce que cela impose

FinancYou projette le patrimoine d'un particulier après impôt, sur plusieurs
décennies, à partir de scénarios économiques simulés. Un utilisateur peut
arbitrer son épargne sur la foi d'un chiffre affiché ici. Cela commande tout le
reste :

- **Un chiffre faux est plus grave qu'une fonctionnalité manquante.** Retirer une
  fonctionnalité qui ment est toujours préférable à la laisser mentir.
- **Aucune valeur inventée.** Ni dans le code, ni dans une donnée, ni dans un
  graphique. Si une valeur n'est pas calculée, elle ne s'affiche pas. Le dépôt a
  contenu une cascade fiscale composée de nombres arbitraires : cela ne doit pas
  se reproduire.
- **Une lacune se déclare.** Un `known_gaps`, un `NotImplementedError`, un
  message explicite — jamais un zéro silencieux ni un tableau vide.

## Fiscalité : donnée d'entrée, jamais code

**La fiscalité est une donnée d'entrée du modèle**, décrite par pays et par
millésime dans `investment_calculator/tax_regimes/*.json`, validée par
`tax_regimes/schema.json`.

- Aucun taux, seuil, abattement ou plafond dans le code du moteur. Un test de
  garde (`tests/test_tax_regime_contract.py`) fait échouer la CI sinon.
- Ajouter un pays est une opération de données, pas de code.
- La liste des pays proposés à l'utilisateur se déduit des fichiers présents.
- Un régime `draft` est refusé au chargement : un chiffre non validé ne doit pas
  atteindre un utilisateur.
- Les hypothèses de marché (rendement du dividende, part de loyer, fraction
  réalisée) ne sont **pas** de la fiscalité et n'ont rien à faire dans un régime.

Détail et justification : `docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md`.

## Structure

| Répertoire | Rôle |
|---|---|
| `investment_calculator/modules/` | Les cinq modules du pipeline : scénarios, fiscalité, profil, optimisation, restitution. |
| `investment_calculator/stochastic_models/` | Hull-White, Black-Scholes, immobilier, corrélation, calibration. |
| `investment_calculator/tax_regimes/` | Régimes fiscaux, données d'entrée. |
| `time_series_slicer/` | Découpage de séries temporelles, indépendant du reste. |
| `web_ui/app_enhanced.py` | **L'application. Base unique** depuis la phase 0. |
| `web_ui/archive/` | Ancienne application mono-page, conservée pour référence, non maintenue. |
| `legacy/` | Le code R d'origine et ses données de calibration. Lecture seule : c'est la référence de vérité pour porter la calibration. |
| `docs/adr/` | Décisions d'architecture, une par fichier, jamais réécrites. |

Le nom de distribution est `financyou` ; les paquets importables restent
`investment_calculator` et `time_series_slicer`.

## Règles de contribution

**Une PR par sous-étape.** Jamais par phase. Un diff de 500 lignes se relit, un
diff de 5 000 se merge sans être lu. Au-delà de 500 lignes, découper.

**Chaque PR porte sa preuve.** La description contient le test qui échouait avant
et passe après, ou la mesure avant/après. Une PR sans preuve n'est pas relisible.

**Aucune régression numérique silencieuse.** Avant de commencer, exécuter
`python examples/complete_pipeline_with_files.py` et conserver
`outputs/optimal_portfolio.json`. Après, réexécuter et comparer : la graine est
fixée à 42, les chiffres doivent être identiques. S'ils ont bougé, c'est
intentionnel et la PR l'explique, ou c'est une régression.

**Un agent ne franchit jamais une porte de validation.** Il s'arrête, produit le
rapport, et attend une décision humaine. Les portes sont définies dans la feuille
de route (`claude/feuille_de_route_mise_en_ligne.md` du projet).

**Un agent ne se porte pas garant d'une valeur fiscale ou réglementaire.** Il
peut la chercher, citer sa source, et la proposer. Le champ `validated_by` d'un
régime nomme une personne.

## Qualité

```bash
python -m pytest tests/ -q     # doit être intégralement vert
ruff check .                    # 0 erreur
mypy                            # strict sur investment_calculator.modules.*
```

- Le code, les noms de fonctions et de variables sont en **anglais**.
- Les commentaires, docstrings et messages d'erreur sont en **français**.
- Pas d'`except:` nu, pas d'`except Exception: pass`. Une exception avalée est un
  bug caché ; on capture l'exception attendue et on journalise.
- Pas de `print()` dans la bibliothèque : `logger = logging.getLogger(__name__)`.
  Les `print()` restent permis dans `examples/` et `web_ui/`.
- Un message d'erreur dit ce qui ne va pas **et** comment le corriger.

## Ce qu'il ne faut pas faire

- Modifier `legacy/` : c'est la référence contre laquelle le portage est vérifié.
- Modifier un millésime fiscal existant. Une nouvelle année donne un nouveau
  fichier, sinon les simulations archivées ne sont plus rejouables.
- Allonger `LITTERAUX_TOLERES` dans `tests/test_tax_regime_contract.py` pour
  faire passer la CI. Cette liste ne doit que se réduire.
- Ajouter une dépendance sans la borner en version, en bas et en haut.
- Committer `outputs/`, un fichier de données volumineux, ou un secret.

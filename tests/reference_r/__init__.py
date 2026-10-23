"""
Traductions fidèles du code R d'origine, servant de référence aux tests.

Chaque fonction reproduit ligne à ligne un script de ``legacy/``, défauts
compris, avec des indices décalés de R (base 1) vers Python (base 0). Elles ne
sont importées que par les tests. Le portage de la bibliothèque s'en écarte
là où le R est faux. Chaque écart est nommé dans la docstring du module porté,
et un test le montre.

Chaque traduction est elle-même vérifiée contre le vrai R. Le script
``generate_r_outputs.R`` exécute les scripts de ``legacy/R_Financyou`` sur les
cas des tests et fige leurs sorties dans ``r_outputs.json``.
``tests/test_reference_r.py`` compare chaque traduction à ces sorties. R n'est
donc pas nécessaire pour faire tourner les tests.
"""

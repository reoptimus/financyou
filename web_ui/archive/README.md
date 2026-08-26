# Archive

`app_simple.py` est l'ancienne application Streamlit mono-page. Elle est
conservée pour référence — son parcours en cinq onglets et sa génération de
rapport HTML n'ont pas d'équivalent dans `app_enhanced.py` et doivent être
repris lors de la fusion des parcours (étape 2.1).

**Elle n'est ni maintenue, ni testée, ni déployée.** Elle contient les bugs de
clés identifiés à l'audit (volatilité, probabilité d'atteinte d'objectif,
frontière efficiente jamais affichées correctement). Ne pas l'utiliser comme
base de travail : la base unique est `web_ui/app_enhanced.py`.

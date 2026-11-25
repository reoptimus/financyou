"""
Configuration de l'interface : un seul thème Streamlit, et des valeurs jamais
tronquées.

Streamlit lit le ``.streamlit/config.toml`` de la racine, mais aussi celui qui
se trouve à côté du script. L'ancien ``web_ui/.streamlit/config.toml`` portait
un thème bleu (#1f77b4, texte #262730) qui écrasait le thème indigo dans la
page principale : curseurs et textes de formulaire n'avaient pas les couleurs
du reste de l'interface.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from web_ui import theme

ROOT = Path(__file__).resolve().parent.parent


def test_un_seul_fichier_de_configuration_streamlit() -> None:
    assert not (ROOT / 'web_ui' / '.streamlit' / 'config.toml').exists(), (
        "Un second config.toml à côté du script écrase le thème de la racine : "
        "mettez les réglages dans .streamlit/config.toml."
    )


def test_le_theme_streamlit_est_celui_de_l_interface() -> None:
    config = tomllib.loads((ROOT / '.streamlit' / 'config.toml').read_text(encoding='utf-8'))
    assert config['theme']['primaryColor'].upper() == theme.PRIMARY.upper()
    assert config['theme']['textColor'].upper() == theme.INK.upper()


def test_l_image_docker_embarque_la_configuration_streamlit() -> None:
    dockerfile = (ROOT / 'Dockerfile').read_text(encoding='utf-8')
    assert re.search(r'^COPY .*\.streamlit/ \./\.streamlit/', dockerfile, re.MULTILINE)


def test_une_valeur_d_indicateur_n_est_jamais_tronquee() -> None:
    rules = re.findall(r'([^{}]*stMetricValue[^{}]*)\{([^}]*)\}', theme._CSS)
    declarations = ' '.join(body for _, body in rules)
    assert 'text-overflow: clip' in declarations
    assert 'white-space: normal' in declarations

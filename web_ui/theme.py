"""
Identité visuelle de l'interface : palette, typographie, gabarit des graphiques.

Ce module ne touche à aucun chiffre : il fixe l'apparence (feuille de style
injectée, gabarit Plotly, formats d'affichage à la française). Les couleurs de
base du thème Streamlit sont dans ``.streamlit/config.toml``.
"""

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

NAVY = "#1E3A5F"
NAVY_DARK = "#0F1F33"
INK = "#16202E"
MUTED = "#5B6878"
LINE = "#E3E7ED"
SURFACE = "#F4F6F9"
ACCENT = "#B08D57"
POSITIVE = "#2F6B4F"
NEGATIVE = "#A23B3B"

# Séries catégorielles : du marine aux tons neutres, l'accent doré en dernier.
SERIES = ["#1E3A5F", "#4F7CAC", "#93B1CF", "#B08D57", "#6B7F94", "#2F6B4F", "#C9D6E3"]

# Bandes de probabilité : bornes extrêmes claires, médiane marine.
BAND_COLORS = {"5 %": "#C9D6E3", "10 %": "#93B1CF", "Médiane": NAVY,
               "90 %": "#93B1CF", "95 %": "#C9D6E3"}
SCENARIO_BAND_COLORS = ["#93B1CF", NAVY, "#93B1CF"]

# Dégradé des tranches : clair pour le court terme, marine pour le long terme.
TRANCHE_SCALE = [[0.0, "#0F1F33"], [0.5, "#4F7CAC"], [1.0, "#DCE6F0"]]

NARROW_SPACE = " "

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
button, input, textarea, select, label, p, li {
    font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
}
[data-testid="stAppViewContainer"] { color: %(ink)s; }
[data-testid="stMainBlockContainer"], .block-container {
    max-width: 1180px; padding-top: 2.5rem; padding-bottom: 4rem;
}
[data-testid="stHeader"] { background: transparent; }

/* Titres : serif pour la page, sans serif resserré pour les sections. */
h1, .fy-title {
    font-family: 'Source Serif 4', Georgia, serif !important;
    font-weight: 600 !important; letter-spacing: -0.01em; color: %(ink)s;
}
h2, h3 {
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
    letter-spacing: -0.01em; color: %(ink)s;
}
[data-testid="stMarkdownContainer"] h3 {
    font-size: 1.05rem; text-transform: none; margin-top: 1.4rem;
    padding-bottom: 0.5rem; border-bottom: 1px solid %(line)s;
}
[data-testid="stCaptionContainer"], .stCaption { color: %(muted)s; }

/* En-tête de page. */
.fy-header { margin: 0 0 1.75rem 0; padding-bottom: 1.25rem; border-bottom: 1px solid %(line)s; }
.fy-eyebrow {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em;
    text-transform: uppercase; color: %(accent)s; margin-bottom: 0.35rem;
}
.fy-title { font-size: 2.1rem; line-height: 1.15; margin: 0; }
.fy-lead {
    color: %(muted)s; font-size: 1rem; line-height: 1.6; max-width: 760px; margin-top: 0.6rem;
}

/* Indicateurs : cartes à filet, chiffres tabulaires. */
[data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid %(line)s; border-radius: 6px;
    padding: 1rem 1.15rem; border-top: 3px solid %(navy)s;
}
[data-testid="stMetricLabel"] p {
    font-size: 0.85rem; font-weight: 500; color: %(muted)s; white-space: normal;
}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] div {
    white-space: normal; overflow: visible;
}
[data-testid="stMetricValue"] {
    font-size: 1.75rem; font-weight: 600; color: %(ink)s;
    font-variant-numeric: tabular-nums;
}

/* Boutons. */
.stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button {
    border-radius: 4px; font-weight: 500; box-shadow: none;
}
button[kind="primary"], button[kind="primaryFormSubmit"] {
    background: %(navy)s; border-color: %(navy)s;
}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {
    background: %(navy_dark)s; border-color: %(navy_dark)s;
}

/* Formulaires, tableaux, encadrés. */
[data-testid="stForm"] {
    border: 1px solid %(line)s; border-radius: 6px; background: #FFFFFF; padding: 1.5rem;
}
[data-testid="stDataFrame"], [data-testid="stTable"] {
    border: 1px solid %(line)s; border-radius: 6px;
}
[data-testid="stExpander"] details { border: 1px solid %(line)s; border-radius: 6px; }
[data-testid="stAlert"] { border-radius: 4px; }

/* Barre latérale : marine, navigation en liste. */
[data-testid="stSidebar"] h3 {
    font-size: 0.7rem !important; letter-spacing: 0.14em; text-transform: uppercase;
    color: #8A9BB0 !important; margin: 1.6rem 0 0.4rem 0; border: none;
}
[data-testid="stSidebar"] .stButton button {
    justify-content: flex-start; text-align: left; background: transparent;
    border: none; border-left: 2px solid transparent; border-radius: 0;
    padding: 0.45rem 0.8rem; min-height: 0; color: #C3CEDB;
}
[data-testid="stSidebar"] .stButton button > div { justify-content: flex-start; width: 100%%; }
[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(255,255,255,0.05); color: #FFFFFF;
}
[data-testid="stSidebar"] .stButton button[kind="primary"] {
    background: rgba(255,255,255,0.08); border-left-color: %(accent)s; color: #FFFFFF;
    font-weight: 600;
}
[data-testid="stSidebar"] .stButton button p { font-size: 0.92rem; }
[data-testid="stSidebar"] .stButton { margin-bottom: -0.55rem; }
[data-testid="stSidebar"] .stDownloadButton button {
    background: transparent; border: 1px solid rgba(255,255,255,0.25); color: #FFFFFF;
}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #8A9BB0; }
.fy-brand { padding: 0.25rem 0.8rem 1.25rem 0.8rem; }
.fy-brand-name {
    font-family: 'Source Serif 4', Georgia, serif; font-size: 1.5rem; font-weight: 600;
    color: #FFFFFF !important; letter-spacing: -0.01em;
}
.fy-brand-tag {
    font-size: 0.7rem; letter-spacing: 0.14em; text-transform: uppercase;
    color: %(accent)s !important; margin-top: 0.15rem;
}

/* Accueil : étapes. */
.fy-steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 1rem; margin: 1.5rem 0 2rem 0; }
.fy-step {
    border: 1px solid %(line)s; border-radius: 6px; padding: 1.15rem 1.2rem; background: #FFFFFF;
}
.fy-step-num {
    font-family: 'Source Serif 4', Georgia, serif; font-size: 1.4rem; color: %(accent)s;
}
.fy-step-title { font-weight: 600; margin: 0.3rem 0 0.35rem 0; color: %(ink)s; }
.fy-step-text { color: %(muted)s; font-size: 0.9rem; line-height: 1.5; }
</style>
"""


def apply_theme() -> None:
    """Injecter la feuille de style et faire du gabarit FinancYou celui de Plotly."""
    st.markdown(_CSS % {
        'ink': INK, 'muted': MUTED, 'line': LINE, 'navy': NAVY, 'navy_dark': NAVY_DARK,
        'accent': ACCENT,
    }, unsafe_allow_html=True)
    pio.templates.default = "plotly_white+financyou"


def page_header(title: str, lead: str | None = None, eyebrow: str | None = None) -> None:
    """En-tête de page : surtitre, titre et chapeau."""
    parts = ['<div class="fy-header">']
    if eyebrow:
        parts.append(f'<div class="fy-eyebrow">{eyebrow}</div>')
    parts.append(f'<h1 class="fy-title">{title}</h1>')
    if lead:
        parts.append(f'<div class="fy-lead">{lead}</div>')
    parts.append('</div>')
    st.markdown("".join(parts), unsafe_allow_html=True)


def fr_amount(value: float, decimals: int = 0) -> str:
    """Nombre à la française : espace fine insécable pour les milliers, virgule décimale."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", NARROW_SPACE).replace(".", ",")


def fr_euros(value: float) -> str:
    """Montant en euros arrondi à l'euro, à la française."""
    return f"{fr_amount(value)}{NARROW_SPACE}€"


def fr_percent(value: float, decimals: int = 2) -> str:
    """Part exprimée en pourcentage, à la française (0,0586 donne « 5,86 % »)."""
    return f"{fr_amount(value * 100, decimals)}{NARROW_SPACE}%"


pio.templates["financyou"] = go.layout.Template(layout=go.Layout(
    font={'family': "Inter, -apple-system, 'Segoe UI', sans-serif", 'color': INK, 'size': 13},
    colorway=SERIES,
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    separators=", ",
    margin={'l': 10, 'r': 10, 't': 40, 'b': 10},
    xaxis={'gridcolor': LINE, 'linecolor': "#C5CDD8", 'zeroline': False,
           'title': {'font': {'color': MUTED, 'size': 12}}, 'tickfont': {'color': MUTED}},
    yaxis={'gridcolor': LINE, 'linecolor': "#C5CDD8", 'zeroline': False,
           'title': {'font': {'color': MUTED, 'size': 12}}, 'tickfont': {'color': MUTED}},
    legend={'font': {'color': MUTED, 'size': 12}, 'bgcolor': "rgba(0,0,0,0)",
            'orientation': 'h', 'x': 0, 'xanchor': 'left', 'y': 1.02, 'yanchor': 'bottom'},
    hoverlabel={'bgcolor': "#FFFFFF", 'bordercolor': LINE, 'font': {'color': INK}},
))

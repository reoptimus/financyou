"""
Identité visuelle de l'interface : palette, typographie, gabarit des graphiques.

Ce module ne touche à aucun chiffre : il fixe l'apparence (feuille de style
injectée, gabarit Plotly, formats d'affichage à la française). Les couleurs de
base du thème Streamlit sont dans ``.streamlit/config.toml``.

Style clair et aéré : fond blanc légèrement teinté, cartes blanches arrondies à
ombre douce, navigation horizontale en pastilles, qui défile sur téléphone.
"""

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

PRIMARY = "#3B4FD8"
PRIMARY_DARK = "#2A3BB5"
PRIMARY_SOFT = "#EEF0FD"
INK = "#0E1525"
MUTED = "#667085"
LINE = "#E7E9F0"
SURFACE = "#F7F8FC"
POSITIVE = "#1F9D6B"
NEGATIVE = "#E5484D"

# Séries catégorielles : indigo, bleus, puis tons neutres.
SERIES = ["#3B4FD8", "#7C8CF0", "#B4BEF7", "#1F9D6B", "#98A2B3", "#F5A524", "#DDE1FB"]

# Bandes de probabilité : bornes extrêmes claires, médiane indigo.
BAND_COLORS = {"5 %": "#C9CFF9", "10 %": "#8E9BF2", "Médiane": PRIMARY,
               "90 %": "#8E9BF2", "95 %": "#C9CFF9"}
SCENARIO_BAND_COLORS = ["#8E9BF2", PRIMARY, "#8E9BF2"]

# Dégradé des tranches : clair pour le court terme, indigo foncé pour le long terme.
TRANCHE_SCALE = [[0.0, "#1E2A8A"], [0.5, "#6F7FEA"], [1.0, "#E3E7FC"]]
TIMELINE_LINE = "#F5A524"

NARROW_SPACE = " "

# Configuration commune des graphiques : pas de barre d'outils, adaptés à l'écran.
PLOTLY_CONFIG = {'displayModeBar': False, 'responsive': True}

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
button, input, textarea, select, label, p, li {
    font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif;
}
[data-testid="stAppViewContainer"] {
    color: %(ink)s;
    background: radial-gradient(1200px 420px at 50%% -120px, #E9ECFD 0%%, rgba(233,236,253,0) 70%%),
                %(surface)s;
}
[data-testid="stMainBlockContainer"], .block-container {
    max-width: 1120px; padding-top: 1rem; padding-bottom: 4rem;
}
[data-testid="stHeader"] { background: transparent; }

h1, h2, h3, .fy-title { color: %(ink)s; letter-spacing: -0.02em; }
h1.fy-title { font-weight: 500 !important; }
[data-testid="stMarkdownContainer"] h3 {
    font-size: 1.1rem; font-weight: 600; margin-top: 1.6rem; padding: 0;
}
[data-testid="stCaptionContainer"], .stCaption { color: %(muted)s; }

/* En-tête : marque et navigation en pastilles, collé en haut au défilement. */
.st-key-fy_header {
    position: sticky; top: 0; z-index: 990; gap: 0.5rem;
    background: rgba(247,248,252,0.85); backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    margin: 0 -1rem; padding: 0.75rem 1rem 0.6rem 1rem;
    border-bottom: 1px solid %(line)s;
}
.fy-brand { font-size: 1.2rem; font-weight: 700; letter-spacing: -0.02em; color: %(ink)s; }
.fy-brand span { color: %(primary)s; }
.st-key-fy_nav {
    flex-wrap: nowrap !important; overflow-x: auto; overflow-y: hidden; gap: 0.25rem !important;
    scrollbar-width: none; -webkit-overflow-scrolling: touch; scroll-snap-type: x proximity;
    padding-bottom: 2px;
}
.st-key-fy_nav::-webkit-scrollbar { display: none; }
.st-key-fy_nav > div {
    flex: 0 0 auto !important; width: auto !important; scroll-snap-align: start;
}
.st-key-fy_nav button {
    border-radius: 999px !important; padding: 0.35rem 0.85rem !important; min-height: 0;
    white-space: nowrap; border: 1px solid transparent; color: %(muted)s;
}
.st-key-fy_nav button p { font-size: 0.9rem; font-weight: 500; white-space: nowrap; }
.st-key-fy_nav button:hover { background: #FFFFFF; color: %(ink)s; border-color: %(line)s; }
.st-key-fy_nav button[kind="primary"] {
    background: %(ink)s; color: #FFFFFF; border-color: %(ink)s;
}
.st-key-fy_nav button[kind="primary"]:hover { background: %(ink)s; border-color: %(ink)s; }
.st-key-fy_nav button[kind="primary"] p { color: #FFFFFF; }

/* En-tête de page. */
.fy-header { margin: 1.75rem 0 1.5rem 0; }
.fy-eyebrow {
    display: inline-block; font-size: 0.75rem; font-weight: 600; color: %(primary)s;
    background: %(primary_soft)s; border-radius: 999px; padding: 0.2rem 0.7rem;
    margin-bottom: 0.75rem;
}
.fy-title { font-size: 2.4rem; line-height: 1.12; font-weight: 400; margin: 0; }
.fy-lead {
    color: %(muted)s; font-size: 1.02rem; line-height: 1.6; max-width: 720px; margin-top: 0.7rem;
}
.fy-hero { text-align: center; margin: 3rem auto 2.25rem auto; }
.fy-hero .fy-title { font-size: 3rem; max-width: 760px; margin: 0 auto; }
.fy-hero .fy-lead { margin: 0.9rem auto 0 auto; }

/* Cartes : indicateurs, formulaires, tableaux, encadrés. */
[data-testid="stMetric"], [data-testid="stForm"], .fy-step {
    background: #FFFFFF; border: 1px solid %(line)s; border-radius: 14px;
    box-shadow: 0 1px 2px rgba(16,24,40,0.04), 0 8px 24px rgba(16,24,40,0.04);
}
[data-testid="stMetric"] { padding: 1.05rem 1.2rem; }
[data-testid="stMetricLabel"] p {
    font-size: 0.85rem; font-weight: 500; color: %(muted)s; white-space: normal;
}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] div {
    white-space: normal; overflow: visible;
}
[data-testid="stMetricValue"] {
    font-size: 1.8rem; font-weight: 500; color: %(ink)s; letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
}
[data-testid="stForm"] { padding: 1.5rem; }
[data-testid="stDataFrame"], [data-testid="stTable"] {
    background: #FFFFFF; border: 1px solid %(line)s; border-radius: 12px; overflow: hidden;
}
[data-testid="stExpander"] details {
    background: #FFFFFF; border: 1px solid %(line)s; border-radius: 12px;
}
[data-testid="stAlert"] { border-radius: 12px; }
[data-testid="stPlotlyChart"] {
    background: #FFFFFF; border: 1px solid %(line)s; border-radius: 14px; overflow: hidden;
}

/* Boutons : pastilles. */
.stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button {
    border-radius: 999px; font-weight: 500; box-shadow: none; padding-left: 1.1rem;
    padding-right: 1.1rem;
}
button[kind="primary"], button[kind="primaryFormSubmit"] {
    background: %(primary)s; border-color: %(primary)s;
}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {
    background: %(primary_dark)s; border-color: %(primary_dark)s;
}

/* Barre latérale : réglages du calcul et saisie. */
[data-testid="stSidebar"] { border-right: 1px solid %(line)s; }
[data-testid="stSidebar"] h3 {
    font-size: 0.72rem !important; letter-spacing: 0.1em; text-transform: uppercase;
    color: %(muted)s !important; margin: 1.2rem 0 0.3rem 0;
}

/* Accueil : étapes. */
.fy-steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem; margin: 0 0 2rem 0; }
.fy-step { padding: 1.2rem 1.25rem; }
.fy-step-num {
    display: inline-flex; align-items: center; justify-content: center;
    width: 2rem; height: 2rem; border-radius: 999px; background: %(primary_soft)s;
    color: %(primary)s; font-weight: 600; font-size: 0.85rem;
}
.fy-step-title { font-weight: 600; margin: 0.75rem 0 0.3rem 0; color: %(ink)s; }
.fy-step-text { color: %(muted)s; font-size: 0.9rem; line-height: 1.5; }
.st-key-fy_start, .st-key-fy_start .stButton {
    display: flex; justify-content: center; width: 100%%;
}

/* Téléphone. */
@media (max-width: 640px) {
    [data-testid="stMainBlockContainer"], .block-container {
        padding-left: 1rem; padding-right: 1rem; padding-top: 0.25rem;
    }
    .fy-header { margin: 1.25rem 0 1rem 0; }
    .fy-title { font-size: 1.8rem; }
    .fy-hero { margin: 1.75rem auto 1.5rem auto; }
    .fy-hero .fy-title { font-size: 2.1rem; }
    .fy-lead { font-size: 0.95rem; }
    [data-testid="stMetricValue"] { font-size: 1.55rem; }
    [data-testid="stForm"] { padding: 1rem; }
    [data-testid="stHorizontalBlock"] { gap: 0.6rem; }
}
</style>
"""


def apply_theme() -> None:
    """Injecter la feuille de style et faire du gabarit FinancYou celui de Plotly."""
    st.markdown(_CSS % {
        'ink': INK, 'muted': MUTED, 'line': LINE, 'surface': SURFACE, 'primary': PRIMARY,
        'primary_dark': PRIMARY_DARK, 'primary_soft': PRIMARY_SOFT,
    }, unsafe_allow_html=True)
    pio.templates.default = "plotly_white+financyou"


def page_header(title: str, lead: str | None = None, eyebrow: str | None = None,
                hero: bool = False) -> None:
    """En-tête de page : pastille de surtitre, titre et chapeau ; centré pour l'accueil."""
    parts = [f'<div class="fy-header{" fy-hero" if hero else ""}">']
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
    font={'family': "Inter, -apple-system, 'Segoe UI', sans-serif", 'color': INK, 'size': 12},
    colorway=SERIES,
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    separators=", ",
    margin={'l': 8, 'r': 8, 't': 40, 'b': 8},
    xaxis={'gridcolor': LINE, 'linecolor': LINE, 'zeroline': False, 'automargin': True,
           'title': {'font': {'color': MUTED, 'size': 12}}, 'tickfont': {'color': MUTED}},
    yaxis={'gridcolor': LINE, 'linecolor': LINE, 'zeroline': False, 'automargin': True,
           'title': {'font': {'color': MUTED, 'size': 12}}, 'tickfont': {'color': MUTED}},
    legend={'font': {'color': MUTED, 'size': 11}, 'bgcolor': "rgba(0,0,0,0)",
            'orientation': 'h', 'x': 0, 'xanchor': 'left', 'y': 1.02, 'yanchor': 'bottom'},
    hoverlabel={'bgcolor': "#FFFFFF", 'bordercolor': LINE, 'font': {'color': INK}},
))

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

# Icône et couleur de chaque page : la même dans la navigation, l'en-tête de la
# page et les étapes de l'accueil, pour qu'on reconnaisse la page d'un coup d'œil.
PAGE_STYLE = {
    'Home': ("home", "#3B4FD8"),
    'Profile': ("person", "#0EA5E9"),
    'Holdings': ("account_balance_wallet", "#10B981"),
    'Projects': ("flag", "#F59E0B"),
    'Budget': ("receipt_long", "#EC4899"),
    'Rentals': ("apartment", "#8B5CF6"),
    'Projection': ("insights", "#F97316"),
}

# Configuration commune des graphiques : pas de barre d'outils, adaptés à l'écran.
PLOTLY_CONFIG = {'displayModeBar': False, 'responsive': True}

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,500,1,0&icon_names=%(icon_names)s&display=block');

html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
button, input, textarea, select, label, p, li {
    font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif;
}
[data-testid="stAppViewContainer"] {
    color: %(ink)s;
    background: #FFFFFF;
}
[data-testid="stMainBlockContainer"], .block-container {
    max-width: 1200px; padding-top: 1rem; padding-bottom: 4rem;
}
[data-testid="stHeader"] { background: transparent; }
.fy-icon {
    font-family: 'Material Symbols Rounded'; font-weight: normal; font-style: normal;
    line-height: 1; letter-spacing: normal; text-transform: none; white-space: nowrap;
    -webkit-font-feature-settings: 'liga'; font-feature-settings: 'liga';
    -webkit-font-smoothing: antialiased;
}
.fy-badge {
    display: inline-flex; align-items: center; justify-content: center; flex: 0 0 auto;
    width: 2.75rem; height: 2.75rem; border-radius: 12px; font-size: 1.5rem;
}

h1, h2, h3, .fy-title { color: %(ink)s; letter-spacing: -0.02em; }
h1.fy-title { font-weight: 500 !important; }
[data-testid="stMarkdownContainer"] h3 {
    font-size: 1.1rem; font-weight: 600; margin-top: 1.6rem; padding: 0;
}
[data-testid="stCaptionContainer"], .stCaption { color: %(muted)s; }

/* En-tête : marque et navigation en pastilles, collé en haut au défilement. */
.st-key-fy_header {
    position: sticky; top: 0; z-index: 990; gap: 0.9rem !important;
    background: rgba(255,255,255,0.92); backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    margin: 0 -1rem; padding: 1rem 1rem 0.75rem 1rem;
    border-bottom: 1px solid %(line)s;
}
.fy-brand {
    display: flex; align-items: center; gap: 0.6rem; padding: 0.1rem 0 0.9rem 0.4rem;
    font-size: 1.7rem; font-weight: 700; letter-spacing: -0.03em; color: %(ink)s;
    line-height: 1;
}
.fy-brand-mark {
    display: inline-flex; align-items: center; justify-content: center;
    width: 2.6rem; height: 2.6rem; border-radius: 12px; color: #FFFFFF; font-size: 1.6rem;
    background: linear-gradient(135deg, %(primary)s 0%%, #8B5CF6 100%%);
    box-shadow: 0 6px 16px rgba(59,79,216,0.28);
}
.fy-brand-name span { color: %(primary)s; }

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
    border-radius: 999px !important; padding: 0.35rem 0.7rem !important; min-height: 0;
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
.fy-title-row { display: flex; align-items: center; gap: 0.9rem; }
.fy-lead {
    color: %(muted)s; font-size: 1.02rem; line-height: 1.6; max-width: 720px; margin-top: 0.7rem;
}
.fy-hero { text-align: center; margin: 3rem auto 2.25rem auto; }
.fy-hero .fy-title { font-size: 3rem; max-width: 760px; margin: 0 auto; }
.fy-hero .fy-title-row { justify-content: center; }
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
/* Une valeur ne se tronque jamais : « +68 pb par… » cachait l'unité sur un écran
   de 1366 px. Elle passe à la ligne entre deux mots, jamais au milieu d'un nombre. */
[data-testid="stMetricValue"], [data-testid="stMetricValue"] div,
[data-testid="stMetricValue"] p {
    white-space: normal; overflow: visible; text-overflow: clip;
}
[data-testid="stForm"] { padding: 1.5rem; }

/* Rechargement d'une saisie : Streamlit écrit ces textes en anglais, sans option
   de traduction. Le texte d'origine est masqué et remplacé, sans changer le bouton. */
[data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] p {
    font-size: 0;
}
[data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] p::after {
    content: "Choisir un fichier"; font-size: 0.875rem;
}
[data-testid="stFileUploaderDropzoneInstructions"] span { font-size: 0; }
[data-testid="stFileUploaderDropzoneInstructions"] span::after {
    content: "Fichier JSON"; font-size: 0.8rem;
}
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
    /* Laisse la place au bouton du panneau latéral, au-dessus de la marque. */
    .st-key-fy_header { padding-top: 2.6rem; }
    .fy-title { font-size: 1.6rem; }
    .fy-badge { width: 2.3rem; height: 2.3rem; font-size: 1.3rem; }
    .fy-brand { font-size: 1.5rem; }
    .fy-hero { margin: 1.75rem auto 1.5rem auto; }
    .fy-hero .fy-title { font-size: 2.1rem; }
    .fy-lead { font-size: 0.95rem; }
    [data-testid="stMetricValue"] { font-size: 1.55rem; }
    [data-testid="stForm"] { padding: 1rem; }
    [data-testid="stHorizontalBlock"] { gap: 0.6rem; }
}
%(nav_icons)s
</style>
"""


def apply_theme() -> None:
    """Injecter la feuille de style et faire du gabarit FinancYou celui de Plotly."""
    nav_icons = "\n".join(
        f'.st-key-nav_{page} [data-testid="stIconMaterial"] {{ color: {color}; }}'
        for page, (_, color) in PAGE_STYLE.items()
    )
    icon_names = ",".join(sorted({icon for icon, _ in PAGE_STYLE.values()} | {"trending_up"}))
    st.markdown(_CSS % {
        'ink': INK, 'muted': MUTED, 'line': LINE, 'surface': SURFACE, 'primary': PRIMARY,
        'primary_dark': PRIMARY_DARK, 'primary_soft': PRIMARY_SOFT, 'nav_icons': nav_icons,
        'icon_names': icon_names,
    }, unsafe_allow_html=True)
    pio.templates.default = "plotly_white+financyou"


def icon_badge(page: str, size_class: str = "fy-badge") -> str:
    """Pastille carrée teintée portant l'icône de couleur de la page."""
    icon, color = PAGE_STYLE[page]
    return (f'<span class="{size_class} fy-icon" style="color: {color}; '
            f'background: {color}1F;">{icon}</span>')


def brand_html() -> str:
    """Logo : pictogramme en dégradé et nom FinancYou."""
    return ('<div class="fy-brand"><span class="fy-brand-mark fy-icon">trending_up</span>'
            '<span class="fy-brand-name">Financ<span>You</span></span></div>')


def page_header(title: str, lead: str | None = None, eyebrow: str | None = None,
                hero: bool = False, page: str | None = None) -> None:
    """En-tête de page : pastille de surtitre, icône, titre et chapeau ; centré pour l'accueil."""
    parts = [f'<div class="fy-header{" fy-hero" if hero else ""}">']
    if eyebrow:
        parts.append(f'<div class="fy-eyebrow">{eyebrow}</div>')
    badge = icon_badge(page) if page and not hero else ""
    parts.append(f'<div class="fy-title-row">{badge}<h1 class="fy-title">{title}</h1></div>')
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

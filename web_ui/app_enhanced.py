"""
FinancYou : interface Streamlit.

Elle rassemble la saisie de l'utilisateur (profil, versements, épargne
existante) et affiche le résultat de ``web_ui.pipeline.run_projection``. Aucun
champ n'a de valeur par défaut : ce qui n'est pas saisi n'est pas supposé.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from investment_calculator.placement_catalog import (
    list_placement_catalogs,
    load_placement_catalog,
)
from web_ui.pipeline import build_profile_config, run_projection

st.set_page_config(
    page_title="FinancYou",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = {
    "🏠 Accueil": "Home",
    "👤 Profil et versements": "Profile",
    "💼 Épargne existante": "Holdings",
    "📊 Projection": "Projection",
}


def init_session_state():
    """Initialiser l'état de session."""
    defaults = {'form': None, 'holdings': [], 'results': None, 'page': 'Home'}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar():
    """Navigation et réglages du calcul."""
    with st.sidebar:
        st.markdown("## 💰 FinancYou")
        for label, page in PAGES.items():
            if st.button(label, use_container_width=True, key=f"nav_{page}"):
                st.session_state.page = page
                st.rerun()

        st.markdown("---")
        st.markdown("### ⚙️ Réglages")
        # Les catalogues proposés se déduisent des fichiers livrés ; chacun
        # porte le régime fiscal de son pays et de son millésime (ADR 0002).
        st.session_state.catalog_id = st.selectbox(
            "Catalogue de placements", list_placement_catalogs(), key="catalog_select"
        )
        placement_ids = load_placement_catalog(st.session_state.catalog_id).placement_ids
        reference_options = ["Aucun", *placement_ids]
        st.session_state.risk_free_placement = st.selectbox(
            "Placement de référence du ratio de Sharpe",
            reference_options,
            index=reference_options.index("livret_a") if "livret_a" in placement_ids else 0,
            key="reference_select",
        )
        st.session_state.risk_aversion = st.slider(
            "Aversion au risque (λ)", 0.5, 20.0, 5.0, 0.5, key="risk_aversion_slider"
        )
        st.session_state.num_scenarios = st.slider(
            "Nombre de scénarios", 10, 500, 100, 10, key="scenarios_slider"
        )


def page_home():
    """Présentation et étapes."""
    st.markdown("# 💰 FinancYou")
    st.markdown(
        "Projection du patrimoine après frais et impôts, sur des scénarios "
        "économiques simulés, et répartition des versements entre les placements "
        "du catalogue."
    )
    st.markdown(
        "1. **Profil et versements** : âge, horizon, revenus, épargne mensuelle.\n"
        "2. **Épargne existante** : ce que vous détenez déjà, laissé en place.\n"
        "3. **Projection** : répartition des nouveaux versements et patrimoine projeté."
    )
    if st.button("📝 Commencer", type="primary"):
        st.session_state.page = "Profile"
        st.rerun()


def page_profile():
    """Saisie du profil et des versements."""
    st.markdown("# 👤 Profil et versements")
    saved = st.session_state.form or {}

    with st.form("profile"):
        st.markdown("### Situation")
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Âge actuel", 18, 100, saved.get('age'))
            retirement_age = st.number_input(
                "Âge de départ à la retraite (horizon de la projection)", 18, 100,
                saved.get('retirement_age'),
            )
            couple = st.checkbox(
                "Imposition en couple (abattement de l'assurance-vie doublé)",
                saved.get('couple', False),
            )
        with col2:
            annual_income = st.number_input(
                "Revenu annuel net (€)", 0.0, None, saved.get('annual_income'), 1000.0
            )
            annual_expenses = st.number_input(
                "Dépenses annuelles (€, facultatif)", 0.0, None,
                saved.get('annual_expenses'), 1000.0,
            )

        st.markdown("### Versements")
        col1, col2 = st.columns(2)
        with col1:
            monthly_amount = st.number_input(
                "Épargne mensuelle (€)", 0.0, None, saved.get('monthly_amount'), 50.0
            )
        with col2:
            increase = saved.get('annual_increase')
            annual_increase = st.number_input(
                "Hausse annuelle des versements (%), 0 pour un versement constant",
                -20.0, 20.0, None if increase is None else increase * 100, 0.5,
            )

        st.markdown("### Contraintes (facultatives)")
        col1, col2 = st.columns(2)
        with col1:
            cap_equity = st.checkbox(
                "Plafonner la part en actions", saved.get('max_equity') is not None
            )
            max_equity = st.slider(
                "Part maximale en actions (%)", 0, 100,
                round(100 * (saved.get('max_equity') or 1.0)), 5,
            )
        with col2:
            floor_bond = st.checkbox(
                "Imposer une part minimale d'obligations", saved.get('min_bond') is not None
            )
            min_bond = st.slider(
                "Part minimale en obligations (%)", 0, 100,
                round(100 * (saved.get('min_bond') or 0.0)), 5,
            )
        st.caption(
            "Le fonds en euros compte pour sa part d'actions et d'obligations ; "
            "le Livret A ne compte ni comme action ni comme obligation."
        )
        submitted = st.form_submit_button("💾 Enregistrer", type="primary")

    if submitted:
        required = {
            "âge actuel": age, "âge de départ à la retraite": retirement_age,
            "revenu annuel": annual_income, "épargne mensuelle": monthly_amount,
            "hausse annuelle des versements": annual_increase,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            st.error(f"À renseigner avant d'enregistrer : {', '.join(missing)}.")
            return
        st.session_state.form = {
            'age': age,
            'retirement_age': retirement_age,
            'couple': couple,
            'annual_income': annual_income,
            'annual_expenses': annual_expenses,
            'monthly_amount': monthly_amount,
            'annual_increase': annual_increase / 100,
            'max_equity': max_equity / 100 if cap_equity else None,
            'min_bond': min_bond / 100 if floor_bond else None,
        }
        st.session_state.results = None
        st.success("✅ Profil enregistré.")


def page_holdings():
    """Saisie de l'épargne existante, laissée dans ses placements."""
    st.markdown("# 💼 Épargne existante")
    st.markdown(
        "Ce que vous détenez déjà reste dans son placement : il n'est pas réalloué, "
        "s'ajoute au patrimoine projeté, donne son ancienneté à son enveloppe et "
        "s'impute sur les plafonds de versement."
    )
    catalog = load_placement_catalog(st.session_state.catalog_id)
    labels = {pid: catalog.placement(pid)['label'] for pid in catalog.placement_ids}

    holdings = st.session_state.holdings
    if holdings:
        table = pd.DataFrame(holdings).rename(columns={
            'placement': 'Placement', 'value': 'Valeur (€)',
            'contributions': 'Versements (€)', 'years_held': 'Ancienneté (ans)',
        })
        table['Placement'] = table['Placement'].map(lambda p: labels.get(p, p))
        st.dataframe(table, use_container_width=True)
        to_remove = st.selectbox(
            "Retirer un avoir", range(len(holdings)),
            format_func=lambda k: f"{labels.get(holdings[k]['placement'])} "
                                  f"({holdings[k]['value']:,.0f} €)",
        )
        if st.button("🗑️ Retirer"):
            holdings.pop(to_remove)
            st.session_state.results = None
            st.rerun()
    else:
        st.info("Aucune épargne existante saisie.")

    with st.form("add_holding"):
        st.markdown("### Ajouter un avoir")
        placement = st.selectbox(
            "Placement", catalog.placement_ids, format_func=lambda p: labels[p]
        )
        value = st.number_input("Valeur actuelle (€)", 0.0, None, None, 1000.0)
        contributions = st.number_input("Versements cumulés (€)", 0.0, None, None, 1000.0)
        years_held = st.number_input(
            "Ancienneté de l'enveloppe (années)", 0.0, 100.0, None, 1.0
        )
        if st.form_submit_button("➕ Ajouter"):
            if None in (value, contributions, years_held):
                st.error("Renseignez la valeur, les versements et l'ancienneté.")
            else:
                holdings.append({'placement': placement, 'value': value,
                                 'contributions': contributions, 'years_held': years_held})
                st.session_state.results = None
                st.rerun()


def page_projection():
    """Calcul et résultats."""
    st.markdown("# 📊 Projection")
    form = st.session_state.form
    if form is None:
        st.warning("⚠️ Enregistrez d'abord votre profil.")
        if st.button("Aller au profil"):
            st.session_state.page = "Profile"
            st.rerun()
        return

    if st.button("🚀 Lancer la projection", type="primary"):
        with st.spinner("Calcul en cours..."):
            st.session_state.results = run_analysis(form)

    if st.session_state.results:
        display_results(st.session_state.results)


def display_results(results):
    """Afficher l'allocation, le patrimoine projeté et la frontière efficiente."""
    optimization = results['optimization']
    portfolio = optimization['optimal_portfolio']
    statistics = optimization['simulation_results']['statistics']

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rendement annualisé attendu", f"{portfolio['expected_return']:.2%}")
    col2.metric("Volatilité", f"{portfolio['expected_volatility']:.2%}")
    if portfolio['sharpe_ratio'] is not None:
        col3.metric("Ratio de Sharpe", f"{portfolio['sharpe_ratio']:.2f}")
    col4.metric(
        f"Patrimoine net médian à {portfolio['horizon']} ans",
        f"{statistics['median_terminal_wealth']:,.0f} €",
    )
    st.caption(
        f"Rendements nets de frais et d'impôts, annualisés sur {portfolio['horizon']} ans "
        f"(catalogue {portfolio['placement_catalog']}). Le patrimoine inclut l'épargne "
        "existante et est net de l'impôt de sortie."
    )

    st.markdown("### Répartition des nouveaux versements")
    catalog = load_placement_catalog(portfolio['placement_catalog'])
    weights = pd.DataFrame({
        'Placement': [catalog.placement(p)['label'] for p in portfolio['weights']],
        'Part': list(portfolio['weights'].values()),
    })
    st.dataframe(weights.style.format({'Part': '{:.1%}'}), use_container_width=True)
    st.caption(optimization['constraints_explanation'])

    frontier = optimization['efficient_frontier']
    if len(frontier) > 0:
        st.markdown("### Frontière efficiente")
        fig = px.scatter(
            frontier, x='volatility', y='return',
            labels={'volatility': 'Volatilité', 'return': 'Rendement attendu'},
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Limites connues du catalogue"):
        for gap in optimization['known_gaps']:
            st.markdown(f"- {gap}")


def run_analysis(form):
    """Lancer le calcul pour la saisie enregistrée ; afficher l'erreur s'il échoue."""
    profile_config = build_profile_config({**form, 'holdings': st.session_state.holdings})
    reference = st.session_state.get('risk_free_placement', 'Aucun')
    try:
        return run_projection(
            profile_config,
            num_scenarios=st.session_state.num_scenarios,
            catalog_id=st.session_state.catalog_id,
            risk_aversion=st.session_state.risk_aversion,
            risk_free_placement=None if reference == 'Aucun' else reference,
            couple=form['couple'],
        )
    except (ValueError, NotImplementedError) as error:
        st.error(f"Calcul impossible : {error}")
        return None


def main():
    """Point d'entrée de l'application."""
    init_session_state()
    render_sidebar()
    page = st.session_state.get('page', 'Home')
    if page == 'Profile':
        page_profile()
    elif page == 'Holdings':
        page_holdings()
    elif page == 'Projection':
        page_projection()
    else:
        page_home()


if __name__ == "__main__":
    main()

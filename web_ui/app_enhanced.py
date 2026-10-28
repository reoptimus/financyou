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
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from investment_calculator.placement_catalog import (
    list_placement_catalogs,
    load_placement_catalog,
)
from web_ui.pipeline import build_profile_config, build_projects, build_property, run_projection

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
    "🎯 Projets": "Projects",
    "🏡 Budget du foyer": "Budget",
    "🏢 Investissement locatif": "Rentals",
    "📊 Projection": "Projection",
}

RENTAL_LABELS = {
    'name': 'Bien', 'price': 'Coût total (€)', 'down_payment': 'Apport (€)',
    'loan_rate': 'Taux', 'loan_years': 'Durée', 'gross_yield': 'Rendement brut',
    'collected_share': 'Part encaissée', 'annual_charges': 'Charges (€)',
    'rent_growth': 'Évolution du loyer', 'purchase_year': 'Achat (année)',
    'market_value': 'Valeur hors frais (€)', 'value_growth': 'Évolution de la valeur',
}


def init_session_state():
    """Initialiser l'état de session."""
    defaults = {
        'form': None, 'holdings': [], 'projects': [], 'available_savings': None,
        'budget': None, 'loans': [], 'properties': [],
        'results': None, 'page': 'Home',
    }
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
        "3. **Projets** (facultatif) : les dépenses prévues, pour placer chaque euro "
        "jusqu'au projet qui l'utilisera.\n"
        "4. **Projection** : répartition des nouveaux versements et patrimoine projeté."
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


def page_projects():
    """Saisie des projets du foyer, au format du R : début, versements, durée, revente."""
    st.markdown("# 🎯 Projets")
    st.markdown(
        "Un projet est une dépense datée : un versement initial l'année de début, "
        "puis un versement chaque année pendant la durée, et une éventuelle revente "
        "en fin de projet, qui s'ajoute au dernier versement. L'argent d'un projet "
        "proche est placé à court terme, l'épargne de long terme à long terme."
    )
    projects = st.session_state.projects
    if projects:
        table = pd.DataFrame(projects).rename(columns={
            'name': 'Projet', 'start_year': 'Début (dans n ans)',
            'initial_payment': 'Versement initial (€)', 'annual_payment': 'Versement annuel (€)',
            'duration_years': 'Durée (ans)', 'resale': 'Revente (€)',
        })
        st.dataframe(table, use_container_width=True)
        to_remove = st.selectbox(
            "Retirer un projet", range(len(projects)),
            format_func=lambda k: projects[k]['name'],
        )
        if st.button("🗑️ Retirer le projet"):
            projects.pop(to_remove)
            st.session_state.results = None
            st.rerun()
    else:
        st.info("Aucun projet saisi : la projection place tout jusqu'à la retraite.")

    available = st.number_input(
        "Épargne déjà disponible pour financer ces projets (€)", 0.0, None,
        st.session_state.available_savings, 1000.0,
        help="Distincte de l'épargne existante, qui reste dans ses placements.",
    )
    if available != st.session_state.available_savings:
        st.session_state.available_savings = available
        st.session_state.results = None

    with st.form("add_project"):
        st.markdown("### Ajouter un projet")
        name = st.text_input("Nom du projet")
        col1, col2 = st.columns(2)
        with col1:
            start_year = st.number_input("Début, dans combien d'années", 0, 100, None, 1)
            initial_payment = st.number_input("Versement initial (€)", 0.0, None, None, 1000.0)
            annual_payment = st.number_input("Versement annuel (€)", 0.0, None, None, 500.0)
        with col2:
            duration_years = st.number_input("Durée des versements annuels (ans)", 0, 100, None, 1)
            resale = st.number_input("Revente en fin de projet (€)", 0.0, None, None, 1000.0)
        if st.form_submit_button("➕ Ajouter le projet"):
            row = {'name': name.strip(), 'start_year': start_year,
                   'initial_payment': initial_payment, 'annual_payment': annual_payment,
                   'duration_years': duration_years, 'resale': resale}
            if not row['name'] or None in row.values():
                st.error("Renseignez le nom et tous les montants (0 si sans objet).")
                return
            try:
                build_projects([row])
            except ValueError as error:
                st.error(str(error))
                return
            projects.append(row)
            st.session_state.results = None
            st.rerun()


def _percent(value):
    return None if value is None else value / 100


def _as_percent(value):
    return None if value is None else value * 100


def page_budget():
    """Budget du foyer, facultatif : son épargne libre remplace les versements du profil."""
    st.markdown("# 🏡 Budget du foyer")
    form = st.session_state.form
    if form is None:
        st.warning("⚠️ Enregistrez d'abord votre profil : l'épargne actuelle en vient.")
        return
    st.markdown(
        "Revenus, retraite, impôt, loyer et crédits, année par année. Les dépenses "
        "courantes se déduisent de votre épargne actuelle (profil). L'épargne libre "
        "de chaque année alimente alors le plan par tranches de vos projets."
    )
    loans = st.session_state.loans
    if loans:
        st.dataframe(pd.DataFrame(loans).rename(columns={
            'name': 'Crédit', 'annual_payment': 'Annuité (€)', 'rate': 'Taux',
            'years_left': 'Années restantes',
        }), use_container_width=True)
        if st.button("🗑️ Retirer le dernier crédit"):
            loans.pop()
            st.session_state.results = None
            st.rerun()
    with st.form("add_loan"):
        st.markdown("### Crédit en cours")
        name = st.text_input("Nom du crédit")
        payment = st.number_input("Annuité (€)", 0.0, None, None, 500.0)
        rate = st.number_input("Taux annuel (%)", 0.0, 30.0, None, 0.1)
        years_left = st.number_input("Annuités restantes", 0, 50, None, 1)
        if st.form_submit_button("➕ Ajouter le crédit"):
            if not name.strip() or None in (payment, rate, years_left):
                st.error("Renseignez le nom, l'annuité, le taux et la durée restante.")
            else:
                loans.append({'name': name.strip(), 'annual_payment': payment,
                              'rate': rate / 100, 'years_left': int(years_left)})
                st.session_state.results = None
                st.rerun()

    saved = st.session_state.budget or {}
    adults = 2 if form['couple'] else 1
    with st.form("budget_form"):
        earners = []
        for k in range(adults):
            st.markdown(f"### Adulte {k + 1}")
            prev = (saved.get('earners') or [{}] * adults)[k]
            col1, col2 = st.columns(2)
            with col1:
                income = st.number_input("Revenu imposable annuel (€)", 0.0, None,
                                         prev.get('taxable_income'), 1000.0, key=f"inc{k}")
                growth = st.number_input("Évolution annuelle (%)", -20.0, 20.0,
                                         _as_percent(prev.get('annual_growth')), 0.5,
                                         key=f"gro{k}")
            with col2:
                retire = st.number_input("Retraite dans (années), vide si après l'horizon",
                                         0, 60, prev.get('retirement_year'), 1,
                                         key=f"ret{k}")
                replacement = st.number_input(
                    "Taux de remplacement (%)", 0.0, 150.0,
                    _as_percent(prev.get('replacement_rate')), 5.0, key=f"rep{k}",
                )
            earners.append({'taxable_income': income, 'annual_growth': _percent(growth),
                            'retirement_year': retire, 'replacement_rate': _percent(replacement)})
        st.markdown("### Foyer")
        rent = st.number_input("Loyer annuel versé (€, 0 si propriétaire)", 0.0, None,
                               saved.get('rent'), 500.0)
        dependents = st.text_input(
            "Personnes à charge : nombre d'années à charge de chacune, séparées par des virgules"
        )
        follow = st.checkbox("Les dépenses suivent les revenus (sinon constantes)")
        submitted = st.form_submit_button("💾 Enregistrer le budget", type="primary")
    if submitted:
        if rent is None or any(e['taxable_income'] is None or e['annual_growth'] is None
                               for e in earners):
            st.error("Renseignez le revenu et son évolution pour chaque adulte, et le loyer.")
            return
        try:
            years = [int(x) for x in dependents.replace(" ", "").split(",") if x]
        except ValueError:
            st.error("Années à charge : saisissez des nombres entiers séparés par des virgules.")
            return
        st.session_state.budget = {
            'earners': earners, 'rent': rent, 'dependent_years': years,
            'expenses_follow_income': follow,
        }
        st.session_state.results = None
        st.success("✅ Budget enregistré.")
    if st.session_state.budget and st.button("Ne plus utiliser le budget"):
        st.session_state.budget = None
        st.session_state.results = None
        st.rerun()


def page_rentals():
    """Biens achetés à crédit pour être loués nus ; ils entrent dans le budget du foyer."""
    st.markdown("# 🏢 Investissement locatif")
    st.markdown(
        "Un bien acheté à crédit et loué nu : l'apport, les annuités, les loyers, les "
        "charges et l'impôt (micro-foncier) entrent dans le budget du foyer. Toutes les "
        "hypothèses sont les vôtres : aucune n'est proposée par défaut."
    )
    if st.session_state.budget is None:
        st.info("Ces biens ne comptent qu'avec un budget du foyer enregistré.")
    properties = st.session_state.properties
    if properties:
        st.dataframe(pd.DataFrame(properties).rename(columns=RENTAL_LABELS),
                     use_container_width=True)
        if st.button("🗑️ Retirer le dernier bien"):
            properties.pop()
            st.session_state.results = None
            st.rerun()
    with st.form("add_property"):
        name = st.text_input("Nom du bien")
        col1, col2 = st.columns(2)
        with col1:
            price = st.number_input("Coût total de l'achat, frais compris (€)", 0.0, None,
                                    None, 5000.0)
            market_value = st.number_input("Valeur du bien hors frais (€)", 0.0, None, None,
                                           5000.0)
            down = st.number_input("Apport (€)", 0.0, None, None, 5000.0)
            rate = st.number_input("Taux du crédit (%)", 0.0, 30.0, None, 0.1)
            years = st.number_input("Durée du crédit (années)", 0, 40, None, 1)
            purchase = st.number_input("Achat dans (années, 0 = cette année)", 0, 60, None, 1)
        with col2:
            gross_yield = st.number_input("Loyer annuel hors charges / coût total (%)",
                                          0.0, 30.0, None, 0.1)
            collected = st.number_input("Part du loyer encaissée (vacance, impayés) (%)",
                                        0.0, 100.0, None, 1.0)
            charges = st.number_input("Charges annuelles du propriétaire (€)", 0.0, None,
                                      None, 100.0)
            rent_growth = st.number_input("Évolution du loyer et des charges (%/an)",
                                          -20.0, 20.0, None, 0.1)
            value_growth = st.number_input("Évolution de la valeur du bien (%/an)",
                                           -20.0, 20.0, None, 0.1)
        submitted = st.form_submit_button("➕ Ajouter le bien")
    if submitted:
        values = (price, market_value, down, rate, years, purchase, gross_yield, collected,
                  charges, rent_growth, value_growth)
        if not name.strip() or None in values:
            st.error("Renseignez tous les champs : aucune hypothèse n'est prise à votre place.")
            return
        row = {
            'name': name.strip(), 'price': price, 'down_payment': down,
            'loan_rate': rate / 100, 'loan_years': int(years),
            'gross_yield': gross_yield / 100, 'collected_share': collected / 100,
            'annual_charges': charges, 'rent_growth': rent_growth / 100,
            'purchase_year': int(purchase), 'market_value': market_value,
            'value_growth': value_growth / 100,
        }
        try:
            build_property(row)
        except ValueError as exc:
            st.error(str(exc))
            return
        properties.append(row)
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

    waterfall = optimization.get('wealth_waterfall')
    if waterfall is not None:
        st.markdown("### Du capital de départ au patrimoine net")
        steps = waterfall.as_steps()
        fig = go.Figure(go.Waterfall(
            x=[label for label, _ in steps] + ["Patrimoine net"],
            y=[amount for _, amount in steps] + [waterfall.net_wealth],
            measure=["relative"] * len(steps) + ["total"],
        ))
        fig.update_layout(yaxis_title="€, moyenne sur les scénarios", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Chaque coût est l'écart entre deux projections, avec et sans lui : il "
            "compte aussi ce que l'argent prélevé aurait rapporté jusqu'à l'horizon."
        )

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

    if 'budget' in results:
        display_budget(results['budget'])

    if 'tranche_plan' in results:
        display_tranche_plan(results['tranche_plan'], catalog)


def display_budget(budget):
    """Afficher le budget du foyer et son épargne libre."""
    st.markdown("### Budget du foyer")
    table = budget['table'].rename(columns={
        'salaries': 'Revenus d\'activité', 'pensions': 'Pensions', 'income_tax': 'Impôt',
        'rent': 'Loyer', 'loan_payments': 'Annuités', 'expenses': 'Dépenses',
        'rental_income': 'Loyers encaissés', 'property_charges': 'Charges des biens',
        'rental_social_tax': 'Prélèvements sociaux (loyers)', 'down_payments': 'Apports',
        'property_equity': 'Valeur nette des biens', 'free_savings': 'Épargne libre',
    })
    st.line_chart(table['Épargne libre'])
    if 'Valeur nette des biens' in table:
        st.markdown("Valeur nette des biens loués (valeur moins capital restant dû, "
                    "avant frais et impôt de revente)")
        st.line_chart(table['Valeur nette des biens'])
    st.dataframe(table.style.format('{:,.0f}'), use_container_width=True)
    with st.expander("Limites connues du budget"):
        for gap in budget['known_gaps']:
            st.markdown(f"- {gap}")


def display_tranche_plan(plan, catalog):
    """Afficher le plan par tranches : capital, euros par placement, poids par horizon."""
    st.markdown("### Plan par tranches, avec vos projets")
    labels = {pid: catalog.placement(pid)['label'] for pid in catalog.placement_ids}
    amounts = plan['amounts'].rename(columns=labels)
    long_form = amounts.reset_index().melt(
        id_vars='year', var_name='Placement', value_name='Montant (€)'
    )
    fig = px.area(long_form, x='year', y='Montant (€)', color='Placement',
                  labels={'year': 'Année'})
    st.plotly_chart(fig, use_container_width=True)
    if plan['unplaced'].any():
        st.caption(
            f"{plan['unplaced'].max():,.0f} € n'arrivent qu'à l'horizon et ne sont pas placés."
        )
    st.markdown("Répartition optimale selon la durée de placement (années)")
    weights = plan['weights_by_horizon'].rename(index=labels)
    st.dataframe(weights.style.format('{:.1%}'), use_container_width=True)
    with st.expander("Limites connues du plan par tranches"):
        for gap in plan['known_gaps']:
            st.markdown(f"- {gap}")


def _budget_with_loans():
    budget = st.session_state.budget
    if budget is None:
        return None
    return {**budget, 'loans': st.session_state.loans,
            'properties': st.session_state.properties}


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
            projects=build_projects(st.session_state.projects),
            available_savings=st.session_state.available_savings,
            budget=_budget_with_loans(),
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
    elif page == 'Projects':
        page_projects()
    elif page == 'Budget':
        page_budget()
    elif page == 'Rentals':
        page_rentals()
    elif page == 'Projection':
        page_projection()
    else:
        page_home()


if __name__ == "__main__":
    main()

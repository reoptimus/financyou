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
from plotly.colors import sample_colorscale

sys.path.insert(0, str(Path(__file__).parent.parent))

from investment_calculator.placement_catalog import (
    list_placement_catalogs,
    load_placement_catalog,
)
from web_ui.pipeline import (
    build_home,
    build_profile_config,
    build_projects,
    build_property,
    dependent_years_from_ages,
    future_children,
    run_projection,
    tranche_label,
    work_changes_by_earner,
)
from web_ui.project_templates import FIELD_KINDS, TEMPLATES, project_row
from web_ui.saved_inputs import dump_inputs, load_inputs

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
    'market_value': 'Valeur hors frais (€)', 'landlord_status': 'Bailleur privé',
    'housing_type': 'Logement',
}


def init_session_state():
    """Initialiser l'état de session."""
    defaults = {
        'form': None, 'holdings': [], 'projects': [], 'available_savings': None,
        'budget': None, 'loans': [], 'properties': [], 'work_changes': [],
        'rental_regime': 'micro_foncier', 'results': None, 'page': 'Home',
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
        render_saved_inputs()


def render_saved_inputs():
    """Télécharger la saisie dans un fichier, ou la recharger."""
    st.markdown("---")
    st.markdown("### 💾 Votre saisie")
    st.download_button(
        "Télécharger ma saisie", dump_inputs(st.session_state),
        file_name="financyou-saisie.json", mime="application/json",
        use_container_width=True,
    )
    uploaded = st.file_uploader("Recharger une saisie", type="json", key="saved_upload")
    if uploaded is not None and st.button("Remplacer ma saisie par ce fichier",
                                          use_container_width=True):
        try:
            inputs = load_inputs(uploaded.getvalue())
        except ValueError as error:
            st.error(str(error))
            return
        # Les questions du logement gardent sinon la réponse de la saisie remplacée.
        for key in [k for k in st.session_state if str(k).startswith('home_')]:
            del st.session_state[key]
        st.session_state.update(inputs)
        st.session_state.results = None
        st.success("✅ Saisie rechargée.")
    st.caption("Rien n'est conservé par FinancYou : gardez ce fichier pour reprendre plus tard.")


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
                "Épargne mensuelle (€)", 0.0, None, saved.get('monthly_amount'), 50.0,
                help="Somme que vous épargnez en moyenne chaque mois, hors remboursement "
                     "de crédits immobiliers.",
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

    render_work_changes()

    st.markdown("### Ajouter un projet")
    template_id = st.selectbox(
        "Type de projet", list(TEMPLATES), format_func=lambda t: TEMPLATES[t].label,
        key="project_template",
    )
    template = TEMPLATES[template_id]
    st.caption(template.description)
    st.caption("Pour un bien acheté pour être loué, utilisez la page Investissement locatif.")
    with st.form("add_project"):
        name = st.text_input("Nom du projet")
        values = {}
        columns = st.columns(2)
        first_column = (len(template.fields) + 1) // 2
        for k, field in enumerate(template.fields):
            low, high, step, whole = FIELD_KINDS[field.kind]
            with columns[0 if k < first_column else 1]:
                values[field.key] = st.number_input(
                    field.label,
                    int(low) if whole else low,
                    None if high is None else (int(high) if whole else high),
                    None, int(step) if whole else step,
                    key=f"project_{template_id}_{field.key}",
                )
        if st.form_submit_button("➕ Ajouter le projet"):
            try:
                row = project_row(template_id, name, values)
                build_projects([row])
            except ValueError as error:
                st.error(str(error))
                return
            projects.append(row)
            st.session_state.results = None
            st.rerun()


def render_work_changes():
    """Temps partiels et congés : ils réduisent le salaire d'un adulte dans le budget."""
    st.markdown("### Temps partiel ou congé")
    st.caption(
        "Le salaire de l'adulte est multiplié par la part travaillée pendant la "
        "période. La pension de retraite et les allocations (congé parental, "
        "chômage) ne sont pas modifiées."
    )
    changes = st.session_state.work_changes
    if changes:
        st.dataframe(pd.DataFrame(changes).assign(
            earner=lambda t: t['earner'] + 1, worked_share=lambda t: t['worked_share'] * 100,
        ).rename(columns={
            'name': 'Projet', 'earner': 'Adulte', 'start_year': 'Début (dans n ans)',
            'years': 'Durée (ans)', 'worked_share': 'Part travaillée (%)',
        }), use_container_width=True)
        if st.button("🗑️ Retirer le dernier temps partiel ou congé"):
            changes.pop()
            st.session_state.results = None
            st.rerun()
    if st.session_state.budget is None:
        st.info("Un temps partiel ou un congé agit sur les revenus : remplissez d'abord "
                "la page Budget du foyer.")
        return
    adults = len(st.session_state.budget['earners'])
    with st.form("add_work_change"):
        name = st.text_input("Nom (temps partiel, congé parental, année sabbatique…)",
                             key="work_name")
        col1, col2 = st.columns(2)
        earner = col1.selectbox("Adulte concerné", range(adults),
                                format_func=lambda k: f"Adulte {k + 1}", key="work_earner")
        start = col1.number_input("Début, dans combien d'années", 0, 100, None, 1,
                                  key="work_start")
        years = col2.number_input("Durée (ans)", 1, 100, None, 1, key="work_years")
        share = col2.number_input(
            "Part travaillée (%)", 0.0, 100.0, None, 10.0, key="work_share",
            help="80 pour un temps partiel à 80 %, 0 pour un congé sans solde.",
        )
        if st.form_submit_button("➕ Ajouter le temps partiel ou le congé"):
            if not name.strip() or None in (start, years, share):
                st.error("Renseignez le nom, le début, la durée et la part travaillée.")
                return
            row = {'name': name.strip(), 'earner': int(earner), 'start_year': int(start),
                   'years': int(years), 'worked_share': share / 100}
            try:
                work_changes_by_earner([row], adults)
            except ValueError as error:
                st.error(str(error))
                return
            changes.append(row)
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
        st.markdown("### Autres crédits en cours")
        st.caption("Le crédit de votre résidence principale se saisit dans « Votre logement ».")
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
    home_answers = render_home_questions(saved.get('home'), saved.get('rent'))
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
                                         key=f"ret{k}",
                                         help="Nombre d'années avant la retraite à taux plein.")
                replacement = st.number_input(
                    "Taux de remplacement (%)", 0.0, 150.0,
                    _as_percent(prev.get('replacement_rate')), 5.0, key=f"rep{k}",
                    help="Pension de retraite rapportée au dernier revenu d'activité. "
                         "Votre relevé de carrière (info-retraite.fr) permet de l'estimer.",
                )
            earners.append({'taxable_income': income, 'annual_growth': _percent(growth),
                            'retirement_year': retire, 'replacement_rate': _percent(replacement)})
        st.markdown("### Foyer")
        col1, col2 = st.columns(2)
        children = col1.text_input(
            "Âge de chaque enfant à charge, séparés par des virgules (vide si aucun)",
            ", ".join(str(a) for a in saved.get('children_ages', [])),
            help="Les enfants à charge au titre de votre impôt : ils donnent les parts "
                 "du quotient familial.",
        )
        end_age = col2.number_input(
            "Âge auquel ils cesseront d'être à votre charge", 0, 40,
            saved.get('children_end_age'), 1,
            help="Il dépend de votre foyer : études, rattachement au foyer fiscal.",
        )
        col1, col2 = st.columns(2)
        arrivals = col1.text_input(
            "Naissances ou adoptions à venir : dans combien d'années, séparées par des "
            "virgules (vide si aucune)",
            ", ".join(str(c['arrival_year']) for c in saved.get('future_children', [])),
            help="Chaque enfant à venir compte une part fiscale de plus et augmente les "
                 "dépenses, de son arrivée jusqu'à l'âge de fin de charge ci-dessus. "
                 "Un enfant déjà né se saisit par son âge.",
        )
        childcare = col2.number_input(
            "Frais de garde annuels d'un enfant de moins de 6 ans (€, vide si aucun)",
            0.0, None, saved.get('childcare_cost'), 100.0,
            help="Crèche, assistante maternelle, garderie : ils ouvrent un crédit d'impôt "
                 "pour chaque enfant de moins de 6 ans, aujourd'hui ou à venir.",
        )
        col2.caption(
            "Les dépenses suivent la composition du foyer, selon l'échelle de l'Insee : "
            "1 unité pour le premier adulte, 0,5 pour toute autre personne de 14 ans ou "
            "plus, 0,3 pour un enfant de moins de 14 ans. Un enfant coûte donc davantage "
            "en grandissant, et plus rien une fois sorti de votre charge."
        )
        follow = st.checkbox(
            "Les dépenses suivent les revenus (sinon constantes)",
            help="Votre niveau de vie, donc votre consommation, suivra-t-il l'évolution "
                 "de vos revenus ?",
        )
        submitted = st.form_submit_button("💾 Enregistrer le budget", type="primary")
    if submitted:
        if any(e['taxable_income'] is None or e['annual_growth'] is None for e in earners):
            st.error("Renseignez le revenu et son évolution pour chaque adulte.")
            return
        try:
            rent, home = build_home(home_answers)
        except ValueError as error:
            st.error(str(error))
            return
        try:
            ages = [int(x) for x in children.replace(" ", "").split(",") if x]
        except ValueError:
            st.error("Âges des enfants : saisissez des nombres entiers séparés par des virgules.")
            return
        try:
            years = dependent_years_from_ages(ages, end_age)
            try:
                arrival_years = [int(x) for x in arrivals.replace(" ", "").split(",") if x]
            except ValueError:
                raise ValueError("Enfants à venir : saisissez des nombres d'années entiers "
                                 "séparés par des virgules.") from None
            coming = future_children(arrival_years, end_age)
        except ValueError as error:
            st.error(str(error))
            return
        st.session_state.budget = {
            'earners': earners, 'rent': rent, 'home': home, 'dependent_years': years,
            'children_ages': ages, 'children_end_age': end_age,
            'future_children': coming, 'childcare_cost': childcare,
            'expenses_follow_income': follow,
        }
        st.session_state.results = None
        st.success("✅ Budget enregistré.")
    if st.session_state.budget and st.button("Ne plus utiliser le budget"):
        st.session_state.budget = None
        st.session_state.results = None
        st.rerun()


def render_home_questions(home, rent):
    """
    Questions « Votre logement » des prototypes R : locataire ou propriétaire,
    puis loyer, ou valeur du bien et crédit en cours. Hors du formulaire, pour
    que les questions suivent la réponse précédente.
    """
    st.markdown("### Votre logement")
    home = home or {}
    statuses = {'tenant': "Locataire", 'owner': "Propriétaire"}
    previous = None if not home else ('owner' if home.get('owner') else 'tenant')
    status = st.radio(
        "Êtes-vous propriétaire de votre logement ?", list(statuses),
        index=None if previous is None else list(statuses).index(previous),
        format_func=statuses.get, horizontal=True, key="home_status",
    )
    answers = {'status': status}
    if status == 'tenant':
        answers['monthly_rent'] = st.number_input(
            "Loyer mensuel, charges comprises (€)", 0.0, None,
            None if not rent else rent / 12, 10.0, key="home_rent",
            help="Montant mensuel de votre loyer, toutes charges comprises.",
        )
    elif status == 'owner':
        loan = home.get('loan') or {}
        answers['value'] = st.number_input(
            "Valeur de votre bien : prix net vendeur estimé (€)", 0.0, None,
            home.get('value'), 5000.0, key="home_value",
            help="Votre patrimoine compte cette valeur, moins le capital restant dû.",
        )
        paid = st.radio(
            "Avez-vous fini de le payer ?", [True, False],
            index=None if not home.get('owner') else (0 if home.get('loan') is None else 1),
            format_func=lambda v: "Oui" if v else "Non", horizontal=True, key="home_paid",
        )
        answers['paid'] = paid
        if paid is False:
            st.caption(
                "Le détail du crédit permet d'estimer le patrimoine réellement possédé "
                "aujourd'hui, net du capital encore dû, et vos engagements à venir."
            )
            col1, col2, col3 = st.columns(3)
            answers['monthly_payment'] = col1.number_input(
                "Mensualité du crédit (€)", 0.0, None,
                None if not loan else loan['annual_payment'] / 12, 10.0, key="home_payment",
            )
            answers['rate'] = col2.number_input(
                "Taux du crédit (%)", 0.0, 30.0, _as_percent(loan.get('rate')), 0.1,
                key="home_rate",
            )
            answers['years_left'] = col3.number_input(
                "Années restantes", 0, 50, loan.get('years_left'), 1, key="home_years",
            )
    return answers


def page_rentals():
    """Biens achetés à crédit pour être loués nus ; ils entrent dans le budget du foyer."""
    st.markdown("# 🏢 Investissement locatif")
    st.markdown(
        "Un bien acheté à crédit et loué nu : l'apport, les annuités, les loyers, les "
        "charges et l'impôt entrent dans le budget du foyer. Les "
        "hypothèses du bien sont les vôtres, sans valeur par défaut ; sa valeur suit "
        "ensuite les scénarios immobiliers du GSE."
    )
    if st.session_state.budget is None:
        st.info("Ces biens ne comptent qu'avec un budget du foyer enregistré.")
    regimes = {'micro_foncier': "Micro-foncier (abattement forfaitaire)",
               'real_regime': "Régime réel (charges et intérêts déduits, déficit foncier)"}
    chosen = st.radio(
        "Imposition des loyers", list(regimes), format_func=regimes.get,
        index=list(regimes).index(st.session_state.rental_regime), horizontal=True,
        help="Au micro-foncier, un abattement forfaitaire remplace les charges, sous un "
             "plafond de loyers. Au régime réel, charges et intérêts se déduisent ; un "
             "déficit s'impute en partie sur le revenu global.",
    )
    if chosen != st.session_state.rental_regime:
        st.session_state.rental_regime = chosen
        st.session_state.results = None
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
        statuses = {None: "Aucun", 'intermediate': "Loyer intermédiaire",
                    'social': "Loyer social", 'very_social': "Loyer très social"}
        status = col1.selectbox(
            "Statut du bailleur privé (dispositif Jeanbrun)", list(statuses),
            format_func=statuses.get, key="landlord_status",
            help="Location nue à loyer encadré, 9 ans, achat jusqu'en 2028 : une part du "
                 "prix s'amortit chaque année, au régime réel. Les plafonds de loyers et de "
                 "ressources des locataires ne sont pas vérifiés ici.",
        )
        housing = col2.selectbox(
            "Type de logement", ['new', 'renovated_old'], key="housing_type",
            format_func={'new': "Neuf", 'renovated_old': "Ancien rénové (travaux ≥ 30 %)"}.get,
        )
        submitted = st.form_submit_button("➕ Ajouter le bien")
    if submitted:
        values = (price, market_value, down, rate, years, purchase, gross_yield, collected,
                  charges, rent_growth)
        if not name.strip() or None in values:
            st.error("Renseignez tous les champs : aucune hypothèse n'est prise à votre place.")
            return
        row = {
            'name': name.strip(), 'price': price, 'down_payment': down,
            'loan_rate': rate / 100, 'loan_years': int(years),
            'gross_yield': gross_yield / 100, 'collected_share': collected / 100,
            'annual_charges': charges, 'rent_growth': rent_growth / 100,
            'purchase_year': int(purchase), 'market_value': market_value,
            'landlord_status': status, 'housing_type': housing,
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

    horizon = portfolio['horizon']
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rendement annualisé attendu", f"{portfolio['expected_return']:.2%}")
    # L'écart-type est pris entre scénarios sur le rendement annualisé à H ans : il
    # vaut environ σ_annuel / √H et ne se compare pas à une volatilité annuelle.
    col2.metric(
        f"Dispersion du rendement annualisé à {horizon} ans",
        f"{portfolio['expected_volatility']:.2%}",
        help=(
            f"Écart-type, entre scénarios, du rendement net annualisé sur {horizon} ans. "
            "Ce n'est pas une volatilité annuelle : sur un long horizon, les bonnes et "
            f"mauvaises années se compensent, et ce chiffre est environ √{horizon} fois "
            "plus petit que la volatilité annuelle du même portefeuille."
        ),
    )
    if portfolio['sharpe_ratio'] is not None:
        col3.metric(
            f"Ratio de Sharpe à {horizon} ans",
            f"{portfolio['sharpe_ratio']:.2f}",
            help=(
                "Rendement annualisé en excès du placement de référence, divisé par la "
                f"dispersion à {horizon} ans. Calculé sur cette dispersion et non sur la "
                "volatilité annuelle, il ne se compare pas aux ratios de Sharpe usuels, "
                f"environ √{horizon} fois plus faibles."
            ),
        )
    col4.metric(
        f"Patrimoine net médian à {portfolio['horizon']} ans",
        f"{statistics['median_terminal_wealth']:,.0f} €",
    )
    envelope = portfolio.get('envelope_value')
    if envelope is not None and envelope['value'] is not None:
        st.metric(
            "Valeur des enveloppes",
            f"{envelope['value'] * 1e4:+.0f} pb par an",
            help=(
                "Équivalent certain de l'allocation avec toutes les enveloppes, moins "
                f"celui de la meilleure allocation limitée au {envelope['reference_wrapper']}."
            ),
        )
    elif envelope is not None:
        st.caption(f"Valeur des enveloppes non calculée : {envelope['reason']}")
    st.caption(
        f"Rendements nets de frais et d'impôts, annualisés sur {portfolio['horizon']} ans "
        f"(catalogue {portfolio['placement_catalog']}). Le patrimoine inclut l'épargne "
        "existante et est net de l'impôt de sortie."
    )

    if 'capital_timeline' in results:
        display_capital_timeline(results['capital_timeline'], st.session_state.available_savings)

    st.markdown("### Patrimoine par niveau de probabilité, hors projets")
    bands = results.get('wealth_bands')
    if bands is not None:
        st.line_chart(bands.rename(columns={
            'p5': '5 %', 'p10': '10 %', 'p50': 'Médiane', 'p90': '90 %', 'p95': '95 %',
        }))
        st.caption(
            "La courbe 10 % se lit : une chance sur dix d'être en dessous. Patrimoine "
            "avant impôt de sortie, épargne existante comprise, sans vos projets ; "
            "le plan avec projets n'est pas encore simulé scénario par scénario."
        )

    st.markdown("### Répartition des nouveaux versements")
    catalog = load_placement_catalog(portfolio['placement_catalog'])
    weights = pd.DataFrame({
        'Placement': [catalog.placement(p)['label'] for p in portfolio['weights']],
        'Part': list(portfolio['weights'].values()),
    })
    st.dataframe(weights.style.format({'Part': '{:.1%}'}), use_container_width=True)
    st.caption(optimization['constraints_explanation'])
    for placement_id, reason in optimization.get('excluded_placements', {}).items():
        st.info(f"{catalog.placement(placement_id)['label']} : {reason} "
                "Saisissez le budget du foyer pour le proposer.")

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
            labels={
                'volatility': f"Dispersion du rendement annualisé à {portfolio['horizon']} ans",
                'return': 'Rendement attendu',
            },
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Limites connues du catalogue"):
        for gap in optimization['known_gaps']:
            st.markdown(f"- {gap}")

    if 'budget' in results:
        display_budget(results['budget'])

    if 'tranche_plan' in results:
        display_tranche_plan(results['tranche_plan'], catalog)


def display_capital_timeline(timeline, available_savings):
    """
    Chronologie du capital constitué : le stock d'euros que les flux certains
    (épargne, projets) accumulent, découpé en tranches horizontales pour
    l'optimisation. Sans rendement ni scénario économique.
    """
    st.markdown("### Chronologie du capital constitué")
    capital = timeline['capital']
    fig = go.Figure()
    layers = timeline['layers']
    if layers is not None:
        longest = max(1, max(t.duration for t in timeline['tranches']))
        shown = set()
        for k, tranche in enumerate(timeline['tranches']):
            # Une couleur par durée de placement : clair pour le court terme,
            # foncé pour le long terme ; une entrée de légende par durée.
            group = (f"Placée {tranche.duration} an(s)" if tranche.duration > 0
                     else "Arrive à l'horizon, non placée")
            color = sample_colorscale('Viridis', 1 - tranche.duration / longest)[0]
            fig.add_bar(x=capital.index, y=layers[k], name=group, legendgroup=group,
                        showlegend=group not in shown, marker_color=color,
                        legendrank=longest - tranche.duration,
                        hovertemplate="%{y:,.0f} €<extra>" + tranche_label(tranche) + "</extra>")
            shown.add(group)
    fig.add_scatter(x=capital.index, y=capital, mode='lines+markers', name="Capital constitué",
                    line={'color': '#d62728', 'width': 3})
    fig.update_layout(barmode='stack', bargap=0.05, xaxis_title="Année",
                      yaxis_title="€", legend={'orientation': 'h', 'y': -0.25})
    st.plotly_chart(fig, use_container_width=True)
    start = ("l'épargne déjà disponible saisie" if available_savings is not None
             else "0 € d'épargne déjà disponible (non saisie, page Projets)")
    st.caption(
        "Évolution certaine des flux, en euros : l'épargne versée chaque année s'ajoute, "
        "les projets payés se retranchent, sans rendement ni scénario économique. Chaque "
        "bande est une tranche de cette courbe, découpée horizontalement : elle est placée "
        f"à l'horizon de sa durée. La courbe part de {start}."
    )
    if timeline['reason'] is not None:
        st.warning(f"La courbe ne se découpe pas en tranches : {timeline['reason']}")


def display_budget(budget):
    """Afficher le budget du foyer et son épargne libre."""
    st.markdown("### Budget du foyer")
    table = budget['table'].rename(columns={
        'salaries': 'Revenus d\'activité', 'pensions': 'Pensions', 'income_tax': 'Impôt',
        'rent': 'Loyer', 'loan_payments': 'Annuités', 'expenses': 'Dépenses',
        'rental_income': 'Loyers encaissés', 'property_charges': 'Charges des biens',
        'rental_social_tax': 'Prélèvements sociaux (loyers)', 'down_payments': 'Apports',
        'free_savings': 'Épargne libre',
    })
    indicators = budget.get('indicators')
    if indicators is not None:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Revenus sur l'horizon", f"{indicators['total_income']:,.0f} €")
        col2.metric("Impôts sur l'horizon", f"{indicators['total_income_tax']:,.0f} €",
                    help="Impôt sur le revenu et prélèvements sociaux sur les loyers.")
        if indicators['max_debt_ratio'] is not None:
            col3.metric("Taux d'endettement maximal", f"{indicators['max_debt_ratio']:.1%}",
                        help="Loyer et annuités rapportés aux revenus d'activité et pensions.")
        else:
            col3.caption(f"Taux d'endettement non calculé : {indicators['debt_ratio_reason']}.")
        col4.metric("Épargne libre minimale", f"{indicators['min_free_savings']:,.0f} €",
                    help=f"Atteinte l'année {indicators['min_free_savings_year']}. "
                         "Négative, le foyer puise dans son capital.")
    st.line_chart(table['Épargne libre'])
    st.caption(
        "L'épargne libre est la part de vos revenus que vous mettez de côté chaque "
        "année, une fois payés l'impôt, le loyer, les crédits et les dépenses courantes. "
        "Négative, vos revenus ne couvrent pas vos dépenses : elle est prise sur votre "
        "épargne."
    )
    if 'property_equity' in budget:
        st.markdown("Valeur nette des biens loués selon les scénarios immobiliers : valeur "
                    "moins capital restant dû, avant frais et impôt de revente")
        st.line_chart(budget['property_equity'].rename(columns={
            'p5': '5 % des scénarios', 'median': 'Médiane', 'p95': '95 % des scénarios',
        }))
    if 'home_equity' in budget:
        st.markdown("Valeur nette de votre résidence principale selon les scénarios "
                    "immobiliers : valeur moins capital restant dû, avant frais de revente")
        st.line_chart(budget['home_equity'].rename(columns={
            'p5': '5 % des scénarios', 'median': 'Médiane', 'p95': '95 % des scénarios',
        }))
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
    capital = plan['capital']
    low = min(range(len(capital)), key=capital.__getitem__)
    st.caption(
        f"Épargne cumulée avec vos projets, hors rendement : au plus bas, "
        f"{capital[low]:,.0f} € l'année {low}."
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
            'properties': st.session_state.properties,
            'work_changes': st.session_state.work_changes,
            'rental_regime': st.session_state.rental_regime}


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

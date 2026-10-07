"""
Module 4: Portfolio Optimization (MOCA)

This module optimizes portfolio allocation and simulates investment outcomes across scenarios.

INPUT STRUCTURE:
{
    'scenarios': pd.DataFrame,          # After-tax scenarios from Module 2
    'user_constraints': dict,           # From Module 3 validated profile
    'investment_time_series': pd.DataFrame,  # From Module 3
    'optimization_objective': str,      # 'max_return', 'max_sharpe', 'min_volatility',
                                       # 'min_cvar', 'risk_parity', 'target_return'
    'optimization_params': {
        'target_return': float,
        'risk_aversion': float,
        'confidence_level': float,
        'min_weight': float,
        'max_weight': float,
        'transaction_costs': dict,
        'rebalancing_threshold': float
    },
    'asset_universe': dict
}

OUTPUT STRUCTURE:
{
    'optimal_portfolio': dict,
    'efficient_frontier': pd.DataFrame,
    'simulation_results': dict,         # includes 'rebalancing_schedule'
    'sensitivity_analysis': dict,
    'goal_analysis': dict
}
"""

import logging
import time
from enum import Enum

import numpy as np
import pandas as pd
from scipy.optimize import minimize

# Journalisation : logger nommé d'après le module, il hérite donc de la
# configuration posée par investment_calculator.logging_config.configure_logging().
logger = logging.getLogger(__name__)


class OptimizationObjective(Enum):
    """Portfolio optimization objectives"""
    MAX_RETURN = "max_return"
    MAX_SHARPE = "max_sharpe"
    MIN_VOLATILITY = "min_volatility"
    MIN_CVAR = "min_cvar"
    RISK_PARITY = "risk_parity"
    TARGET_RETURN = "target_return"
    EQUAL_WEIGHT = "equal_weight"


class PortfolioOptimizer:
    """
    Portfolio Optimization Engine (MOCA) - Module 4

    Optimizes portfolio allocation and simulates outcomes across scenarios.

    Example:
        >>> from investment_calculator.modules import optimizer
        >>> config = {
        ...     'scenarios': after_tax_scenarios_df,
        ...     'user_constraints': profile['constraints'],
        ...     'investment_time_series': time_series_df,
        ...     'optimization_objective': 'max_sharpe'
        ... }
        >>> opt = optimizer.PortfolioOptimizer()
        >>> results = opt.optimize(config)
        >>> print(results['optimal_portfolio'])
    """

    def __init__(self) -> None:
        """Initialize the Portfolio Optimizer."""
        pass

    def optimize(self, config: dict) -> dict:
        """
        Optimize portfolio and run simulations.

        Args:
            config: Configuration dictionary (see module docstring)

        Returns:
            Dictionary with optimal portfolio, simulations, and analysis
        """
        # Chronomètre pour tracer la durée totale de l'optimisation.
        start_time = time.perf_counter()

        # Validate configuration
        validated_config = self._validate_config(config)

        scenarios_df = validated_config['scenarios']
        objective = validated_config['optimization_objective']
        params = validated_config['optimization_params']
        constraints = validated_config['user_constraints']

        logger.info(
            "Début de l'optimisation de portefeuille (objectif=%s, %d lignes de scénarios)",
            objective,
            len(scenarios_df),
        )

        # Extract returns for optimization
        asset_returns = self._extract_asset_returns(scenarios_df)
        risk_free_rate = self._risk_free_rate(scenarios_df)

        # Run optimization
        optimal_portfolio = self._run_optimization(
            asset_returns,
            objective,
            params,
            constraints,
            risk_free_rate
        )

        # Generate efficient frontier
        efficient_frontier = self._generate_efficient_frontier(
            asset_returns,
            constraints,
            params,
            risk_free_rate
        )

        # Run simulations
        simulation_results = self._run_simulations(
            scenarios_df,
            asset_returns,
            optimal_portfolio,
            validated_config['investment_time_series'],
            params
        )

        # Sensitivity analysis
        sensitivity_analysis = self._sensitivity_analysis(
            asset_returns,
            optimal_portfolio,
            params
        )

        # Goal analysis
        goal_analysis = self._analyze_goals(
            simulation_results,
            validated_config.get('goal_amount', None)
        )

        logger.info(
            "Fin de l'optimisation (objectif=%s) en %.3f s : rendement attendu=%.4f, "
            "volatilité=%.4f, ratio de Sharpe=%.4f, %d points sur la frontière efficiente",
            objective,
            time.perf_counter() - start_time,
            optimal_portfolio['expected_return'],
            optimal_portfolio['expected_volatility'],
            optimal_portfolio['sharpe_ratio'],
            len(efficient_frontier),
        )

        return {
            'optimal_portfolio': optimal_portfolio,
            'efficient_frontier': efficient_frontier,
            'simulation_results': simulation_results,
            'sensitivity_analysis': sensitivity_analysis,
            'goal_analysis': goal_analysis
        }

    def _validate_config(self, config: dict) -> dict:
        """
        Validate and complete configuration.

        Args:
            config: User configuration

        Returns:
            Validated configuration
        """
        if 'scenarios' not in config:
            raise ValueError("Missing required field: scenarios")

        validated = {
            'scenarios': config['scenarios'],
            'user_constraints': config.get('user_constraints', {}),
            'investment_time_series': config.get('investment_time_series', pd.DataFrame()),
            'optimization_objective': config.get('optimization_objective', 'max_sharpe'),
            'asset_universe': config.get('asset_universe', {}),
            'goal_amount': config.get('goal_amount', None)
        }

        # Default optimization parameters
        default_params = {
            'target_return': 0.08,
            'risk_aversion': 5.0,
            'confidence_level': 0.95,
            'min_weight': 0.0,
            'max_weight': 1.0,
            'transaction_costs': {
                'stocks': 0.001,
                'bonds': 0.0005,
                'real_estate': 0.002
            },
            'rebalancing_threshold': 0.05
        }

        user_params = config.get('optimization_params', {})
        validated['optimization_params'] = {**default_params, **user_params}

        return validated

    def _extract_asset_returns(self, scenarios_df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract periodic asset returns from scenarios DataFrame.

        Chaque ligne est un couple (scénario, période) : les moments sont estimés
        sur les rendements **périodiques**. Moyenner d'abord les pas de temps de
        chaque scénario, comme le faisait l'ancienne version, divisait la
        volatilité par environ √(nombre de périodes) et faisait de la frontière
        efficiente un artefact des hypothèses de dérive.

        Args:
            scenarios_df: Scenarios with after-tax returns

        Returns:
            DataFrame of periodic asset returns, indexé par (scenario_id,
            time_period) quand ces colonnes existent, une colonne par actif

        Raises:
            ValueError: si le pas de temps des scénarios n'est pas annuel
        """
        # Identify return columns (after_tax versions if available)
        return_columns = []
        asset_names = []

        for col in scenarios_df.columns:
            if 'return' in col.lower() and 'after_tax' in col.lower():
                return_columns.append(col)
                # Extract asset name
                asset_name = col.replace('_after_tax', '').replace('_return', '')
                asset_names.append(asset_name)

        if not return_columns:
            # Fallback to pre-tax returns
            for col in scenarios_df.columns:
                excluded = ['interest_rate', 'inflation', 'gdp_growth']
                if 'return' in col.lower() and col not in excluded:
                    return_columns.append(col)
                    asset_name = col.replace('_return', '')
                    asset_names.append(asset_name)

        self._check_annual_timestep(scenarios_df)

        index_columns = [c for c in ('scenario_id', 'time_period') if c in scenarios_df.columns]
        periodic_returns = scenarios_df[index_columns + return_columns].copy()
        if index_columns:
            periodic_returns = periodic_returns.set_index(index_columns)
        periodic_returns.columns = asset_names

        return periodic_returns

    @staticmethod
    def _check_annual_timestep(scenarios_df: pd.DataFrame) -> None:
        """
        Vérifie que les scénarios sont à pas annuel.

        Les statistiques de l'optimiseur (rendement attendu, volatilité) sont
        annuelles. Les deux générateurs de scénarios ne donnent pas le même sens
        à un rendement infra-annuel (rendement de période pour le chemin
        stochastique, rendement annualisé pour le chemin simple) : plutôt que de
        deviner une annualisation, on refuse un pas qui n'est pas annuel.
        """
        if 'time_period' not in scenarios_df.columns:
            return
        periods = np.sort(scenarios_df['time_period'].unique())
        if len(periods) < 2:
            return
        steps = np.diff(periods)
        if not np.allclose(steps, 1.0):
            raise ValueError(
                "L'optimiseur n'accepte que des scénarios à pas annuel (timestep=1.0) ; "
                f"pas observé(s) : {sorted(set(np.round(steps, 6)))}. "
                "Générez les scénarios avec 'timestep': 1.0."
            )

    @staticmethod
    def _risk_free_rate(scenarios_df: pd.DataFrame) -> float:
        """
        Taux sans risque annuel moyen des scénarios (colonne ``interest_rate``).

        Il sert au ratio de Sharpe, qui mesure le rendement **excédentaire**
        par unité de risque. Sans cette colonne, on ne peut pas le calculer :
        on le dit plutôt que de supposer un taux nul.
        """
        if 'interest_rate' not in scenarios_df.columns:
            raise ValueError(
                "Les scénarios n'ont pas de colonne 'interest_rate' : le taux sans "
                "risque est nécessaire au ratio de Sharpe. Utilisez des scénarios "
                "produits par scenario_generator."
            )
        return float(scenarios_df['interest_rate'].mean())

    def _run_optimization(
        self,
        asset_returns: pd.DataFrame,
        objective: str,
        params: dict,
        constraints: dict,
        risk_free_rate: float
    ) -> dict:
        """
        Run portfolio optimization.

        Args:
            asset_returns: Asset return DataFrame
            objective: Optimization objective
            params: Optimization parameters
            constraints: User constraints
            risk_free_rate: Taux sans risque annuel, pour le ratio de Sharpe

        Returns:
            Dictionary with optimal weights and statistics
        """
        n_assets = len(asset_returns.columns)
        asset_names = list(asset_returns.columns)

        # Calculate mean returns and covariance
        mean_returns = asset_returns.mean().values
        cov_matrix = asset_returns.cov().values

        # Handle constraints
        min_weight = max(params['min_weight'], constraints.get('min_bond_allocation', 0.0))
        max_weight = min(params['max_weight'], constraints.get('max_equity_allocation', 1.0))

        if objective == 'max_sharpe':
            optimal_weights = self._optimize_max_sharpe(
                mean_returns, cov_matrix, n_assets, min_weight, max_weight, risk_free_rate
            )
        elif objective == 'min_volatility':
            optimal_weights = self._optimize_min_volatility(
                cov_matrix, n_assets, min_weight, max_weight
            )
        elif objective == 'max_return':
            # Max return = 100% in highest return asset (within constraints)
            max_return_idx = np.argmax(mean_returns)
            optimal_weights = np.zeros(n_assets)
            optimal_weights[max_return_idx] = 1.0
        elif objective == 'target_return':
            target_return = params['target_return']
            optimal_weights = self._optimize_target_return(
                mean_returns, cov_matrix, n_assets, target_return, min_weight, max_weight,
                risk_free_rate
            )
        elif objective == 'risk_parity':
            optimal_weights = self._optimize_risk_parity(
                cov_matrix, n_assets, min_weight, max_weight
            )
        elif objective == 'equal_weight':
            optimal_weights = np.ones(n_assets) / n_assets
        else:
            # Default to max Sharpe
            optimal_weights = self._optimize_max_sharpe(
                mean_returns, cov_matrix, n_assets, min_weight, max_weight, risk_free_rate
            )

        # Calculate portfolio statistics
        portfolio_return = np.dot(optimal_weights, mean_returns)
        portfolio_variance = np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        sharpe_ratio = self._sharpe_ratio(portfolio_return, portfolio_volatility, risk_free_rate)

        # Calculate max drawdown (estimated from simulations)
        max_drawdown = self._estimate_max_drawdown(asset_returns, optimal_weights)

        return {
            # strict=False : longueurs structurellement égales (n_assets) ; on
            # conserve le comportement historique de zip() plutôt que de lever.
            'weights': dict(zip(asset_names, optimal_weights, strict=False)),
            'expected_return': float(portfolio_return),
            'expected_volatility': float(portfolio_volatility),
            'sharpe_ratio': float(sharpe_ratio),
            'risk_free_rate': float(risk_free_rate),
            'max_drawdown': float(max_drawdown)
        }

    @staticmethod
    def _sharpe_ratio(
        portfolio_return: float, portfolio_volatility: float, risk_free_rate: float
    ) -> float:
        """Ratio de Sharpe : rendement excédentaire sur le taux sans risque, par unité de risque."""
        if portfolio_volatility <= 0:
            return 0.0
        return float((portfolio_return - risk_free_rate) / portfolio_volatility)

    def _optimize_max_sharpe(
        self,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
        n_assets: int,
        min_weight: float,
        max_weight: float,
        risk_free_rate: float
    ) -> np.ndarray:
        """Optimize for maximum Sharpe ratio (excess return over the risk-free rate)."""
        def neg_sharpe(weights: np.ndarray) -> float:
            portfolio_return = np.dot(weights, mean_returns)
            portfolio_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            if portfolio_std <= 0:
                return 1e10
            return float(-(portfolio_return - risk_free_rate) / portfolio_std)

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
        x0 = np.ones(n_assets) / n_assets

        result = minimize(neg_sharpe, x0, method='SLSQP', bounds=bounds, constraints=constraints)

        if not result.success:
            # Repli sur l'équipondération : comportement historique conservé,
            # mais l'échec de convergence n'est plus silencieux.
            logger.warning(
                "Échec de convergence SLSQP (max_sharpe) : %s — repli sur l'équipondération",
                result.message,
            )
            return x0
        return np.asarray(result.x)

    def _optimize_min_volatility(
        self,
        cov_matrix: np.ndarray,
        n_assets: int,
        min_weight: float,
        max_weight: float
    ) -> np.ndarray:
        """Optimize for minimum volatility."""
        def portfolio_volatility(weights: np.ndarray) -> float:
            return float(np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))))

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
        x0 = np.ones(n_assets) / n_assets

        result = minimize(
            portfolio_volatility, x0, method='SLSQP', bounds=bounds, constraints=constraints
        )

        if not result.success:
            logger.warning(
                "Échec de convergence SLSQP (min_volatility) : %s — repli sur l'équipondération",
                result.message,
            )
            return x0
        return np.asarray(result.x)

    def _optimize_target_return(
        self,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
        n_assets: int,
        target_return: float,
        min_weight: float,
        max_weight: float,
        risk_free_rate: float
    ) -> np.ndarray:
        """Optimize for target return with minimum volatility."""
        def portfolio_volatility(weights: np.ndarray) -> float:
            return float(np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))))

        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
            {'type': 'eq', 'fun': lambda w: np.dot(w, mean_returns) - target_return}
        ]
        bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
        x0 = np.ones(n_assets) / n_assets

        result = minimize(
            portfolio_volatility, x0, method='SLSQP', bounds=bounds, constraints=constraints
        )

        if result.success:
            return np.asarray(result.x)
        else:
            # If target return not achievable, return max Sharpe
            logger.warning(
                "Échec de convergence SLSQP (target_return=%.4f) : %s — repli sur max_sharpe",
                target_return,
                result.message,
            )
            return self._optimize_max_sharpe(
                mean_returns, cov_matrix, n_assets, min_weight, max_weight, risk_free_rate
            )

    def _optimize_risk_parity(
        self,
        cov_matrix: np.ndarray,
        n_assets: int,
        min_weight: float,
        max_weight: float
    ) -> np.ndarray:
        """Optimize for risk parity (equal risk contribution)."""
        def risk_parity_objective(weights: np.ndarray) -> float:
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            marginal_contrib = np.dot(cov_matrix, weights)
            risk_contrib = weights * marginal_contrib / np.sqrt(portfolio_variance)
            return float(np.sum((risk_contrib - risk_contrib.mean()) ** 2))

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
        x0 = np.ones(n_assets) / n_assets

        result = minimize(
            risk_parity_objective, x0, method='SLSQP', bounds=bounds, constraints=constraints
        )

        if not result.success:
            logger.warning(
                "Échec de convergence SLSQP (risk_parity) : %s — repli sur l'équipondération",
                result.message,
            )
            return x0
        return np.asarray(result.x)

    def _estimate_max_drawdown(self, asset_returns: pd.DataFrame, weights: np.ndarray) -> float:
        """
        Estimate maximum drawdown from scenarios.

        La perte maximale est calculée sur la trajectoire de chaque scénario,
        puis on retient sa médiane : c'est la perte maximale « typique » sur
        l'horizon de projection.

        Args:
            asset_returns: Periodic asset returns, indexed by (scenario_id, time_period)
            weights: Portfolio weights

        Returns:
            Median over scenarios of the maximum drawdown (positive fraction)
        """
        portfolio_returns = asset_returns.to_numpy() @ weights

        if 'scenario_id' in (asset_returns.index.names or []):
            scenario_ids = asset_returns.index.get_level_values('scenario_id')
            paths = (
                pd.Series(portfolio_returns, index=scenario_ids)
                .groupby(level=0, sort=False)
                .apply(lambda r: r.to_numpy())
            )
            n_periods = paths.map(len)
            if n_periods.nunique() != 1:
                raise ValueError(
                    "Les scénarios n'ont pas tous le même nombre de périodes : "
                    "impossible d'estimer la perte maximale."
                )
            returns_matrix = np.vstack(paths.to_list())
        else:
            returns_matrix = portfolio_returns[np.newaxis, :]

        cumulative = np.cumprod(1.0 + returns_matrix, axis=1)
        running_max = np.maximum.accumulate(cumulative, axis=1)
        drawdowns = (cumulative - running_max) / running_max
        max_drawdowns = np.abs(drawdowns.min(axis=1))

        return float(np.median(max_drawdowns))

    def _generate_efficient_frontier(
        self,
        asset_returns: pd.DataFrame,
        constraints: dict,
        params: dict,
        risk_free_rate: float,
        n_points: int = 50
    ) -> pd.DataFrame:
        """
        Generate efficient frontier.

        Args:
            asset_returns: Asset returns
            constraints: User constraints
            params: Optimization parameters
            n_points: Number of points on frontier

        Returns:
            DataFrame with efficient frontier points
        """
        mean_returns = asset_returns.mean().values
        cov_matrix = asset_returns.cov().values
        n_assets = len(asset_returns.columns)

        min_return = mean_returns.min()
        max_return = mean_returns.max()

        target_returns = np.linspace(min_return, max_return, n_points)

        frontier_results = []

        for target_ret in target_returns:
            try:
                weights = self._optimize_target_return(
                    mean_returns,
                    cov_matrix,
                    n_assets,
                    target_ret,
                    params['min_weight'],
                    params['max_weight'],
                    risk_free_rate
                )

                portfolio_return = np.dot(weights, mean_returns)
                portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                sharpe = self._sharpe_ratio(portfolio_return, portfolio_volatility, risk_free_rate)

                result_dict = {
                    'return': portfolio_return,
                    'volatility': portfolio_volatility,
                    'sharpe': sharpe
                }

                # Add weights
                for i, asset in enumerate(asset_returns.columns):
                    result_dict[f'{asset}_weight'] = weights[i]

                frontier_results.append(result_dict)

            except (ValueError, ArithmeticError) as exc:
                # Un rendement cible peut être infaisable sous les contraintes de
                # poids, ou la matrice de covariance peut être singulière : on
                # ignore ce point de la frontière, mais on trace la raison.
                # ValueError couvre np.linalg.LinAlgError (qui en hérite) ;
                # ArithmeticError couvre les divisions par zéro et débordements.
                logger.warning(
                    "Point de frontière efficiente ignoré (rendement cible=%.6f) : %s",
                    target_ret,
                    exc,
                )
                continue

        logger.debug(
            "Frontière efficiente générée : %d/%d points retenus",
            len(frontier_results),
            n_points,
        )

        return pd.DataFrame(frontier_results)

    def _run_simulations(
        self,
        scenarios_df: pd.DataFrame,
        asset_returns: pd.DataFrame,
        optimal_portfolio: dict,
        time_series: pd.DataFrame,
        params: dict
    ) -> dict:
        """
        Simulate the optimal portfolio over every scenario, with rebalancing costs.

        Le portefeuille dérive avec les rendements de chaque actif. À chaque fin
        d'année, si l'écart d'un poids à sa cible dépasse
        ``rebalancing_threshold``, il est ramené à la cible et les coûts de
        transaction (``transaction_costs``, en fraction du montant échangé) sont
        prélevés sur le patrimoine. Les versements sont investis à
        l'allocation cible ; les retraits sont prélevés au prorata des
        positions. Le calcul est vectorisé sur les scénarios.

        Args:
            scenarios_df: After-tax scenarios (for the inflation column)
            asset_returns: Periodic asset returns from _extract_asset_returns
            optimal_portfolio: Optimal portfolio weights
            time_series: Investment time series (flows, from Module 3)
            params: Parameters (transaction_costs, rebalancing_threshold)

        Returns:
            Dictionary with terminal wealth, wealth paths, rebalancing schedule
            and statistics
        """
        asset_names = list(asset_returns.columns)
        target = np.array([optimal_portfolio['weights'][a] for a in asset_names])
        costs = self._transaction_cost_rates(asset_names, params['transaction_costs'])
        threshold = float(params['rebalancing_threshold'])

        if 'scenario_id' not in (asset_returns.index.names or []):
            raise ValueError("Les scénarios doivent porter une colonne 'scenario_id'.")
        ordered = asset_returns.sort_index()
        scenario_ids = ordered.index.get_level_values(0).unique()
        n_scenarios = len(scenario_ids)
        n_periods = len(ordered) // n_scenarios
        if n_scenarios * n_periods != len(ordered):
            raise ValueError(
                "Les scénarios n'ont pas tous le même nombre de périodes : "
                "impossible de simuler les trajectoires de patrimoine."
            )
        returns = ordered.to_numpy().reshape(n_scenarios, n_periods, len(asset_names))
        flows = self._investment_flows(time_series, n_periods)

        holdings = np.tile(flows[0] * target, (n_scenarios, 1))
        wealth_paths = np.zeros((n_scenarios, n_periods + 1))
        wealth_paths[:, 0] = flows[0]
        total_costs = np.zeros(n_scenarios)
        schedule = []

        for t in range(n_periods):
            holdings = holdings * (1.0 + returns[:, t, :])
            wealth = holdings.sum(axis=1)

            flow = flows[t + 1]
            if flow >= 0:
                holdings = holdings + flow * target
            else:
                share = np.divide(
                    holdings, wealth[:, None], out=np.zeros_like(holdings),
                    where=wealth[:, None] > 0,
                )
                holdings = holdings + flow * share
            holdings = np.where(holdings.sum(axis=1, keepdims=True) > 0, holdings, 0.0)
            wealth = holdings.sum(axis=1)

            current = np.divide(
                holdings, wealth[:, None], out=np.tile(target, (n_scenarios, 1)),
                where=wealth[:, None] > 0,
            )
            rebalance = np.abs(current - target).max(axis=1) > threshold
            trades = np.abs(target * wealth[:, None] - holdings)
            period_costs = np.where(rebalance, trades @ costs, 0.0)
            holdings = np.where(
                rebalance[:, None], (wealth - period_costs)[:, None] * target, holdings
            )
            total_costs += period_costs
            wealth_paths[:, t + 1] = holdings.sum(axis=1)

            turnover = np.divide(
                trades.sum(axis=1) / 2.0, wealth, out=np.zeros_like(wealth), where=wealth > 0
            )
            schedule.append({
                'period': t + 1,
                'share_of_scenarios_rebalanced': float(rebalance.mean()),
                'mean_turnover': float(np.where(rebalance, turnover, 0.0).mean()),
                'mean_cost': float(period_costs.mean()),
            })

        terminal = wealth_paths[:, -1]
        terminal_wealth_df = pd.DataFrame({
            'scenario_id': scenario_ids,
            'wealth': terminal,
            'transaction_costs': total_costs,
        })
        if 'inflation' in scenarios_df.columns:
            # Patrimoine en euros constants de la date de départ.
            inflation = (
                scenarios_df.set_index(list(ordered.index.names))['inflation']
                .sort_index().to_numpy().reshape(n_scenarios, n_periods)
            )
            terminal_wealth_df['real_wealth'] = terminal / np.prod(1.0 + inflation, axis=1)
        terminal_wealth_df['percentile'] = terminal_wealth_df['wealth'].rank(pct=True) * 100

        statistics = {
            'mean_terminal_wealth': float(terminal.mean()),
            'median_terminal_wealth': float(np.median(terminal)),
            'std_terminal_wealth': float(terminal.std()),
            'percentiles': {
                '5': float(np.percentile(terminal, 5)),
                '25': float(np.percentile(terminal, 25)),
                '50': float(np.percentile(terminal, 50)),
                '75': float(np.percentile(terminal, 75)),
                '95': float(np.percentile(terminal, 95))
            },
            'var_95': float(np.percentile(terminal, 5)),
            'cvar_95': float(terminal[terminal <= np.percentile(terminal, 5)].mean()),
            'mean_transaction_costs': float(total_costs.mean()),
        }

        wealth_paths_df = pd.DataFrame(
            wealth_paths,
            columns=[f"year_{i}" for i in range(n_periods + 1)]
        )
        wealth_paths_df.insert(0, 'scenario_id', scenario_ids)

        return {
            'terminal_wealth': terminal_wealth_df,
            'wealth_paths': wealth_paths_df,
            'rebalancing_schedule': pd.DataFrame(schedule),
            'statistics': statistics
        }

    @staticmethod
    def _transaction_cost_rates(asset_names: list[str], cost_params: dict) -> np.ndarray:
        """
        Taux de coût de transaction de chaque actif, dans l'ordre de ``asset_names``.

        Les clés historiques sont au pluriel (``stocks``, ``bonds``) alors que
        les actifs sont au singulier (``stock``, ``bond``) : on accepte les deux.
        Un actif sans coût déclaré est une erreur, pas un coût nul.
        """
        rates = []
        for asset in asset_names:
            for key in (asset, f"{asset}s"):
                if key in cost_params:
                    rates.append(float(cost_params[key]))
                    break
            else:
                raise ValueError(
                    f"Aucun coût de transaction pour l'actif {asset!r} dans "
                    f"optimization_params['transaction_costs'] ({sorted(cost_params)}). "
                    "Ajoutez-le, éventuellement à 0 si c'est le cas."
                )
        return np.array(rates)

    @staticmethod
    def _investment_flows(time_series: pd.DataFrame, n_periods: int) -> np.ndarray:
        """
        Flux d'investissement : ``flows[0]`` est la mise initiale, ``flows[t]``
        le versement (positif) ou le retrait (négatif) de fin d'année ``t``.

        La série vient du module 3. Sans elle, il n'y a pas de patrimoine à
        projeter : on le dit plutôt que d'inventer une mise initiale.
        """
        if time_series.empty:
            raise ValueError(
                "investment_time_series est vide : la projection du patrimoine a "
                "besoin des versements et retraits (module 3, user_profile)."
            )
        if 'net_flow' in time_series.columns:
            series = time_series['net_flow']
        elif 'contribution' in time_series.columns:
            series = time_series['contribution'] - time_series.get('withdrawal', 0.0)
        else:
            raise ValueError(
                "investment_time_series doit contenir 'net_flow' ou 'contribution'."
            )
        flows = np.zeros(n_periods + 1)
        values = series.to_numpy(dtype=float)[: n_periods + 1]
        flows[: len(values)] = values
        return flows

    def _sensitivity_analysis(
        self,
        asset_returns: pd.DataFrame,
        optimal_portfolio: dict,
        params: dict
    ) -> dict:
        """
        Perform sensitivity analysis.

        Args:
            asset_returns: Asset returns
            optimal_portfolio: Optimal portfolio
            params: Parameters

        Returns:
            Sensitivity analysis results
        """
        # Analyze sensitivity to return assumptions
        mean_returns = asset_returns.mean()
        cov_matrix = asset_returns.cov().to_numpy()
        weights = np.array(list(optimal_portfolio['weights'].values()))

        # Test +10% change in expected returns
        return_sensitivity = {}
        for asset in asset_returns.columns:
            modified_returns = mean_returns.copy()
            modified_returns[asset] *= 1.1  # +10%

            new_portfolio_return = np.dot(weights, modified_returns.values)
            impact = new_portfolio_return - optimal_portfolio['expected_return']

            return_sensitivity[asset] = float(impact)

        # Test +10% change in each asset's volatility (correlations unchanged)
        volatility_sensitivity = {}
        for i, asset in enumerate(asset_returns.columns):
            scale = np.ones(len(weights))
            scale[i] = 1.1
            modified_cov = cov_matrix * np.outer(scale, scale)
            new_volatility = float(np.sqrt(weights @ modified_cov @ weights))
            volatility_sensitivity[asset] = (
                new_volatility - optimal_portfolio['expected_volatility']
            )

        return {
            'return_sensitivity': return_sensitivity,
            'volatility_sensitivity': volatility_sensitivity,
        }

    def _analyze_goals(
        self,
        simulation_results: dict,
        goal_amount: float | None
    ) -> dict:
        """
        Analyze goal achievement probability.

        Args:
            simulation_results: Simulation results
            goal_amount: Target goal amount

        Returns:
            Goal analysis dictionary
        """
        terminal_wealth = simulation_results['terminal_wealth']['wealth'].values

        if goal_amount is None:
            goal_amount = np.median(terminal_wealth)

        # Calculate probability of achieving goal
        probability_of_achieving = (terminal_wealth >= goal_amount).mean()

        # Expected surplus/deficit
        surplus_deficit = terminal_wealth - goal_amount
        expected_surplus_deficit = surplus_deficit.mean()

        return {
            'goal_amount': float(goal_amount),
            'probability_of_achieving': float(probability_of_achieving),
            'expected_surplus_deficit': float(expected_surplus_deficit),
        }


# Convenience functions
def quick_optimize(
    scenarios_df: pd.DataFrame,
    objective: str = 'max_sharpe',
    *,
    initial_wealth: float,
) -> dict:
    """
    Quick optimization with default parameters.

    Args:
        scenarios_df: Scenarios DataFrame
        objective: Optimization objective
        initial_wealth: Mise initiale, sans versement ultérieur

    Returns:
        Optimization results

    Example:
        >>> results = quick_optimize(scenarios_df, 'max_sharpe', initial_wealth=10_000)
    """
    config = {
        'scenarios': scenarios_df,
        'optimization_objective': objective,
        'investment_time_series': pd.DataFrame({'period': [0], 'net_flow': [initial_wealth]}),
    }

    optimizer = PortfolioOptimizer()
    return optimizer.optimize(config)

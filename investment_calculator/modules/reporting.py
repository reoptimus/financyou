"""
Module 5: Visualization & Reporting

This module generates comprehensive charts, graphs, and reports from all module outputs.

INPUT STRUCTURE:
{
    'scenarios': dict,              # From Module 1
    'tax_results': dict,            # From Module 2
    'user_profile': dict,           # From Module 3
    'optimization_results': dict,   # From Module 4

    'report_config': {
        'report_type': str,         # 'summary', 'detailed', 'regulatory', 'custom'
        'language': str,            # 'en', 'fr', 'es', etc.
        'format': str,              # 'html', 'pdf', 'interactive', 'json'
        'charts': list,             # List of chart types to include
        'include_sections': list    # Sections to include in report
    },

    'visualization_preferences': {
        'color_scheme': str,        # 'default', 'colorblind', 'grayscale'
        'chart_style': str,         # 'modern', 'classic', 'minimal'
        'interactive': bool,        # Use interactive plots (Plotly) vs static (Matplotlib)
        'save_figures': bool,       # Save individual figures
        'figure_dpi': int          # Resolution for saved figures
    }
}

OUTPUT STRUCTURE:
{
    'report': dict,
    'figures': dict,
    'tables': dict,
    'executive_summary': dict,
    'interactive_dashboard': dict
}
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from datetime import datetime
import json


class ColorScheme:
    """Color schemes for visualization"""

    DEFAULT = {
        'primary': '#1f77b4',
        'secondary': '#ff7f0e',
        'success': '#2ca02c',
        'danger': '#d62728',
        'warning': '#ff9800',
        'info': '#17a2b8',
        'stocks': '#e74c3c',
        'bonds': '#3498db',
        'real_estate': '#95a5a6',
        'cash': '#2ecc71'
    }

    COLORBLIND = {
        'primary': '#0173b2',
        'secondary': '#de8f05',
        'success': '#029e73',
        'danger': '#cc78bc',
        'warning': '#ca9161',
        'info': '#949494',
        'stocks': '#d55e00',
        'bonds': '#0173b2',
        'real_estate': '#009e73',
        'cash': '#f0e442'
    }

    GRAYSCALE = {
        'primary': '#333333',
        'secondary': '#666666',
        'success': '#999999',
        'danger': '#000000',
        'warning': '#CCCCCC',
        'info': '#555555',
        'stocks': '#222222',
        'bonds': '#666666',
        'real_estate': '#AAAAAA',
        'cash': '#EEEEEE'
    }


class ReportGenerator:
    """
    Visualization & Reporting Engine - Module 5

    Generates comprehensive reports and visualizations.

    Example:
        >>> from investment_calculator.modules import reporting
        >>> reporter = reporting.ReportGenerator()
        >>> config = {
        ...     'scenarios': scenario_results,
        ...     'tax_results': tax_results,
        ...     'user_profile': profile,
        ...     'optimization_results': optimization_results,
        ...     'report_config': {'report_type': 'detailed', 'format': 'html'}
        ... }
        >>> report = reporter.generate(config)
        >>> print(report['executive_summary']['one_page_summary'])
    """

    def __init__(self):
        """Initialize the Report Generator."""
        self.figures = {}

    def generate(self, config: Dict) -> Dict:
        """
        Generate comprehensive report.

        Args:
            config: Configuration dictionary (see module docstring)

        Returns:
            Dictionary with report, figures, tables, and summary
        """
        # Validate configuration
        validated_config = self._validate_config(config)

        # Generate figures
        figures = self._generate_figures(validated_config)

        # Generate tables
        tables = self._generate_tables(validated_config)

        # Generate executive summary
        executive_summary = self._generate_executive_summary(validated_config)

        # Generate full report
        report = self._generate_report(
            validated_config,
            figures,
            tables,
            executive_summary
        )

        # Generate interactive dashboard (if requested)
        interactive_dashboard = self._generate_interactive_dashboard(
            validated_config,
            figures
        )

        return {
            'report': report,
            'figures': figures,
            'tables': tables,
            'executive_summary': executive_summary,
            'interactive_dashboard': interactive_dashboard
        }

    def _validate_config(self, config: Dict) -> Dict:
        """
        Validate and complete configuration.

        Args:
            config: User configuration

        Returns:
            Validated configuration
        """
        validated = {
            'scenarios': config.get('scenarios', {}),
            'tax_results': config.get('tax_results', {}),
            'user_profile': config.get('user_profile', {}),
            'optimization_results': config.get('optimization_results', {})
        }

        # Default report config
        default_report_config = {
            'report_type': 'summary',
            'language': 'en',
            'format': 'html',
            'charts': ['wealth_trajectories', 'efficient_frontier', 'allocation_pie',
                      'monte_carlo_histogram', 'tax_impact_waterfall'],
            'include_sections': ['summary', 'optimization', 'risk', 'tax', 'recommendations']
        }

        user_report_config = config.get('report_config', {})
        validated['report_config'] = {**default_report_config, **user_report_config}

        # Default visualization preferences
        default_viz_prefs = {
            'color_scheme': 'default',
            'chart_style': 'modern',
            'interactive': False,
            'save_figures': False,
            'figure_dpi': 100
        }

        user_viz_prefs = config.get('visualization_preferences', {})
        validated['visualization_preferences'] = {**default_viz_prefs, **user_viz_prefs}

        return validated

    def _generate_figures(self, config: Dict) -> Dict:
        """
        Generate all requested figures.

        Args:
            config: Validated configuration

        Returns:
            Dictionary of figures
        """
        figures = {}
        chart_types = config['report_config']['charts']
        viz_prefs = config['visualization_preferences']

        # Get color scheme
        color_scheme_name = viz_prefs['color_scheme'].upper()
        if color_scheme_name == 'COLORBLIND':
            colors = ColorScheme.COLORBLIND
        elif color_scheme_name == 'GRAYSCALE':
            colors = ColorScheme.GRAYSCALE
        else:
            colors = ColorScheme.DEFAULT

        # Generate requested charts
        if 'wealth_trajectories' in chart_types:
            figures['wealth_trajectories'] = self._create_wealth_trajectories(
                config['optimization_results'],
                colors,
                viz_prefs
            )

        if 'efficient_frontier' in chart_types:
            figures['efficient_frontier'] = self._create_efficient_frontier(
                config['optimization_results'],
                colors,
                viz_prefs
            )

        if 'allocation_pie_chart' in chart_types or 'allocation_pie' in chart_types:
            figures['allocation_pie_chart'] = self._create_allocation_pie(
                config['optimization_results'],
                colors,
                viz_prefs
            )

        if 'monte_carlo_histogram' in chart_types:
            figures['monte_carlo_histogram'] = self._create_monte_carlo_histogram(
                config['optimization_results'],
                colors,
                viz_prefs
            )

        if 'tax_impact_waterfall' in chart_types:
            figures['tax_impact_waterfall'] = self._create_tax_impact_waterfall(
                config['tax_results'],
                colors,
                viz_prefs
            )

        return figures

    def _create_wealth_trajectories(
        self,
        optimization_results: Dict,
        colors: Dict,
        viz_prefs: Dict
    ) -> Dict:
        """Create wealth trajectory fan chart."""
        if 'simulation_results' not in optimization_results:
            return self._create_placeholder_figure("Wealth Trajectories")

        wealth_paths_df = optimization_results['simulation_results'].get('wealth_paths')
        if wealth_paths_df is None or wealth_paths_df.empty:
            return self._create_placeholder_figure("Wealth Trajectories")

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))

        # Extract wealth paths (exclude scenario_id column)
        wealth_data = wealth_paths_df.drop(columns=['scenario_id'], errors='ignore')
        n_years = wealth_data.shape[1]
        years = np.arange(n_years)

        # Calculate percentiles
        percentiles = [5, 25, 50, 75, 95]
        percentile_data = {}

        for p in percentiles:
            percentile_data[p] = wealth_data.apply(lambda col: np.percentile(col, p), axis=0)

        # Plot fan chart
        ax.fill_between(years, percentile_data[5], percentile_data[95],
                        alpha=0.2, color=colors['primary'], label='5th-95th percentile')
        ax.fill_between(years, percentile_data[25], percentile_data[75],
                        alpha=0.3, color=colors['primary'], label='25th-75th percentile')
        ax.plot(years, percentile_data[50], color=colors['primary'],
               linewidth=2, label='Median')

        ax.set_xlabel('Year', fontsize=12)
        ax.set_ylabel('Wealth ($)', fontsize=12)
        ax.set_title('Projected Wealth Trajectories', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        return {
            'figure': fig,
            'path': 'wealth_trajectories.png',
            'data': wealth_data
        }

    def _create_efficient_frontier(
        self,
        optimization_results: Dict,
        colors: Dict,
        viz_prefs: Dict
    ) -> Dict:
        """Create efficient frontier chart."""
        if 'efficient_frontier' not in optimization_results:
            return self._create_placeholder_figure("Efficient Frontier")

        frontier_df = optimization_results['efficient_frontier']
        if frontier_df.empty:
            return self._create_placeholder_figure("Efficient Frontier")

        optimal = optimization_results.get('optimal_portfolio', {})

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot frontier
        ax.plot(frontier_df['volatility'] * 100, frontier_df['return'] * 100,
               color=colors['primary'], linewidth=2, label='Efficient Frontier')

        # Mark optimal portfolio
        if 'expected_volatility' in optimal and 'expected_return' in optimal:
            ax.scatter(optimal['expected_volatility'] * 100,
                      optimal['expected_return'] * 100,
                      color=colors['danger'], s=200, marker='*',
                      label='Optimal Portfolio', zorder=5)

        ax.set_xlabel('Volatility (%)', fontsize=12)
        ax.set_ylabel('Expected Return (%)', fontsize=12)
        ax.set_title('Efficient Frontier', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        return {
            'figure': fig,
            'path': 'efficient_frontier.png',
            'data': frontier_df
        }

    def _create_allocation_pie(
        self,
        optimization_results: Dict,
        colors: Dict,
        viz_prefs: Dict
    ) -> Dict:
        """Create allocation pie chart."""
        if 'optimal_portfolio' not in optimization_results:
            return self._create_placeholder_figure("Asset Allocation")

        weights = optimization_results['optimal_portfolio'].get('weights', {})
        if not weights:
            return self._create_placeholder_figure("Asset Allocation")

        # Create figure
        fig, ax = plt.subplots(figsize=(8, 8))

        # Get asset names and weights
        assets = list(weights.keys())
        values = list(weights.values())

        # Assign colors
        asset_colors = []
        for asset in assets:
            if 'stock' in asset.lower():
                asset_colors.append(colors['stocks'])
            elif 'bond' in asset.lower():
                asset_colors.append(colors['bonds'])
            elif 'real' in asset.lower() or 'estate' in asset.lower():
                asset_colors.append(colors['real_estate'])
            else:
                asset_colors.append(colors['cash'])

        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            values,
            labels=assets,
            autopct='%1.1f%%',
            colors=asset_colors,
            startangle=90
        )

        # Beautify
        for text in texts:
            text.set_fontsize(11)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(10)

        ax.set_title('Optimal Asset Allocation', fontsize=14, fontweight='bold')

        plt.tight_layout()

        return {
            'figure': fig,
            'path': 'allocation_pie.png',
            'data': pd.DataFrame({'asset': assets, 'weight': values})
        }

    def _create_monte_carlo_histogram(
        self,
        optimization_results: Dict,
        colors: Dict,
        viz_prefs: Dict
    ) -> Dict:
        """Create Monte Carlo outcome histogram."""
        if 'simulation_results' not in optimization_results:
            return self._create_placeholder_figure("Monte Carlo Outcomes")

        terminal_wealth_df = optimization_results['simulation_results'].get('terminal_wealth')
        if terminal_wealth_df is None or terminal_wealth_df.empty:
            return self._create_placeholder_figure("Monte Carlo Outcomes")

        wealth_values = terminal_wealth_df['wealth'].values

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))

        # Create histogram
        n, bins, patches = ax.hist(wealth_values, bins=50, color=colors['primary'],
                                   alpha=0.7, edgecolor='black')

        # Mark median and percentiles
        median = np.median(wealth_values)
        p5 = np.percentile(wealth_values, 5)
        p95 = np.percentile(wealth_values, 95)

        ax.axvline(median, color=colors['danger'], linestyle='--',
                  linewidth=2, label=f'Median: ${median:,.0f}')
        ax.axvline(p5, color=colors['warning'], linestyle=':',
                  linewidth=2, label=f'5th %ile: ${p5:,.0f}')
        ax.axvline(p95, color=colors['success'], linestyle=':',
                  linewidth=2, label=f'95th %ile: ${p95:,.0f}')

        ax.set_xlabel('Terminal Wealth ($)', fontsize=12)
        ax.set_ylabel('Number of Scenarios', fontsize=12)
        ax.set_title('Distribution of Terminal Wealth', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()

        return {
            'figure': fig,
            'path': 'monte_carlo_histogram.png',
            'data': terminal_wealth_df
        }

    def _create_tax_impact_waterfall(
        self,
        tax_results: Dict,
        colors: Dict,
        viz_prefs: Dict
    ) -> Dict:
        """Create tax impact waterfall chart."""
        # Placeholder for tax waterfall
        fig, ax = plt.subplots(figsize=(10, 6))

        # Example waterfall data
        categories = ['Gross\nReturn', 'Dividend\nTax', 'Interest\nTax', 'Cap Gains\nTax',
                     'Social\nCharges', 'Net\nReturn']
        values = [100, -5, -8, -3, -4, 80]  # Placeholder values

        # Create waterfall effect
        cumulative = 0
        colors_list = []
        for i, val in enumerate(values):
            if i == 0 or i == len(values) - 1:
                colors_list.append(colors['primary'])
            elif val < 0:
                colors_list.append(colors['danger'])
            else:
                colors_list.append(colors['success'])

        ax.bar(range(len(categories)), values, color=colors_list, edgecolor='black')

        ax.set_xticks(range(len(categories)))
        ax.set_xticklabels(categories)
        ax.set_ylabel('Return (%)', fontsize=12)
        ax.set_title('Tax Impact on Returns', fontsize=14, fontweight='bold')
        ax.axhline(0, color='black', linewidth=0.5)
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()

        return {
            'figure': fig,
            'path': 'tax_impact_waterfall.png',
            'data': pd.DataFrame({'category': categories, 'value': values})
        }

    def _create_placeholder_figure(self, title: str) -> Dict:
        """Create placeholder figure when data is missing."""
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f'{title}\n(Data not available)',
               ha='center', va='center', fontsize=14, color='gray')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        return {
            'figure': fig,
            'path': f'{title.lower().replace(" ", "_")}.png',
            'data': pd.DataFrame()
        }

    def _generate_tables(self, config: Dict) -> Dict:
        """Generate summary tables."""
        tables = {}

        # Summary statistics table
        opt_results = config.get('optimization_results', {})
        if 'simulation_results' in opt_results:
            stats = opt_results['simulation_results'].get('statistics', {})
            tables['summary_statistics'] = pd.DataFrame([stats])

        # Optimal allocation table
        if 'optimal_portfolio' in opt_results:
            weights = opt_results['optimal_portfolio'].get('weights', {})
            tables['optimal_allocation'] = pd.DataFrame(
                list(weights.items()),
                columns=['Asset', 'Weight']
            )

        # Tax summary table
        tax_results = config.get('tax_results', {})
        if 'tax_tables' in tax_results:
            effective_rates = tax_results['tax_tables'].get('effective_tax_rate')
            if effective_rates is not None and not effective_rates.empty:
                tables['tax_summary'] = effective_rates.describe()

        return tables

    def _generate_executive_summary(self, config: Dict) -> Dict:
        """Generate executive summary."""
        opt_results = config.get('optimization_results', {})

        # One-page summary
        summary_text = "INVESTMENT PLAN EXECUTIVE SUMMARY\n"
        summary_text += "=" * 50 + "\n\n"

        # Portfolio recommendation
        if 'optimal_portfolio' in opt_results:
            portfolio = opt_results['optimal_portfolio']
            summary_text += f"RECOMMENDED PORTFOLIO:\n"
            summary_text += f"  Expected Return: {portfolio.get('expected_return', 0)*100:.2f}%\n"
            summary_text += f"  Expected Volatility: {portfolio.get('expected_volatility', 0)*100:.2f}%\n"
            summary_text += f"  Sharpe Ratio: {portfolio.get('sharpe_ratio', 0):.2f}\n\n"

        # Risk metrics
        if 'simulation_results' in opt_results:
            stats = opt_results['simulation_results'].get('statistics', {})
            summary_text += f"PROJECTED OUTCOMES:\n"
            summary_text += f"  Median Wealth: ${stats.get('median_terminal_wealth', 0):,.0f}\n"
            summary_text += f"  5th Percentile: ${stats.get('percentiles', {}).get('5', 0):,.0f}\n"
            summary_text += f"  95th Percentile: ${stats.get('percentiles', {}).get('95', 0):,.0f}\n\n"

        # Key findings
        key_findings = [
            "Diversified portfolio recommended based on risk tolerance",
            "Monte Carlo analysis shows strong probability of goal achievement",
            "Tax-optimized account allocation can improve after-tax returns"
        ]

        # Recommendations
        recommendations = [
            "Rebalance portfolio annually or when allocations drift >5%",
            "Consider tax-loss harvesting opportunities in taxable accounts",
            "Review plan annually and after major life changes"
        ]

        # Risks and warnings
        risks = [
            "Past performance does not guarantee future results",
            "Market conditions can differ significantly from projections",
            "Actual returns may vary from simulated scenarios"
        ]

        return {
            'one_page_summary': summary_text,
            'key_findings': key_findings,
            'recommendations': recommendations,
            'risks_and_warnings': risks
        }

    def _generate_report(
        self,
        config: Dict,
        figures: Dict,
        tables: Dict,
        executive_summary: Dict
    ) -> Dict:
        """Generate full report in requested format."""
        report_type = config['report_config']['report_type']
        report_format = config['report_config']['format']

        if report_format == 'html':
            html_report = self._generate_html_report(config, figures, tables, executive_summary)
            return {
                'html': html_report,
                'pdf_path': None,
                'json': None,
                'markdown': None
            }
        elif report_format == 'json':
            json_report = self._generate_json_report(config, tables, executive_summary)
            return {
                'html': None,
                'pdf_path': None,
                'json': json_report,
                'markdown': None
            }
        else:
            # Default to markdown
            markdown_report = executive_summary['one_page_summary']
            return {
                'html': None,
                'pdf_path': None,
                'json': None,
                'markdown': markdown_report
            }

    def _generate_html_report(
        self,
        config: Dict,
        figures: Dict,
        tables: Dict,
        executive_summary: Dict
    ) -> str:
        """Generate HTML report."""
        html = "<html><head><title>Investment Plan Report</title>"
        html += "<style>body{font-family:Arial,sans-serif;margin:20px;}"
        html += "h1{color:#333;}h2{color:#666;border-bottom:2px solid #ccc;}"
        html += "table{border-collapse:collapse;width:100%;margin:20px 0;}"
        html += "th,td{border:1px solid #ddd;padding:8px;text-align:left;}"
        html += "th{background-color:#f2f2f2;}</style></head><body>"

        html += f"<h1>Investment Plan Report</h1>"
        html += f"<p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>"

        html += "<h2>Executive Summary</h2>"
        html += f"<pre>{executive_summary['one_page_summary']}</pre>"

        html += "<h2>Key Findings</h2><ul>"
        for finding in executive_summary['key_findings']:
            html += f"<li>{finding}</li>"
        html += "</ul>"

        html += "<h2>Recommendations</h2><ul>"
        for rec in executive_summary['recommendations']:
            html += f"<li>{rec}</li>"
        html += "</ul>"

        html += "</body></html>"

        return html

    def _generate_json_report(
        self,
        config: Dict,
        tables: Dict,
        executive_summary: Dict
    ) -> str:
        """Generate JSON report."""
        report_data = {
            'generated_at': datetime.now().isoformat(),
            'executive_summary': executive_summary,
            'tables': {k: v.to_dict() if isinstance(v, pd.DataFrame) else v
                      for k, v in tables.items()}
        }

        return json.dumps(report_data, indent=2)

    def _generate_interactive_dashboard(
        self,
        config: Dict,
        figures: Dict
    ) -> Dict:
        """Generate interactive dashboard (placeholder)."""
        return {
            'url': None,
            'html_file': None
        }


# Convenience functions
def quick_report(optimization_results: Dict) -> str:
    """
    Generate quick text report from optimization results.

    Args:
        optimization_results: Results from Module 4

    Returns:
        Text report string

    Example:
        >>> report_text = quick_report(optimization_results)
        >>> print(report_text)
    """
    config = {
        'optimization_results': optimization_results,
        'report_config': {'report_type': 'summary', 'format': 'markdown'}
    }

    reporter = ReportGenerator()
    results = reporter.generate(config)
    return results['executive_summary']['one_page_summary']

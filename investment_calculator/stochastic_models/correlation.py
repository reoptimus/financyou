"""
Correlated Random Variable Generation

This module generates correlated random variables for multi-asset scenario generation.
It uses Cholesky decomposition to impose a correlation structure on independent
standard normal variates.

The correlation structure is based on empirical research (e.g., Ahlgrim et al.)
and includes:
1. Short-term interest rates
2. Inflation
3. Real estate returns
4. Long-term interest rates
5. Excess equity returns
6. Additional asset classes (bonds, commodities, etc.)

Key Features:
- Cholesky decomposition for correlation
- Antithetic variance reduction
- 3D array structure (assets × scenarios × time)
- Integration with Hull-White residuals
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Tuple
import warnings


class CorrelatedRandomGenerator:
    """
    Generator for correlated random variables across multiple asset classes.

    This class creates a "cube" of correlated random shocks that can be used
    to simulate multiple asset classes simultaneously while preserving their
    empirical correlation structure.

    The correlation matrix is decomposed using Cholesky decomposition:
        If Σ is the correlation matrix, then L is the lower triangular matrix
        such that Σ = L * L^T

    Then correlated shocks are generated as:
        ε_correlated = L * ε_independent

    Attributes:
        correlation_matrix: Correlation matrix between asset classes
        n_assets: Number of asset classes
        n_scenarios: Number of Monte Carlo scenarios
        n_steps: Number of time steps
        asset_names: Names of the asset classes
    """

    # Default correlation matrix based on Ahlgrim et al. (2005)
    # "A Financial Planning Tool for Young Households"
    DEFAULT_CORRELATION_MATRIX = np.array([
        #  Short  Infl   RE    Long  Equity
        [  1.00,  0.25,  0.35,  0.80,  0.15],  # Short-term rates
        [  0.25,  1.00,  0.45,  0.30,  0.10],  # Inflation
        [  0.35,  0.45,  1.00,  0.40,  0.50],  # Real Estate
        [  0.80,  0.30,  0.40,  1.00,  0.20],  # Long-term rates
        [  0.15,  0.10,  0.50,  0.20,  1.00],  # Equity excess returns
    ])

    DEFAULT_ASSET_NAMES = [
        'short_rate',
        'inflation',
        'real_estate',
        'long_rate',
        'equity'
    ]

    def __init__(
        self,
        correlation_matrix: Optional[np.ndarray] = None,
        asset_names: Optional[list] = None,
        n_scenarios: int = 1000,
        n_steps: int = 120,
        use_antithetic: bool = True,
        random_seed: Optional[int] = None
    ):
        """
        Initialize correlated random generator.

        Args:
            correlation_matrix: Correlation matrix (n_assets × n_assets).
                               If None, uses default matrix.
            asset_names: Names of asset classes. If None, uses defaults.
            n_scenarios: Number of Monte Carlo scenarios
            n_steps: Number of time steps
            use_antithetic: Whether to use antithetic variates
            random_seed: Random seed for reproducibility
        """
        if correlation_matrix is None:
            self.correlation_matrix = self.DEFAULT_CORRELATION_MATRIX.copy()
        else:
            self.correlation_matrix = np.array(correlation_matrix)

        self.asset_names = asset_names or self.DEFAULT_ASSET_NAMES.copy()
        self.n_assets = len(self.correlation_matrix)
        self.n_scenarios = n_scenarios
        self.n_steps = n_steps
        self.use_antithetic = use_antithetic
        self.random_seed = random_seed

        # Validate inputs
        self._validate_inputs()

        # Compute Cholesky decomposition
        self.cholesky_matrix = self._compute_cholesky()

        # Set random seed if provided
        if random_seed is not None:
            np.random.seed(random_seed)

    def _validate_inputs(self):
        """Validate input parameters."""
        # Check correlation matrix is square
        if self.correlation_matrix.shape[0] != self.correlation_matrix.shape[1]:
            raise ValueError(
                f"Correlation matrix must be square, got shape {self.correlation_matrix.shape}"
            )

        # Check correlation matrix is symmetric
        if not np.allclose(self.correlation_matrix, self.correlation_matrix.T):
            warnings.warn("Correlation matrix is not symmetric, symmetrizing...")
            self.correlation_matrix = (
                self.correlation_matrix + self.correlation_matrix.T
            ) / 2

        # Check diagonal is 1
        if not np.allclose(np.diag(self.correlation_matrix), 1.0):
            warnings.warn("Correlation matrix diagonal is not 1, normalizing...")
            # Normalize to correlation matrix
            std_devs = np.sqrt(np.diag(self.correlation_matrix))
            self.correlation_matrix = self.correlation_matrix / np.outer(std_devs, std_devs)

        # Check positive semi-definite
        eigenvalues = np.linalg.eigvalsh(self.correlation_matrix)
        if np.any(eigenvalues < -1e-8):
            raise ValueError(
                f"Correlation matrix is not positive semi-definite. "
                f"Minimum eigenvalue: {eigenvalues.min()}"
            )

        # Check asset names match
        if len(self.asset_names) != self.n_assets:
            raise ValueError(
                f"Number of asset names ({len(self.asset_names)}) does not match "
                f"correlation matrix size ({self.n_assets})"
            )

    def _compute_cholesky(self) -> np.ndarray:
        """
        Compute Cholesky decomposition of correlation matrix.

        Returns:
            Lower triangular Cholesky matrix
        """
        try:
            # Compute Cholesky decomposition (lower triangular)
            L = np.linalg.cholesky(self.correlation_matrix)
            return L
        except np.linalg.LinAlgError:
            # If Cholesky fails, add small diagonal to make positive definite
            warnings.warn(
                "Correlation matrix is not positive definite, adding small diagonal..."
            )
            epsilon = 1e-6
            regularized = self.correlation_matrix + epsilon * np.eye(self.n_assets)
            return np.linalg.cholesky(regularized)

    def generate(
        self,
        rate_residuals: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
        Generate correlated random shocks for all asset classes.

        Args:
            rate_residuals: Optional pre-generated interest rate residuals
                           from Hull-White model (n_scenarios × n_steps).
                           If provided, these are used for the first asset
                           class (short rates) to ensure consistency.

        Returns:
            Dictionary containing:
                - 'shocks': 3D array of correlated shocks (n_assets × n_scenarios × n_steps)
                - 'asset_names': List of asset class names
                - 'correlation_matrix': The correlation matrix used
        """
        # Determine number of scenarios (ensure even for antithetic)
        n_sim = self.n_scenarios // 2 * 2 if self.use_antithetic else self.n_scenarios

        # Generate independent standard normal variates
        # Shape: (n_assets × n_scenarios × n_steps)

        if rate_residuals is not None:
            # Use provided interest rate residuals for first asset class
            # rate_residuals shape: (n_scenarios, n_steps)
            n_sim = rate_residuals.shape[0]
            n_steps_residuals = rate_residuals.shape[1]

            # Update n_steps if different
            if n_steps_residuals != self.n_steps:
                self.n_steps = n_steps_residuals

            independent_shocks = self._generate_independent_shocks(
                n_assets=self.n_assets - 1,  # Exclude first asset (rates)
                n_scenarios=n_sim,
                n_steps=self.n_steps
            )
            # Prepend rate residuals
            # Reshape rate_residuals from (n_scenarios, n_steps) to (1, n_scenarios, n_steps)
            rate_residuals_3d = rate_residuals[np.newaxis, :, :]
            independent_shocks = np.vstack([
                rate_residuals_3d,
                independent_shocks
            ])
        else:
            # Generate all shocks independently
            independent_shocks = self._generate_independent_shocks(
                n_assets=self.n_assets,
                n_scenarios=n_sim,
                n_steps=self.n_steps
            )

        # Apply correlation structure using Cholesky decomposition
        correlated_shocks = self._apply_correlation(independent_shocks)

        return {
            'shocks': correlated_shocks,
            'asset_names': self.asset_names,
            'correlation_matrix': self.correlation_matrix.copy()
        }

    def _generate_independent_shocks(
        self,
        n_assets: int,
        n_scenarios: int,
        n_steps: int
    ) -> np.ndarray:
        """
        Generate independent standard normal shocks.

        Args:
            n_assets: Number of asset classes
            n_scenarios: Number of scenarios
            n_steps: Number of time steps

        Returns:
            3D array of shape (n_assets, n_scenarios, n_steps)
        """
        if self.use_antithetic:
            # Generate half the scenarios
            n_half = n_scenarios // 2
            shocks_half = np.random.normal(
                loc=0, scale=1, size=(n_assets, n_half, n_steps)
            )
            # Create antithetic variates
            shocks = np.concatenate([shocks_half, -shocks_half], axis=1)
        else:
            # Generate all scenarios independently
            shocks = np.random.normal(
                loc=0, scale=1, size=(n_assets, n_scenarios, n_steps)
            )

        return shocks

    def _apply_correlation(self, independent_shocks: np.ndarray) -> np.ndarray:
        """
        Apply correlation structure to independent shocks using Cholesky.

        For each time step t:
            ε_correlated[:, :, t] = L @ ε_independent[:, :, t]

        Args:
            independent_shocks: Independent shocks (n_assets × n_scenarios × n_steps)

        Returns:
            Correlated shocks (n_assets × n_scenarios × n_steps)
        """
        n_assets, n_scenarios, n_steps = independent_shocks.shape
        correlated_shocks = np.zeros_like(independent_shocks)

        # Apply Cholesky transformation at each time step
        for t in range(n_steps):
            # Extract independent shocks at time t: (n_assets × n_scenarios)
            epsilon_t = independent_shocks[:, :, t]

            # Apply correlation: L @ ε
            # L is (n_assets × n_assets), ε is (n_assets × n_scenarios)
            correlated_t = self.cholesky_matrix @ epsilon_t

            # Store result
            correlated_shocks[:, :, t] = correlated_t

        return correlated_shocks

    def get_asset_shocks(
        self,
        shocks_cube: np.ndarray,
        asset_name: str
    ) -> np.ndarray:
        """
        Extract shocks for a specific asset class.

        Args:
            shocks_cube: Full 3D shocks array
            asset_name: Name of the asset class

        Returns:
            2D array of shocks for the asset (n_scenarios × n_steps)
        """
        if asset_name not in self.asset_names:
            raise ValueError(
                f"Asset '{asset_name}' not found. Available: {self.asset_names}"
            )

        asset_idx = self.asset_names.index(asset_name)
        return shocks_cube[asset_idx, :, :]

    def verify_correlation(self, shocks_cube: np.ndarray) -> pd.DataFrame:
        """
        Verify that generated shocks have the desired correlation structure.

        Args:
            shocks_cube: Generated shocks (n_assets × n_scenarios × n_steps)

        Returns:
            DataFrame showing actual vs. target correlations
        """
        n_assets, n_scenarios, n_steps = shocks_cube.shape

        # Flatten scenarios and time for correlation calculation
        # Shape: (n_assets × (n_scenarios * n_steps))
        flattened = shocks_cube.reshape(n_assets, -1)

        # Calculate empirical correlation
        empirical_corr = np.corrcoef(flattened)

        # Create comparison DataFrame
        comparison = pd.DataFrame({
            'Asset_i': [],
            'Asset_j': [],
            'Target_Correlation': [],
            'Empirical_Correlation': [],
            'Difference': []
        })

        for i in range(n_assets):
            for j in range(i + 1, n_assets):
                comparison = pd.concat([comparison, pd.DataFrame({
                    'Asset_i': [self.asset_names[i]],
                    'Asset_j': [self.asset_names[j]],
                    'Target_Correlation': [self.correlation_matrix[i, j]],
                    'Empirical_Correlation': [empirical_corr[i, j]],
                    'Difference': [empirical_corr[i, j] - self.correlation_matrix[i, j]]
                })], ignore_index=True)

        return comparison

    @staticmethod
    def load_correlation_from_excel(filepath: str, sheet_name: str = 'Sheet1') -> np.ndarray:
        """
        Load correlation matrix from Excel file.

        Args:
            filepath: Path to Excel file
            sheet_name: Sheet name containing the correlation matrix

        Returns:
            Correlation matrix as numpy array
        """
        df = pd.read_excel(filepath, sheet_name=sheet_name, index_col=0)
        return df.values

    @staticmethod
    def load_correlation_from_csv(filepath: str) -> np.ndarray:
        """
        Load correlation matrix from CSV file.

        Args:
            filepath: Path to CSV file

        Returns:
            Correlation matrix as numpy array
        """
        df = pd.read_csv(filepath, index_col=0)
        return df.values

    def reorder_assets(self, new_order: list):
        """
        Reorder asset classes in the correlation matrix.

        This is useful when integrating with other models that expect
        a specific ordering (e.g., putting interest rates first).

        Args:
            new_order: List of asset indices in desired order
        """
        if len(new_order) != self.n_assets:
            raise ValueError(
                f"New order must have {self.n_assets} elements, got {len(new_order)}"
            )

        if set(new_order) != set(range(self.n_assets)):
            raise ValueError(
                f"New order must be a permutation of {list(range(self.n_assets))}"
            )

        # Reorder correlation matrix (both rows and columns)
        self.correlation_matrix = self.correlation_matrix[new_order, :][:, new_order]

        # Reorder asset names
        self.asset_names = [self.asset_names[i] for i in new_order]

        # Recompute Cholesky
        self.cholesky_matrix = self._compute_cholesky()


# Example correlation matrices from literature

AHLGRIM_2005_CORRELATION = np.array([
    #  Short  Infl   RE    Long  Equity
    [  1.00,  0.25,  0.35,  0.80,  0.15],  # Short-term rates
    [  0.25,  1.00,  0.45,  0.30,  0.10],  # Inflation
    [  0.35,  0.45,  1.00,  0.40,  0.50],  # Real Estate
    [  0.80,  0.30,  0.40,  1.00,  0.20],  # Long-term rates
    [  0.15,  0.10,  0.50,  0.20,  1.00],  # Equity excess returns
])

# Conservative correlation (lower correlations)
CONSERVATIVE_CORRELATION = np.array([
    [  1.00,  0.15,  0.20,  0.70,  0.10],
    [  0.15,  1.00,  0.30,  0.20,  0.05],
    [  0.20,  0.30,  1.00,  0.25,  0.35],
    [  0.70,  0.20,  0.25,  1.00,  0.15],
    [  0.10,  0.05,  0.35,  0.15,  1.00],
])

# High correlation (stress scenario)
STRESS_CORRELATION = np.array([
    [  1.00,  0.40,  0.50,  0.90,  0.25],
    [  0.40,  1.00,  0.60,  0.45,  0.20],
    [  0.50,  0.60,  1.00,  0.55,  0.65],
    [  0.90,  0.45,  0.55,  1.00,  0.30],
    [  0.25,  0.20,  0.65,  0.30,  1.00],
])

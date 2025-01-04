import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from scipy.stats import gaussian_kde

# Function to calculate Bernstein Polynomial
def bernstein_polynomial(x, coeffs):
    """
    Compute the Bernstein polynomial for a given set of coefficients.
    
    Args:
        x (float or array): The input data (normalized to [0, 1]).
        coeffs (array): Coefficients of the Bernstein polynomial.

    Returns:
        float or array: Value of the polynomial at x.
    """
    n = len(coeffs) - 1
    bernstein_sum = np.sum(
        [c * np.math.comb(n, k) * x**k * (1 - x)**(n - k) for k, c in enumerate(coeffs)], axis=0
    )
    return bernstein_sum

# Objective function to minimize (negative log-likelihood)
def bernstein_loss(coeffs, x_data, x_min, x_max):
    """
    Loss function for Bernstein polynomial fitting based on data.

    Args:
        coeffs (array): Coefficients of the Bernstein polynomial.
        x_data (array): Data to fit.
        x_min (float): Minimum of data range.
        x_max (float): Maximum of data range.

    Returns:
        float: Negative log-likelihood for Bernstein polynomial.
    """
    # Normalize the data to [0, 1]
    x_normalized = (x_data - x_min) / (x_max - x_min)
    pdf_values = bernstein_polynomial(x_normalized, coeffs)
    # Avoid log(0) issues by adding a small value
    pdf_values = np.clip(pdf_values, 1e-10, None)
    return -np.sum(np.log(pdf_values))

# Fit the Bernstein Polynomial to data
def fit_bernstein(data, degree=5):
    """
    Fit Bernstein polynomial of a given degree to the data.

    Args:
        data (array): Input data.
        degree (int): Degree of the Bernstein polynomial.

    Returns:
        array: Coefficients of the fitted Bernstein polynomial.
    """
    x_min, x_max = data.min(), data.max()

    # Initial guess for coefficients (uniform distribution)
    initial_coeffs = np.ones(degree + 1) / (degree + 1)

    # Minimize the negative log-likelihood
    result = minimize(
        bernstein_loss,
        initial_coeffs,
        args=(data, x_min, x_max),
        bounds=[(0, None)] * len(initial_coeffs),  # Ensure non-negativity
        constraints={"type": "eq", "fun": lambda c: np.sum(c) - 1},  # Ensure sum = 1
    )

    if not result.success:
        raise RuntimeError("Bernstein fit failed.")

    return result.x, x_min, x_max

# Plot the Bernstein Polynomial and data
def plot_bernstein(data, coeffs, x_min, x_max, bins=50):
    """
    Plot the data and the fitted Bernstein polynomial.

    Args:
        data (array): Input data.
        coeffs (array): Coefficients of the Bernstein polynomial.
        x_min (float): Minimum of data range.
        x_max (float): Maximum of data range.
        bins (int): Number of histogram bins.
    """
    x_normalized = np.linspace(0, 1, 1000)
    pdf_values = bernstein_polynomial(x_normalized, coeffs)

    # Convert normalized x back to original range
    x_original = x_normalized * (x_max - x_min) + x_min

    # Plot histogram
    plt.figure(figsize=(10, 6))
    plt.hist(data, bins=bins, density=True, alpha=0.6, color="g", label="Data")

    # Plot Bernstein fit
    plt.plot(x_original, pdf_values / (x_max - x_min), color="red", lw=2, label="Bernstein Fit")
    plt.xlabel("pt")
    plt.ylabel("Density")
    plt.title("Bernstein Polynomial Fit")
    plt.legend()
    plt.show()

# Example usage
# Generate synthetic data (use your real data here)
# Uncomment to use loaded data: data = tree["pt"].array(library="np")

# Fit the Bernstein polynomial
degree = 5  # Adjust the degree as needed
coeffs, x_min, x_max = fit_bernstein(data, degree=degree)

# Plot the result
plot_bernstein(data, coeffs, x_min, x_max)


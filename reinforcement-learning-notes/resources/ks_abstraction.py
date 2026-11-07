"""Reproduce the Krusell–Smith state-abstraction example in Chapter 5."""

import argparse
from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.request import urlopen

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq


NOTEBOOK_COMMIT = "67221bda0b90400a85a584ef8bb4ad38a3e83b64"
NOTEBOOK_URL = (
    "https://raw.githubusercontent.com/ChennoShen239/compecon-notes/"
    f"{NOTEBOOK_COMMIT}/materials/lec05/KSMethod.ipynb"
)
NOTEBOOK_SHA256 = "05fbb914fe4f140e2ea945e872c4202e90d4d3aa0923ec05f9999d883bfd25b9"
SEED = 42
PERIOD = 1000
MIDDLE_FRACTION_MOVED = 0.5
ACTION_XTOL = 1e-12
TIGHT_POLICY_TOL = 1e-10


def load_benchmark(notebook_path):
    if notebook_path is None:
        with urlopen(NOTEBOOK_URL, timeout=30) as response:
            notebook = response.read()
    else:
        notebook = notebook_path.read_bytes()
    if sha256(notebook).hexdigest() != NOTEBOOK_SHA256:
        raise ValueError("The notebook does not match the pinned SHA-256.")

    cells = json.loads(notebook)["cells"]
    scope = {"__name__": "ks_notebook"}

    def run_cells(*indices):
        for index in indices:
            source = "".join(cells[index]["source"])
            exec(compile(source, f"KSMethod.ipynb cell {index}", "exec"), scope)

    # Run definitions and settings only. The notebook's demonstrations print summaries.
    with redirect_stdout(StringIO()):
        run_cells(1)
        scope["jax"].config.update("jax_platforms", "cpu")
        run_cells(3, 5, 7, 9, 14)
        # Reconstruct the joint law before loading the household solver settings.
        # Axes of the conditional law are (current z, next z, current e).
        unemployment = np.asarray(scope["params"].ur_vals)
        stay_unemployed = np.array([[0.6, 0.25], [0.75, 1 / 3]])
        become_unemployed = (
            unemployment[None, :] - unemployment[:, None] * stay_unemployed
        ) / (1 - unemployment[:, None])
        p_unemployed = np.stack((stay_unemployed, become_unemployed), axis=-1)
        p_aggregate = np.array([[0.875, 0.125], [0.125, 0.875]])
        joint = (
            p_aggregate[:, None, :, None]
            * np.stack((p_unemployed, 1 - p_unemployed), axis=-1).transpose(0, 2, 1, 3)
        ).reshape(4, 4)
        np.testing.assert_allclose(joint.sum(axis=1), 1, rtol=0, atol=1e-12)
        scope["shocks"] = scope["build_shock_process"](scope["jnp"].asarray(joint))
        run_cells(18, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 48, 52, 60, 62)
    return SimpleNamespace(**scope)


def fit_population_policy(ks, aggregate, employment, initial_capital):
    solution = ks.solve_ks_model(
        ks.B0, ks.policy_init, initial_capital, aggregate, employment, ks.params,
        ks.grids, ks.shocks, ks.household, ks.simulation, ks.solver_config, ks.outer_config,
    )
    residual = solution["history"][-1]["diff_B"]
    if not residual <= ks.outer_config.tol_B:
        raise RuntimeError(f"Forecast coefficient iteration ended with residual {residual:g}.")

    # The notebook updates the coefficients after solving for its last policy.
    coefficients = solution["B"]
    policy, _, iterations, difference = ks.solve_individual_problem(
        coefficients, solution["policy"], ks.params, ks.grids, ks.shocks,
        ks.household, ks.solver_config,
    )
    if not float(difference) <= ks.solver_config.tol_policy:
        raise RuntimeError(f"Household policy iteration ended with residual {difference:g}.")
    resources = np.asarray(ks.household.resources)
    if not np.all(
        (policy >= ks.grids.k_min) & (policy <= ks.grids.k_max)
        & np.where(resources > 0, policy < resources, policy == 0)
    ):
        raise RuntimeError("The fitted policy violates the capital or consumption bounds.")

    diagnostics = {
        "forecast_coefficients": np.asarray(coefficients).tolist(),
        "forecast_coefficient_residual": residual,
        "forecast_iterations": len(solution["history"]),
        "policy_update_sup_norm": float(difference),
        "final_policy_iterations": int(iterations),
    }
    return policy, coefficients, diagnostics


def population_choices(ks, policy, capital, employment, z_index, K):
    choices = [
        ks.interp_2d_policy(policy[:, :, z_index, e], capital, K, ks.grids)
        for e in (0, 1)
    ]
    return np.where(employment == 0, *choices)


def reweight_employed(capital, employment, unemployment_rate):
    weights = np.where(
        employment == 0, unemployment_rate / np.count_nonzero(employment == 0),
        (1 - unemployment_rate) / np.count_nonzero(employment == 1),
    )
    employed = np.flatnonzero(employment == 1)
    employed = employed[np.argsort(capital[employed], kind="stable")]
    tail_size = len(employed) // 5
    low, middle, high = np.split(employed, (tail_size, len(employed) - tail_size))
    means = np.array([capital[group].mean() for group in (low, middle, high)])
    if not means[0] < means[1] < means[2]:
        raise RuntimeError("The employed households need three distinct group means.")

    mass_moved = MIDDLE_FRACTION_MOVED * weights[middle].sum()
    low_share = (means[2] - means[1]) / (means[2] - means[0])
    reweighted = weights.copy()
    reweighted[middle] *= 1 - MIDDLE_FRACTION_MOVED
    reweighted[low] += mass_moved * low_share / len(low)
    reweighted[high] += mass_moved * (1 - low_share) / len(high)
    reweighting = {
        "tail_size": tail_size,
        "fraction_of_middle_mass_moved": MIDDLE_FRACTION_MOVED,
        "mass_moved": float(mass_moved),
        "group_mean_capital": means.tolist(),
    }
    focal_index = employed[len(employed) // 2]
    return weights, reweighted, focal_index, reweighting


def advance(ks, capital, employment, z_index, weights, next_capital):
    mass = weights.sum()
    unemployment = weights[employment == 0].sum()
    K = np.dot(weights, capital)
    K_next = np.dot(weights, next_capital)
    if not np.all(weights > 0):
        raise RuntimeError("All occupied holdings must retain positive weight.")
    np.testing.assert_allclose(mass, 1, rtol=0, atol=1e-12)
    np.testing.assert_allclose(unemployment, ks.params.ur_vals[z_index], rtol=0, atol=1e-12)
    next_unemployment = []
    for z_next in (0, 1):
        probability = np.asarray(ks.shocks.P_cond_unemp[z_index, z_next])[employment]
        next_weights = weights[:, None] * np.stack((probability, 1 - probability), axis=-1)
        next_unemployment.append(float(next_weights[:, 0].sum()))
        np.testing.assert_allclose(next_weights.sum(), 1, rtol=0, atol=1e-12)
        np.testing.assert_allclose(next_weights.sum(axis=1) @ next_capital, K_next,
                                   rtol=0, atol=1e-12)
    np.testing.assert_allclose(next_unemployment, ks.params.ur_vals, rtol=0, atol=1e-12)
    return {
        "mass": float(mass),
        "min_weight": float(weights.min()),
        "unemployment_rate": float(unemployment),
        "K": float(K),
        "capital_variance": float(np.dot(weights, (capital - K) ** 2)),
        "K_next": float(K_next),
        "next_unemployment_rates": next_unemployment,
    }


def bellman_derivative(ks, policy, resources, assets, probabilities, K_next):
    """Differentiate current log utility plus the integrated envelope continuation."""
    if not ks.grids.km_min < K_next < ks.grids.km_max:
        raise RuntimeError("The next aggregate capital is outside the policy grid.")

    future_z, future_e = np.asarray(ks.solver_config.future_states).T
    rent, wage = ks.prices_from_capital(K_next, future_z, ks.params)
    gross_return = np.asarray(1 + rent - ks.params.delta)
    income = np.asarray(ks.net_labor_income(wage, future_z, future_e, ks.params))
    saving = np.column_stack([
        ks.interp_2d_policy(policy[:, :, z, e], assets, K_next, ks.grids)
        for z, e in zip(future_z, future_e)
    ])
    consumption = assets[:, None] * gross_return + income - saving
    # For fixed K', consumption is affine between the own-capital knots.
    if not (
        np.all(consumption[0, future_e == 0] == 0)
        and np.all(consumption[0, future_e == 1] > 0)
        and np.all(consumption[1:] > 0)
        and np.all(np.diff(consumption, axis=0) >= 0)
    ):
        raise RuntimeError("Reference consumption is not positive and nondecreasing on (0, m].")

    def derivative(a):
        c = np.array([np.interp(a, assets, values) for values in consumption.T])
        return -1 / (resources - a) + ks.params.beta * (probabilities @ (gross_return / c))

    return derivative


def solve_bellman_decision(ks, policy, resources, z_index, e, next_aggregates):
    if not 0 < resources <= ks.grids.k_max:
        raise RuntimeError("The action interval must lie within the own-capital grid.")
    grid = np.asarray(ks.grids.k_grid)
    assets = np.append(grid[grid < resources], resources)
    probabilities = np.asarray(ks.shocks.P_joint[z_index, e]).ravel()
    derivative_A, derivative_B = [
        bellman_derivative(ks, policy, resources, assets, probabilities, K_next)
        for K_next in next_aggregates
    ]

    def average_derivative(a):
        return (derivative_A(a) + derivative_B(a)) / 2

    lower = resources * 1e-12
    upper = resources - lower
    actions = []
    for derivative in (derivative_A, derivative_B, average_derivative):
        if not derivative(lower) > 0 > derivative(upper):
            raise RuntimeError("The Bellman derivative does not bracket an interior maximum.")
        actions.append(brentq(derivative, lower, upper, xtol=ACTION_XTOL))
    a_A, a_B, shared = actions

    losses = []
    errors = []
    for derivative, optimum in zip((derivative_A, derivative_B), (a_A, a_B)):
        low, high = sorted((optimum, shared))
        knots = assets[(low < assets) & (assets < high)]
        # Integrate the derivative to avoid subtracting two nearly equal value levels.
        loss, error = quad(derivative, shared, optimum, points=knots, epsabs=1e-18)
        losses.append(loss)
        errors.append(error)

    return {
        "state_optimal_actions": [a_A, a_B],
        "shared_action": shared,
        "shared_action_losses": losses,
        "action_root_xtol": ACTION_XTOL,
        "max_loss_quadrature_error_estimate": max(errors),
    }


def run_experiment(notebook_path):
    ks = load_benchmark(notebook_path)
    key = ks.jax.random.PRNGKey(SEED)
    key, aggregate = ks.simulate_agshock(key, ks.simulation.T, ks.shocks)
    employment = ks.simulate_idshock(key, aggregate, ks.simulation.N, ks.shocks, ks.params)
    initial_capital = ks.jnp.full((ks.simulation.N,), ks.kss)
    policy, coefficients, diagnostics = fit_population_policy(
        ks, aggregate, employment, initial_capital,
    )

    # The last carry is k_t when the scan takes shocks dated 0 through t-1.
    K_history, capital = ks.simulate_aggregate_path(
        policy, aggregate[:PERIOD], employment[:PERIOD], initial_capital, ks.grids,
    )
    if not np.all((K_history > ks.grids.km_min) & (K_history < ks.grids.km_max)):
        raise RuntimeError("The snapshot path touches the aggregate capital grid bounds.")
    capital = np.asarray(capital)
    status = np.asarray(employment[PERIOD])
    z_index = int(aggregate[PERIOD])
    K_panel = capital.mean()
    if not np.all((capital >= ks.grids.k_min) & (capital <= ks.grids.k_max)):
        raise RuntimeError("The snapshot holdings are outside the policy grid.")
    np.testing.assert_allclose(
        population_choices(ks, policy, capital, status, z_index, K_panel),
        ks.simulate_aggregate_path(
            policy, aggregate[PERIOD:PERIOD + 1], employment[PERIOD:PERIOD + 1],
            capital, ks.grids,
        )[1],
        rtol=0, atol=1e-12,
    )

    params = ks.params
    unemployment = float(params.ur_vals[z_index])
    weights_A, weights_B, focal, reweighting = reweight_employed(capital, status, unemployment)
    K = float(weights_A @ capital)
    np.testing.assert_allclose(weights_B @ capital, K, rtol=0, atol=1e-12)
    if not ks.grids.km_min < K < ks.grids.km_max:
        raise RuntimeError("The matched aggregate capital is outside the policy grid.")
    rent, wage = ks.prices_from_capital(K, z_index, params)
    labor_income = ks.net_labor_income(wage, z_index, status, params)
    available = (1 + rent - params.delta) * capital + labor_income
    next_capital = population_choices(ks, policy, capital, status, z_index, K)
    if not np.all(
        (next_capital >= ks.grids.k_min) & (next_capital <= ks.grids.k_max)
        & (next_capital < available)
    ):
        raise RuntimeError("The population choices violate the capital or consumption bounds.")
    distributions = [
        advance(ks, capital, status, z_index, weights, next_capital)
        for weights in (weights_A, weights_B)
    ]

    k = float(capital[focal])
    e = int(status[focal])
    resources = float(available[focal])
    next_aggregates = [item["K_next"] for item in distributions]
    decision = solve_bellman_decision(ks, policy, resources, z_index, e, next_aggregates)

    # Hold the matched states and forecast coefficients fixed while tightening the solver.
    tight_config = ks.solver_config._replace(tol_policy=TIGHT_POLICY_TOL)
    tight_policy, _, _, difference = ks.solve_individual_problem(
        coefficients, policy, params, ks.grids, ks.shocks, ks.household, tight_config,
    )
    if not float(difference) <= TIGHT_POLICY_TOL:
        raise RuntimeError(f"The tighter household solve ended with residual {difference:g}.")
    tight_choices = population_choices(ks, tight_policy, capital, status, z_index, K)
    tight_aggregates = [
        advance(ks, capital, status, z_index, weights, tight_choices)["K_next"]
        for weights in (weights_A, weights_B)
    ]
    tight_decision = solve_bellman_decision(ks, tight_policy, resources, z_index, e, tight_aggregates)
    actions = [*decision["state_optimal_actions"], decision["shared_action"]]
    tight_actions = [*tight_decision["state_optimal_actions"], tight_decision["shared_action"]]
    decision["tight_policy_check"] = {
        "policy_update_tolerance": TIGHT_POLICY_TOL,
        "policy_update_sup_norm": float(difference),
        "K_next_gap_change": abs(
            (tight_aggregates[1] - tight_aggregates[0]) - (next_aggregates[1] - next_aggregates[0])
        ),
        "max_action_change": max(abs(a - b) for a, b in zip(actions, tight_actions)),
        "max_loss_change": max(
            abs(a - b) for a, b in zip(decision["shared_action_losses"],
                                      tight_decision["shared_action_losses"])
        ),
    }

    return {
        "benchmark": {
            "notebook_commit": NOTEBOOK_COMMIT,
            "notebook_sha256": NOTEBOOK_SHA256,
            "discount_factor": params.beta,
            "risk_aversion": params.sigma,
            "capital_share": params.alpha,
            "depreciation": params.delta,
            "labor_endowment": params.l_bar,
            "unemployment_benefit_rate": params.benefit_rate,
            "productivity": np.asarray(params.z_vals).tolist(),
            "unemployment_rates": np.asarray(params.ur_vals).tolist(),
            "joint_transition": np.asarray(ks.shocks.P).tolist(),
            **diagnostics,
        },
        "simulation": {
            "seed": SEED,
            "period": PERIOD,
            "households": ks.simulation.N,
            "periods": ks.simulation.T,
            "discard_for_fit": ks.simulation.ndiscard,
            "unweighted_K": float(K_panel),
            "unweighted_unemployment_rate": float(np.mean(status == 0)),
        },
        "reweighting": reweighting,
        "focal": {
            "k": k, "employment": e, "productivity": float(params.z_vals[z_index]),
            "unemployment_rate": unemployment, "K": K, "resources": resources,
            "action": k, "reward": float(np.log(resources - k)),
        },
        "distributions": distributions,
        "decision": decision,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook", type=Path, help="Local copy of the pinned notebook.")
    args = parser.parse_args()
    print(json.dumps(run_experiment(args.notebook), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

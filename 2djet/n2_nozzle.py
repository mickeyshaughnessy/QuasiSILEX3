#!/usr/bin/env python3
"""Mass-only separation of N2 isotopologues in a 2D narrow-to-wide nozzle.

The steady continuum nozzle does not separate isotopes: gamma is the same for
14N2, 14N15N and 15N2, so the Mach-number field is mass-independent and every
species is locked to one bulk velocity. Spatial separation appears only after
collisions freeze. The shared directed speed stays, and the leftover random
transverse speed scales as 1/sqrt(m). Heavier molecules stay closer to the axis.

This script computes that free-flight stage analytically and checks it with a
Monte Carlo of straight-line trajectories.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Representative atmospheric abundances (IUPAC / Wikipedia conventional values).
# Natural nitrogen has two stable nuclides. A stream of N2 therefore contains
# three isotopologues. 13N (half-life 9.97 min) is not part of that stream.
ABUND_14 = 0.99636
ABUND_15 = 0.00364
MASS_14 = 14.00307400446  # u
MASS_15 = 15.0001088989  # u

SPECIES = (
    {
        "name": "14N2",
        "label": r"$^{14}$N$_2$",
        "mass_u": 2 * MASS_14,
        "feed": ABUND_14**2,
        "color": "#1f4e79",
    },
    {
        "name": "14N15N",
        "label": r"$^{14}$N$^{15}$N",
        "mass_u": MASS_14 + MASS_15,
        "feed": 2 * ABUND_14 * ABUND_15,
        "color": "#c47b00",
    },
    {
        "name": "15N2",
        "label": r"$^{15}$N$_2$",
        "mass_u": 2 * MASS_15,
        "feed": ABUND_15**2,
        "color": "#9b2226",
    },
)

GAMMA = 1.4
R_GAS = 8.314462618  # J/mol/K
T0 = 300.0  # K, stagnation temperature
MACH = 5.0  # hydrodynamic Mach number at the quitting surface
# Nozzle wall half-angles to compare. 0 deg is a parallel beam (thermal bloom only).
WALL_ANGLES_DEG = (0.0, 2.0, 5.0, 15.0, 30.0)


def isentropic_state(mach: float, t0: float, mass_u_mean: float) -> dict:
    """Shared bulk state of a collisionally locked diatomic mixture."""
    factor = 1.0 + 0.5 * (GAMMA - 1.0) * mach**2
    temperature = t0 / factor
    mass_kg = mass_u_mean * 1.0e-3
    sound_speed = math.sqrt(GAMMA * R_GAS * temperature / mass_kg)
    bulk_speed = mach * sound_speed
    return {
        "temperature_K": temperature,
        "sound_speed_m_s": sound_speed,
        "bulk_speed_m_s": bulk_speed,
        "mach": mach,
    }


def speed_ratio(bulk_speed: float, temperature: float, mass_u: float) -> float:
    """S = u / sqrt(2 kT/m). Angular width of the thermal bloom scales as 1/S."""
    mass_kg = mass_u * 1.0e-3
    thermal = math.sqrt(2.0 * R_GAS * temperature / mass_kg)
    return bulk_speed / thermal


def gaussian_sigma(speed_ratio_value: float) -> float:
    """Std-dev of the thermal angle (radians) for a 1D Maxwellian v_y."""
    return 1.0 / (speed_ratio_value * math.sqrt(2.0))


def _phi(z: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2.0)))


def transmission(skim_half_angle: float, wall_half_angle: float, sigma: float) -> float:
    """Fraction of one species with |theta_geom + theta_thermal| < skim angle.

    theta_geom is uniform on [-wall, wall] (radial source flow in a straight
    wedge). theta_thermal is Normal(0, sigma). A wall angle of 0 is a parallel
    beam and the fraction reduces to erf(S * alpha).
    """
    if skim_half_angle <= 0.0:
        return 0.0
    if wall_half_angle <= 0.0:
        z = skim_half_angle / sigma
        return math.erf(z / math.sqrt(2.0))

    mu = np.linspace(-wall_half_angle, wall_half_angle, 801)
    passed = _phi((skim_half_angle - mu) / sigma) - _phi((-skim_half_angle - mu) / sigma)
    return float(np.trapezoid(passed, mu) / (2.0 * wall_half_angle))


def axial_density_ratio(wall: float, sigma_heavy: float, sigma_light: float) -> float:
    """P_heavy(0) / P_light(0). Equals sqrt(m_h/m_l) when the wall angle is 0."""
    if wall <= 0.0:
        # P(0) = 1 / (sigma * sqrt(2 pi))
        return sigma_light / sigma_heavy

    def p0(sigma: float) -> float:
        # Average of the gaussian over geometric angle, evaluated at theta = 0.
        mu = np.linspace(-wall, wall, 801)
        dens = np.exp(-0.5 * (mu / sigma) ** 2) / (sigma * math.sqrt(2.0 * math.pi))
        return float(np.trapezoid(dens, mu) / (2.0 * wall))

    return p0(sigma_heavy) / p0(sigma_light)


def atom_fraction_15(mole_fractions: dict) -> float:
    """Fraction of nitrogen atoms that are 15N."""
    n28 = mole_fractions["14N2"]
    n29 = mole_fractions["14N15N"]
    n30 = mole_fractions["15N2"]
    return (n29 + 2.0 * n30) / (2.0 * (n28 + n29 + n30))


def composition_from_transmission(transmissions: dict) -> dict:
    weights = {sp["name"]: sp["feed"] * transmissions[sp["name"]] for sp in SPECIES}
    total = sum(weights.values())
    return {name: weight / total for name, weight in weights.items()}


def run_monte_carlo(
    bulk_speed: float,
    temperature: float,
    wall_half_angle: float,
    n_per_species: int,
    quench_x: float,
    detector_x: float,
    rng: np.random.Generator,
) -> dict:
    """Straight-line flight from a flat quitting plane to a detector plane.

    Radial source flow sets the directed velocity along the ray from the
    virtual origin. An independent thermal v_y is then added. Isotopes share
    the directed speed and differ only in the thermal draw.
    """
    records = {}
    for sp in SPECIES:
        sigma_v = math.sqrt(R_GAS * temperature / (sp["mass_u"] * 1.0e-3))
        # Uniform in geometric angle, mapped onto the flat quitting plane.
        theta = rng.uniform(-wall_half_angle, wall_half_angle, n_per_species)
        y0 = quench_x * np.tan(theta)
        # Thermal kick perpendicular to the ray. The ray already carries the
        # shared bulk speed, so only this kick depends on mass.
        v_thermal = rng.normal(0.0, sigma_v, n_per_species)
        v_x = bulk_speed * np.cos(theta) - v_thermal * np.sin(theta)
        v_y = bulk_speed * np.sin(theta) + v_thermal * np.cos(theta)
        flight = (detector_x - quench_x) / v_x
        y_det = y0 + v_y * flight
        records[sp["name"]] = {
            "theta_deg": np.degrees(np.arctan2(v_y, v_x)),
            "y_det": y_det,
            "flight_s": flight,
        }
    return records


def main() -> None:
    out_dir = Path(__file__).resolve().parent / "figures"
    out_dir.mkdir(exist_ok=True)

    feed = {sp["name"]: sp["feed"] for sp in SPECIES}
    mass_mean = sum(sp["feed"] * sp["mass_u"] for sp in SPECIES)
    state = isentropic_state(MACH, T0, mass_mean)

    print("N2 isotopologues in a 2D diverging nozzle")
    print("mechanism: shared directed speed, thermal spread scales as 1/sqrt(m)")
    print()
    print(f"stagnation temperature    {T0:.1f} K")
    print(f"hydrodynamic Mach         {MACH:.1f}")
    print(f"frozen temperature        {state['temperature_K']:.2f} K")
    print(f"mixture molar mass        {mass_mean:.5f} u")
    print(f"shared bulk speed         {state['bulk_speed_m_s']:.2f} m/s")
    print(f"feed 15N atom fraction    {atom_fraction_15(feed):.6e}")
    print()
    print(f"{'species':<10} {'mass u':>10} {'feed':>12} {'S':>8} {'sigma deg':>10} {'sqrt(m/m28)':>12}")

    sigmas = {}
    ratios = {}
    for sp in SPECIES:
        s_value = speed_ratio(state["bulk_speed_m_s"], state["temperature_K"], sp["mass_u"])
        sigma = gaussian_sigma(s_value)
        sigmas[sp["name"]] = sigma
        ratios[sp["name"]] = s_value
        mass_factor = math.sqrt(sp["mass_u"] / SPECIES[0]["mass_u"])
        print(
            f"{sp['name']:<10} {sp['mass_u']:10.5f} {sp['feed']:12.6e} "
            f"{s_value:8.4f} {math.degrees(sigma):10.3f} {mass_factor:12.5f}"
        )

    # Uncoupled check: each gas converts its own enthalpy, so u scales as
    # 1/sqrt(m) and S is identical. Angular separation is then exactly zero.
    print()
    print("uncoupled limit (each isotopologue expands as its own gas):")
    s_uncoupled = []
    for sp in SPECIES:
        own = isentropic_state(MACH, T0, sp["mass_u"])
        s_value = speed_ratio(own["bulk_speed_m_s"], own["temperature_K"], sp["mass_u"])
        s_uncoupled.append(s_value)
        print(f"  {sp['name']:<10} u = {own['bulk_speed_m_s']:.2f} m/s   S = {s_value:.6f}")
    print(f"  spread in S: {max(s_uncoupled) - min(s_uncoupled):.3e} (numerical noise)")

    light = SPECIES[0]["name"]
    print()
    print("axial enrichment beta = (n_i/n_28)_product / (n_i/n_28)_feed")
    print("beta -> sqrt(m_i/m_28) only for a vanishing on-axis cut and a parallel beam")
    header = f"{'wall deg':>10} {'skim deg':>10} " + " ".join(f"{sp['name']:>12}" for sp in SPECIES[1:])
    print(header)
    skim_table = (0.5, 2.0, 5.0, 10.0, 20.0)
    for wall_deg in WALL_ANGLES_DEG:
        wall = math.radians(wall_deg)
        for skim_deg in skim_table:
            skim = math.radians(skim_deg)
            trans = {
                sp["name"]: transmission(skim, wall, sigmas[sp["name"]]) for sp in SPECIES
            }
            betas = {sp["name"]: trans[sp["name"]] / trans[light] for sp in SPECIES}
            cols = " ".join(f"{betas[sp['name']]:12.6f}" for sp in SPECIES[1:])
            print(f"{wall_deg:10.1f} {skim_deg:10.1f} {cols}")

    # Practical single-stage cut: parallel beam, skimmer passing ~10% of 14N2.
    # Solve roughly by scanning.
    wall = 0.0
    target = 0.10
    best_skim = None
    best_err = 1.0
    for skim_deg in np.linspace(0.05, 15.0, 2000):
        skim = math.radians(float(skim_deg))
        passed = transmission(skim, wall, sigmas[light])
        err = abs(passed - target)
        if err < best_err:
            best_err = err
            best_skim = float(skim_deg)
    skim = math.radians(best_skim)
    trans = {sp["name"]: transmission(skim, wall, sigmas[sp["name"]]) for sp in SPECIES}
    product = composition_from_transmission(trans)
    print()
    print(
        f"parallel beam, skimmer half-angle {best_skim:.3f} deg "
        f"(passes {trans[light]*100:.2f}% of 14N2)"
    )
    print(f"{'species':<10} {'feed':>12} {'product':>12} {'beta vs 14N2':>14} {'cut':>10}")
    for sp in SPECIES:
        beta = (product[sp["name"]] / product[light]) / (sp["feed"] / feed[light])
        print(
            f"{sp['name']:<10} {sp['feed']:12.6e} {product[sp['name']]:12.6e} "
            f"{beta:14.6f} {trans[sp['name']]:10.4f}"
        )
    print(f"feed 15N atom fraction     {atom_fraction_15(feed):.6e}")
    print(f"product 15N atom fraction  {atom_fraction_15(product):.6e}")
    print(
        "stages of this cut to double the 14N15N/14N2 ratio: "
        f"{math.log(2) / math.log((product['14N15N']/product['14N2']) / (feed['14N15N']/feed['14N2'])):.1f}"
    )

    # ----- figures -----
    plt.rcParams.update({
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 12,
        "figure.dpi": 140,
    })

    theta = np.linspace(-25.0, 25.0, 1201)
    theta_rad = np.radians(theta)

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4))

    # Parallel beam: the distributions nearly overlap. Plot the ratio.
    ax = axes[0]
    pdfs = {}
    for sp in SPECIES:
        sigma = sigmas[sp["name"]]
        pdf = np.exp(-0.5 * (theta_rad / sigma) ** 2) / (sigma * math.sqrt(2.0 * math.pi))
        # Convert to per-degree density for the axis label.
        pdfs[sp["name"]] = pdf * math.pi / 180.0
        ax.plot(theta, pdfs[sp["name"]], color=sp["color"], label=sp["label"], lw=1.8)
    ax.set_xlim(-20, 20)
    ax.set_xlabel("angle from axis (deg)")
    ax.set_ylabel("probability density (1/deg)")
    ax.set_title("parallel beam after Mach 5 freeze-out")
    ax.legend(frameon=False)

    ax = axes[1]
    for sp in SPECIES[1:]:
        ratio = pdfs[sp["name"]] / pdfs[light]
        ax.plot(theta, ratio, color=sp["color"], label=sp["label"] + r" / $^{14}$N$_2$", lw=1.8)
    ax.axhline(1.0, color="0.5", lw=0.8)
    ax.set_xlim(-20, 20)
    ax.set_ylim(0.92, 1.05)
    ax.set_xlabel("angle from axis (deg)")
    ax.set_ylabel("density ratio to $^{14}$N$_2$")
    ax.set_title("heavy enriched on axis, light in the wings")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "angular_ratio.png")
    plt.close(fig)

    # Separation factor versus skimmer angle, several wall openings.
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    skim_deg = np.linspace(0.2, 30.0, 400)
    linestyles = ("-", "--", "-.", ":", (0, (3, 1, 1, 1)))
    for wall_deg, style in zip(WALL_ANGLES_DEG, linestyles):
        wall = math.radians(wall_deg)
        beta = []
        for alpha_deg in skim_deg:
            alpha = math.radians(float(alpha_deg))
            f_heavy = transmission(alpha, wall, sigmas["14N15N"])
            f_light = transmission(alpha, wall, sigmas["14N2"])
            beta.append(f_heavy / f_light)
        ax.plot(
            skim_deg,
            beta,
            linestyle=style,
            lw=1.8,
            label=f"wall half-angle {wall_deg:.0f}°",
        )
    ax.axhline(
        math.sqrt(SPECIES[1]["mass_u"] / SPECIES[0]["mass_u"]),
        color="0.3",
        lw=0.8,
        label=r"$\sqrt{m_{29}/m_{28}}$",
    )
    ax.set_xlabel("skimmer half-angle (deg)")
    ax.set_ylabel(r"separation factor $\beta$ for $^{14}$N$^{15}$N / $^{14}$N$_2$")
    ax.set_title("opening the nozzle washes the mass separation out")
    ax.set_xlim(0, 30)
    ax.set_ylim(1.0, 1.020)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(out_dir / "separation_vs_skimmer.png")
    plt.close(fig)

    # Monte Carlo check at a 5 degree wall, plus the enrichment map.
    rng = np.random.default_rng(7)
    wall_deg = 5.0
    wall = math.radians(wall_deg)
    n_mc = 1_000_000
    mc = run_monte_carlo(
        bulk_speed=state["bulk_speed_m_s"],
        temperature=state["temperature_K"],
        wall_half_angle=wall,
        n_per_species=n_mc,
        quench_x=1.0,
        detector_x=5.0,
        rng=rng,
    )

    print()
    print("Monte Carlo check, 5° wall: rms flight angle")
    print(f"{'species':<10} {'MC rms deg':>12} {'analytic deg':>14}")
    for sp in SPECIES:
        mc_rms = math.degrees(float(np.std(np.radians(mc[sp["name"]]["theta_deg"]))))
        # Uniform geometric angle on [-wall, wall] plus an independent gaussian.
        predicted = math.degrees(math.sqrt(wall**2 / 3.0 + sigmas[sp["name"]] ** 2))
        print(f"{sp['name']:<10} {mc_rms:12.3f} {predicted:14.3f}")

    edges = np.linspace(-24.0, 24.0, 25)
    centers = 0.5 * (edges[:-1] + edges[1:])
    hist = {}
    for sp in SPECIES:
        counts, _ = np.histogram(mc[sp["name"]]["theta_deg"], bins=edges)
        hist[sp["name"]] = counts

    def convolved_pdf(theta_rad: np.ndarray, sigma: float) -> np.ndarray:
        mu = np.linspace(-wall, wall, 601)
        # theta_rad shape (n,), mu shape (m,) -> density shape (n,)
        z = (theta_rad[:, None] - mu[None, :]) / sigma
        gauss = np.exp(-0.5 * z**2) / (sigma * math.sqrt(2.0 * math.pi))
        return np.trapezoid(gauss, mu, axis=1) / (2.0 * wall)

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.axhline(1.0, color="0.5", lw=0.8)
    for sp in SPECIES[1:]:
        ratio = hist[sp["name"]] / hist[light]
        # Poisson error on a ratio of counts.
        err = ratio * np.sqrt(1.0 / hist[sp["name"]] + 1.0 / hist[light])
        ax.errorbar(
            centers,
            ratio,
            yerr=err,
            fmt="o",
            ms=4,
            color=sp["color"],
            lw=0.8,
            label=sp["label"] + " Monte Carlo",
        )
        curve = convolved_pdf(np.radians(centers), sigmas[sp["name"]])
        base = convolved_pdf(np.radians(centers), sigmas[light])
        ax.plot(centers, curve / base, color=sp["color"], lw=1.4)
    ax.set_xlim(-24, 24)
    ax.set_ylim(0.90, 1.10)
    ax.set_xlabel("flight angle (deg)")
    ax.set_ylabel("relative to $^{14}$N$_2$")
    ax.set_title("5° nozzle: heavy on axis, light in the wings")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(out_dir / "monte_carlo_check.png")
    plt.close(fig)

    # A few trajectories so the geometry is visible. Thermal kicks are real,
    # so the three masses do not form visually separate fans.
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    rng_draw = np.random.default_rng(3)
    quench_x = 1.0
    detector_x = 4.0
    wall = math.radians(wall_deg)
    x_wall = np.linspace(0.15, detector_x, 50)
    ax.plot(x_wall, x_wall * math.tan(wall), color="0.2", lw=1.2)
    ax.plot(x_wall, -x_wall * math.tan(wall), color="0.2", lw=1.2)
    ax.axvline(quench_x, color="0.5", ls="--", lw=0.8)
    for sp in SPECIES:
        sigma_v = math.sqrt(R_GAS * state["temperature_K"] / (sp["mass_u"] * 1.0e-3))
        theta0 = rng_draw.uniform(-wall, wall, 24)
        y0 = quench_x * np.tan(theta0)
        v_th = rng_draw.normal(0.0, sigma_v, 24)
        v_x = state["bulk_speed_m_s"] * np.cos(theta0) - v_th * np.sin(theta0)
        v_y = state["bulk_speed_m_s"] * np.sin(theta0) + v_th * np.cos(theta0)
        y1 = y0 + v_y * (detector_x - quench_x) / v_x
        for y_start, y_end in zip(y0, y1):
            ax.plot(
                [quench_x, detector_x],
                [y_start, y_end],
                color=sp["color"],
                alpha=0.35,
                lw=0.8,
            )
    ax.set_xlabel("distance from virtual source")
    ax.set_ylabel("transverse position")
    ax.set_title("free flight after the quitting plane (dashed)")
    fig.tight_layout()
    fig.savefig(out_dir / "trajectories.png")
    plt.close(fig)

    print()
    print(f"figures written to {out_dir}")


if __name__ == "__main__":
    main()

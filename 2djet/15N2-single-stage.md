# Single-stage mass separation of ¹⁵N₂

This note is only the mass difference. No laser, no selective excitation, no condensation. The stage factor is small on purpose. A gaseous-diffusion cascade is how a factor near 1 becomes a real change in assay.

## The gas

Natural nitrogen is 99.636% ¹⁴N and 0.364% ¹⁵N. A random N₂ molecule is one of three isotopologues:

| Molecule | Mass (u) | Mole fraction |
|---|---:|---:|
| ¹⁴N₂ | 28.006 | 0.99273 |
| ¹⁴N¹⁵N | 29.003 | 0.007254 |
| ¹⁵N₂ | 30.000 | 1.325×10⁻⁵ |

¹⁵N₂ is the species this cascade is aimed at. ¹⁴N¹⁵N is enriched by the same jets and has to be carried along in the arithmetic.

## What one nozzle does

Inside the nozzle the three molecules share one bulk velocity. Collisions lock them together, and the Mach field does not depend on mass. They separate only after collisions freeze.

At freeze-out every molecule has the same directed speed. The leftover random sideways speed is √(kT/m). The lighter molecule wanders farther off axis. A slit on the centerline therefore passes a slightly higher fraction of ¹⁵N₂ than of ¹⁴N₂.

The single-stage coefficient used below is that ratio of transmissions:

α₃₀ = t(¹⁵N₂) / t(¹⁴N₂)

α₂₉ = t(¹⁴N¹⁵N) / t(¹⁴N₂)

It is exactly the factor by which the center cut multiplies the abundance ratio against ¹⁴N₂. The ratio update does not depend on how much of each species is in the feed:

R₃₀(after) = α₃₀ · R₃₀(before), &nbsp; R = n(¹⁵N₂) / n(¹⁴N₂)

Same for R₂₉ with α₂₉.

The largest α mass alone can give is the square root of the mass ratio, and only for a parallel beam with a vanishingly narrow slit:

√(m₃₀ / m₂₈) = 1.0350

√(m₂₉ / m₂₈) = 1.0176

A real slit and a real wall angle both come in under that ceiling. Opening the wall spreads every species the same way and washes the mass effect out.

## Reference stage

Mach 5 from 300 K. Freeze-out temperature 50 K. Shared bulk speed 721 m/s. Wall half-angle 5°. Skimmer half-angle 4°, which is a center slit that takes 27.8% of the feed.

| | ¹⁴N₂ | ¹⁴N¹⁵N | ¹⁵N₂ |
|---|---:|---:|---:|
| Speed ratio S | 4.183 | 4.257 | 4.329 |
| Thermal half-width | 9.69° | 9.52° | 9.36° |
| Transmission t | 0.2776 | 0.2809 | 0.2842 |
| α against ¹⁴N₂ | 1 | 1.0121 | 1.0238 |

One pass on natural gas:

| | Feed | Center product |
|---|---:|---:|
| ¹⁵N₂ mole fraction | 1.325×10⁻⁵ | 1.356×10⁻⁵ |
| ¹⁴N¹⁵N mole fraction | 0.007254 | 0.007341 |
| ¹⁵N atom fraction | 0.3640% | 0.3684% |

The wings are the depleted stream. Relative to the wings, the center is richer in ¹⁵N₂ by

α(center/wings) = 1.0333

which is almost the whole square-root ceiling. The 4° slit puts most of that difference on the product side of the cut (α₃₀ = 1.0238) and leaves only a 0.92% depletion in the wings. That asymmetry is what sets the shape of the cascade.

## Repeating the stage

Forward the center cut into an identical jet. After N enriching stages the ratios are

R₃₀(N) = R₃₀(0) · (1.0238)ᴺ

R₂₉(N) = R₂₉(0) · (1.0121)ᴺ

and the mole fractions follow by normalizing R₂₈ = 1, R₂₉, R₃₀. ¹⁴N¹⁵N starts 548 times more abundant than ¹⁵N₂, so it is most of the heavy fraction for a long way up the cascade. ¹⁵N₂ climbs faster, and it does catch up.

| Enriching stages | ¹⁵N₂ | Gain | ¹⁴N¹⁵N |
|---:|---:|---:|---:|
| 0 | 1.33×10⁻⁵ | 1 | 0.725% |
| 10 | 1.68×10⁻⁵ | 1.26 | 0.818% |
| 40 | 3.39×10⁻⁵ | 2.56 | 1.17% |
| 87 | 0.0102% | 7.7 | 2.04% |
| 187 | 0.102% | 77 | 6.51% |
| 291 | 1.01% | 762 | 19.4% |
| 415 | 10.1% | 7.7×10³ | 46.9% |
| 561 | 50.1% | 3.8×10⁴ | 43.1% |

So 1% ¹⁵N₂ is 291 stages at this nozzle, and that product is still about one fifth ¹⁴N¹⁵N. Fifty percent ¹⁵N₂ is 561 stages. The stage count is logarithmic in the desired gain: N = ln(gain) / ln(α), until the heavy fraction is large enough that ¹⁴N₂ stops dominating the mixture.

## Series versus a diffusion cascade

Throwing the wings away at every stage is a series of cuts. Each stage keeps a fraction θ ≈ 0.278 of the molecules, so the feed required per product molecule is

F/P ≈ (1/θ)ᴺ ≈ 3.60ᴺ

| Stages | ¹⁵N₂ in the product | Feed molecules per product |
|---:|---:|---:|
| 40 | 0.0034% | 1.8×10²² |
| 87 | 0.010% | ~10⁴⁸ |
| 291 | 1% | 7.6×10¹⁶¹ |

That is not a plant. Gaseous diffusion has the same problem and solves it the same way: send the depleted stream back to the previous stage, and add a stripping section below the feed so the waste is actually lean.

On this nozzle the wing multiplies the ¹⁵N₂ ratio by

γ₃₀ = (1 − t₃₀) / (1 − t₂₈) = 0.9908

Stripping the waste by a factor of ten takes

N_strip = ln(10) / ln(1/γ₃₀) = 251 stages

Isotope balance then fixes the external feed. With waste at one tenth of the natural ¹⁵N₂ fraction,

F/P = (x_P − x_W) / (x_F − x_W)

| Product ¹⁵N₂ | Enriching stages | Stripping stages | Feed per product |
|---:|---:|---:|---:|
| 0.010% | 87 | 251 | 8.4 |
| 0.10% | 187 | 251 | 86 |
| 1% | 291 | 251 | 847 |
| 10% | 415 | 251 | 8.5×10³ |
| 50% | 561 | 251 | 4.2×10⁴ |

The recycled plant still wants a few hundred stages, because α − 1 is only 0.024. What it no longer wants is a feed that grows as 3.6ᴺ. For a 1% product the recycle cuts the feed from 7.6×10¹⁶¹ molecules per molecule of product down to about 850.

Widening the slit raises θ toward one half and makes the upflow and the downflow easier to match, and it also lowers α. At a 5° wall and an 8° skimmer, θ(¹⁴N₂) = 0.52 and α₃₀ falls to 1.0212. More stages, kinder plumbing. Narrowing the slit raises α toward 1.035 and starves the product stream. The cascade view on the jet page recomputes both numbers from the live Mach, wall, and skimmer.

## What this is not

SILEX does not cascade a 0.4% mass difference in UF₆. The laser changes the effective mass, monomer against cluster, and the quoted stage factors are of order 2. The nozzle in this note has no such lever. Its only coefficient is α₃₀ = 1.0238 at the reference setting, and the way up is the same one gaseous diffusion used: many stages, wings returned.

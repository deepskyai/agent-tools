# Formula reference

Derivations and constants underpinning `gradient.py` and `fuel_uplift.py`.

## Constants

| Constant | Value | Source |
|---|---|---|
| Feet per nautical mile | 6076.11549 | ICAO / NIST |
| Litres per US gallon | 3.785411784 | NIST |
| Kilograms per pound | 0.45359237 | International yard and pound, 1959 |
| Jet A-1 thermal expansion coef. | 0.00070 kg·L⁻¹·°C⁻¹ | ASTM D1250 (linearised around 15 °C) |
| Jet A-1 nominal SG @ 15 °C | 0.800 | ASTM D1655 / DEF STAN 91-091 nominal; spec range 0.775–0.840 |

## Gradient relationships

Eight variables, three independent geometric equations:

```
(1)  d  = GS · t / 60            distance_nm    = gs_kt · time_min / 60
(2)  Δh = ROC · t                altitude_ft    = rate_fpm · time_min
(3)  γ  = Δh / d                 gradient_ft_per_nm = altitude_ft / distance_nm
```

Gradient conversions:

```
γ%        = γ · 100 / 6076.11549                         (ft/NM → %)
θ         = atan(γ% / 100)                               (% → degrees)
ROC       = γ% / 100 · GS · 6076.11549 / 60              (the classic "ROC = GS · gradient")
          ≈ γ% · GS · 1.01268                            (with ROC in fpm and GS in kt)
```

### Practical approximations pilots use

| Pilot rule | Exact form |
|---|---|
| "ROC ≈ GS × gradient%" | ROC_fpm = (γ%/100) · GS_kt · 6076.12 / 60 = 1.01268 · γ% · GS_kt |
| "3-to-1 descent" (300 ft per NM) | γ = 300 ft/NM = 4.93% ≈ 2.82° |
| "3° path" | γ ≈ 318 ft/NM ≈ 5.24% |
| "2.5° path" | γ ≈ 265 ft/NM ≈ 4.37% |

The script uses exact conversions — use the approximations only for mental
math cross-checks.

### Degrees of freedom

There are 8 variables and 6 relationships (3 above + the 3 gradient-family
conversions γ ↔ γ% ↔ θ plus the ROC/GS/γ% link). Effective DOF = 3. Supply
**any 3 independent values** and the whole set is solvable. Typical useful
triplets:

- `d, Δh, GS` — required gradient + time + ROC
- `Δh, θ (or γ%), GS` — descent planning, gives TOD distance + ROD + time
- `γ, GS` — ROC required for a given gradient

Over-specification (e.g. d, GS, t and also Δh and ROC) is accepted; the
solver doesn't verify consistency. If your inputs disagree, you'll get a
silently wrong answer — give the minimal set instead.

## Fuel uplift

```
SG(T)  = SG(15) - 0.00070 · (T - 15)                    [°C, kg/L]
mass   = volume_L · SG(T)                                [kg]
vol    = mass / SG(T)                                    [L]

mass_lbs = mass_kg / 0.45359237
vol_usg  = vol_L / 3.785411784
```

### Temperature correction accuracy

The −0.00070 kg·L⁻¹·°C⁻¹ coefficient is the mean Jet A-1 slope over
0–50 °C. Accurate to within ~0.1% of actual density for fuel temperatures
within ±30 °C of 15 °C. For extreme cold-soak or hot tarmac fuel ops use
the actual density-at-temp from the fuel ticket if provided.

### Why 3%?

The Jet A-1 specification range for density at 15 °C is 0.775–0.840
(DEF STAN 91-091 / ASTM D1655). Assuming the nominal 0.800 when the real
value sits at an edge introduces:

```
± (0.840 − 0.800) / 0.800 = ± 5.0%   (worst case)
± (0.815 − 0.800) / 0.800 = ± 1.9%   (typical real-world spread)
```

Industry rule-of-thumb: **a ≥3% discrepancy between ordered mass and mass
computed from volume × nominal SG means something is wrong — bad ticket,
unit mix-up, or short uplift — not just natural SG variation.**

## References

- ICAO Doc 7030 (Regional SUPPs)
- FAA Order 8260.3 — TERPS (for gradient vs angle conventions)
- ASTM D1250 — Petroleum Measurement Tables (volume/density at temperature)
- ASTM D1655 — Standard Specification for Aviation Turbine Fuels
- DEF STAN 91-091 — Turbine Fuel Aviation Kerosene Type, Jet A-1

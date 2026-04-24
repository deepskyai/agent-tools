# Formula reference

Derivations, constants, and edge cases for every script in `scripts/`.

## Constants

| Constant | Value | Source |
|---|---|---|
| Feet per nautical mile | 6076.11549 | ICAO / NIST |
| Litres per US gallon | 3.785411784 | NIST |
| Kilograms per pound | 0.45359237 | International yard and pound, 1959 |
| hPa per inHg | 33.8638866667 | NIST |
| ISA sea-level temp | 288.15 K (15 °C) | ICAO Doc 7488 |
| ISA sea-level pressure | 1013.25 hPa (29.92 inHg) | ICAO Doc 7488 |
| ISA lapse rate | 1.98 °C / 1000 ft (6.5 °C/km) | troposphere |
| Jet A-1 thermal expansion | 0.00070 kg·L⁻¹·°C⁻¹ | ASTM D1250, linearised around 15 °C |
| Jet A-1 nominal SG @ 15 °C | 0.800 (spec 0.775–0.840) | ASTM D1655 / DEF STAN 91-091 |
| Speed of sound | a = 38.967854 · √T_K  (knots) | γ = 1.4, R = 287.05 J/kg·K |

---

## 1. Gradient (`gradient.py`)

Three independent geometric equations connect eight variables; the solver
propagates them until fixed-point.

```
(1)  d  = GS · t / 60            distance_nm    = gs_kt · time_min / 60
(2)  Δh = ROC · t                altitude_ft    = rate_fpm · time_min
(3)  γ  = Δh / d                 gradient_ft_per_nm = altitude_ft / distance_nm
```

Conversions within the gradient family:

```
γ%        = γ · 100 / 6076.11549                 (ft/NM → %)
θ         = atan(γ% / 100)                       (% → degrees)
ROC_fpm   = γ%/100 · GS_kt · 6076.11549 / 60
          ≈ 1.01268 · γ% · GS_kt                 ("ROC = GS · gradient")
```

### Pilot rules-of-thumb vs exact

| Rule | Exact |
|---|---|
| 3-to-1 descent (300 ft/NM) | 4.93%, 2.82° |
| 3° path | 318 ft/NM, 5.24% |
| 2.5° path | 265 ft/NM, 4.37% |
| "ROC ≈ GS × gradient%" | ROC_fpm = 1.01268 · γ% · GS_kt |

Minimum input set = any 3 independent values. Over-specification is accepted
silently; if inputs disagree, the solver uses the first equation that
matches. Give the minimal set for safety.

---

## 2. Fuel uplift (`fuel_uplift.py`)

```
SG(T)  = SG_15 − 0.00070 · (T − 15)                [kg/L, with T in °C]
mass   = volume_L · SG(T)                          [kg]
vol    = mass / SG(T)                              [L]
mass_lbs = mass_kg / 0.45359237
vol_usg  = vol_L / 3.785411784
```

The 3% tolerance rule comes from the Jet A-1 spec range: 0.775–0.840
with 0.800 nominal. Assuming nominal SG when the real value sits at an
edge causes ±~3% mass error. A >3% delta between ordered and delivered
mass signals something other than natural SG variation (wrong SG, unit
mix-up, missed temperature correction, short uplift).

Temperature-correction accuracy: linear approximation is within ~0.1% of
actual density for fuel temperatures ±30 °C of 15 °C.

---

## 3. Wind components (`wind_components.py`)

Let `α` = signed wind angle relative to runway, normalised to (−180°, 180°]:

```
α        = ((wind_from − runway_heading + 540) mod 360) − 180
head_kt  = wind_speed · cos(α)      (+ headwind, − tailwind)
cross_kt = wind_speed · sin(α)      (+ from right, − from left)
```

Runway parsing: any decimal ≤ 37 is treated as a runway number and
multiplied by 10 (e.g. `27` → 270°), larger values as a direct heading.

---

## 4. Pressure / density altitude (`altitude.py`)

```
PA_ft   = elevation_ft
          + (1 − (QNH_hPa / 1013.25) ** 0.190284) · 145366.45
ISA_C   = 15 − 1.98 · (PA_ft / 1000)
ΔISA    = OAT_C − ISA_C
DA_ft   = PA_ft + 118.8 · ΔISA
```

The "118.8 ft/°C" factor comes from the derivative of DA with respect to T
at sea-level ISA. The FAA rule-of-thumb "120 ft/°C" is the same number to
within 1%. Accurate below ~10 000 ft; errors grow at stratospheric levels.

For a quick mental check: every 10 °C above ISA ≈ +1200 ft DA.

---

## 5. Airspeed (`airspeed.py`)

ICAO standard atmosphere, troposphere only (PA ≤ 36 089 ft):

```
T_isa   = 288.15 − 0.0019812 · PA_ft                [K]
T       = T_isa + ΔISA       (or use OAT directly)
δ       = (1 − 6.87559e-6 · PA_ft) ^ 5.2561         (pressure ratio)
σ       = δ · (288.15 / T)                           (density ratio)
a_kt    = 38.967854 · √T                             (speed of sound, kt)
TAS     = CAS / √σ
Mach    = TAS / a_kt
EAS     = CAS                                        (compressibility ignored)
```

Compressibility correction (CAS vs EAS) is <1% under ~M 0.5 and has been
intentionally omitted to keep the code short. For transonic / supersonic
performance work, use the FMS or FCOM tables.

Above the tropopause (36 089 ft), temperature is constant at 216.65 K and
the pressure/density ratios use a different formula — this script does NOT
model that regime correctly. Use with care at and above FL360.

---

## 6. PET / PSR (`pet_psr.py`)

Point of Equal Time between airports A (distance 0) and B (distance D),
with groundspeed GSₒ outbound and GSₕ home:

```
D_PET   = D · GSₕ / (GSₒ + GSₕ)
T_PET   = D_PET / GSₒ
```

Point of Safe Return given usable endurance E hours (after deducting reserves):

```
D_PSR    = E · GSₒ · GSₕ / (GSₒ + GSₕ)
T_out    = D_PSR / GSₒ
T_home   = D_PSR / GSₕ
T_out + T_home = E   (by construction)
```

Both are still-air derivations assuming constant GSₒ / GSₕ along the leg.
For real-world planning, use GS values that already include wind and step
through each 1-hour segment of the route.

---

## 7. Top-of-Descent (`descent.py`)

Pure rule-of-thumb:

```
base_NM   = (alt_current − alt_target) / 1000 · slope_per_1000ft   (3 by default)
speed_NM  = max(0, (v_current − v_target) / 10)                    (1 NM per 10 kt bled)
wind_NM   = headwind_kt / 10                                       (HW+, TW−)
TOD_NM    = base + speed + wind + buffer
```

`slope_per_1000ft = 3` approximates a 3° idle descent for jets. Use 2.5 for
a shallower profile (high drag configs or low-altitude starts).

This does NOT model idle thrust, Mach/IAS schedule crossover, or specific
aircraft FMS laws — it's for mental-math / briefing sanity checks only.

---

## 8. Weight & Balance (`weight_balance.py`)

```
TOW     = Σ wᵢ
Moment  = Σ wᵢ · aᵢ
CG_arm  = Moment / TOW
%MAC    = 100 · (CG_arm − LEMAC) / MAC_length
```

No unit conversion is performed — inputs must be consistent (all kg/m or
all lb/in). CG limits are compared directly on arm; `%MAC` is only
computed when `mac_length` and `lemac` are supplied.

Envelope checking is linear-only (forward + aft limit). For piecewise
envelopes (e.g. tapered fwd CG with gross weight), run the script and then
overlay results manually — the generic script can't load every type-
specific polygon.

---

## 9. ETOPS / EDTO (`etops.py`)

```
D_still_air = (t_min / 60) · TAS_OEI
D_wind      = (t_min / 60) · (TAS_OEI − headwind_kt)
```

Common thresholds: 60 / 75 / 90 / 120 / 138 / 180 / 207 / 240 /
≥ 300 minutes (FAA / EASA).

Still-air radius only — operational ETOPS layers on equal-time analysis,
fuel reserves, decompression-profile replan, and the aircraft-specific
drift-down. Use this for quick dispatch review, not final dispatch fuel.

---

## 10. Holding entry (`holding.py`)

```
θ = (aircraft_heading − inbound_course) mod 360
```

**Right-turn (standard) hold:**

| θ range            | Entry     |
|--------------------|-----------|
| (110°, 180°)       | Teardrop  (70° wedge on hold side of outbound)  |
| [180°, 250°)       | Parallel  (70° wedge on non-hold side of outbound) |
| elsewhere          | Direct    (remaining 180° arc)   |

**Left-turn (non-standard) hold:** mirror image — parallel and teardrop
sectors swap. A heading exactly equal to the outbound course (θ = 180°) is
assigned to parallel, which matches the intuitive "fly outbound one minute
then turn back" procedure when arriving already pointing along outbound.

Boundaries are assigned cleanly for programmatic use; in the real world
crews on a sector edge pick the entry that best suits the traffic /
maneuvering constraints. Reference: FAA AIM 5-3-8.

---

## Sources

- ICAO Doc 7488 — Manual of the ICAO Standard Atmosphere
- ICAO Doc 7030 — Regional Supplementary Procedures
- FAA Order 8260.3 — TERPS (gradient / angle conventions)
- FAA AIM 5-3-8 — Holding pattern procedures
- ASTM D1250 — Petroleum Measurement Tables
- ASTM D1655 — Aviation Turbine Fuel Specification
- DEF STAN 91-091 — Jet A-1 specification

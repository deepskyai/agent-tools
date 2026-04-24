---
name: flight-ops-calculators
description: Pure-offline flight-ops calculators for pilots. Includes (1) a flexible climb/descent gradient solver that takes any sufficient subset of distance, time, ground speed, altitude change, rate of climb/descent, angle, or gradient (%, ft/NM) and solves for everything else; and (2) a Jet A-1 fuel uplift reconciliation tool that checks actual mass delivered against ordered mass using ticket SG and temperature, applying the industry "3% rule" to flag bad uplifts. Use whenever a pilot asks about climb/descent geometry (TOD, ROC required, gradient vs angle, obstacle clearance), or needs to verify a fuel uplift (kg vs L, lbs vs USG, SG conversion, ticket vs ordered mass).
---

# Flight Ops Calculators

Two deterministic command-line tools in `scripts/`. Both output JSON by default
(so the agent can parse), or a human table with `--pretty`.

No network, no API keys, no approximations beyond what's stated in
`references/formulas.md`.

---

## Tool 1 — `gradient.py`

Flexible climb/descent solver. Eight variables, six relationships; give it any
sufficient subset and it solves for the rest.

### Variables

| CLI flag | Symbol | Unit | Sign convention |
|---|---|---|---|
| `--distance-nm` | d | nautical miles | always ≥ 0 |
| `--time-min` | t | minutes | always ≥ 0 |
| `--gs-kt` | GS | knots | always ≥ 0 |
| `--altitude-ft` | Δh | feet | **+ climb, − descent** |
| `--rate-fpm` | ROC | feet per minute | **+ climb, − descent** |
| `--angle-deg` | θ | degrees | + climb, − descent |
| `--gradient-pct` | γ% | percent | + climb, − descent |
| `--gradient-ft-per-nm` | γ | ft/NM | + climb, − descent |

### When to invoke

Any pilot question involving climb or descent geometry. Typical triggers:

- "What climb gradient do I need to make 1500 ft by 5 DME at 140 kt?"
- "If I'm at 10 000 ft 30 NM from the FAF, what ROD gives me a 3° path at GS 250?"
- "Convert 200 ft/NM to degrees and percent."
- "At 5% gradient and GS 180, what ROC do I need?"
- "3-to-1 rule: what's my TOD for 37 000 ft?"

### Invocation

```bash
python3 scripts/gradient.py [flags] [--pretty]
```

Pass only the variables you know; leave the rest out. Script reports which
variables remained unsolved under `_unsolved`.

### Examples

```bash
# Required gradient to make 1500 ft of altitude over 5 NM, GS 140 kt
python3 scripts/gradient.py --distance-nm 5 --altitude-ft 1500 --gs-kt 140 --pretty

# 3° descent path from FL100 at GS 250 — how far out must TOD be, and what ROD?
python3 scripts/gradient.py --altitude-ft -10000 --angle-deg -3 --gs-kt 250 --pretty

# Convert 200 ft/NM to percent and degrees
python3 scripts/gradient.py --gradient-ft-per-nm 200 --pretty

# ROC required for a 5% climb gradient at 180 kt
python3 scripts/gradient.py --gradient-pct 5 --gs-kt 180 --pretty
```

### How to read the output

JSON mode returns all eight primary variables plus metric mirrors
(`distance_km`, `altitude_m`, `gs_kmh`, `rate_mps`, `time_sec`) and a
`_unsolved` list. `null` means the variable couldn't be determined from the
inputs given — if something you expected is `null`, you didn't supply enough
independent values.

---

## Tool 2 — `fuel_uplift.py`

Jet A-1 uplift reconciliation. The pilot ordered *X kg/lbs*; the fueler
delivered *Y L/USG* at SG *s* and temperature *T*. Does it match?

### When to invoke

- "We ordered 12 000 kg, ticket shows 15 200 L at SG 0.794. Is that right?"
- "Getting 26 455 lbs from 4016 USG — does that look legit?"
- "How many litres should I see on the ticket for 8 000 kg at SG 0.81?"
- Any time a fuel figure needs unit conversion (kg ↔ lbs ↔ L ↔ USG with SG).

### Invocation

```bash
python3 scripts/fuel_uplift.py \
    (--expected-mass-kg N | --expected-mass-lbs N) \
    (--volume-L N | --volume-usg N) \
    [--sg-15c 0.800] \
    [--fuel-temp-c 15] \
    [--tolerance-pct 3.0] \
    [--pretty]
```

Defaults: `sg-15c = 0.800` (industry nominal), `fuel-temp-c = 15`,
`tolerance-pct = 3.0` (the "3% rule").

### Examples

```bash
# Ordered 12 000 kg, received 15 200 L at SG 0.794, fuel temp 22 °C
python3 scripts/fuel_uplift.py --expected-mass-kg 12000 \
    --volume-L 15200 --sg-15c 0.794 --fuel-temp-c 22 --pretty

# Imperial: ordered 26 455 lbs, received 4016 USG, no SG on ticket (uses 0.800)
python3 scripts/fuel_uplift.py --expected-mass-lbs 26455 --volume-usg 4016 --pretty

# Tighter tolerance (1.5%) for a high-stakes ferry flight fuel check
python3 scripts/fuel_uplift.py --expected-mass-kg 8000 --volume-L 10100 \
    --sg-15c 0.810 --tolerance-pct 1.5 --pretty
```

### How to read the output

- **`verdict`** — `PASS` or `FAIL` vs `tolerance_pct`.
- **`discrepancy.pct`** — signed percentage; **positive** means you got
  **more** fuel than ordered, negative means less.
- **`expected_volume`** — what you *should have* seen on the ticket for the
  mass you ordered at this SG/temp. Good for cross-checking before signing.
- **`sg_effective`** — SG at fuel temperature (not ticket's 15 °C value).

### The "3% rule" in one line

Jet A-1 SG per ASTM D1655 is 0.775–0.840 with 0.800 as nominal. If you
assume 0.800 but the actual fuel is at either edge, your kg↔L conversion
is off by ±~3%. A >3% discrepancy is a red flag — look for wrong SG, wrong
unit, missed temperature correction, or a short uplift.

---

## For the agent: decision hints

- If the pilot says *"gradient"*, *"climb rate"*, *"descent path"*, *"TOD"*,
  *"3-to-1"*, *"obstacle clearance at X NM"*, or gives any 3 of the eight
  variables above → invoke `gradient.py`.
- If the pilot says *"uplift"*, *"fuel ticket"*, *"SG"*, *"L vs kg"*,
  *"USG vs lbs"*, or wants to verify a volume ↔ mass conversion → invoke
  `fuel_uplift.py`.
- Always run with `--pretty` when explaining to a human; use JSON when you
  need to quote exact numbers back or chain into further calculation.
- If the user gives inconsistent inputs (e.g. d, GS, t that don't satisfy
  d = GS·t/60), the solver uses the first equation that matches; warn the
  user that the inputs were over-specified and re-run with a minimal set.

See `references/formulas.md` for derivations and edge cases.

---
name: flight-ops-calculators
description: Ten pure-offline flight-ops calculators for pilots. (1) gradient — flexible climb/descent solver over {distance, time, GS, altitude, ROC, angle, %-gradient, ft/NM}. (2) fuel_uplift — Jet A-1 kg↔L↔USG↔lbs reconciliation with SG + temperature correction and the industry 3% tolerance rule. (3) wind_components — headwind/crosswind from wind + runway. (4) altitude — pressure altitude, ISA deviation, density altitude. (5) airspeed — CAS↔TAS↔Mach in the ICAO troposphere. (6) pet_psr — Point of Equal Time and Point of Safe Return. (7) descent — 3-to-1 Top-of-Descent with speed/wind/buffer tax. (8) weight_balance — CG + %MAC with limit checking. (9) etops — EDTO/ETOPS diversion-radius given threshold time and OEI TAS. (10) holding — direct/parallel/teardrop entry per FAA AIM 5-3-8. Use whenever a pilot asks about climb/descent geometry, TOD, fuel unit conversion, wind components, pressure/density altitude, true-airspeed conversion, long-range diversion planning, weight & balance, ETOPS diversion radius, or holding-pattern entries. All tools take CLI flags and emit JSON by default, human-readable tables with --pretty.
---

# Flight Ops Calculators

Ten deterministic command-line tools in `scripts/`. All JSON-by-default, all
with `--pretty` for humans, all pure Python stdlib (no deps, no network, no
API keys). Run any with `--help` for usage.

```
scripts/
├── gradient.py          climb/descent geometry solver
├── fuel_uplift.py       Jet A-1 uplift reconciliation (3% rule)
├── wind_components.py   crosswind / headwind
├── altitude.py          PA / DA / ISA-dev
├── airspeed.py          CAS / TAS / Mach
├── pet_psr.py           Point of Equal Time & Point of Safe Return
├── descent.py           Top-of-Descent (3× rule + tax)
├── weight_balance.py    W&B + CG + %MAC
├── etops.py             EDTO / ETOPS diversion radius
└── holding.py           direct / parallel / teardrop entry
```

See `references/formulas.md` for derivations, constants, and edge cases.

---

## 1. `gradient.py` — climb/descent solver

Eight variables — `distance_nm`, `time_min`, `gs_kt`, `altitude_ft`,
`rate_fpm`, `angle_deg`, `gradient_pct`, `gradient_ft_per_nm` — and six
relationships. Supply any sufficient subset (typically 3 values), solves for
the rest. Sign convention: + climb, − descent for altitude, rate, angle, and
gradient.

Triggers: "climb gradient", "ROC required", "3-to-1 descent", "TOD distance",
"angle vs %", "ft/NM", obstacle clearance, any 3 of the variables above.

```bash
# Required gradient to clear 1500 ft in 5 NM at 140 kt
python3 scripts/gradient.py --distance-nm 5 --altitude-ft 1500 --gs-kt 140 --pretty

# 3° descent from FL100 at GS 250 — how far out is TOD, what's the ROD?
python3 scripts/gradient.py --altitude-ft -10000 --angle-deg -3 --gs-kt 250 --pretty

# ROC for 5% gradient at GS 180
python3 scripts/gradient.py --gradient-pct 5 --gs-kt 180 --pretty
```

## 2. `fuel_uplift.py` — Jet A-1 uplift reconciliation

Compares mass ordered vs mass actually delivered (volume × SG × temp
correction), flags >3% deltas (the Jet A-1 SG-band rule).

Triggers: "fuel ticket", "uplift", "SG", "kg vs L", "lbs vs USG",
"ordered X kg got Y L".

```bash
python3 scripts/fuel_uplift.py --expected-mass-kg 12000 --volume-L 15200 \
    --sg-15c 0.794 --fuel-temp-c 22 --pretty
```

## 3. `wind_components.py` — headwind / crosswind

Inputs: wind direction (°T), wind speed (kt), runway (number like `27`, `09L`
or a full heading in degrees).

Triggers: "crosswind", "headwind component", "runway wind", approach-brief
wind math.

```bash
python3 scripts/wind_components.py --wind-from 210 --wind-kt 18 --runway 27 --pretty
```

## 4. `altitude.py` — PA / DA / ISA-dev

Inputs: field elevation, altimeter (QNH hPa or inHg), OAT.

Triggers: "density altitude", "pressure altitude", "hot & high", "ISA
deviation", performance-chart entry arguments.

```bash
python3 scripts/altitude.py --elevation-ft 5000 --qnh-hpa 1005 --oat-c 28 --pretty
```

## 5. `airspeed.py` — CAS ↔ TAS ↔ Mach

Inputs: pressure altitude + (OAT **or** ISA-dev) + any one of CAS, TAS, Mach.
Subsonic troposphere model; ignores compressibility correction (<1% under
M 0.5). Don't use for transonic performance work — use the FMS/FCOM.

Triggers: "convert IAS to TAS", "what Mach is 280 KIAS at FL350", "TAS at
FL250 ISA+10", flight-plan groundspeed sanity checks.

```bash
python3 scripts/airspeed.py --cas-kt 250 --pa-ft 10000 --pretty
python3 scripts/airspeed.py --mach 0.78 --pa-ft 37000 --isa-dev 10 --pretty
```

## 6. `pet_psr.py` — Point of Equal Time & Point of Safe Return

Inputs: distance (for PET), endurance in hours (for PSR), GS out, GS home.
Can compute either one, or both in the same call.

Triggers: "PET", "equitime point", "PSR", "point of safe return",
"diversion planning", long over-water / over-polar flight math.

```bash
# Both at once
python3 scripts/pet_psr.py --distance-nm 2200 --endurance-hr 5.8 \
    --gs-out 460 --gs-home 420 --pretty
```

## 7. `descent.py` — Top-of-Descent planner

3-to-1 rule with itemised tax: speed reduction (1 NM per 10 kt), wind
(1 NM per 10 kt headwind), extra buffer. Rule-of-thumb only — use the FMS
for precise profiles.

Triggers: "TOD", "when to start down", "3× rule", "descent planning",
"slow down from M0.78 to 250".

```bash
python3 scripts/descent.py --current-alt 37000 --target-alt 2000 \
    --current-speed 290 --target-speed 250 --headwind 20 --pretty
```

## 8. `weight_balance.py` — W&B + CG

Generic. Two input styles:

- CLI: repeat `--station "name:weight:arm"` for each row.
- JSON file: `--json wb.json` (see the script's docstring for schema).

Optional CG limits, max weight, and MAC data → output includes in/out-of-
limits flags, margins, and CG as %MAC.

Triggers: "weight and balance", "CG", "%MAC", "loadsheet", envelope check.

```bash
python3 scripts/weight_balance.py \
    --station "BEW:42000:21.5" \
    --station "Crew:400:10.2" \
    --station "Pax:8400:20.0" \
    --station "Cargo:3200:28.1" \
    --station "Fuel:9000:19.7" \
    --cg-fwd 18.5 --cg-aft 24.0 --max-weight 62000 --pretty
```

## 9. `etops.py` — EDTO/ETOPS diversion radius

Inputs: authorised threshold time (min), OEI cruise TAS (kt), optional
headwind component. Outputs still-air and wind-corrected radii.

Triggers: "ETOPS 180 circle", "diversion radius", "EDTO time", long-range
dispatch review.

```bash
python3 scripts/etops.py --threshold-min 180 --oei-tas 400 --headwind 35 --pretty
```

## 10. `holding.py` — entry type

Inputs: inbound holding course (°T), aircraft heading at the fix (°T),
turn direction (default right). Returns direct / parallel / teardrop plus a
short how-to-fly description. Rules per FAA AIM 5-3-8.

Triggers: "holding entry", "direct / parallel / teardrop", "how do I enter
the hold".

```bash
python3 scripts/holding.py --inbound 270 --heading 120 --pretty
```

---

## Agent decision hints

- Map user language → tool:
  - gradient/angle/ROC/ft-per-NM/TOD math → `gradient.py`
  - fuel ticket/SG/kg↔L/lbs↔USG → `fuel_uplift.py`
  - wind + runway → `wind_components.py`
  - hot/high, density altitude, PA → `altitude.py`
  - KIAS/Mach/TAS conversion → `airspeed.py`
  - long-range diversion time/fuel → `pet_psr.py`
  - when to start descent → `descent.py`
  - W&B / CG / %MAC → `weight_balance.py`
  - ETOPS/EDTO circle → `etops.py`
  - holding entry type → `holding.py`
- Always run with `--pretty` when explaining to a human; JSON is better when
  you need to parse exact numbers and chain into further calculation.
- If the user asks a TOD / ROD / angle question that spans multiple tools,
  prefer `gradient.py` (it handles the core math) and use `descent.py` only
  when speed/wind taxes matter.
- If the user supplies inconsistent inputs (e.g. over-specifying `gradient`),
  warn them and rerun with a minimal consistent set.

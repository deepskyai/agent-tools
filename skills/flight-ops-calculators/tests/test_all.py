#!/usr/bin/env python3
"""
Test suite for every calculator in ../scripts/.
Zero dependencies — pure stdlib. Run with:

    python3 tests/test_all.py

Exit code 0 = all tests passed, 1 = at least one failed.
"""
from __future__ import annotations

import math
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, os.pardir, "scripts")
sys.path.insert(0, SCRIPTS)

# Module imports ------------------------------------------------------------
import gradient
import fuel_uplift
import wind_components
import altitude
import airspeed
import pet_psr
import descent
import weight_balance
import etops
import holding


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def approx(actual, expected, tol=1e-3, abs_tol=1e-6):
    """Relative tolerance with abs fallback near zero."""
    if expected is None or actual is None:
        return actual is expected
    if abs(expected) < 1.0:
        return abs(actual - expected) <= max(tol, abs_tol)
    return abs(actual - expected) <= tol * abs(expected)


def _check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")


# ----------------------------------------------------------------------------
# 1. gradient.py
# ----------------------------------------------------------------------------

def test_gradient_three_to_one_rule():
    """1500 ft in 5 NM at 140 kt → 300 ft/NM, 4.94%, 2.83°, ROC 700, t=2.14 min."""
    r = gradient.solve(d=5, h=1500, gs=140)
    _check("ft/NM",    approx(r["gradient_ft_per_nm"], 300.0))
    _check("%",        approx(r["gradient_pct"],       4.9374, tol=1e-3))
    _check("angle",    approx(r["angle_deg"],          2.8268, tol=1e-3))
    _check("ROC",      approx(r["rate_fpm"],           700.0,  tol=1e-3))
    _check("time",     approx(r["time_min"],           5 * 60 / 140, tol=1e-3))


def test_gradient_descent_3deg_fl100_gs250():
    """3° descent from FL100 at GS 250 → 31.4 NM, ROD 1327 fpm."""
    r = gradient.solve(h=-10000, ang=-3, gs=250)
    _check("dist",   approx(r["distance_nm"],  31.404, tol=1e-3))
    _check("ROD",    approx(r["rate_fpm"],    -1326.82, tol=1e-3))
    _check("signs",  r["gradient_pct"] < 0 and r["gradient_ft_per_nm"] < 0)


def test_gradient_family_conversions():
    """200 ft/NM ↔ % ↔ degrees round-trip."""
    r = gradient.solve(fpnm=200)
    _check("%",     approx(r["gradient_pct"], 200 * 100 / 6076.11549))
    _check("deg",   approx(r["angle_deg"],    math.degrees(math.atan(r["gradient_pct"] / 100))))


def test_gradient_under_specified():
    """Given only GS — nothing else can be solved."""
    r = gradient.solve(gs=250)
    unsolved = [k for k, v in r.items() if v is None]
    _check("unsolved", len(unsolved) >= 5, detail=f"only {unsolved} unsolved")


# ----------------------------------------------------------------------------
# 2. fuel_uplift.py
# ----------------------------------------------------------------------------

def test_fuel_exact_match_at_nominal():
    """8000 kg ordered, 10 000 L @ SG 0.80 @ 15 °C → 0% delta."""
    r = fuel_uplift.reconcile(expected_mass_kg=8000, volume_L=10000, sg_15c=0.80)
    _check("delta", approx(r["discrepancy"]["pct"], 0.0, abs_tol=1e-9))
    _check("pass",  r["verdict"] == "PASS")


def test_fuel_temperature_correction():
    """SG 0.80 @ 15 °C → 0.786 @ 35 °C (20 °C above reference)."""
    _check("T+20", approx(fuel_uplift.sg_at_temp(0.80, 35.0), 0.80 - 0.00070 * 20))


def test_fuel_short_uplift_flagged():
    """Ordered 10 000 kg but only got 11 000 L @ 0.80 → -12%, FAIL."""
    r = fuel_uplift.reconcile(expected_mass_kg=10000, volume_L=11000, sg_15c=0.80)
    _check("neg",  r["discrepancy"]["pct"] < 0)
    _check("12%", approx(r["discrepancy"]["pct"], -12.0, tol=1e-3))
    _check("fail", r["verdict"] == "FAIL")


def test_fuel_imperial_round_trip():
    """kg↔lbs conversion consistency."""
    r = fuel_uplift.reconcile(expected_mass_kg=1000, volume_L=1000 / 0.80, sg_15c=0.80)
    _check("lbs", approx(r["actual_mass"]["lbs"], 1000 / 0.45359237))


# ----------------------------------------------------------------------------
# 3. wind_components.py
# ----------------------------------------------------------------------------

def test_wind_pure_headwind():
    """Wind direction = runway heading → full headwind, zero crosswind."""
    h, x, _ = wind_components.components(270.0, 20.0, 270.0)
    _check("head", approx(h, 20.0))
    _check("cross", approx(x, 0.0, abs_tol=1e-9))


def test_wind_pure_tailwind():
    """Wind from 90° to a 270° runway = 180° offset → -20 kt headwind."""
    h, x, _ = wind_components.components(90.0, 20.0, 270.0)
    _check("tail", approx(h, -20.0))
    _check("cross", approx(x, 0.0, abs_tol=1e-9))


def test_wind_pure_crosswind_right():
    """Wind from 180° on runway 270° = 90° from right → full right crosswind."""
    h, x, _ = wind_components.components(180.0, 15.0, 270.0)
    _check("head", approx(h, 0.0, abs_tol=1e-9))
    _check("cross", approx(x, -15.0))  # 180 is LEFT of heading 270°


def test_wind_runway_parsing():
    """'27' → 270°, '09L' → 90°, '273' → 273°."""
    _check("27",  approx(wind_components.parse_runway("27"), 270.0))
    _check("09L", approx(wind_components.parse_runway("09L"), 90.0))
    _check("273", approx(wind_components.parse_runway("273"), 273.0))


# ----------------------------------------------------------------------------
# 4. altitude.py
# ----------------------------------------------------------------------------

def test_altitude_standard_day():
    """Elev 0, QNH 1013.25, OAT 15 → PA = 0, DA = 0."""
    pa = altitude.pressure_altitude(0.0, 1013.25)
    _check("PA",  approx(pa, 0.0, abs_tol=1e-3))
    _check("ISA", approx(altitude.isa_temp_c(0.0), 15.0))
    _check("DA",  approx(altitude.density_altitude(0.0, 15.0), 0.0, abs_tol=1e-3))


def test_altitude_low_qnh_raises_pa():
    """Low QNH → PA higher than field elevation.
    Exact ICAO formula yields ≈27 ft per hPa near sea level
    (the 30 ft/hPa pilot rule is approximate — high by ~10%)."""
    pa = altitude.pressure_altitude(1000.0, 1003.25)  # 10 hPa low
    _check("PA_raised", pa > 1000.0, detail=f"PA={pa}")
    _check("PA_realistic", 1260.0 < pa < 1290.0, detail=f"PA={pa}")


def test_altitude_hot_day_raises_da():
    """+20 °C above ISA at FL050 ≈ +2400 ft of DA."""
    pa = 5000.0
    isa = altitude.isa_temp_c(pa)
    da = altitude.density_altitude(pa, isa + 20.0)
    _check("DA", approx(da - pa, 118.8 * 20.0))


# ----------------------------------------------------------------------------
# 5. airspeed.py
# ----------------------------------------------------------------------------

def test_airspeed_sea_level_isa():
    """At SL ISA: σ = 1, TAS = CAS, a = 661.5 kt."""
    r = airspeed.convert(pa_ft=0.0, cas_kt=200.0, oat_c=15.0)
    _check("sigma", approx(r["sigma"], 1.0, tol=1e-3))
    _check("TAS",   approx(r["tas_kt"], 200.0, tol=1e-3))
    _check("a",     approx(r["speed_of_sound_kt"], 661.5, tol=1e-3))


def test_airspeed_round_trip_cas_tas():
    """CAS → TAS → back to CAS should be self-consistent."""
    r1 = airspeed.convert(pa_ft=10000.0, cas_kt=250.0, oat_c=-4.8)
    r2 = airspeed.convert(pa_ft=10000.0, tas_kt=r1["tas_kt"], oat_c=-4.8)
    _check("round_trip", approx(r2["cas_kt"], 250.0, tol=1e-6))


def test_airspeed_mach_at_fl370():
    """TAS at FL370 ISA ≈ 447 kt for M0.78 (script model gives ~449 due to troposphere extrapolation)."""
    r = airspeed.convert(pa_ft=37000.0, mach=0.78)
    _check("TAS range", 440 < r["tas_kt"] < 460, detail=f"TAS={r['tas_kt']}")


# ----------------------------------------------------------------------------
# 6. pet_psr.py
# ----------------------------------------------------------------------------

def test_pet_symmetric_wind():
    """Symmetric GS → PET at exact midpoint."""
    r = pet_psr.pet(1000.0, 450.0, 450.0)
    _check("midpoint", approx(r["distance_from_departure_nm"], 500.0))


def test_pet_asymmetric_wind():
    """2200 NM, 460 out / 420 home → PET at 1050 NM from departure."""
    r = pet_psr.pet(2200.0, 460.0, 420.0)
    _check("PET", approx(r["distance_from_departure_nm"], 1050.0))


def test_psr_endurance_balance():
    """T_out + T_home must equal endurance by construction."""
    r = pet_psr.psr(5.8, 460.0, 420.0)
    total_hr = (r["time_out_min"] + r["time_home_min"]) / 60.0
    _check("endurance", approx(total_hr, 5.8, tol=1e-6))


# ----------------------------------------------------------------------------
# 7. descent.py
# ----------------------------------------------------------------------------

def test_descent_base_3x_rule():
    """35 000 ft loss at 3× rule → 105 NM base."""
    r = descent.plan(current_alt_ft=37000, target_alt_ft=2000)
    _check("base", approx(r["base_3x_nm"], 105.0))
    _check("spd",  r["speed_reduction_nm"] == 0.0)
    _check("wind", r["wind_correction_nm"] == 0.0)


def test_descent_full_tax():
    """Base 105 + speed (40/10=4) + wind (20/10=2) = 111 NM total."""
    r = descent.plan(
        current_alt_ft=37000, target_alt_ft=2000,
        current_speed_kt=290, target_speed_kt=250, headwind_kt=20,
    )
    _check("total", approx(r["recommended_tod_nm"], 111.0))


def test_descent_speed_no_negative_tax():
    """If current speed ≤ target, speed-reduction tax must be 0 (not negative)."""
    r = descent.plan(current_alt_ft=10000, target_alt_ft=0,
                     current_speed_kt=200, target_speed_kt=250)
    _check("no_neg", r["speed_reduction_nm"] == 0.0)


# ----------------------------------------------------------------------------
# 8. weight_balance.py
# ----------------------------------------------------------------------------

def test_wb_cg_computation():
    """Simple two-station load: (1000 @ 10) + (1000 @ 20) → CG 15."""
    r = weight_balance.compute(
        stations=[
            {"name": "A", "weight": 1000, "arm": 10},
            {"name": "B", "weight": 1000, "arm": 20},
        ],
    )
    _check("TOW", approx(r["total_weight"], 2000))
    _check("CG",  approx(r["cg_arm"], 15.0))


def test_wb_in_limits_and_overweight():
    """CG inside window but TOW above max → out-of-weight but in-CG."""
    r = weight_balance.compute(
        stations=[
            {"name": "A", "weight": 50000, "arm": 20},
            {"name": "B", "weight": 20000, "arm": 22},
        ],
        cg_limit_fwd=18.0, cg_limit_aft=24.0,
        max_weight=60000,
    )
    _check("cg_ok",       r["cg_limits"]["within_limits"])
    _check("overweight", not r["weight_limits"]["within_limits"])
    _check("margin",      approx(r["weight_limits"]["margin"], -10000))


def test_wb_pct_mac():
    """CG arm = LEMAC + 0.25 * MAC → 25% MAC."""
    r = weight_balance.compute(
        stations=[{"name": "A", "weight": 1000, "arm": 100 + 0.25 * 40}],
        mac_length=40, lemac=100,
    )
    _check("pct_mac", approx(r["cg_pct_mac"], 25.0))


# ----------------------------------------------------------------------------
# 9. etops.py
# ----------------------------------------------------------------------------

def test_etops_still_air_radius():
    """180 min × 400 kt / 60 = 1200 NM."""
    r = etops.diversion_radius(180.0, 400.0)
    _check("still", approx(r["diversion_radius_still_air_nm"], 1200.0))


def test_etops_headwind_shrinks():
    """HW shrinks the circle proportionally to reduced effective GS."""
    r = etops.diversion_radius(180.0, 400.0, headwind_kt=40.0)
    _check("wind_GS", approx(r["effective_gs_kt"], 360.0))
    _check("wind_radius", approx(r["diversion_radius_with_wind_nm"], 1080.0))


# ----------------------------------------------------------------------------
# 10. holding.py
# ----------------------------------------------------------------------------

def test_holding_direct_on_inbound():
    """Arriving on inbound course → direct."""
    r = holding.entry(inbound_course_deg=270, heading_deg=270, turn="right")
    _check("direct", r["entry"] == "direct")


def test_holding_teardrop_hold_side():
    """Right-turn inb 270°, heading 060° (in hold-side sector) → teardrop."""
    r = holding.entry(inbound_course_deg=270, heading_deg=60, turn="right")
    _check("teardrop", r["entry"] == "teardrop", detail=str(r))


def test_holding_parallel_non_hold_side():
    """Right-turn inb 270°, heading 120° (non-hold side sector) → parallel."""
    r = holding.entry(inbound_course_deg=270, heading_deg=120, turn="right")
    _check("parallel", r["entry"] == "parallel", detail=str(r))


def test_holding_boundary_on_outbound():
    """Arriving on outbound heading (θ = 180°) → parallel (our chosen boundary)."""
    r = holding.entry(inbound_course_deg=270, heading_deg=90, turn="right")
    _check("boundary", r["entry"] == "parallel", detail=str(r))


def test_holding_left_turn_mirror():
    """Left-turn hold mirrors right: hdg that was teardrop (right) → parallel (left)."""
    r_right = holding.entry(inbound_course_deg=270, heading_deg=60,  turn="right")
    r_left  = holding.entry(inbound_course_deg=270, heading_deg=60,  turn="left")
    _check("mirror_right", r_right["entry"] == "teardrop")
    _check("mirror_left",  r_left["entry"]  == "parallel")


# ----------------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------------

def _discover_tests():
    return sorted(
        [(name, fn) for name, fn in globals().items()
         if name.startswith("test_") and callable(fn)]
    )


def main() -> int:
    tests = _discover_tests()
    passed = failed = 0
    print(f"Running {len(tests)} tests for flight-ops-calculators\n")
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1
        except Exception:
            print(f"  ERROR {name}:")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{len(tests)} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

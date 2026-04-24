# Plate-reading guide

Where to find each briefing datum on the three common plate layouts:
FAA d-TPP, Jeppesen, and ICAO AIP.

---

## Universal briefing checklist

When reading any plate, work through these bands in order:

1. **Header / title band** — airport, procedure name, effective date, AIRAC.
2. **Frequencies / comms box** — approach, tower, ground, ATIS.
3. **Plan view** — MSA, IAFs, transitions, navaids, missed-approach holding.
4. **Profile view** — glideslope intercept, FAF, step-downs, MAP.
5. **Minima strip** — DA/MDA, visibility by category, circling.
6. **Airport diagram inset / notes** — runway data, lighting, cold-temp flag.
7. **Notes box(es)** — non-standard items, CAUTION banners.

---

## FAA d-TPP layout

FAA plates have a fixed structure — the fastest layout to extract from.

| Element | Location |
|---|---|
| Procedure title | Top-center in large type (e.g. "ILS OR LOC RWY 28R") |
| ICAO and airport name | Top-right of title |
| Effective date | Top-right corner, usually "Orig" / "Amdt" + date |
| Communications | Narrow boxed strip below title (ATIS, APP, TWR, GND, CLNC) |
| MSA | Circle in upper-left of plan view with sectors labelled, or a note "MSA 25 NM" |
| Navaid data | Boxes within plan view (ident, frequency, Morse, channel) |
| Final approach course | Arrow + number in plan view and profile ("284°") |
| Glideslope angle | Profile view ("3.00°", "GS 3.00°") |
| TCH | Profile view near threshold ("TCH 55") |
| FAF | Maltese cross ✠ on profile, with altitude and fix name |
| Missed approach | Top of minima strip, short sentence starting "MISSED APPROACH:" |
| Minima | Matrix at bottom, rows: S-ILS, S-LOC, CIRCLING; columns: A, B, C, D |
| Cold-temperature restriction | If applicable, snowflake ❄ symbol in notes with threshold temp |
| Notes | Boxed list above the minima strip |
| Lighting / runway | Airport-diagram inset in lower-right |

### FAA-specific gotchas

- **MALSR vs ALSF-2**: visibility reduction for minima requires presence of
  specific lighting systems — called out in notes with a † symbol.
- **Circling category D minima** may be **higher** than C; do not assume
  monotonic.
- **NoPT**: "No Procedure Turn" label on transitions — means the pilot
  flies straight in, no hold-in-lieu required.
- **"A" icon**: indicates non-standard takeoff minimums / obstacle
  departure procedure — see separate plate.
- **"T" icon**: indicates alternate minimums not standard.
- **Plus-sign altitudes (`+1800`)** mean "at or above"; minus-sign means
  "at or below"; boxed means "at"; underlined-both means "mandatory".

---

## Jeppesen layout

Jeppesen pages are denser but better organised into named boxes. Look for
labelled headers.

| Element | Location |
|---|---|
| Chart index | Top header: `<ICAO> <airport>  <procedure>  <index>` |
| Briefing strip | Wide band across top: COMM, ILS freq, APP course, GS, DA(H), MDA(H), MAP |
| Freq box | Below briefing strip, labeled "ATIS", "APP", "TWR" |
| Navaid data | Labeled boxes with ident, channel, DME |
| MSA | Circle in plan view labeled "MSA" with reference fix |
| Profile | Right-hand column of plate; FAF is a solid triangle ▲ |
| Missed approach | Text box next to profile view, labeled "MISSED APCH" |
| Minima table | Bottom of plate, split by aircraft category with both DA and HAT |
| Chart date | Bottom-left corner: "CHANGES:" list with revision date |
| Cold-temp | Notes band |

### Jeppesen-specific gotchas

- Jeppesen uses **FL** in some countries (metric levels), check units.
- **DA(H)** means DA with HAT in parentheses; both values are useful.
- **"Straight-in MDA"** and **"Circling MDA"** are labelled distinctly; make
  sure the extractor captures both when the approach supports both.
- Jeppesen chart revisions often include only PARTIAL updates — capture the
  list of "CHANGES" if present.

---

## ICAO AIP layout (national charts)

Country-specific AIP charts vary widely. Common elements:

| Element | Typical location |
|---|---|
| Procedure title | Top band, may be in local language + English |
| Effective date | Upper-right corner, AIP amendment number |
| Frequencies | Box upper-left with ATIS / TWR / APP in that order |
| Navaid data | Plan view, boxed |
| MSA | Plan view, stated as "MSA 25 NM from <fix>" |
| Minima | Bottom strip, usually metric and imperial dual-column |
| Cold-temp | May be absent — some states use ICAO Doc 7030 table instead |

### AIP-specific gotchas

- **Metric vs imperial** mixing: altitudes often in meters (m), visibilities in
  kilometres or metres, distances in km instead of NM. **Preserve the units
  as shown; note the unit system in the JSON.**
- **Circling restrictions** may be published as prohibited sectors — extract
  as free-form text into `notes`.
- Some AIPs publish **temperature-compensated DA** when outside ISA — capture
  as a note, not a minima line.
- **Missed approach may require an immediate turn** before a specific
  altitude — capture that nuance in `missed_approach.text`.

---

## Common plate gotchas (all layouts)

### Cold-temperature airports
- If the plate shows a snowflake ❄ and a temperature (e.g. "−17 °C"),
  the airport requires cold-temperature altitude corrections below that
  temperature. Capture both the flag and the threshold in the JSON. Flag
  it in `agent_threats` if the user appears to be flying in winter.

### Circling-only approaches
- Labeled with "C" suffix (e.g. "VOR-C"). `procedure.circling_only = true`.
- Circling restrictions (e.g. "not authorized east of RWY") are
  critical — always put in `notes` and in `agent_threats`.

### RNP approaches
- Look for "RNP" in the title and "LNAV/VNAV", "LPV", or "LNAV" in the
  minima strip.
- Extract every RNP value visible (e.g. RNP 0.3, RNP 0.1-AR) into
  `rnp_values_nm`.
- If RNP-AR, flag operational-authorization required in `agent_threats`.

### Climb-gradient required on missed
- Some missed approaches specify a non-standard climb gradient (e.g.
  "297 ft/NM to 5000"). Capture it in `missed_approach.text` AND, when
  relevant, in `final_approach.required_climb_gradient_ft_per_nm` if the
  plate publishes a takeoff/departure gradient too.

### Visibility expressed in different units
- Statute miles (SM) — FAA
- Meters — ICAO AIP
- Kilometres — ICAO AIP high
- RVR feet / metres — applies only when ALS present
- Always preserve the string as printed, e.g. "RVR 1800" or "1½" or "2400m".

### "VDP" (Visual Descent Point)
- Plates may publish a VDP on non-precision approaches. Capture the fix
  name and the distance/altitude into `final_approach.step_down_fixes`
  tagged as "VDP".

### FAF vs FAP
- **FAF** (Final Approach Fix, non-precision): Maltese cross ✠ on profile.
- **FAP** (Final Approach Point, precision): where GS is intercepted on
  glideslope. No ✠ — look for the GS intercept altitude.

---

## Agent-generated threat list

When producing the `agent_threats` array, consider flagging:

- Cold-temp airport if the user mentions winter / low temps.
- Terrain within the missed-approach climb path (if visible on plate).
- RNP authorization required.
- Circling-only + nighttime (some ops forbid circling at night).
- Non-standard climb gradient required.
- "Takeoff minimums not standard" or "Alternate minimums not standard".
- Visibility floor (lighting-dependent).
- LOC intercept at the FAF (no GS below DA).

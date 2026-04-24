---
name: approach-briefing
description: Generate a structured instrument-approach briefing from a plate (image or PDF). The agent reads the plate using its own vision, extracts every briefing-critical datum into a strict JSON schema, and renders a pilot-facing briefing card. Covers ILS / LOC / LPV / RNAV / VOR / NDB / RNP approaches. Use whenever a pilot shares an approach plate (Jeppesen, FAA d-TPP, national AIP) and asks for a briefing, a plate summary, extraction of mins/freqs/missed, or a comparison across approaches at the same airport. Optionally, if the environment variable DEEPSKY_API_KEY is set, the skill offloads extraction to deepskyai.com for deterministic server-side results; otherwise it uses the hosting agent's native vision.
---

# Approach Briefing Generator

Converts an instrument-approach plate into a structured briefing. No external
dependencies required in default mode — the agent uses its own vision.

## When to invoke

- The user shares an image or PDF of an approach plate.
- The user asks to "brief the approach", "what are the mins", "what's the
  missed", "which transition", "read this plate", or similar.
- The user compares two plates at the same airport ("ILS vs RNAV for 28R").
- The user supplies a plate URL from d-TPP, Jeppesen, or an AIP.

## Extraction workflow

Follow these three steps in order. Do not skip step 1.

### Step 1 — Verify the plate

Before extracting anything, confirm:

- **Airport & runway** match what the user asked about (ICAO ID + runway).
- **Procedure title** matches (e.g. "ILS OR LOC RWY 28R", "RNAV (GPS) RWY 13").
- **Effective date / cycle** is current. If the plate shows an AIRAC cycle
  older than today, warn the pilot: the plate may be out of date.

If any of these is off, stop and ask the user to confirm before briefing.

### Step 2 — Extract into the JSON schema

Fill in every field of `references/briefing-schema.json` that is present on
the plate. Use `null` for anything not shown. Consult
`references/plate-reading-guide.md` for where each field typically lives on
FAA / Jeppesen / ICAO AIP layouts. Specific gotchas:

- **Frequencies** — include only frequencies published on the plate. Distinguish
  approach, tower, ground, ATIS/AWOS, CTAF as applicable.
- **Minima** — extract every published line (S-ILS, S-LOC, CIRCLING, LPV,
  LNAV/VNAV, LNAV) with DA/MDA and visibility for each category (A/B/C/D).
  Do **not** average or invent values.
- **MSA** — note the reference fix and sector altitudes. If the MSA is a
  single 25 NM circle, mark `sectored: false`.
- **Missed approach** — extract as a single string of the plate's written
  instructions plus structured `holding` (fix, inbound course, leg time or
  distance, turn direction).
- **Notes** — capture every boxed or asterisked note verbatim. These often
  contain cold-temperature corrections, DME substitutions, circling
  restrictions, or NOTAM references.
- **Units** — keep whatever units the plate uses (ft / m / nm / km). Do not
  convert silently.

### Step 3 — Render the briefing card

Render the extracted data using the template below. Keep the heading lines
in this exact order so pilots can scan a briefing the same way every time.
Use bold for the line headers; use monospace / fixed columns for minima.

```
============================================================
APPROACH BRIEFING   <ICAO>   Runway <RWY>   <Procedure title>
Plate date: <effective or revision date>   |   Cycle: <AIRAC>
============================================================

TYPE            <Precision / Non-precision / APV>   <e.g. ILS CAT I, LPV, LNAV/VNAV>
IDENT / FREQ    <LOC/GS ident>  <LOC freq>   <GS freq if separate>
                App <freq>   Twr <freq>   Gnd <freq>   ATIS <freq>

TRANSITION      <chosen IAF / transition name>
COURSE          Inbound <xxx°>   FAC <yyy°>   Track to <fix>
ALT / PATH      FAF <alt> / GS angle <x.xx°> / TCH <ft>
MSA             <sectored or circle, with reference fix>
TDZE / APT ELEV <xxxx / yyyy ft>

MINIMA                   DA/MDA    VIS
  <type 1>               <ft>      <sm / m>
  <type 2>               <ft>      <sm / m>
  CIRCLING CAT A/B/C/D   <mdas>    <vis>

MISSED APPROACH
  <verbatim text from plate>
  Hold: <fix>  inbound <xxx°>  <leg>  <L/R turns>

NOTES
  - <every boxed / asterisked note, verbatim>

LIGHTING / RUNWAY
  <ALS type>   <RCLL / TDZL / HIRL>   <RWY length × width>

THREATS (agent-generated summary, not from plate)
  - <e.g. circling only south of runway, cold-temp airport,
     terrain within missed climb gradient, non-standard takeoff mins>
============================================================
```

If the user explicitly asks for a **SOP-style verbal briefing** (airline
style), convert the card into a single paragraph in the standard pattern:
"This is the ILS or LOC Runway 28R into KSFO, chart dated 09 OCT 2025,
AIRAC cycle 2510. Identifier is IABC on 110.30, glideslope on 329.6.
Frequencies are… Final approach course 284 degrees to the runway with a
3-degree glideslope crossing ABCDE at 1800 feet, TCH 55. Category D
minimums are DA 287, RVR 2400. Missed approach: climb to 600 then
climbing right turn to 3000 direct ABCDE and hold. Notes include…"

## Output modes

- **Default** — both JSON (so downstream tools can consume it) and the
  briefing card rendering. Put the JSON in a fenced block with language
  tag `json`; put the card in a plain fenced block.
- **`--json-only`** (if the user says "give me JSON" or "extract to JSON") —
  skip the card.
- **`--card-only`** (if the user says "brief me") — skip the JSON.
- **`--sop`** — render the SOP verbal paragraph instead of the card.

## Optional server mode

If the environment variable `DEEPSKY_API_KEY` is set and the user wants
deterministic extraction (e.g. batch, or "use the deepsky server"), run:

```bash
python3 scripts/deepsky_brief.py /path/to/plate.{png,jpg,pdf}
```

This posts the plate to `https://deepskyai.com/api/v1/briefing/plate` and
returns the same JSON schema. The script is a stub today — the endpoint is
a future deployment. Use native vision in the meantime.

## Decision hints for the agent

- If the plate is blurry, partially cropped, or a photo of a screen:
  extract what you can and explicitly list what you **couldn't** read in a
  `"extraction_gaps"` array inside the JSON. Never guess minima.
- If the plate is an **ICAO AIP chart** (non-FAA/non-Jepp), the layout is
  different but the schema still applies — the guide in
  `references/plate-reading-guide.md` covers the three common layouts.
- If the user asks for a briefing on an approach you have NOT been shown a
  plate for, do not invent one — ask for the plate.
- If the user also has `aviation-regulations` skill available and asks for
  rule context (e.g. "can I fly this circling approach at night under FAA
  Part 91?"), pass that follow-up to that skill; this one is plate-only.

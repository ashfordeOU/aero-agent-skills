---
name: icing-flight-test
description: "Use when you must categorize an icing encounter and plan the icing certification flight test campaign for a transport airplane against the FAR/CS 25 Appendix C icing envelopes: judge the continuous maximum and intermittent maximum regime membership from liquid water content, median volumetric diameter and total air temperature, rate the icing encounter severity for the flight test log, screen the natural icing search conditions against the freezing level and the forecast liquid water content, build the artificial ice shape test matrix with glaze, rime, mixed and runback shapes over the critical surfaces, and list the ice protection effectiveness test points to fly. Produces the envelope verdict, severity rating, search go/no-go and shape matrix verdict that gate the program. Trigger: icing flight test, natural icing, artificial ice shapes, appendix C envelope, liquid water content, median volumetric diameter, runback ice, supercooled large droplet, icing encounter severity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: envelope
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: envelope
  tags: [icing-flight-test, natural-icing, artificial-ice-shapes, appendix-c-envelope, liquid-water-content, median-volumetric-diameter, runback-ice, supercooled-large-droplet, icing-encounter-severity, ice-protection-effectiveness-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# Icing Flight Test (flight-test-operations/envelope/icing-flight-test)

Use when the task is planning the icing certification flight test
campaign for a transport airplane: categorizing each icing encounter
against the FAR/CS 25 Appendix C continuous maximum and intermittent
maximum envelopes, rating encounter severity, screening the natural
icing search conditions, and building the artificial ice shape test
matrix that simulates the critical in-flight and runback ice shapes on
the surfaces that see the ice. This leaf implements the simplified
envelope model in pure Python, stdlib only. It pairs with
flight-test-operations/envelope/envelope-expansion for the program
sequencing around the icing block and
flight-test-operations/envelope/v-speeds for the test speed reference,
and it cites vehicle-design/sizing/ice-protection-sizing as the
design-side sibling whose thermal sizing math this leaf does not
replace.

## Domain quick reference

- Envelope model: the Appendix C continuous maximum (stratiform) and
  intermittent maximum (cumuliform) envelopes bound the flight liquid
  water content (LWC) as a function of total air temperature (TAT) over
  -30 C to 0 C, at given median volumetric diameter (MVD) bands. The
  module constants are paraphrased representative boundary points at
  reference level, NOT the regulation's full table; the full Appendix C
  table is authority-controlled and must be read from the regulation.
- Continuous maximum anchors: LWC_CM_MAX = 0.44 g/m3 at -10 C, scaling
  linearly to LWC_CM_0C = 0.20 g/m3 at 0 C and LWC_CM_N30C = 0.15 g/m3
  at -30 C; MVD band 15 to 40 micron (CM_MVD_MIN, CM_MVD_MAX).
- Intermittent maximum anchors: LWC_IM_MAX = 1.4 g/m3 at -10 C, scaling
  linearly to LWC_IM_0C = 0.65 g/m3 at 0 C and LWC_IM_N30C = 0.35 g/m3
  at -30 C; MVD band 15 to 50 micron (IM_MVD_MIN, IM_MVD_MAX).
- LWC limit segments: cm_lwc_limit(tat) and im_lwc_limit(tat)
  interpolate the two linear segments between the anchors and clamp the
  temperature to [-30, 0] C.
- Envelope verdict: envelope_verdict(lwc, mvd, tat) reports the regime
  as continuous-max when the point sits under the continuous limit in
  its MVD band, intermittent-max when it sits under the intermittent
  limit in its MVD band but above the continuous envelope, and outside
  otherwise; margin = governing limit LWC - encounter LWC.
- SLD exclusion: any encounter with mvd > SLD_MVD_MIN = 50 micron is a
  supercooled large droplet case and sits outside the Appendix C
  envelope by this model.
- Severity: encounter_severity(lwc, tat, duration_min) forms the ratio
  lwc / cm_lwc_limit(tat); below 0.5 trace, below 1.0 light, below 1.5
  moderate when also under the intermittent limit (else severe), at or
  above 1.5 severe. A duration above SEVERE_DURATION_MIN = 30 min steps
  the label up one level, capped at severe.
- Natural icing search: natural_icing_search_ok accepts a forecast point
  when TAT is within [-30, 0] C, the forecast LWC is at least
  SEARCH_LWC_FRACTION = 0.1 times the continuous limit, and the
  freezing level sits at or above the cloud base.
- Artificial shapes: artificial_shape_check audits the shape matrix
  against CRITICAL_SURFACES = [wing, horizontal-tail, vertical-tail,
  windshield, probe], requiring coverage_frac at least COVERAGE_MIN =
  0.8 and roughness_ok True per surface, with shape types glaze, rime,
  mixed and runback.
- Effectiveness points: standard_envelope_rows() lists the boundary
  conditions to fly; effectiveness_test_points(configs, rows) pairs
  each configuration (anti-ice on or off, de-ice cycle setting) with
  the envelope rows and their expected regimes.
- Units: LWC in g/m3, MVD in micron, TAT in C, altitude in ft,
  duration in minutes.

## Workflow

1. Fix the encounter flight condition: total air temperature TAT (C),
   measured or forecast liquid water content LWC (g/m3), median
   volumetric diameter MVD (micron) and the exposure duration.
2. Get the governing limits with cm_lwc_limit and im_lwc_limit and
   confirm the anchor behavior at -30, -10 and 0 C.
3. Categorize the encounter with envelope_verdict; record the regime,
   the margin and the reasons. Treat any mvd above 50 micron as the
   supercooled large droplet exclusion with its explicit reason.
4. Rate the encounter with encounter_severity for the flight test log;
   let the exposure duration step trace or light encounters up when the
   run exceeds 30 minutes.
5. Screen the natural icing search conditions with
   natural_icing_search_ok: TAT band, forecast LWC against 10 percent
   of the continuous limit, and the freezing level relative to the
   cloud base.
6. Build the artificial ice shape matrix and audit it with
   artificial_shape_check: every surface in CRITICAL_SURFACES must
   carry a glaze, rime, mixed or runback shape at coverage_frac at
   least 0.8 with representative roughness.
7. Lay out the effectiveness block: standard_envelope_rows() gives the
   boundary rows, then effectiveness_test_points pairs each test
   configuration (anti-ice on or off with its de-ice cycle setting)
   against the rows that must be flown.
8. Summarize each encounter for the test log with summarize and close
   with the deterministic contract test scripts/test_icing_flight_test.py.

## Worked example

Certification campaign planning for the reference encounter at TAT
-10 C, LWC 0.30 g/m3, MVD 20 micron:

- cm_lwc_limit(-10) = 0.44 g/m3; envelope_verdict(0.30, 20, -10)
  returns in_envelope True, regime continuous-max, margin 0.44 - 0.30 =
  0.14 g/m3.
- A heavier point at the same temperature, LWC 1.0 g/m3, MVD 25
  micron, sits above the continuous limit: im_lwc_limit(-10) = 1.4
  g/m3, so the verdict is intermittent-max with margin 0.4 g/m3.
- LWC 1.6 g/m3 at MVD 25 micron exceeds both limits: verdict outside
  with margin -0.2 g/m3.
- LWC 0.3 g/m3 at MVD 60 micron and TAT -5 C is outside with the
  supercooled-large-droplet reason, even though its LWC alone would fit.
- Severity: LWC 0.22 g/m3 at -10 C gives ratio 0.5, rated light
  (index 1); the same exposure held 45 minutes steps to moderate
  (index 2).
- Artificial shape matrix covering wing and horizontal-tail only fails
  artificial_shape_check with a missing vertical-tail issue (plus
  windshield and probe); the full five-surface matrix at coverage 0.9
  with roughness_ok True passes with no issues.
- Natural icing search at TAT -8 C, cloud base 3000 ft, freezing level
  2000 ft and forecast LWC 0.1 g/m3 returns ok False (freezing level
  below the cloud base); the same point with the freezing level at
  4000 ft returns ok True.
- Effectiveness rows pair the anti-ice-off and anti-ice-on
  configurations with the continuous-maximum-peak-lwc and
  intermittent-maximum-peak-lwc rows and their expected regimes.
- summarize(0.30, 20, -10, 45) folds the verdict and the severity into
  one report dict for the log.

## Verification

- Confirm cm_lwc_limit(-10) returns exactly 0.44 and im_lwc_limit(-10)
  exactly 1.4, with the linear segments hitting 0.32 g/m3 at -5 C for
  the continuous envelope.
- Confirm the worked margins: continuous-max margin 0.14 at LWC 0.30,
  intermittent-max margin 0.4 at LWC 1.0.
- Confirm the MVD band edges: MVD 40 stays continuous-max, MVD 41 and
  MVD 50 fall under intermittent-max, and anything above 50 micron is
  the supercooled large droplet exclusion.
- Confirm severity ratio 0.5 rates light and steps to moderate past 30
  minutes, capped at severe.
- Confirm every negative lwc or mvd, every non-finite input, every
  coverage_frac outside [0, 1], every unknown surface and every
  unknown shape type raises ValueError.
- Run the contract test offline: python3
  scripts/test_icing_flight_test.py (35 tests, deterministic).

## Related leaves

- flight-test-operations/envelope/envelope-expansion: program
  sequencing and expansion steps around the icing block.
- flight-test-operations/envelope/v-speeds: test speed references used
  during the icing points.
- flight-test-operations/envelope/stall-characteristics-testing:
  stall and handling checks flown with artificial ice shapes in place.
- vehicle-design/sizing/ice-protection-sizing: the design-side thermal
  sizing sibling this leaf does not replace.
- avionics/do160/environmental-qualification: chamber qualification of
  the ice detection and probe equipment, distinct from this flight
  level campaign.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_icing_flight_test.py

The test covers the LWC limit segments at the three anchor
temperatures, both worked-example envelope margins, the SLD exclusion
reason, the severity ladder with the duration step, the natural icing
search screening flags, the artificial shape matrix coverage and
roughness issues, the effectiveness test point pairing, and ValueError
rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: FAR 25 Appendix C and CS 25
  Appendix C define the authority-controlled icing envelopes; this leaf
  carries only a simplified typical summary as paraphrased module
  constants per standards-map.yaml. Read the regulation for the full
  table before any certification submission.
- compliance: STANDARDS-REF, gated: false.

---
name: e2020-undervoltage-threshold-nominal-bus-range
description: "Verify that a ground adjustable undervoltage trip point covers its required span when expressed against the nominal bus value, per clause 5.4.3.1.1 of ECSS-E-ST-20-20C. Use when a unit declares a ladder of trip points as shares of nominal and the settable span has to be judged rather than one figure: convert each share to volts at the nominal bus, widen it by reference and sensing tolerance, keep only settings whose band clears the lowest normal bus voltage and stays above the equipment operating floor, show the usable settings reach both ends of the required span, check the step resolution, and refuse an in flight adjustment. Trigger: ecss, e-st-20-20c, ground-adjustable-undervoltage-threshold, undervoltage-threshold-percent-of-nominal-bus, undervoltage-setting-step-resolution, nuisance-undervoltage-trip-clearance, undervoltage-adjustment-range-coverage, equipment-operating-floor-clearance."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e2020-undervoltage-threshold-nominal-bus-range, ground-adjustable-undervoltage-threshold, undervoltage-threshold-percent-of-nominal-bus, undervoltage-setting-step-resolution, nuisance-undervoltage-trip-clearance, undervoltage-adjustment-range-coverage, equipment-operating-floor-clearance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — Undervoltage Threshold Against the Nominal Bus (space-systems/ecss/e2020-undervoltage-threshold-nominal-bus-range)

Use when the task is the adjustable trip point question of
ECSS-E-ST-20-20C clause 5.4.3.1.1 — showing that the undervoltage trip
point of a unit, declared as a share of the nominal bus voltage, can
actually be set anywhere across the span the design requires, by a
ground activity.

## Domain quick reference

- The requirement is about a span, not a point. The right trip point
  depends on the mission, the battery and the loads that end up behind
  the unit, so the design is asked for adjustability across a range and
  a single well-chosen threshold does not answer it.
- Expressing the point as a share of nominal is what makes it portable.
  The same unit on a 28 V bus and a 50 V bus trips at the same fraction
  of its supply, so the ladder is validated in per cent and converted to
  volts only once the nominal value is known. A trip point quoted
  straight in volts hides which bus it belongs to.
- A setting is not a point either. Reference tolerance, divider
  tolerance, sensing offset and drift widen each setting into a band,
  and it is that band, not the label on the setting, that has to sit
  where the design needs it.
- Two bounds close on the band from opposite directions. From above, it
  has to stay clear of the lowest voltage the bus reaches in normal
  operation by a declared margin, or the unit sheds its load during a
  manoeuvre, a discharge or an eclipse. From below, it has to stay above
  the voltage under which the protected equipment is no longer
  characterised, which is the very situation the protection exists to
  prevent.
- Only settings whose band clears both bounds count towards the span. A
  unit advertising a wide adjustment whose top half nuisance-trips is
  not adjustable over that span in any useful sense, so coverage is
  judged on the usable settings and not on the ladder as printed.
- A setting outside the required span that is not usable is a different
  matter from one inside it. The design was never asked to work there,
  but the setting remains selectable by whoever configures the unit, so
  it is reported and marked rather than failed.
- Granularity is part of the requirement. If neighbouring settings are
  further apart than the resolution the design calls for, a required
  trip point can fall between two settings and be reachable by neither.
- Adjustment is a ground activity. A trip point reachable by telecommand
  in flight is a different and more hazardous provision than a strap, a
  link or a selection resistor fitted before launch.

## Workflow

1. Validate the ladder: at least two settings, unique identifiers, no
   two settings on the same trip point, and every point below nominal,
   because a trip at or above the nominal bus is not an undervoltage
   trip. Sort into rising order so the report reads as a ladder.
2. Refuse to continue without a nominal bus voltage or a required span;
   neither the conversion nor the coverage question exists without them.
3. Check the declared means of adjustment. A strap, link, jumper,
   potentiometer or selection resistor is a ground activity; a
   telecommand is not, and that closes the assessment. An undeclared
   means is an advisory, not a pass.
4. Convert every setting to volts at the nominal bus and widen it by the
   relative and absolute setting tolerance into the band it can land in.
5. Grade each band against the two bounds: the lowest steady-state bus
   voltage less the nuisance clearance above, the equipment operating
   floor below. A band clearing both is usable.
6. Take the lowest and highest usable settings as the achievable span
   and compare both ends with the required span, reporting the shortfall
   at each end in per cent of nominal.
7. Report each unusable setting, as a finding when it sits inside the
   required span and as an advisory when it sits outside it.
8. Compare the widest gap between neighbouring settings with the
   resolution the design calls for, and close with a verdict.

## Pitfalls

- Checking the nominal trip point against the bounds. The setting
  tolerance is what decides whether the protection nuisance-trips or
  sits under the equipment floor, and the labelled point is the one
  value guaranteed not to be the worst case.
- Judging coverage on the printed ladder. Settings that cannot be used
  still appear in the data sheet, and counting them makes an unusable
  adjustment look like a compliant one.
- Converting to volts before validating the shares. A share at or above
  nominal becomes a plausible-looking voltage and the error survives all
  the way to the report.
- Treating the two bounds as one margin. They come from different
  places — the bus profile above, the protected equipment below — and a
  design can fail either while comfortably clearing the other.
- Failing a setting outside the required span. The design was not asked
  to work there; the honest output is an advisory that the setting is
  selectable and should be marked.
- Ignoring the step between settings. A span that covers the requirement
  in three coarse jumps cannot reach a point between them, which is a
  resolution failure, not a coverage one.
- Accepting an in-flight adjustment as satisfying a ground-adjustable
  requirement. It is a broader capability and a larger hazard, and it is
  not the provision that was asked for.
- Comparing a band edge with a bound by bare arithmetic. The edge is
  built from a product and a sum, so a case meant to sit exactly on the
  bound can land a few units in the last place outside it; the
  comparison absorbs that while the bounds stay as declared.

## Behavior contract (gate 3)

The ladder validation, share-to-volts conversion, setting-band
construction, grading against the nuisance ceiling and the equipment
floor, usable span extraction, required-range coverage, step-resolution
check, ground-only adjustment check and overall verdict are exercised by
the gate 3 contract test:
scripts/test_e2020_undervoltage_threshold_nominal_bus_range.py against
scripts/e2020_undervoltage_threshold_nominal_bus_range_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_undervoltage_threshold_nominal_bus_range.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e2020-undervoltage-hysteresis-width
description: "Verify the minimum width between the undervoltage trip point and the enable point of a protection function, per clause 5.4.3.5.1 of ECSS-E-ST-20-20C. Use when a unit declares both thresholds and the separation still standing after setting tolerance has to be shown. Take the declared separation, erode it by the tolerance of each comparator, express it against the nominal bus, and compare that worst case with the minimum the project requires. Report a design carrying no hysteresis at all as outside the clause rather than failing it, and flag an enable point the bus can never reach. Trigger: ecss, e-st-20-20c-clause-5-4-3-5-1, undervoltage-trip-to-enable-separation, undervoltage-hysteresis-width-minimum, undervoltage-enable-point-reachability, undervoltage-threshold-tolerance-erosion, undervoltage-hysteresis-width-against-nominal-bus."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e-st-20-20c-clause-5-4-3-5-1, e2020-undervoltage-hysteresis-width, undervoltage-trip-to-enable-separation, undervoltage-hysteresis-width-minimum, undervoltage-enable-point-reachability, undervoltage-threshold-tolerance-erosion, undervoltage-hysteresis-width-against-nominal-bus]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Undervoltage Hysteresis Width (space-systems/ecss/e2020-undervoltage-hysteresis-width)

Use when the task is clause 5.4.3.5.1 of ECSS-E-ST-20-20C: an undervoltage
protection that carries hysteresis has to keep a stated minimum separation
between the point where it trips and the point where it enables again. This
leaf takes the two declared thresholds, the tolerance each of them is set and
sensed with, and the minimum the project asks for, and says what separation
actually survives.

## Domain quick reference

- The clause is conditional. It does not ask for hysteresis; it says how wide
  the gap has to be once hysteresis is there. A unit whose enable point sits
  on its trip point is not short of width, it has no hysteresis, and the
  honest answer is that this clause does not grade it — a different clause
  decides whether the absence is acceptable.
- The width that matters is the one left after tolerance. The trip comparator
  can sit at the top of its band while the enable comparator sits at the
  bottom of its own, so the two tolerances subtract from the designed gap
  together. A design with a nominal gap wider than the minimum and a tolerance
  stack wider than the surplus has no compliant width at all.
- Expressing the width against the nominal bus is what makes the number
  portable. A 1.4 V gap means something different on a 28 V bus and on a 100 V
  bus, so the minimum is normally stated as a fraction of nominal and the
  volts are derived from it rather than quoted on their own.
- A project can also carry an absolute floor, in volts, below which no gap is
  acceptable whatever the bus is. Where both a fraction and a floor exist the
  binding requirement is the larger of the two, not the one that happens to
  suit the design.
- Both thresholds have to be reachable on the bus they protect. An enable
  point at or above the nominal bus voltage can never be crossed on the way
  up, so the protection latches the load off for good; a trip point at or
  above nominal trips a healthy bus. Either placement is wrong regardless of
  how wide the gap between them is.
- Width is a ratio question as well as a volts question. Reporting the gap as
  a percentage of nominal alongside the volts lets the same design be compared
  against a sibling unit on another bus without redoing the arithmetic.

## Workflow

1. Validate the thresholds, the nominal bus and both tolerances; an enable
   point below the trip point is an input error, not a negative gap to be
   reported.
2. Derive the declared separation and the same separation as a fraction of the
   nominal bus.
3. Decide whether hysteresis exists at all, with a named tolerance absorbing
   the representation error of the subtraction.
4. Erode the declared separation by the trip tolerance and the enable
   tolerance together to obtain the worst-case width.
5. Form the required width from the minimum fraction against the nominal bus
   and the absolute floor, taking whichever binds harder.
6. Compare worst case with required, treating an exact landing on the bound as
   met rather than short.
7. Check placement of both thresholds against the nominal bus, and return the
   verdict: outside the clause when no hysteresis is declared, non-compliant
   on a placement error or a width shortfall, compliant otherwise.

## Pitfalls

- Grading the designed gap and ignoring the tolerance stack. The clause is
  about the separation the hardware guarantees, and two comparators drifting
  toward each other is the ordinary case, not a worst case to be waived.
- Failing a design that has no hysteresis. The minimum width applies where
  hysteresis exists; reporting an absent band as a width shortfall answers a
  question nobody asked and hides the real one.
- Taking the fraction and the absolute floor as alternatives. Where a project
  states both, the wider of the two is the requirement; picking the softer one
  because it passes is a grading error.
- Quoting the width in volts with no reference bus. The figure cannot be
  compared with the minimum, and a sibling unit on a different bus voltage
  will be judged against the wrong number.
- Letting the enable point rise to or above the nominal bus to buy width. The
  gap looks generous and the protection never re-enables, which is a heavier
  failure than the shortfall it was meant to cure.
- Relaxing the minimum to clear a design that lands exactly on it. The
  equality is a floating-point representation question, handled by the
  tolerance inside the comparison, not by moving the limit.

## Behavior contract (gate 3)

The threshold validation, declared separation, hysteresis presence decision,
tolerance erosion, required-width derivation from fraction and floor, margin
comparison, threshold placement checks and verdict are exercised by the gate 3
contract test:
scripts/test_e2020_undervoltage_hysteresis_width.py against
scripts/e2020_undervoltage_hysteresis_width_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_undervoltage_hysteresis_width.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

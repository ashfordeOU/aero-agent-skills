---
name: e2008-blocking-diode-dimensions-weight
description: "Use when a blocking diode measurement sheet is judged against its control drawing. Verify a blocking diode against the lateral outline, thickness, terminal geometry and interconnector placement of ECSS-E-ST-20-08C clause 12.6.2: put each measured feature inside its own plus and minus band and name the state, judge the anode and cathode pads one at a time for bonding coverage and string-current density, combine the two axis offsets of every attachment point into one diametrical true-position value, grow the measured outline by that value into the keep-out envelope the layout must reserve, and cross-check the weighed mass against the mass the outline and density already imply. Trigger: ecss, e-st-20-08c-clause-12-6-2, blocking-diode-outline-tolerance-band, blocking-diode-thickness-band, blocking-diode-terminal-pad-geometry, blocking-diode-interconnector-true-position, blocking-diode-keep-out-envelope, blocking-diode-mass-density-crosscheck."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-blocking-diode-dimensions-weight, blocking-diode-outline-tolerance-band, blocking-diode-thickness-band, blocking-diode-terminal-pad-geometry, blocking-diode-interconnector-true-position, blocking-diode-keep-out-envelope, blocking-diode-mass-density-crosscheck]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Blocking Diode Dimensions and Weight (space-systems/ecss/e2008-blocking-diode-dimensions-weight)

Use when the task is to decide whether a delivered blocking diode is
dimensionally the part the panel was laid out around under
ECSS-E-ST-20-08C clause 12.6.2 -- lateral size, thickness, the terminal
geometry the attachments land on, and where the interconnector
attachment points actually sit against the control drawing.

## Domain quick reference

- Four families of feature carry the clause. The lateral outline sets
  the layout, the keep-out reservation and the bonding footprint. The
  thickness sets the stack height under the coverglass or the potting
  and is the term the mass follows most directly. The terminal
  geometry decides whether the attachments can be made at all and
  whether they can pass the string current. The interconnector
  placement decides whether those attachments land where the harness
  expects them.
- A blocking diode sits in series with its string, so both terminals
  carry the whole string current and both pads are judged, one at a
  time, against the same duty. A generous anode does not excuse a
  starved cathode, and the two fail independently.
- Every dimensional feature is judged inside its own plus and minus
  band, and the direction of the departure is part of the answer: a
  diode running long is a different layout problem from one running
  short, and both differ from one that fits.
- A tolerance written as a subtraction rarely lands on the limit the
  drawing means. Nominal 0,30 minus 0,03 is not 0,27 in binary, so a
  part measuring exactly the drawn limit must not be refused by the
  arithmetic that checks it.
- Attachment offsets are not judged one axis at a time. A point inside
  the per-axis allowance on both axes can still sit outside the round
  zone the drawing permits, which is why the offsets are combined into
  one diametrical true-position value and that value is compared.
- The same true-position value then grows the outline into the
  envelope the layout has to reserve. A part can measure inside every
  band and still not fit, because the reservation has to hold the body
  wherever the placement tolerance is free to put it.
- Mass is not an independent measurement. Outline, thickness and
  declared material density already imply it, so a weighed mass that
  disagrees with the implied mass means one of the two came off a
  different part.
- A diode cannot be machined back to size. An out-of-band feature is a
  procurement outcome, not a rework instruction, so the departure is
  reported with its state rather than absorbed.

## Workflow

1. Validate the acceptance policy first: terminal coverage floor,
   current-density ceiling, true-position zone and mass crosscheck
   tolerance. A mass tolerance that would admit a part of any mass is
   refused rather than used.
2. Take each dimensional feature in turn, derive its band from the
   nominal and the two tolerances, and name the state as in-band,
   under-band or over-band. A feature landing exactly on a limit is
   in-band; the comparison tolerance absorbs representation error and
   the limit does not move.
3. Derive the footprint from the measured lateral dimensions, not the
   nominal ones, because the pads have to sit on the diode that
   arrived.
4. Refuse a pad pair that cannot both be on the part as measured
   before either pad is graded, since that is a measurement error and
   not a coverage result.
5. Take each terminal through both of its duties in turn: coverage of
   the footprint, and current density at the declared string current.
   Keep both results per terminal so a starved one is visible.
6. Combine each attachment point's two axis offsets into one
   true-position value and keep the worst point, because the harness
   fits the worst one.
7. Grow the measured outline by that value and put the result inside
   the reserved keep-out, in both directions.
8. Derive the implied mass from the measured outline, thickness and
   declared density, and compare it with the weighed mass before any
   band is believed.
9. Close on one verdict: dimensions conforming, outline out of band,
   terminal geometry inadequate, attachment out of position, keep-out
   envelope exceeded, or mass inconsistent -- reporting every
   departure found, not only the one that names the verdict.

## Pitfalls

- Grading one terminal and assuming the other. The series duty puts
  the same current through both pads, and the small one sets the
  answer whatever the large one measures.
- Checking attachment offsets axis by axis. Both axes inside their
  allowance is not the same statement as the point being inside the
  round zone, and the combined value is the larger of the two numbers
  every time the point is off both axes.
- Reading an in-band outline as a part that fits. The keep-out holds
  the body plus its placement freedom, so a part at the top of its
  band with a loose attachment can burst a reservation that the
  nominal part sat comfortably inside.
- Deriving the footprint from the drawing nominal. The pads have to
  sit on the part that arrived; a diode at the short end of its band
  has a smaller footprint and a better coverage fraction than the
  drawing suggests.
- Treating the mass as a separate acceptance line. It is a crosscheck
  on the outline: a mass that disagrees with the geometry invalidates
  the dimensional sheet rather than adding one more finding to it.
- Rejecting a part that measures the drawn limit. The limit is the
  drawing's, not the subtraction's, and a strict comparison against a
  computed bound refuses good hardware on some machines and accepts it
  on others.
- Recording an out-of-band diode as a rework item. The part cannot be
  cut back, so the state is what gets reported and the layout, not the
  diode, is what has to move.

## Behavior contract (gate 3)

The policy validation, band limits and feature states, deviation
fractions, footprint area, per-terminal coverage and current density,
the combined pad-pair check, the diametrical true-position combination
and worst-point selection, the grown keep-out envelope, the
implied-mass crosscheck and the dimensional verdict are exercised by
the gate 3 contract test:
scripts/test_e2008_blocking_diode_dimensions_weight.py against
scripts/e2008_blocking_diode_dimensions_weight_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_blocking_diode_dimensions_weight.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

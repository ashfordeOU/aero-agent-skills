---
name: e2008-bare-cell-welding-area-limits
description: "Use when a weld-zone void list has to become a verdict. Verify that voids and bubbles inside the contact welding areas of a bare cell stay within the maximum diameter fixed for the part under ECSS-E-ST-20-08C clause 7.5.1.5.2: close the assessment when no drawing fixes the limit, govern on the major axis and fall back to an area-equivalent diameter only as the weaker figure it is, place each void against the weld zone, reject past the limit, review an acceptance held by less than the measurement uncertainty, and catch a crowded zone on void area fraction and count. Trigger: ecss, e-st-20-08c-clause-7-5-1-5-2, contact-welding-area-void-limit, weld-zone-bubble-diameter, void-major-axis-governing-chord, weld-zone-void-area-fraction, drawing-fixed-void-diameter."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bare-cell-welding-area-limits, contact-welding-area-void-limit, weld-zone-bubble-diameter, void-major-axis-governing-chord, weld-zone-void-area-fraction, drawing-fixed-void-diameter, solar-cell-weld-nugget-seat]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Bare Cell Welding Area Void Limits (space-systems/ecss/e2008-bare-cell-welding-area-limits)

Use when the task is the void limit of ECSS-E-ST-20-08C clause 7.5.1.5.2 --
voids or bubbles have been recorded on a bare cell and the ones lying
inside a contact welding area have to be measured against the maximum
diameter fixed for the part.

## Domain quick reference

- The limit belongs to the part, not to the house. It is fixed on the
  drawing, so a verdict quoted without that reference behind it is not a
  verdict against this clause; an unreferenced limit closes the assessment
  rather than passing it.
- The clause reads like a one-line comparison and is not, because the
  diameter of a void has to be decided before anything can be compared
  with it.
- A void is rarely round. When a major and a minor axis are recorded the
  long chord governs, because that is the distance a weld nugget has to
  cross to find sound metal on the far side.
- An area-equivalent diameter is the fallback, not the answer. An
  elongated void and a round one of the same area give the same equivalent
  figure while the elongated one reaches much further, so an area-only
  record is flagged as the weaker statement it is rather than being
  credited as a measurement of reach.
- The margin is part of the comparison. A void inside the limit by less
  than the measurement is good to is not demonstrably inside it, so the
  comparison runs twice: the nominal value decides the rejection and the
  value plus its uncertainty decides whether the acceptance can be made
  without a second look.
- Location still matters. A bubble away from the weld zones is a real
  finding under other clauses of the cell inspection and not a rejection
  here, so it is carried as an advisory rather than dropped.
- A void that straddles the zone boundary still has its body in the weld
  zone, so it is in scope; the containment test works on the void body and
  not on its centre alone.
- A scatter of individually admissible bubbles is still a bad weld zone.
  The void area fraction and the void count per welding area catch the zone
  where every single bubble passed and there is no sound metal left to seat
  a nugget on.
- A limit larger than the zone it applies to is a transcription error, not
  a generous drawing, and it is refused at the input rather than quietly
  passing every void.

## Workflow

1. Normalise each welding area and the limit fixed for it, refusing a limit
   that carries no drawing reference and one wider than the zone itself.
2. Derive the governing diameter of each void: major axis first, a stated
   diameter next, an area-equivalent diameter only as a last resort and
   flagged as such.
3. Place each void against each welding area on its body rather than its
   centre, and set the ones that reach no zone aside as advisories.
4. Compare each contained void with the limit -- past it rejects, inside it
   by less than the measurement uncertainty goes to review.
5. Total the void footprint and the void count for each zone and apply the
   area-level allowances, which can send a zone to review on voids that
   each passed on their own.
6. Roll up by severity rather than record order, and keep an unestablished
   limit ahead of every other outcome: a zone nobody fixed a diameter for
   has not been assessed.

## Pitfalls

- Reporting an area-equivalent diameter for an elongated void. It is the
  one figure guaranteed to understate the reach the weld has to cross.
- Comparing against a house limit because the drawing was not to hand.
- Accepting a void that sits inside the limit by less than the measurement
  uncertainty, which is an acceptance the instrument cannot support.
- Testing containment on the void centre. A void centred just outside the
  zone can still have half its body in it.
- Rejecting a cell on a bubble that is nowhere near a weld zone, or losing
  that bubble entirely because this clause does not reject on it.
- Accepting a zone because every void passed. The area fraction and the
  count exist for exactly that case.
- Taking a drawing limit wider than the welding area at face value.
- Taking the last disposition in the record as the zone verdict instead of
  the most severe one.
- Comparing a diameter with the limit by bare arithmetic. An equivalent
  diameter comes out of a square root and the fraction out of a quotient of
  summed areas, so a value that should sit exactly on its bound can
  evaluate a few units in the last place past it; the comparisons absorb
  that representation error while the bounds stay untouched.

## Behavior contract (gate 3)

The drawing-limit precondition, the governing diameter derivation, the
area-equivalent fallback flag, the body-based containment test, the nominal
and uncertainty comparisons, the void area fraction, the void count
allowance and the severity rollup are exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_welding_area_limits.py against
scripts/e2008_bare_cell_welding_area_limits_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_welding_area_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

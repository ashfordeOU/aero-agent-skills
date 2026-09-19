---
name: q7045-hardness-testing
description: "Evaluate a hardness indentation and, where the table allows it, carry the reading onto another scale. Use when the methods clause of ECSS-Q-ST-70-45 calls for Brinell, Vickers or Rockwell hardness: reduce the impression to its number, test the Brinell impression-to-ball ratio against the band the scale is defined over, reconcile force and indenter through the load index, report an impression pressed too near a neighbour or an edge, and interpolate a conversion inside the table while refusing one beyond it. Trigger: ecss, q-st-70-45, brinell-impression-ball-ratio, brinell-load-index-pairing, vickers-diagonal-asymmetry, rockwell-c-permanent-depth, hardness-scale-conversion-table."
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
  tags: [ecss, q-st-70-45-mechanical-testing-scope, q7045-hardness-testing, brinell-impression-ball-ratio, brinell-load-index-pairing, vickers-diagonal-asymmetry, rockwell-c-permanent-depth, hardness-scale-conversion-table]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanical Testing of Metals -- Hardness Testing (space-systems/ecss/q7045-hardness-testing)

Use when the methods clause of ECSS-Q-ST-70-45 calls for a hardness value: a
ball or a diamond has been pressed into a prepared surface under a defined
force, the impression has been read, and the question is whether the reading
is valid on its own scale and whether it may be reported on a different one.

## Domain quick reference

- An impression has a valid size window. Below the lower end the reading
  samples a handful of grains and scatters; above the upper end the ball is
  pushing into the bulk rather than indenting it, and the number drifts.
- Force and indenter are one setting, not two. The load index ties them, and
  a force paired with a ball outside the standard set puts the reading on a
  different curve from the rest of the report while still looking like a
  hardness number.
- Vickers diagonals should agree. A lopsided impression says the surface was
  not flat and normal to the indenter, and the mean diagonal then hides a
  tilted, oversized hole.
- An impression needs clearance. Pressed close to its neighbour or to a free
  edge, it sits in metal that has already been worked or that can flow away,
  and it reads low in one case and high in the other.
- Conversion is a table lookup with interpolation, and nothing else. Outside
  the tabulated range there is no relation to extrapolate, and at a level
  where the target scale has no entry there is no value to interpolate
  towards; both cases have to refuse rather than invent.

## Workflow

1. Resolve the scale and confirm the measurements that scale needs are all
   present before reducing anything.
2. Reduce the impression: the cap area for Brinell, the mean diagonal for
   Vickers, the permanent depth for Rockwell C.
3. Test the Brinell impression-to-ball ratio against its band and the load
   index against the standard pairings, with inclusive edges.
4. Compare the two Vickers diagonals against the asymmetry limit before the
   mean is trusted.
5. Compare the impression against its spacing and edge-distance minima,
   expressed as multiples of its own size.
6. Convert onto the reporting scale by interpolating inside the table, and
   turn a refused conversion into a finding rather than a silent absence.
7. Compare the reading with the acceptance band on the scale it was taken on,
   never on the converted one.

## Pitfalls

- Converting outside the table. A relation fitted over the tabulated range is
  not a relation beyond it, and the extrapolated number looks exactly as
  authoritative as a real one.
- Accepting a Brinell reading from a non-standard force-and-ball pairing. The
  number is self-consistent and not comparable with anything else measured.
- Averaging two very different Vickers diagonals. The mean is arithmetically
  correct and describes an impression that was never made.
- Applying the acceptance band to the converted value. The band belongs to
  the scale it was written for, and conversion adds its own spread.
- Treating an impression ratio that lands exactly on the band edge as out of
  band. Representation of the edge failed, not the impression.

## Behavior contract (gate 3)

The Brinell, Vickers and Rockwell C reductions, the impression-to-ball ratio
band, the load-index pairing, the diagonal asymmetry limit, the spacing and
edge-distance minima, the table interpolation with its refusals and the
acceptance-band comparison are exercised by the gate 3 contract test:
scripts/test_q7045_hardness_testing.py against
scripts/q7045_hardness_testing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7045_hardness_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

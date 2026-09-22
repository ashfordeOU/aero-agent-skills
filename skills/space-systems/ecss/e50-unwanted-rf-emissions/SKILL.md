---
name: e50-unwanted-rf-emissions
description: "Evaluate the unwanted emissions a space link transmitter produces against the limits that apply to them, under ECSS-E-ST-50C clause 5.6.12.3. Place each measured component in its domain first — inside the necessary bandwidth, in the out-of-band domain around it, or out in the spurious domain — then grade it against that domain's limit: an interpolated spectral mask out of band, a flat limit in the spurious domain, and no grading at all for the wanted carrier. Report per-component margin, the worst offender and a three-way verdict. Use when reviewing spacecraft transmitter spectral compliance. Trigger: ecss, e-st-50-communications, unwanted-rf-emission-limits, out-of-band-emission-domain, spurious-emission-domain, space-link-spectral-emission-mask, transmitter-emission-margin."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.6.12.3
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-unwanted-rf-emissions, unwanted-rf-emission-limits, out-of-band-emission-domain, spurious-emission-domain, space-link-spectral-emission-mask, transmitter-emission-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Unwanted RF Emissions (space-systems/ecss/e50-unwanted-rf-emissions)

Use when a spacecraft transmitter's measured spectrum is being graded, per
ECSS-E-ST-50C clause 5.6.12.3 — which emissions are unwanted, and whether each
of them is under the limit that actually applies to it.

## Domain quick reference

- The domain comes before the limit. A component is inside the necessary
  bandwidth, in the out-of-band domain immediately around it, or out in
  the spurious domain, and each of those carries a different limit.
  Grading against the wrong one produces a confident wrong answer.
- What sits inside the necessary bandwidth is the wanted emission. It is
  not unwanted, it is not graded, and running the out-of-band mask across
  it fails the carrier against its own transmitter.
- The out-of-band domain is bounded, not open. It runs from the edge of
  the necessary bandwidth out to a fixed multiple of that bandwidth
  either side of the carrier; beyond that boundary the spurious limit
  takes over.
- The out-of-band limit is a shape, not a number. It tightens with offset,
  so a component is measured against an interpolated mask value at its own
  offset and two components at the same level can land on opposite sides
  of compliance.
- Meeting a limit exactly is not the same as meeting it. A component with
  no margin met the limit on the day it was measured, under one
  temperature, on one unit; a design margin is what survives the other
  days.
- Levels relative to the carrier keep the arithmetic to subtraction. An
  unwanted emission reported as stronger than the carrier is a
  measurement or bookkeeping error, not a very bad transmitter.

## Workflow

1. State the carrier centre and the necessary bandwidth. Everything else
   in the assessment is an offset from that pair, so an approximate
   bandwidth moves every domain boundary at once.
2. Declare the out-of-band mask as breakpoints in multiples of the
   necessary bandwidth. Two breakpoints is the minimum that can be
   interpolated; one is a flat limit pretending to be a shape.
3. Declare the spurious limit separately. It applies past the out-of-band
   boundary and is not an extension of the mask. Where a component lands
   in a band whose service is especially vulnerable to interference —
   deep-space and radio-astronomy users among them — the limit protecting
   that band may be tighter than the general one, and the figure to use
   comes from the spurious-emission standard the project works to.
4. Place each measured component in its domain, deciding the boundaries
   with a tolerance so a component sitting exactly on one is placed the
   same way on every platform.
5. Grade only what is unwanted. Report the in-band components so the set
   is complete and mark them ungraded rather than dropping them.
6. Compute margin as limit minus level, and separate a component over its
   limit from one under it with less margin than the design asked for.
7. Report the worst graded component and its domain, not just a count.
   The single number a reviewer acts on is which emission is closest to
   its limit and where it sits.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.12.3a | 6 |

## Pitfalls

- Applying one attenuation figure across the whole spectrum. The
  out-of-band mask tightens with offset and the spurious limit is a
  different rule entirely; a single figure passes emissions that fail and
  fails emissions that pass.
- Grading the carrier. It is inside the necessary bandwidth by definition
  and will be tens of decibels above any unwanted-emission limit.
- Treating everything outside the necessary bandwidth as spurious. The
  out-of-band domain sits between the two and usually carries the looser
  limit, so the mistake turns a compliant design into a redesign.
- Deciding a domain boundary or a limit comparison with a bare strict
  inequality. A component exactly on a boundary can be placed differently
  on different platforms, and the verdict follows the machine.
- Passing a component that clears its limit by nothing. Temperature, unit
  variation and ageing all move it the wrong way after the measurement.
- Reporting compliance as a count of exceedances. Zero exceedances with a
  component sitting on its limit is a different programme risk from zero
  exceedances with ten decibels everywhere.

## Behavior contract (gate 3)

Frequency, bandwidth and level validation, mask normalisation and
interpolation with flat extension beyond the end breakpoints, domain
placement with a tolerance at both boundaries, ungraded treatment of the
wanted in-band emission, per-component margin against the mask and the
spurious limit, the three-way set verdict and the worst-component report
are exercised by the gate 3 contract test:
scripts/test_e50_unwanted_rf_emissions.py against
scripts/e50_unwanted_rf_emissions_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_unwanted_rf_emissions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

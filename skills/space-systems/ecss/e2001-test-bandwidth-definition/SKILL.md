---
name: e2001-test-bandwidth-definition
description: "Use when define which bandwidth one multipactor test covers for a high-power radio-frequency unit under ECSS-E-ST-20-01C clause 6.4.1: scale the verified breakdown threshold across the band with the frequency-gap-product law, derive the lower covered edge where the verified multipactor-margin still meets the qualification-activity or acceptance-activity provision, cap the upper edge at the extrapolation-validity ratio, widen the declared operating-band by its band-edge-allowance, compare the two, and when one frequency falls short, tile the band into the minimum ordered set of test frequencies. Trigger: ecss, e-st-20-electrical-scope, e-st-20-01c, multipactor-test-bandwidth, frequency-gap-product, covered-band-edge, extrapolation-validity-ratio, qualification-activity-bandwidth, acceptance-activity-bandwidth, test-frequency-tiling."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-test-bandwidth-definition, multipactor-test-bandwidth, frequency-gap-product, covered-band-edge, extrapolation-validity-ratio, test-frequency-tiling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Test Bandwidth Definition (space-systems/ecss/e2001-test-bandwidth-definition)

Use when the task is stating, for ECSS-E-ST-20-01C clause 6.4.1, which
bandwidth a multipactor test actually covers -- separately for a
qualification-activity and for an acceptance-activity -- and deciding
whether one test frequency is enough or the band has to be tiled.

## Domain quick reference

- A multipactor test is executed at discrete radio-frequency points, but
  the verification statement is written about a band. Clause 6.4.1 is the
  place where that band is pinned down, so the covered span has to be
  derived rather than asserted.
- The extrapolation away from a tested point rests on the frequency-gap
  product. For a fixed critical gap the onset threshold tracks that
  product, and in the parallel-plate first-order description the threshold
  power grows with it raised to a fixed exponent (2.0 by default, a
  project-configurable parameter, not a standard quantity). A pass at
  power p_test and frequency f_test therefore verifies a higher equivalent
  power above f_test and a lower one below it.
- That asymmetry sets the two edges. The lower covered edge is the
  frequency at which the verified multipactor-margin has decayed to the
  value the activity demands; below it the test says nothing useful. The
  upper edge is not set by margin at all -- margin keeps improving -- but
  by an extrapolation-validity ratio, beyond which one measured field map
  and one resonance picture stop representing the hardware.
- The qualification-activity and the acceptance-activity differ twice
  over: the qualification-activity carries the larger required margin and
  also widens the declared operating-band by a band-edge-allowance for
  build spread and thermal drift, while the acceptance-activity takes the
  band as declared with the smaller margin. The same test point can cover
  the acceptance case and fail the qualification case.
- When one point cannot span the widened band, the band is tiled: each
  successive test frequency is placed so its lower covered edge lands on
  the upper covered edge of the one before it, which yields the minimum
  ordered set rather than an arbitrary sweep.

## Workflow

1. Validate the declared operating-band and reject an inverted or
   non-positive band before any bandwidth statement is made.
2. Resolve the activity (qualification-activity or acceptance-activity)
   into its required margin and its band-edge-allowance; an unrecognized
   activity is an error, not a default.
3. Widen the declared band by the band-edge-allowance to obtain the band
   that actually has to be covered.
4. For the proposed test point, derive the lower covered edge from the
   test power, the maximum operating power, the required margin and the
   threshold exponent; reject a test power at or below the operating
   power, because such a run verifies no margin at all.
5. Set the upper covered edge from the extrapolation-validity ratio, and
   collapse the covered span to zero when the required margin is not met
   anywhere inside that window.
6. Compare covered span against band to cover at both edges, absorbing
   representation error with a relative tolerance so an exactly-compliant
   edge is not failed by a few units in the last place.
7. If either edge is uncovered, tile the band into the minimum ordered set
   of test frequencies and hand that set to the test plan; if the
   per-point coverage ratio is not greater than one, report that no tiling
   exists at this power level instead of looping.

## Pitfalls

- Quoting the instrument sweep width as the test bandwidth. The covered
  band comes from the margin that survives extrapolation, not from what
  the source could be swept over.
- Treating the covered band as symmetric about the test frequency. The
  physics is not symmetric: the lower edge is margin-limited, the upper
  edge is model-validity-limited, and forcing a symmetric window either
  wastes upward coverage or invents coverage that was never verified.
- Reusing one qualification result as the acceptance statement without
  re-deriving the band. The margins and the band-edge-allowance both
  change, so the covered edges move.
- Testing at the band centre by reflex. The centre is the worst place to
  start when the lower edge is the margin-limited one; a point chosen so
  its lower covered edge lands on the low band edge covers strictly more.
- Reading a negative or zero covered span as merely a narrow pass. A
  collapsed span means the required margin was never reached inside the
  validity window, which is a finding about the test power, not a
  bandwidth number.
- Comparing band edges with bare floating-point equality. An edge derived
  from a power ratio raised to a fractional exponent lands a few units in
  the last place off its exact value; absorb that in the comparison,
  never by widening the engineering limit.

## Behavior contract (gate 3)

The band validation, activity provision lookup, threshold extrapolation,
covered-edge derivation, coverage assessment and band-tiling logic are
exercised by the gate 3 contract test:
scripts/test_e2001_test_bandwidth_definition.py against
scripts/e2001_test_bandwidth_definition_logic.py (stdlib unittest,
offline, deterministic). Run:
python3 scripts/test_e2001_test_bandwidth_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

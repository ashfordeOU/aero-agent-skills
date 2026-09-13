---
name: e2006-self-sustained-discharge-prevention
description: "Use when verify that on-board equipment cannot feed a self-sustained-discharge after an electrostatic-discharge is triggered, under ECSS-E-ST-20-06C clause 8.2: categorize each adjacent-conductor pair by gap, barrier material, steady potential-difference and the fault-current its source can deliver; derive the secondary-arc sustaining-voltage and sustaining-current thresholds for that gap; decide whether the pair quenches, flickers as a temporary-sustained-arc, or latches as a permanent-sustained-arc; credit only mitigations physically present such as current-limiting, string-segmentation or a series-blocking-diode; and confirm the closure evidence matches the regime. Trigger: ecss, e-st-20-electrical-scope, e-st-20-06c-clause-8-2, self-sustained-discharge, secondary-arc-sustaining-threshold, permanent-sustained-arc, temporary-sustained-arc, adjacent-conductor-gap, arc-current-limiting, sustained-discharge-demonstration."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-self-sustained-discharge-prevention, self-sustained-discharge, secondary-arc-sustaining-threshold, permanent-sustained-arc, temporary-sustained-arc, arc-current-limiting]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Self-Sustained-Discharge Prevention (space-systems/ecss/e2006-self-sustained-discharge-prevention)

Use when the task is the ECSS-E-ST-20-06C clause 8.2 demonstration that no
on-board equipment can keep a discharge alive out of its own generated or
stored energy once a primary electrostatic-discharge has fired somewhere on
the vehicle.

## Domain quick reference

- Clause 8.2 is about what happens *after* the trigger, not about the
  trigger itself. A primary electrostatic-discharge lasts microseconds and
  is a survivable transient; the hazard the clause closes is the secondary
  arc that the equipment's own source then feeds across the same ionized
  gap, indefinitely, until the string or the harness is destroyed.
- The unit of assessment is the adjacent-conductor pair: two conductors
  facing each other across a gap, holding a steady potential-difference,
  backed by a source able to deliver some fault-current into a short. A
  pair is categorized by its barrier — a bare gap, a conformal coat, a
  polyimide tape, a silicone encapsulant, a ceramic standoff — because the
  barrier sets how hard the gap is to keep ionized.
- Two independent sustaining thresholds govern the outcome and both scale
  with the gap. The sustaining-voltage threshold is the potential-difference
  below which the column cannot re-ionize; the sustaining-current threshold
  is the current below which the electrode spots cool and the column
  collapses. The voltage condition is necessary: a pair below the
  sustaining-voltage threshold quenches no matter how much fault-current
  stands behind it.
- Three regimes follow. Below the sustaining-voltage threshold the pair is
  quenched. Above it but below the sustaining-current threshold the pair
  shows a temporary-sustained-arc, which self-extinguishes but still
  deposits energy in the gap. Above both, the pair latches a
  permanent-sustained-arc and clause 8.2 is not met by any amount of
  paperwork — the design has to change.
- Mitigations act on one variable each: current-limiting caps the deliverable
  fault-current, string-segmentation divides the potential-difference across
  the gap, a series-blocking-diode removes a share of the bypass path. Only
  a mitigation physically present in the flight build may be credited.

## Workflow

1. Inventory every adjacent-conductor pair on the equipment — interconnect
   to interconnect, harness to harness, connector pin to pin — with its
   gap, barrier, steady potential-difference and the fault-current its
   source can deliver. Reject an uncategorized barrier before it enters
   the assessment.
2. Apply the mitigations that exist in the flight build, in the order they
   act, to obtain the effective potential-difference and effective
   fault-current at the gap. Reject a mitigation whose parameter is absent
   or non-physical (a single-segment segmentation, a zero limiter rating,
   a full bypass fraction).
3. Derive both sustaining thresholds from the gap and barrier, then
   determine the regime: quenched, temporary-sustained-arc, or
   permanent-sustained-arc. Record both margins, not just the verdict.
4. For a temporary-sustained-arc, compute the energy deposited per event
   from the effective drive and the transient duration, and compare it
   against the benign-transient energy limit. A self-extinguishing arc that
   dumps enough energy to erode an interconnect is still a finding.
5. Check the closure evidence against the regime. A quenched pair may be
   closed by analysis; a temporary-sustained-arc pair needs empirical
   evidence — an arc test or similarity to an already-qualified design.
   Evidence with no report reference is a finding.
6. Roll the per-pair outcomes up per equipment and then per vehicle. The
   clause is met only when no equipment latches and no finding is open.

## Pitfalls

- Reading a large fault-current as sufficient on its own. Without the
  sustaining-voltage threshold being exceeded, the column cannot re-ionize
  and the pair quenches; sizing the whole demonstration around current
  alone flags safe pairs and misses the real ones.
- Crediting a mitigation that lives only in the design note. Current-limiting
  that is not in the flight build, or segmentation that was deleted during
  the harness re-route, turns a compliant record into an unprotected pair
  on orbit.
- Treating a temporary-sustained-arc as a pass because it self-extinguishes.
  It self-extinguishes *each time*, and each time it deposits energy into
  the same gap; the energy per event has to be checked against a limit.
- Letting a floating-point boundary decide a physically compliant pair.
  A potential-difference divided by a segment count can land a few units in
  the last place above a threshold it mathematically equals; the comparison
  absorbs that representation error rather than the engineering limit being
  widened.
- Closing an escalating pair with analysis alone. Secondary-arc onset is
  strongly geometry- and contamination-dependent, which is exactly what a
  model smooths away.

## Behavior contract (gate 3)

The pair categorization, mitigation crediting, sustaining-threshold,
regime-decision, transient-energy and evidence logic is exercised by the
gate 3 contract test:
scripts/test_e2006_self_sustained_discharge_prevention.py against
scripts/e2006_self_sustained_discharge_prevention_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2006_self_sustained_discharge_prevention.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

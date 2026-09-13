---
name: e2008-esd-test-pass-fail-criteria
description: "Decide whether a photovoltaic coupon meets the no-sustained-arcing condition of ECSS-E-ST-20-08C clause 5.5.1.5.2 under the discharge conditions that were applied to it. Use when a coupon discharge run has finished and its event record has to be turned into a verdict: validate every recorded event, categorize each one as transient or sustained from how it terminated, how long it burned against the supply recovery window and whether it drew the current the coupon can feed, check that each event sits at a bias the campaign says was applied, check every required bias condition was applied with at least its minimum discharge population, then fail the coupon on any sustained arc and report the coverage findings beside the verdict. Trigger: ecss, e-st-20-08c, coupon-esd-pass-criteria, sustained-arc-absence, self-extinguishing-discharge, supply-recovery-window, coupon-sustaining-current, discharge-population-coverage, applied-bias-condition-coverage, solar-array-coupon-discharge-record."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-esd-test-pass-fail-criteria, e-st-20-08c, coupon-esd-pass-criteria, sustained-arc-absence, self-extinguishing-discharge, supply-recovery-window, coupon-sustaining-current, applied-bias-condition-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Coupon ESD Pass Criteria (space-systems/ecss/e2008-esd-test-pass-fail-criteria)

Use when the task is the clause 5.5.1.5.2 acceptance decision of
ECSS-E-ST-20-08C: a photovoltaic coupon has been taken through the
discharge conditions of its test, and it is admissible only if none of
the discharges that occurred turned into a sustained arc.

## Domain quick reference

- The criterion is not the absence of discharges. The conditions applied
  to the coupon are meant to produce them; what the coupon has to show is
  that each one died on its own, quickly, without the coupon's own power
  taking it over. A run with no events at all is therefore not evidence
  of a pass, it is evidence that the conditions were never reached.
- Every event is categorized before any verdict is formed, from three
  facts: how it terminated, how long it burned, and how much current it
  carried. An event still burning when the run was stopped, or ended only
  by interrupting the supply, is sustained — the coupon never demonstrated
  extinction. A self-extinguished event is transient when it died inside
  the supply recovery window, or when it never drew the current the
  coupon is able to feed; anything else is sustained.
- The recovery window and the sustaining current are properties of the
  test set-up, not of the event. A bench supply with a long recovery
  window will make short arcs look sustained, and a current limit below
  what the flight string can feed will make sustained arcs look
  transient; both belong in the record beside the events.
- The verdict is only about the conditions actually applied. An event
  logged at a bias that appears in no applied condition cannot be read
  against this criterion — either the condition list or the event record
  is wrong, and that has to be resolved rather than averaged over.
- A clean arc record from an incomplete set of conditions proves nothing.
  Every required bias condition has to have been applied, and with at
  least the minimum discharge population, before the absence of sustained
  arcing means anything about the coupon.

## Workflow

1. Validate each recorded event: identifier, duration, peak arc current,
   the bias the coupon sat at and a recognized termination mode. Reject a
   duplicate identifier, a negative duration or current and an
   unrecognized termination rather than guessing at them.
2. Categorize each event as transient or sustained against the supply
   recovery window and the coupon sustaining current, admitting an exact
   equality at either bound through a named tolerance.
3. Raise a finding for every sustained event, carrying the reason it was
   categorized that way so the record is reviewable.
4. Check each event's bias against the applied conditions, and raise a
   finding for any event recorded outside them.
5. Check each required condition against what was applied: never applied
   is one finding, applied with too thin a discharge population is
   another. Sum split runs at the same bias before comparing.
6. The coupon passes only when the finding list is empty; report the
   sustained and transient counts with the verdict so a near miss stays
   visible.

## Pitfalls

- Reading "no arcs were recorded" as a pass. The conditions exist to
  provoke discharges; an empty record points at a set-up that never
  reached the inception conditions, which the coverage check catches.
- Counting a self-extinguished arc as automatically acceptable. Extinction
  matters only relative to the recovery window and the current the coupon
  can feed — a long arc carrying coupon-sustainable current is sustained
  whatever ended it.
- Judging an externally interrupted event on its duration. Cutting the
  supply removes the evidence: the coupon never showed it could
  extinguish, so the event is sustained regardless of how brief the
  interruption made it look.
- Averaging over an event logged at an unlisted bias. It means the
  condition list and the event record disagree, and the disagreement is a
  finding in its own right, not a rounding matter.
- Widening the recovery window or lowering the sustaining current to move
  a borderline event into the transient family. An equality at either
  bound is a representation question, handled by the tolerance inside the
  comparison; the set-up values stay as measured.

## Behavior contract (gate 3)

The event validation, the transient-versus-sustained categorization
against the recovery window and the sustaining current, the applied-bias
cross-check, the required-condition coverage and the aggregated verdict
are exercised by the gate 3 contract test:
scripts/test_e2008_esd_test_pass_fail_criteria.py against
scripts/e2008_esd_test_pass_fail_criteria_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_esd_test_pass_fail_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

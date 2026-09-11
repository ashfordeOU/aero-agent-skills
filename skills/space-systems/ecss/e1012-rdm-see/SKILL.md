---
name: e1012-rdm-see
description: "Use when determine the radiation design margin for single-event effects (SEE) on spacecraft EEE parts under ECSS-E-ST-10-12C §5.1.3: categorize each SEE-sensitive device as subject to destructive effects (latchup, burnout, gate rupture) or non-destructive effects (upset, functional interrupt, transient), compute the LET-threshold margin for destructive parts and the upset rate margin for non-destructive parts, verify each margin meets the required RDM factor, and flag any part with insufficient margin before design acceptance. Trigger: ecss, e-st-10-system-scope, e-st-10-12c, radiation-design-margin, single-event-effects, see, let-threshold, upset-rate, see-hardness-assurance."
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
  tags: [ecss, e-st-10-system-scope, e-st-10-12c, radiation-design-margin, single-event-effects, see, let-threshold, upset-rate, see-hardness-assurance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — RDM Single-Event Effects (space-systems/ecss/e1012-rdm-see)

Use when the task is to apply the radiation design margin (RDM) approach
for single-event effects (SEE) on spacecraft EEE components under
ECSS-E-ST-10-12C §5.1.3: each SEE-sensitive part is first categorized
by effect type (destructive or non-destructive), then its margin is
computed and checked against the required RDM factor.

## Domain quick reference

- §5.1.3 divides single-event effects into two assessment tracks based
  on whether the effect is destructive or non-destructive. Destructive
  effects — single-event latchup (SEL), single-event burnout (SEB),
  and single-event gate rupture (SEGR) — can permanently damage the
  device and require a LET-threshold margin check. Non-destructive
  effects — single-event upset (SEU), single-event functional interrupt
  (SEFI), and single-event transient (SET) — are recoverable and
  require a rate-based margin check. Each part is assigned to exactly
  one track before its margin is evaluated.
- For destructive effects the RDM is the ratio of the device's measured
  LET threshold (the minimum linear energy transfer, in MeV·cm²/mg,
  that triggers the effect) to the worst-case environment LET at the
  device location after shielding. The LET threshold must come from
  heavy-ion test data for the actual part type; a generic datasheet
  figure is not an acceptable substitute. The minimum required RDM is
  2.0 unless a higher value has been imposed by the project.
- For non-destructive effects the RDM check is applied to the predicted
  upset rate: the predicted rate (events per device per day) multiplied
  by the required RDM factor must not exceed the allowable rate set by
  the system-level upset budget. Equivalently, the ratio of the
  allowable rate to the predicted rate must be at least the required
  RDM factor. The predicted rate is derived from the environment LET
  spectrum and the device's measured cross-section versus LET curve.
- A part with no heavy-ion test data must be treated as worst-case
  (LET threshold = 0 for destructive track; infinitely high predicted
  rate for non-destructive track) — the absence of data is itself a
  non-compliant finding that must be resolved before design acceptance.
- The minimum required RDM factor is 2.0 for both tracks in the
  standard case. Project- or mission-specific requirements may impose
  a higher value.

## Workflow

1. Inventory every SEE-sensitive EEE component and assign each one an
   effect type (SEL, SEB, SEGR, SEU, SEFI, or SET). Reject any part
   with an unrecognized or missing effect type before it enters the
   assessment — an unknown type cannot be routed to the correct track.
2. Categorize each part as destructive (SEL, SEB, SEGR) or
   non-destructive (SEU, SEFI, SET). Parts on the destructive track
   proceed to step 3; parts on the non-destructive track proceed to
   step 4.
3. For each destructive-track part: retrieve the measured LET threshold
   from heavy-ion test data, retrieve the worst-case environment LET at
   the device location (from the shielding analysis), and compute the
   LET margin = LET_threshold / LET_environment. Flag the part if either
   value is missing or non-positive — no margin can be asserted without
   both values.
4. For each non-destructive-track part: retrieve the predicted upset
   rate (events/device/day) from the rate calculation and the allowable
   rate from the system upset budget. Compute the rate margin =
   allowable_rate / (predicted_rate × rdm_factor). A predicted rate of
   zero always passes; a missing or zero allowable rate is a finding.
5. Compare each computed margin against the required RDM factor: a
   destructive-track part passes when LET_margin >= rdm_factor; a
   non-destructive-track part passes when rate_margin >= 1.0 (which is
   equivalent to predicted_rate × rdm_factor <= allowable_rate). Parts
   that fall short are flagged as non-compliant.
6. Aggregate the findings across all parts. The design is SEE-RDM
   compliant only when the findings list is empty. Non-compliant parts
   must be dispositioned (shielding increase, part substitution, or
   system-level upset-budget relaxation with substantiation) before
   design acceptance.

## Pitfalls

- Routing a part to the wrong track — for example, treating SEL (which
  can latch the supply rails and destroy the device if current is not
  cut promptly) as a non-destructive rate effect omits the LET-threshold
  check that guards against catastrophic single-pass failure.
- Using a LET threshold from a different die revision or process node
  than the flight lot — LET sensitivity is a function of the physical
  construction; a threshold measured on a predecessor device is not a
  valid substitute for the actual flight-lot type.
- Accepting a predicted rate of "essentially zero" as an automatic pass
  without reviewing the cross-section data — a very low predicted rate
  can result from an underestimated LET spectrum or a saturation
  cross-section that was not measured at the high-LET tail.
- Applying the RDM factor as a divisor on the allowable rate rather than
  as a multiplier on the predicted rate — both formulations are
  equivalent, but mixing them in a spreadsheet produces a factor-of-RDM²
  error in the effective margin.
- Treating the absence of heavy-ion test data as a "data gap to address
  later" — under §5.1.3 the lack of test data is itself a non-compliant
  finding; the part cannot be accepted into the design without either
  supplying the data or substituting a qualified part.

## Behavior contract (gate 3)

The effect-type categorization, LET-margin computation, rate-margin
computation, per-part compliance check, and multi-part aggregation logic
are exercised by the gate 3 contract test:
scripts/test_e1012_rdm_see.py against
scripts/e1012_rdm_see_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_rdm_see.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e2020-rlcl-spurious-switch-off-recovery
description: "Evaluate whether a retriggerable limiter puts itself back into the conducting state after an unintended switch-off, under ECSS-E-ST-20-20C clause 5.2.18.1.1. Use when a power chain has to show that recovery is automatic and bounded: refuse a return to conduction that waits on a command, count the retrigger cycles a disturbance of a given length forces, build the recovery latency from detection, open interval and turn-on ramp, and weigh it against the hold-up the load actually has. Reach for it when a retrigger budget has to survive a disturbance longer than one open interval, or when a recovery time is quoted with nothing to compare it against. Trigger: ecss, e-st-20-20c-clause-5-2-18-1-1, rlcl-spurious-trip-autonomous-recovery, retrigger-cycle-recovery-latency, load-hold-up-versus-retrigger-latency, rlcl-retrigger-attempt-budget, spurious-switch-off-recovery-margin."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-18-1-1, e2020-rlcl-spurious-switch-off-recovery, rlcl-spurious-trip-autonomous-recovery, retrigger-cycle-recovery-latency, load-hold-up-versus-retrigger-latency, rlcl-retrigger-attempt-budget, spurious-switch-off-recovery-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Limiters -- RLCL Spurious Switch-Off Recovery (space-systems/ecss/e2020-rlcl-spurious-switch-off-recovery)

Use when the task is the clause 5.2.18.1.1 question of ECSS-E-ST-20-20C:
a retriggerable limiter that trips on a disturbance rather than on a real
load fault has to return to the conducting state on its own, and the
question is whether it does so before the load has already been lost.

## Domain quick reference

- Recovery has to belong to the limiter. A return to conduction that
  waits on a ground telecommand, an onboard reconfiguration or an
  operator procedure is a latching limiter with a recovery procedure
  attached. The load is then off for the length of the procedure, which
  is a different number by orders of magnitude.
- Retrigger switched off and retrigger that needs help are two separate
  ways to fail the same clause. Both are worth naming separately,
  because one is a configuration nobody revisited and the other is an
  architecture decision.
- The latency is built, not quoted. It is the recognition time, the
  interval the limiter stays open, the number of cycles the disturbance
  forces, and the ramp the output needs on the way back up. A vendor
  number that covers only the last of those understates what the load
  sees.
- A disturbance outlasting one open interval forces another cycle. That
  is the arithmetic that turns "it retriggers" into a count, and the
  count is what a finite retrigger budget is measured against.
- Recovery is only fast enough relative to something. The load's hold-up
  is that something: power returning after the hold-up has run out finds
  a unit that has already dropped and possibly already reset, and the
  restoration is then a separate event rather than a ride-through.
- A quotient of a duration by an interval it exactly divides is not
  exact in binary. Letting that error round a whole retrigger cycle up
  changes a verdict on one platform and not on another, so the cycle
  count absorbs it deliberately.
- An unlimited retrigger budget is a claim like any other. It is
  recorded rather than trusted, because the qualification evidence is
  where a bound usually turns out to exist.

## Workflow

1. Validate the recovery policy first: whether autonomous recovery is
   required, the hold-up margin the project demands, the margin at which
   a passing case still earns an advisory, and the spare-attempt count
   worth flagging. A minimum margin below one, or an advisory threshold
   underneath the minimum, is refused rather than used.
2. Validate the limiter record: identifier, whether retrigger is
   enabled, whether it acts without help, the recognition time, the open
   interval, the turn-on ramp and the attempt budget. A zero attempt
   budget is a latching limiter and is refused here.
3. Validate the load record and read its hold-up, and index every
   disturbance the chain is expected to ride through. Duplicate
   disturbance names are refused so the worst case stays reproducible.
4. For each disturbance, count the retrigger cycles it forces -- the
   duration measured in whole recognise-and-wait cycles, never fewer
   than the one the trip itself costs -- and build the latency from
   those cycles plus the ramp.
5. Take the disturbance with the longest recovery, breaking a tie on the
   name, and carry its cycle count, latency and spare attempts forward.
6. Close on one verdict: recovery not autonomous, retrigger budget
   exhausted, recovery slower than the load hold-up, or spurious trip
   recovery demonstrated -- with the latency, the margin and the
   governing disturbance beside it.

## Pitfalls

- Quoting the turn-on ramp as the recovery time. The load is open from
  the moment of the trip, not from the moment the limiter decides to try
  again, and the cycles in between are most of the number.
- Assuming one retrigger cycle. A disturbance longer than the open
  interval trips the limiter again, and a budget of three attempts
  against a disturbance needing five is a load that stays off.
- Comparing the latency against nothing. A recovery in eighty
  milliseconds is fast or slow only next to the hold-up of the unit
  behind the limiter.
- Treating a commanded recovery as compliance because power does come
  back. It comes back after somebody acts, which is exactly the
  behaviour this clause exists to distinguish from retriggering.
- Letting a floating-point remainder add a retrigger cycle. A
  disturbance that is an exact multiple of the cycle period must count
  the same on every machine, or the verdict travels badly.
- Reading a zero turn-on ramp as a fast design. It is usually a field
  nobody filled in, and it flatters every latency downstream of it.

## Behavior contract (gate 3)

The policy validation, limiter and load record validation, disturbance
indexing, the retrigger cycle count and its floating-point tolerance,
the latency build, the hold-up margin, the spare-attempt count, the
worst-disturbance selection and the advisories are exercised by the gate
3 contract test:
scripts/test_e2020_rlcl_spurious_switch_off_recovery.py against
scripts/e2020_rlcl_spurious_switch_off_recovery_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_rlcl_spurious_switch_off_recovery.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

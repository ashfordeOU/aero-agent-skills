---
name: e2020-spurious-state-change-immunity
description: "Assess whether a device holds its commanded state through electromagnetic disturbance, radiation events and similar perturbations, per clause 5.2.16.1.1 of ECSS-E-ST-20-20C. Use when an immunity claim has to cover every perturbation that can flip a latch and not only the one that was tested: turn each declared environment and demonstrated immunity into a level margin, separate a provision that prevents a flip from one that merely restores state afterwards, hold a restoring provision against the outage anyone tolerates, and rank an unassessed perturbation above one assessed and found short. Trigger: ecss, e-st-20-20c-clause-5-2-16-1-1, spurious-state-change-immunity, state-holding-perturbation-margin, state-restore-outage-window, single-event-upset-state-flip."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-16-1-1, e2020-spurious-state-change-immunity, state-holding-perturbation-margin, state-restore-outage-window, single-event-upset-state-flip, switch-state-immunity-provision]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution -- Spurious State Change Immunity (space-systems/ecss/e2020-spurious-state-change-immunity)

Use when the task is clause 5.2.16.1.1 of ECSS-E-ST-20-20C: the state a
device holds resists being changed by an electromagnetic disturbance, a
radiation event, or a perturbation of the same character. Immunity is
never one number, so this leaf grades the claim one perturbation class
at a time rather than one device at a time.

## Domain quick reference

- The classes do not behave alike and are not answered by the same
  feature. A conducted transient arrives on the wire, a radiated field
  arrives through the box, a discharge arrives once and hard, a heavy
  ion flips a bit inside the latch, and a bus transient arrives through
  the supply. A filter answers two of those and is silent on the rest.
- The margin is the demonstrated immunity level over the declared
  environment level. Below one, the state moves. At exactly one it moves
  on the next unit that is slightly worse, which is why a floor sits
  above unity rather than on it.
- A level with no design feature behind it is an assertion, not an
  immunity. So a class with a comfortable number and no covering
  provision is still reported: the reviewer is matching each class to
  the thing that implements the answer.
- A periodic refresh does not stop a flip, it ends one. It bounds the
  outage instead, and it earns credit only where its period fits inside
  the outage the user tolerates and inside the policy ceiling. The class
  is still reported as having flipped.
- A class nobody assessed is not a class that passed. It outranks a
  class assessed and found short, because one needs an analysis and the
  other needs a design change.
- The device is reported at the worst class it contains. A device immune
  on four classes and flipping on the fifth is a device that flips.

## Workflow

1. Validate the policy: the margin floor must not sit below one and the
   refresh ceiling must be positive, or the policy accepts a state that
   moves.
2. Name every declared perturbation class and refuse an unrecognised one
   before it enters the argument.
3. For each class, convert the declared environment and demonstrated
   immunity into a margin ratio, and carry the decibel form alongside it
   for reporting.
4. Resolve which declared provisions actually cover the class, then
   split them into the ones that prevent a flip and the ones that only
   restore the state afterwards.
5. Where a restoring provision is present, check its refresh period fits
   inside both the tolerable outage and the policy ceiling.
6. Rank each class: flip credible, flip self-corrected, no provision
   declared, margin insufficient, held with margin.
7. Report the device at its worst class, with the unassessed classes
   named apart from the assessed ones.

## Pitfalls

- Testing one perturbation class, passing it, and writing the immunity
  claim as though the state were now proof against everything.
- Reading a comfortable margin as an answer when nothing in the design
  implements it. The number came from somewhere and the reviewer's job
  is to find out where.
- Crediting a periodic refresh as immunity. It is a recovery, and a
  recovery slower than the outage anybody tolerates is not even that.
- Comparing a refresh period against the policy ceiling and forgetting
  the user's own tolerable outage, or the reverse. Both bound it.
- Treating a margin of exactly one as a pass. It is the value at which
  the next unit off the line fails, which is why the floor sits above.
- Averaging the classes into a single immunity figure. The device is
  reported at its worst class, and an average hides precisely the class
  that will flip it.
- Reporting an unassessed class inside the same list as the classes that
  passed. One needs an analysis and the other needs nothing.

## Behavior contract (gate 3)

The perturbation class and immunity provision vocabularies, the per-class
coverage map that keeps a filter away from a radiated field, the margin
ratio and its decibel form, the split between preventing and restoring
provisions, the refresh window held against both the tolerable outage and
the policy ceiling, the class outcome ladder, the unassessed classes kept
apart from the assessed ones, the waivable assessment requirement and the
worst-class device verdict are exercised by the gate 3 contract test:
scripts/test_e2020_spurious_state_change_immunity.py against
scripts/e2020_spurious_state_change_immunity_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_spurious_state_change_immunity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

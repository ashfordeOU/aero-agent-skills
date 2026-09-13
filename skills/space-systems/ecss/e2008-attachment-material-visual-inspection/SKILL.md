---
name: e2008-attachment-material-visual-inspection
description: "Assess bonded attachments on a photovoltaic assembly for full cure and for any adhesive tackiness left, under ECSS-E-ST-20-08C clause 5.5.3.2.16: reduce each recorded thermal profile to equivalent minutes at the adhesive's reference temperature, crediting nothing to time below the temperature at which it advances, take the ratio against the reference dwell, let a tack observation override a profile that says cured, flag a peak past the damage ceiling, grade fillet coverage and voids, and roll the assembly up with the attachments carrying no tack test named. Use when bonded attachments have been examined and each needs a disposition. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-16, bonded-attachment-cure-inspection, adhesive-remaining-tackiness-check, equivalent-cure-minutes-accumulation, adhesive-cure-ratio-against-dwell, attachment-fillet-coverage-screen."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-attachment-material-visual-inspection, bonded-attachment-cure-inspection, adhesive-remaining-tackiness-check, equivalent-cure-minutes-accumulation, adhesive-cure-ratio-against-dwell, attachment-fillet-coverage-screen]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Attachment Material Visual Inspection (space-systems/ecss/e2008-attachment-material-visual-inspection)

Use when the task is the attachment-material inspection of
ECSS-E-ST-20-08C clause 5.5.3.2.16 -- a bonded attachment on a solar
array examined for whether its adhesive has finished curing and whether
any tackiness is left on it.

## Domain quick reference

- Two independent things answer the question, and they can disagree. The
  recorded thermal profile is a prediction of how far the reaction has
  gone; the tack test is an observation of the part in the inspector's
  hand. Where they disagree the observation governs, because the profile
  is what the oven was asked for and the surface is what the adhesive
  did.
- Remaining tackiness is not a cosmetic finding. Unreacted adhesive
  outgasses onto the coverglass and the optics around it, picks up
  every particle it meets and has not developed the strength the joint
  was sized for, so it takes the attachment out on its own.
- Cure time is not wall-clock time. A segment of the profile advances
  the adhesive at a rate set by its own temperature, so the profile is
  reduced to equivalent minutes at the reference temperature before it
  is compared with anything.
- Below the temperature at which the adhesive advances, nothing
  accumulates. A part that sat on the bench over a weekend has spent
  time, not cure, and crediting that time at some small rate is the
  most flattering arithmetic error available here.
- A tack-free surface over a short profile is not a pass. The surface
  skins before the bond line finishes, so the tack test can read clean
  over an interior that has not reacted.
- Heat also has a ceiling. A profile that overshot the adhesive's
  damage temperature has degraded the bond while accumulating cure
  quickly, so a high cure ratio and an over-temperature peak arrive
  together and only one of them is good news.
- The geometry still has to be there. A fully cured adhesive holding
  half a fillet is a cured joint of the wrong size, so coverage and
  voids are graded beside the cure.
- An attachment with no tack test is not a pass by omission. The clause
  turns on remaining tackiness, so the assembly stays open until every
  attachment has been touched.

## Workflow

1. Validate the cure allowance set and the adhesive cure schedule:
   reference temperature and dwell, the activation temperature the rate
   weighting uses, the temperature below which nothing advances and the
   temperature above which the adhesive is damaged.
2. Check each attachment names the adhesive the schedule is for; an
   accumulation taken against another adhesive's kinetics is refused.
3. Reduce the recorded profile to equivalent minutes at the reference
   temperature, segment by segment, crediting nothing below the cure
   floor, and keep the elapsed time, the time below the floor and the
   peak temperature alongside it.
4. Take the cure ratio against the reference dwell and place it against
   the cured ratio and the review floor.
5. Read the tack result. Tackiness rejects whatever the ratio says, and
   names the disagreement when the profile claimed cured; marginal tack
   returns the part to cure; an untested attachment is left ungraded and
   reported.
6. Grade the peak against the damage ceiling, the fillet coverage
   against its floor and the void fraction against its allowance.
7. Roll the assembly up: how many attachments carry a finding, how many
   are tacky, how much of the assembly allowance is left, which have no
   tack test and which have no record at all.
8. Report the worst disposition, the attachments not accepted, the
   remaining allowance and the completeness flag.

## Pitfalls

- Passing an attachment because the oven log shows the right soak. The
  log is what the profile asked for; the tack test is what the adhesive
  did with it.
- Adding wall-clock minutes across a profile that moved. Sixty minutes
  well above the reference and sixty well below it are not two hours of
  cure in either direction.
- Crediting bench time at a small rate instead of at none. It quietly
  cures every part that was simply left alone.
- Reading a tack-free surface as a cured bond line. The skin forms
  first, so the tack test confirms cure only when the profile agrees
  with it.
- Treating a high cure ratio as unambiguously good. An overshoot past
  the damage ceiling produces exactly that, while degrading the joint.
- Grading cure and ignoring the fillet. A cured adhesive in the wrong
  place is a cured joint that was never the joint on the drawing.
- Closing an assembly in which some attachments were never touched.
  Omission reads as a pass on the only question the clause asks.
- Comparing a cure ratio with its floor, or a counted number of
  attachments with a derived allowance, by bare arithmetic. The ratio
  is a sum of exponentially weighted segment times over a dwell and the
  exponential is not correctly rounded, so a value that should land
  exactly on its limit lands differently on different machines; the
  comparison absorbs that representation error while the limit stays
  untouched.

## Behavior contract (gate 3)

The allowance and schedule validation, the per-temperature rate
weighting and its cure floor, the equivalent-minutes accumulation with
its elapsed, below-floor and peak figures, the cure ratio against the
cured and review levels, the tack override and the untested case, the
damage ceiling, fillet coverage and void grading, and the assembly
allowance with its remaining budget and completeness rollup are
exercised by the gate 3 contract test:
scripts/test_e2008_attachment_material_visual_inspection.py against
scripts/e2008_attachment_material_visual_inspection_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_attachment_material_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

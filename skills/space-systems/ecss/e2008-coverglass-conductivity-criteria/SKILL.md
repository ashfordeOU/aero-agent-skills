---
name: e2008-coverglass-conductivity-criteria
description: "Use when a measured coverglass conductivity figure has to become an acceptance verdict. Assess whether the average surface conductivity of the measured conductive coverglasses reaches the value fixed in the cell assembly control drawing per ECSS-E-ST-20-08C clause 6.4.3.13.3: refuse a requirement carrying no drawing reference, average the sites within each coverglass and the coverglasses with equal weight, compare against the drawing minimum with a tie admissible, report the margin, the worst site and the site spread, and raise a dead-patch advisory an average would otherwise hide. Trigger: ecss, e-st-20-08c-clause-6-4-3-13-3, coverglass-conductivity-acceptance, cell-assembly-control-drawing-value, average-surface-conductivity-criterion, coverglass-conductivity-margin, coverglass-dead-patch-advisory."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-conductivity-criteria, coverglass-conductivity-acceptance, cell-assembly-control-drawing-value, average-surface-conductivity-criterion, coverglass-conductivity-margin, coverglass-dead-patch-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Conductivity Criteria (space-systems/ecss/e2008-coverglass-conductivity-criteria)

Use when the task is the clause 6.4.3.13.3 acceptance decision of
ECSS-E-ST-20-08C: conductive coverglasses have been measured, and the
average surface conductivity that came out of that measurement is
admissible only if it reaches the value the cell assembly control
drawing fixes.

## Domain quick reference

- The value comes from the drawing, not from the coating vendor's
  datasheet, not from house practice and not from the last programme. A
  verdict quoted with no drawing reference behind it is not a verdict
  against this clause, so an unreferenced requirement closes the
  assessment instead of passing it.
- The sense of the comparison is a floor. Surface conductivity is the
  reciprocal of the sheet resistance the charge has to run through, so
  more is better and the drawing value is a minimum. An average landing
  exactly on it is admissible, and the comparison tolerance exists to
  absorb representation error rather than to widen the requirement.
- An average needs a declared weighting or it is not reproducible.
  Sites are averaged within a coverglass and the coverglasses are then
  averaged with equal weight, so one article that happened to receive
  forty probe sites cannot carry the figure while the rest contribute a
  correction. A straight mean over every site in the campaign is a
  different number and it is the wrong one.
- The margin is worth as much as the verdict. A pass at one per cent
  over the drawing value and a pass at eighty per cent over it are the
  same verdict and very different hardware, and the next reviewer
  cannot recover the difference from the word "pass".
- This criterion does not judge uniformity, and pretending it does is
  its own defect. An average can clear the drawing value while one site
  on one article is effectively dead. That is a real finding about the
  coating; it belongs beside the verdict as an advisory and goes to the
  survey clause, not folded silently into this pass or fail.

## Workflow

1. Validate the acceptance policy first: the site floor fraction that
   marks a dead patch and the weighting the average is taken under. A
   floor fraction above one, or an unrecognised weighting, is refused
   rather than used.
2. Read the drawing requirement. An absent requirement, or one whose
   drawing reference is blank, closes immediately on requirement not
   established -- there is nothing for the average to be judged
   against.
3. Validate every article record: a non-blank identifier, no duplicate
   identifier, at least one site and every site conductivity a finite
   positive number. An empty article cannot contribute to an average
   and is refused rather than skipped.
4. Average the sites within each coverglass, then average the
   coverglasses under the declared weighting. Keep the per-article
   means in the record so the subgroup figure can be taken apart again.
5. Compare the average against the drawing minimum, admitting a tie,
   and compute the fractional margin either way. Report the worst site,
   the best site and their ratio alongside, because they are what the
   average concealed.
6. Raise a dead-patch advisory for every site below the policy fraction
   of the drawing value, naming the article and the site. Advisories
   are reported with the verdict and do not move it.
7. Close on one verdict: drawing requirement not established, average
   below the drawing value, or average meets the drawing value.

## Pitfalls

- Comparing against a remembered number. The drawing is the only source
  of the required value, and a criterion applied from memory is a
  criterion nobody can audit.
- Averaging every site in the campaign. That silently weights the
  subgroup by probe effort, and it moves the answer in whichever
  direction the most-sampled article happened to lie.
- Reporting a pass with no margin. The verdict alone hides the
  difference between hardware that comfortably clears the drawing and
  hardware that grazed it, and the next build has nothing to compare to.
- Failing a coverglass set on one dead site, or hiding that site behind
  the average. Neither is this clause: the criterion is the average, the
  dead site is an advisory, and both belong in the record.
- Inverting the sense because the drawing quotes a sheet resistance.
  A resistance ceiling and a conductivity floor are the same
  requirement, but only after the reciprocal has actually been taken.

## Behavior contract (gate 3)

The policy validation, drawing requirement validation, per-article and
per-site averaging, the floor comparison with an admissible tie, the
margin, the worst and best site and their spread, the dead-patch
advisories and the acceptance verdict are exercised by the gate 3
contract test:
scripts/test_e2008_coverglass_conductivity_criteria.py against
scripts/e2008_coverglass_conductivity_criteria_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_conductivity_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

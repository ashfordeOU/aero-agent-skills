---
name: e2008-blocking-diode-visual-inspection
description: "Use when planar blocking diodes have been examined and each needs a disposition. Assess every planar blocking diode examined for workmanship and surface defects under ECSS-E-ST-20-08C clause 12.6.1: refer each observed extent to the smallest die dimension, judge it against the limit its own defect type and location carry, treat a defect nobody declared a limit for as a referral rather than a pass, let a defect seen below the required magnification stand while a clean look below it accepts nothing, sentence each diode accept, refer-for-review, examination-invalid or reject, and hold the lot open until every declared diode carries a final one. Trigger: ecss, e-st-20-08c, planar-blocking-diode-surface-defect-screening, planar-blocking-diode-workmanship-examination, planar-blocking-diode-defect-extent-ratio, planar-blocking-diode-examination-magnification, planar-blocking-diode-inspection-record-completeness."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-visual-inspection, planar-blocking-diode-surface-defect-screening, planar-blocking-diode-workmanship-examination, planar-blocking-diode-defect-extent-ratio, planar-blocking-diode-examination-magnification, planar-blocking-diode-inspection-record-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Blocking Diode Visual Inspection (space-systems/ecss/e2008-blocking-diode-visual-inspection)

Use when the task is clause 12.6.1 of ECSS-E-ST-20-08C: planar blocking
diodes have been looked at for workmanship and surface defects, and each one
now needs a disposition that somebody can defend. This leaf grades the
examination on how each defect was sized, on the limit it was judged
against, on the magnification it was found at, and on whether every declared
diode carries a record at all.

## Domain quick reference

- A defect is judged against the part, not in millimetres. A 0.2 mm scratch
  across a 1 mm die and the same scratch on a 4 mm die are different defects,
  so every observed extent is referred to the smallest die dimension before it
  meets a limit.
- The limit belongs to the defect type and to where the defect sits. A
  scratch in the active area and the same scratch on the periphery are not the
  same finding, and a limit table indexed only by type quietly accepts the
  worse of the two.
- A defect type and location with no declared limit cannot be sentenced. That
  is a referral, not an acceptance -- nothing has been shown about it, and
  reading silence as a pass is how an undeclared defect class leaves the shop.
- Magnification is asymmetric, and this is the part that gets inverted. A
  defect seen below the required magnification is still a defect; nothing
  about a weaker lens un-finds it. A clean look below the requirement
  establishes nothing, because the defects the requirement exists to catch are
  exactly the ones that lens cannot resolve. A low-magnification examination
  can therefore reject and can refer, and it cannot accept.
- Two thresholds, not one. A defect at or below the review threshold is
  accepted, one past it but at or below the reject threshold is referred, and
  one past the reject threshold is rejected. A value landing exactly on a
  threshold takes the gentler side; the comparison tolerance absorbs
  representation error rather than widening the limit.
- A diode nobody examined is not a passing diode. The declared population and
  the examined population are compared, and a diode whose examination came
  back invalid sits with the ones never presented: both are unestablished.
- A referral is not a final disposition either. The lot cannot close while a
  diode is still waiting on review, however small the defect that sent it
  there.

## Workflow

1. Validate the examination policy first: the magnification the examination
   owes, the largest rejected share the lot may carry, and the headroom under
   a review threshold inside which an accepted diode counts as marginal.
2. Validate the declared limit table: a non-blank defect type and location, a
   positive review threshold at or below a positive reject threshold, and no
   threshold longer than the die. A type and location declared twice is a
   transcription defect and is refused; an empty table closes the assessment.
3. Validate every examined diode record: a non-blank identifier, no duplicate
   identifier, a positive smallest die dimension, a positive magnification,
   and a sequence of observed defects that may legitimately be empty.
4. Refer every observed extent to the die dimension and sentence it against
   the threshold pair its own type and location carry, treating an undeclared
   combination as a referral.
5. Roll the observations up per diode: a reject outranks a referral, a
   referral outranks an inadequate magnification, and only a clean look at
   adequate magnification accepts.
6. Take the rejected share of the examined population against the declared
   allowance, then collect the diodes carrying no final disposition -- never
   presented, examination invalid, or still referred.
7. Report the worst diode and its relative defect beside the verdict, and
   raise a marginal advisory for every accepted diode sitting inside the
   policy headroom under its review threshold. Advisories travel with the
   verdict and do not move it.
8. Close on one verdict: surface defect limits not established, lot fails
   visual inspection, lot visual inspection record incomplete, or lot meets
   the visual inspection limits.

## Pitfalls

- Sentencing defects in millimetres. The same absolute extent is trivial on
  one die size and disqualifying on another, and an absolute limit table
  hides which one this lot is.
- Indexing the limits by defect type alone. The periphery allowance then
  leaks into the active area, which is where the diode actually works.
- Reading a clean look at low magnification as a pass. It is the one
  conclusion that examination cannot support, and it is the commonest way a
  workmanship record turns out to prove nothing.
- Discarding a defect because the lens was too weak to be official. The
  examination found it; the inadequate magnification is a reason to look
  again, never a reason to unsee it.
- Closing the lot with referrals outstanding. A referral is a question that
  has not been answered yet, and counting it as neither accept nor problem
  quietly turns it into an accept.

## Behavior contract (gate 3)

The policy validation, the limit table validation with an equal threshold
pair admitted, the extent referred to the smallest die dimension, the
per-observation sentence against a type-and-location limit, the undeclared
combination as a referral, the asymmetry of magnification, the per-diode
rollup, the rejected share against its allowance, the unestablished and
referred populations, the worst diode, the marginal advisories and the lot
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_visual_inspection.py against
scripts/e2008_blocking_diode_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_blocking_diode_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

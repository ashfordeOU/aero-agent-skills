---
name: q6013-class-3-handling-and-storage
description: "Evaluate the handling protection and storage conditions a commercial EEE lot is kept under at the lowest assurance class of ECSS-Q-ST-60-13C clause 6.4: band the part by its declared withstand voltage, derive the minimum measure set that band owes, credit an equivalent measure recorded at the time of use except on the band this class refuses to relax, integrate the temperature and humidity logs into a duration-weighted dose rather than a peak, read the packaging and the shelf-life margin, and return one release, release-with-actions or quarantine verdict. Use when a light store is graded before parts are issued. Trigger: ecss, q-st-60-13c-clause-6-4, class-three-handling-and-storage, minimum-esd-measure-set, recorded-equivalent-measure-substitution, storage-excursion-duration-dose, humidity-indicator-card-reading, stored-lot-release-verdict."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-handling-and-storage, class-three-handling-and-storage, minimum-esd-measure-set, recorded-equivalent-measure-substitution, storage-excursion-duration-dose, humidity-indicator-card-reading, stored-lot-release-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Handling and Storage (space-systems/ecss/q6013-class-3-handling-and-storage)

Use when the task is clause 6.4 of ECSS-Q-ST-60-13C at the lowest assurance
class: commercial parts are sitting in a store that was never built to the
standard of a flight parts bay, and the question before they are issued is
whether what that store actually operates is enough for what is inside the
bags.

## Domain quick reference

- The damage that matters most in the store is the damage that leaves no
  mark. A latent electrostatic injury does not fail incoming inspection; it
  fails after integration, by which time the lot is inside a flight unit and
  the event is months behind. The measures are therefore graded on presence,
  not on whether anything visibly went wrong.
- Sensitivity is banded and the band sets the regime. A part that withstands
  a few hundred volts is not a stricter version of one that withstands
  several thousand; it needs air ionisation and a checked personnel ground,
  because the parts either survive the bench or they do not.
- What this class relaxes is approval, not the measure. An equivalent may
  stand in for an owed measure without anyone reviewing it first, provided
  the substitution was recorded at the time of use. The record is the whole
  of the control, so an unrecorded equivalent is a gap with a story attached.
- The relaxation has a floor under it. On the most sensitive band nothing is
  substituted at all, because a part down at a few hundred volts does not
  survive an improvisation nobody looked at.
- An excursion has a size and a duration, and the product of the two is what
  the lot actually experienced. A store two degrees over its band for a
  season and a store fifteen degrees over it for twenty minutes give the
  same yes-or-no answer and completely different dispositions, so the dose
  is carried to the verdict rather than thrown away at the comparison.
- Undershoot counts as well as overshoot. Condensation on a cold part
  carried into a warm bay is a moisture event even though the store never
  went above its upper limit, so the two doses are accumulated separately
  and both reach the severity grading.
- Packaging is evidence, not a checkbox. The humidity indicator is what says
  whether the barrier did its job, which is why a breached bag with a dry
  indicator and an intact bag with a saturated one are different findings
  with different dispositions.
- A reading sitting exactly on a limit is inside the band. The dose
  arithmetic can leave the two sides a few ULP apart, and that is
  representation error rather than an excursion, absorbed inside the
  comparison rather than by moving the limit.

## Workflow

1. Validate the storage policy: the rising dose thresholds, the indicator
   margin and the review horizon. Thresholds that do not rise, or a
   fractional horizon, are refused rather than used.
2. Band the part from its declared withstand voltage. A negative or
   non-numeric withstand is an input error, not a default to the safest
   band.
3. Derive the minimum measure set the band owes -- the baseline for every
   band, plus ionisation and a shift-start personnel-ground check for the
   sensitive bands -- and name what the store does not operate.
4. Credit an equivalent measure where the substitution was recorded at the
   time of use, refuse it where it was not, and refuse it outright on the
   band this class will not relax. Refuse a substitution offered for a
   measure the band does not owe.
5. Integrate the temperature and relative-humidity logs into an over-limit
   and an under-limit dose, keep the peak alongside the dose, and grade the
   dose into a severity.
6. Read the packaging -- barrier, desiccant and the indicator against its
   printed limit -- and take the shelf-life margin in whole days at the
   review date.
7. Rank every finding by severity and return one verdict: released,
   released-with-actions or quarantined.

## Pitfalls

- Grading the store on what it owns rather than what it operates. A wrist
  strap in a drawer and an ioniser switched off at the wall both read as
  present on an equipment list and neither protects a part on band 0.
- Reading the substitution allowance as permission to improvise. It is
  permission to record, and an equivalent used without a record is exactly
  the gap the allowance was written to avoid.
- Carrying the relaxation onto the most sensitive band. The floor under the
  allowance is there because that band has no margin to spend on a
  substitute nobody assessed.
- Reducing an excursion to a yes or no, or to its peak. The magnitude
  multiplied by the duration is what separates a logged deviation from a
  quarantine, and a peak-only reading misses the slow drift entirely.
- Reading a limit band as a ceiling. Undershoot is a moisture event of its
  own, so the under-limit dose is accumulated rather than discarded.
- Treating an intact bag as a dry part. The indicator is the evidence; a
  sealed bag with a saturated card has already failed and the seal is what
  kept the moisture in.

## Behavior contract (gate 3)

The policy validation, the sensitivity banding, the minimum measure set, the
recorded-equivalent substitution and the band that refuses it, the
over-limit and under-limit excursion dose with its peak and logged hours,
the dose severity grading, the humidity indicator states, the shelf-life
margin and the ranked storage verdict are exercised by the gate 3 contract
test: scripts/test_q6013_class_3_handling_and_storage.py against
scripts/q6013_class_3_handling_and_storage_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_3_handling_and_storage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

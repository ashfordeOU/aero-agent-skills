---
name: q6013-class-1-handling-and-storage
description: "Use when a bonded store, incoming quarantine or shelf-life review is graded before parts are issued. Evaluate the handling and storage regime protecting a highest-assurance commercial EEE lot under ECSS-Q-ST-60-13C clause 4.4: place the part in a human-body-model sensitivity band, derive the electrostatic controls that band owes and name the ones the store does not operate, measure the temperature and humidity excursions against the declared limits, count the moisture floor life consumed since the dry pack was opened, and return the shelf-life margin with one release, release-with-actions or quarantine verdict. Trigger: ecss, q-st-60-13c, class-1-electrostatic-handling-controls, class-1-storage-environment-limits, class-1-shelf-life-margin, moisture-sensitivity-floor-life, solderability-retest-interval, stored-lot-release-verdict."
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
  tags: [ecss, q-st-60-eee-component-scope, q-st-60-13c, q6013-class-1-handling-and-storage, class-1-electrostatic-handling-controls, class-1-storage-environment-limits, class-1-shelf-life-margin, moisture-sensitivity-floor-life, solderability-retest-interval, stored-lot-release-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Class 1 — Handling and Storage (space-systems/ecss/q6013-class-1-handling-and-storage)

Use when the task is clause 4.4 of ECSS-Q-ST-60-13C: electrostatic
protection, storage conditions and shelf life for commercial parts procured at
the highest assurance level. This leaf grades a stored lot on whether the
regime around it matches the sensitivity, moisture behaviour and age of the
parts inside the bag.

## Domain quick reference

- The damage that matters most in the store is the damage that leaves no
  mark. A latent electrostatic injury does not fail incoming inspection; it
  fails after integration, and by then the lot is inside a flight unit and the
  event that caused it is months behind. This is why the controls are graded
  on presence, not on whether anything visibly went wrong.
- Sensitivity is banded, and the band sets the regime. A part that withstands
  a few hundred volts is not merely a stricter version of a part that
  withstands several thousand; it needs air ionisation and continuous
  personnel-grounding monitoring, because periodic checks leave gaps a
  low-band part cannot survive.
- Commercial parts arrive with moisture behaviour attached. Once a dry pack is
  opened the part is on a clock measured in hours, and the clock runs whether
  or not anyone is working on it. An approved bake returns floor life; a
  resealed bag with fresh desiccant pauses the clock but does not reset it.
- Shelf life and the solderability re-test interval are two different clocks
  on the same lot. A lot can sit inside its shelf life and still owe a re-test,
  because the terminations oxidise on their own schedule.
- Storage limits are a band, not a ceiling. Undershoot matters as well as
  overshoot: condensation on a cold part entering a warm bay is a moisture
  event even though the store never went above its upper limit.
- An excursion has a size. A store two degrees above its band for an
  afternoon and a store fifteen degrees above it are the same yes-or-no answer
  and completely different dispositions, so the magnitude is carried through
  to the verdict rather than thrown away at the comparison.

## Workflow

1. Read the declared withstand voltage of the part and place it in its
   human-body-model sensitivity band. A negative or non-numeric withstand
   value is an input error, not a default to the safest band.
2. Derive the control set the band owes — the baseline grounded worksurface,
   personnel grounding and shielding bag for every band, plus ionisation,
   continuous wrist-strap monitoring and entry logging for the most sensitive
   bands — and name the owed controls the store does not operate.
3. Measure the temperature and relative-humidity excursions of the store
   against the declared limits, returning a signed magnitude so an undershoot
   stays distinguishable from an overshoot, with the boundary absorbed by a
   named tolerance rather than by moving the limit.
4. If the lot is moisture sensitive, compute the fraction of the floor life
   consumed since the dry pack was opened, crediting an approved bake. A level
   that carries no floor life is not a fraction problem: it is baked before
   use.
5. Compute the shelf-life margin in days at the review date and test whether
   the solderability re-test interval has elapsed since storage entry or since
   the last recorded re-test.
6. Rank the findings — missing controls, large excursions, consumed floor life
   and expiry first — and return one verdict: released,
   released-with-actions, or quarantined.

## Pitfalls

- Grading the store on what it owns rather than what it operates. A wrist
  strap in a drawer and an ioniser switched off at the wall both read as
  present on an equipment list and neither protects a part in band 0.
- Applying one control set to the whole stores area. The regime follows the
  most sensitive part in the bay, and a single low-band lot raises the
  requirement for the bench it is opened on.
- Counting floor life from when work started. The clock starts when the dry
  pack is opened, so a part opened on Friday and handled on Monday has already
  spent the weekend against its allowance.
- Reading a valid shelf life as a valid lot. Shelf life and the solderability
  re-test interval run independently, and a lot well inside its shelf life can
  still owe a re-test before it is issued.
- Reducing an excursion to a yes or no. The magnitude is what separates a
  logged deviation from a quarantine, so it is carried into the verdict rather
  than collapsed at the comparison.
- Relaxing a storage limit so an exact-limit reading passes. A value sitting
  on the limit is a representation question, handled by the tolerance inside
  the comparison; the declared band stays as specified.

## Behavior contract (gate 3)

The sensitivity banding, owed-control derivation, environment excursion,
moisture floor-life fraction, shelf-life margin, re-test interval test and the
storage verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_handling_and_storage.py against
scripts/q6013_class_1_handling_and_storage_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_handling_and_storage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

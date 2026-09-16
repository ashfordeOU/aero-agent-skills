---
name: q60-class-1-handling-and-storage
description: "Use when a class 1 lot is unpacked, moved between bays or reviewed before issue. Assess the handling, packaging and storage regime protecting a class 1 EEE lot under ECSS-Q-ST-60C clause 4.4: derive the packaging layers the part's fragility and moisture needs owe, test the container as received for seal integrity and a humidity indicator inside its threshold, return the transport shock peak as a fraction of the allowable, accumulate a thermal degradation index over the storage duration, name the handling authorisations the movement lacked, and close with one fit-for-issue, issue-with-actions or hold-for-reconditioning disposition. Trigger: ecss, q-st-60c, class-1-packaging-layer-suitability, class-1-container-seal-integrity, class-1-transport-shock-exposure, class-1-thermal-degradation-index, class-1-handling-issue-disposition."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q-st-60c, q60-class-1-handling-and-storage, class-1-packaging-layer-suitability, class-1-container-seal-integrity, class-1-transport-shock-exposure, class-1-thermal-degradation-index, class-1-handling-issue-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 1 — Handling, Packaging and Storage (space-systems/ecss/q60-class-1-handling-and-storage)

Use when the task is clause 4.4 of ECSS-Q-ST-60C: the handling, packaging and
storage procedures that keep class 1 parts free of damage and degradation.
This leaf grades one pack and its storage history on whether what the parts
travelled and sat in matches what they need.

## Domain quick reference

- The pack is a stack of layers, and each layer answers a different threat.
  The shielding bag answers charge, the cushioned tray answers shock, the
  barrier bag and desiccant answer moisture. Substituting one for another
  leaves the threat it was meant to answer wide open, which is why the owed
  set is derived from the part rather than from what the stores cupboard has.
- Fragility is a statement about what a part cannot survive, not about how
  much it cost. A cheap part with a bonded internal element still needs the
  foam suspension a robust expensive one does not.
- A container tells you what happened to it. An intact seal and an indicator
  card inside its threshold are the only two pieces of evidence available
  before the bag is opened, and once it is open they can never be recovered.
- Shock exposure is a ratio, not an alarm. A pack five percent over its
  allowable and one three times over produce the same alarm and completely
  different dispositions, so the recorded peak is carried through as a
  fraction of the allowable rather than collapsed at the comparison.
- Warm storage and long storage are the same currency. Expressing the
  duration in reference-temperature days lets a short spell in an unconditioned
  bay be compared with years in a controlled store on one scale, with a rise
  of one doubling interval doubling the rate at which the index accumulates.
- Authorisation is part of the regime, not paperwork around it. An untrained
  handler and a movement made without an open work order leave no physical
  trace on the part, so they are graded from the record or not at all.

## Workflow

1. Derive the packaging layers the part owes from its fragility category and
   whether it needs a moisture barrier, then name the owed layers the
   delivered pack does not carry. Compare the names without case sensitivity.
2. Test the container as received: seal state, and the humidity indicator
   reading against its threshold, with an exactly-on-threshold reading
   counted as inside by a named tolerance rather than by moving the threshold.
3. Return the recorded transport shock peak as a fraction of the part's
   allowable. One means the peak landed exactly on the allowable.
4. Accumulate the thermal degradation index over the storage duration at the
   mean storage temperature, normalised to the reference temperature, and
   test it against the declared allowance.
5. Name the handling authorisations the movement did not hold.
6. Rank the findings by severity and return one disposition: fit-for-issue,
   issue-with-actions, or hold-for-reconditioning.

## Pitfalls

- Grading the pack on the outer box. The outer container survives handling
  that destroys the part inside it, and an undamaged box is routinely the
  reason a shock record is never read.
- Reading the humidity indicator after the bag has been open for an hour. The
  card reports the enclosure it is sitting in, so a reading taken late reports
  the room and clears a pack that arrived wet.
- Reducing the shock record to a pass or a fail. The magnitude is what
  separates a logged deviation from reconditioning, and it is thrown away at
  the comparison unless the ratio is carried forward.
- Comparing storage durations without their temperatures. Six months in an
  unconditioned bay is not the same exposure as six months in a controlled
  store, and a duration alone says it is.
- Moving a threshold so a boundary case passes. A reading sitting exactly on
  its threshold is a representation question, handled by the tolerance inside
  the comparison; the declared threshold stays as specified.
- Treating an authorisation gap as an administrative note. An untrained
  handler is the mechanism behind damage that is later recorded as unexplained.

## Behavior contract (gate 3)

The packaging layer derivation, container integrity tests, shock exposure
ratio, thermal degradation index, allowance comparison, authorisation gaps and
the handling disposition are exercised by the gate 3 contract test:
scripts/test_q60_class_1_handling_and_storage.py against
scripts/q60_class_1_handling_and_storage_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q60_class_1_handling_and_storage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

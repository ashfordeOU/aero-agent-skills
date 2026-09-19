---
name: q6005-technology-identification-form-deliverable
description: "Audit a technology identification form delivered as a data item against the entries and arrangement Annex A of ECSS-Q-ST-60-05C mandates. Use when a hybrid manufacturer hands the completed form over and the procurement authority must accept or hold the deliverable: confirm every mandated header and body entry is present and carries a value, fire each conditional rule so a declared option pulls in the further entries it owes, place an entry that sits outside the mandated set, measure how far the delivered arrangement departs from the mandated one through the longest run already in sequence, and return a completeness ratio with ordered findings. Trigger: ecss, q-st-60-05c-annex-a, tif-data-item-entry-set, tif-data-item-arrangement-order, tif-conditional-entry-rule, tif-data-item-completeness-ratio, hybrid-identification-form-deliverable."
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
  tags: [ecss, q-st-60-05-hybrid-microcircuit-scope, q6005-technology-identification-form-deliverable, tif-data-item-entry-set, tif-data-item-arrangement-order, tif-conditional-entry-rule, tif-data-item-completeness-ratio, hybrid-identification-form-deliverable]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Microcircuits — Technology Identification Form Data Item (space-systems/ecss/q6005-technology-identification-form-deliverable)

Use when the task is the data-item step of ECSS-Q-ST-60-05C Annex A —
not why a hybrid supplier owes a technology identification form, and not
how long an issued one stays valid, but whether the document actually
delivered carries the entries the annex mandates, in the arrangement it
mandates, so the procurement authority can accept it or hold it.

## Domain quick reference

- The form is a deliverable data item, so its acceptance is a document
  question before it is an engineering one. Two things are graded: the
  entry set (is everything the annex names written down, with something
  behind the heading) and the arrangement (do the entries appear in the
  order the annex lays out, so a reader and a downstream assessor find
  them where they expect them).
- The mandated entries fall in two blocks. The header block identifies
  the issue of the data item itself — reference, issue number, date,
  manufacturer, the specific manufacturing line, and the preparing and
  accepting names. The body block declares the construction
  technologies the form exists to record — hybrid type, substrate,
  interconnection, die attach, encapsulation, sealing, the process
  control documents and the qualification status.
- Part of the entry set is conditional, not fixed. Declaring a hermetic
  seal owes a leak test method and an internal gas analysis reference;
  declaring a non-hermetic one owes the moisture protection and its
  exposure evidence; a polymer encapsulation owes an outgassing
  screening reference; an RF hybrid type owes a frequency range. The
  mandated set for a case is therefore derived from the declarations
  inside the form, not read off a fixed list.
- A heading delivered with nothing behind it is a different finding
  from a heading that is absent. The absent entry was never addressed;
  the blank entry was addressed and left open, which is a supplier
  action rather than a document rebuild, so the two are separated.
- An entry outside the mandated set is also two findings, not one. An
  entry belonging to a rule that did not fire is out of scope for this
  case and only earns a remark; an entry belonging to no rule at all is
  unknown content in a controlled data item and holds the delivery.
- Arrangement is measured, not judged pass or fail on the first
  displacement. The longest run of delivered entries already in
  mandated sequence, over the entries recognised at all, says how much
  of the document a reader can follow before the order breaks.

## Workflow

1. Normalise the delivered form into a canonical entry map: fold case,
   hyphens and spacing into one spelling, refuse an entry delivered
   twice under two spellings, and refuse a value that is not text.
2. Read the declarations in the body block and fire the conditional
   rules they trigger; the union of the fixed set and the owed entries
   is the mandated set for this case.
3. Split the shortfall: entries never delivered, and entries delivered
   as a heading with no value.
4. Group the surplus: entries owed only by a rule that did not fire
   (out of scope) and entries belonging to no rule (unknown).
5. Measure the arrangement against the mandated order through the
   longest in-sequence run over the recognised entries, and compare the
   resulting ratio with one using a named tolerance, because a ratio of
   counts can land a few units in the last place away from unity.
6. Compute the completeness ratio over the mandated set for this case
   and emit the findings in a stable order: absent, blank, unknown,
   out of scope, arrangement.
7. Return accept when nothing is outstanding, accept-with-remarks when
   only out-of-scope entries remain, and hold otherwise.

## Pitfalls

- Grading the form against a fixed entry list. The conditional rules
  mean a hermetic case and a non-hermetic case owe different documents;
  a fixed list passes a hermetic form that never named its leak test.
- Collapsing an absent entry and a blank entry into one finding. They
  route to different people and take different times to close, and the
  merged count hides which of the two the delivery actually suffers.
- Treating any surplus entry as a defect. A supplier that files the
  frequency range on a non-RF hybrid has volunteered information, not
  broken the data item; holding the delivery for it is a false red.
- Failing the arrangement on the first displaced entry. One heading in
  the wrong place is a remark; the measure that matters is how much of
  the mandated sequence survives, and that needs the run length, not a
  first-mismatch index.
- Comparing the arrangement ratio with 1.0 by strict equality. The
  ratio is a quotient of counts; absorb the representation error with
  the named tolerance rather than rounding the ratio before comparing.

## Behavior contract (gate 3)

The entry normalisation, conditional rule firing, absent and blank
split, surplus grouping, longest in-sequence run, completeness ratio
and the accept / accept-with-remarks / hold verdict are exercised by
the gate 3 contract test:
scripts/test_q6005_technology_identification_form_deliverable.py
against
scripts/q6005_technology_identification_form_deliverable_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q6005_technology_identification_form_deliverable.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

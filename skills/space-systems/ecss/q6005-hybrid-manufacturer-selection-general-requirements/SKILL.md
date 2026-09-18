---
name: q6005-hybrid-manufacturer-selection-general-requirements
description: "Assess whether a candidate hybrid microcircuit manufacturer may be selected at all, by grading it against the validation route its category is bound to. Use when a maker is being chosen for a hybrid buy under ECSS-Q-ST-60-05 clause 5.1: derive the route from the category, confirm every required element of the validation pack is held, in date, and neither suspended nor withdrawn at the selection date, confirm the cover reaches the date the procurement still needs it, and refuse flight heritage, a sister-site approval or a long supply relationship as a stand-in for an open element. Trigger: ecss, q-st-60-05-clause-5-1, hybrid-microcircuit-manufacturer-selection, hybrid-manufacturer-validation-route, hybrid-line-approval-evidence-expiry, hybrid-validation-pack-gap, hybrid-manufacturer-heritage-claim."
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
  tags: [ecss, q-st-60-eee-scope, q6005-hybrid-manufacturer-selection-general-requirements, hybrid-microcircuit-manufacturer-selection, hybrid-manufacturer-validation-route, hybrid-line-approval-evidence-expiry, hybrid-validation-pack-gap, hybrid-manufacturer-heritage-claim]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Microcircuits — Manufacturer Selection Baseline (space-systems/ecss/q6005-hybrid-manufacturer-selection-general-requirements)

Use when the task is the clause 5.1 general requirement of ECSS-Q-ST-60-05 —
a hybrid microcircuit manufacturer is about to be chosen, and the baseline
rule is that whoever is chosen has to pass the validation route the standard
defines for its category further on. The question is not who is best placed
to build the part; it is whether this maker is one the standard lets the
project select in the first place.

## Domain quick reference

- The rule is a gate, not a preference. It does not rank candidates and it
  does not weigh a strong maker against a weak one. A maker either carries
  the route its category owes, or it is not selectable, and a stronger
  showing on one element never compensates for an open one.
- The route follows the category. A maker whose production line already
  carries an approval owes the shorter pack — the line approval itself, the
  quality management certification, and the process identification. A maker
  whose line does not owes those plus the audit report and the line
  evaluation record, because the approval it will eventually hold has yet to
  be established.
- A document on file is not the same as a document in force. Each element
  has an issue date, an expiry and a standing, and a suspension or a
  withdrawal defeats an expiry that is still years out. A pack read for
  presence alone reports a maker as selectable on paperwork that no longer
  means anything.
- Selection is a decision about the future. Evidence that is in force on the
  day the choice is made but lapses before the lot is due leaves the buy
  uncovered exactly where the cover was the point, so the pack is graded
  against the date the procurement runs to as well as the date it is read.
- Heritage is the argument that is always available and never sufficient.
  Flight history, a sister site's approval and a long-standing supply
  relationship are all reasons to expect the route to close easily; none of
  them closes it, and offering one against an open element is itself worth
  recording.

## Workflow

1. Normalise the candidate's category and derive the validation route it is
   bound to. Two categories exist; a commercial label is not a third.
2. Canonicalise every offered document: a recognised element kind, an issue
   date, an expiry that is not before the issue, and a declared standing.
   Reject a malformed record rather than reading past it.
3. Resolve duplicates by kind, preferring an element in force over one that
   is not, and the longer cover between two that are in force.
4. Decide each required element at the selection date: held and in force,
   held but lapsed, held but suspended or withdrawn, or absent. Keep those
   four outcomes apart in the report — they call for different actions.
5. Where the procurement names a date it must stay covered to, grade each
   in-force element against that date too, and flag the ones that expire
   first.
6. Record any substitute claim offered while the route is open, and leave
   the route open regardless.
7. Return selectable only when no element is absent, lapsed, unusable or
   short of cover.

## Pitfalls

- Grading the pack for presence. The defect that survives a presence check is
  a suspended certificate with a distant expiry, which reads as the healthiest
  document in the file.
- Applying the shorter pack to a maker whose line is not approved. The two
  extra elements are the ones that establish the approval the shorter route
  assumes, so dropping them makes the route circular.
- Reading the selection date as the only date that matters. A pack that
  lapses mid-build met the rule on the day it was read and fails it for every
  day the lot is actually made.
- Letting a surplus element offset a missing one. A maker with an approved
  line that also holds an audit report is welcome to; it does not turn an
  absent process identification into a closed route.
- Recording a heritage argument as mitigation. It is evidence about the
  project's reasoning, not about the maker, and filing it against an open
  element is how an open element stops being tracked.

## Behavior contract (gate 3)

The category-to-route derivation, evidence record validation, date parsing,
state resolution at a selection date, duplicate grouping, cover-to-date
grading, substitute-claim handling and the selectable decision are exercised
by the gate 3 contract test:
scripts/test_q6005_hybrid_manufacturer_selection_general_requirements.py
against
scripts/q6005_hybrid_manufacturer_selection_general_requirements_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q6005_hybrid_manufacturer_selection_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

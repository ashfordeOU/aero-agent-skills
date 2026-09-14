---
name: e2008-coverglass-packing-and-storage
description: "Determine which rule set governs coverglass packing, dispatch, handling and storage under ECSS-E-ST-20-08C clause 8.11. Use when one of those four activities has to be traced to the referenced product assurance standard: resolve the reference each activity declares, demote an unapproved project tailoring, hold a product assurance reference cited at a superseded issue, ask packing and handling for the measure keeping one coated face off the next, and measure declared storage temperature, humidity and unspent storage life only once storage itself is governed. Trigger: ecss, e-st-20-08c-clause-8-11, coverglass-packing-and-storage-rules, coverglass-product-assurance-reference-resolution, coverglass-storage-environment-envelope, coverglass-storage-life-margin, coverglass-coated-surface-protection."
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
  tags: [ecss, e-st-20-08-coverglass-scope, e-st-20-08c-clause-8-11, e2008-coverglass-packing-and-storage, coverglass-packing-and-storage-rules, coverglass-product-assurance-reference-resolution, coverglass-storage-environment-envelope, coverglass-storage-life-margin, coverglass-coated-surface-protection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coverglasses -- Packing and Storage (space-systems/ecss/e2008-coverglass-packing-and-storage)

Use when the task is clause 8.11 of ECSS-E-ST-20-08C: how coverglasses are
packed, dispatched, handled and stored is not set out here at all, it is
pointed at the referenced product assurance standard. This leaf does the
work a pointer clause actually creates -- saying, per activity, which rule
set governs it, at which issue, and whether that answer still stands.

## Domain quick reference

- A pointer clause is not an empty clause. What it demands is that the
  project can name, per activity, the governing reference and its
  standing. An activity nobody can point at is an open activity, not a
  compliant one, and that is the finding this leaf exists to raise.
- The four activities are resolved independently. Packing can rest on the
  product assurance standard while dispatch quietly runs on a carrier's
  own handbook, and a single project-level answer hides exactly that.
- The kind of reference decides the disposition, not the fact that a
  reference exists. A product assurance reference governs; a project
  tailoring governs only while its record is approved; a supplier
  instruction and an absent reference govern nothing, because the point
  of the pointer is that the referenced standard, not local custom, is
  the governing text.
- A reference is also read for its issue. An activity citing the product
  assurance standard at an issue the governing one has replaced is
  governed in name only, and that is a different finding from citing
  nothing -- one has the right document at the wrong edition, the other
  has no document.
- An unapproved tailoring is likewise its own reason. It is not the same
  finding as no reference at all: one has a document waiting on a
  signature, the other has nothing to sign.
- Coverglasses are coated optical parts, which is what separates this
  clause from a general packing rule. Packing and handling are the two
  activities where one coated face can meet another surface, so both have
  to name the measure that keeps them apart; an interleaving that nobody
  declared is an interleaving nobody can be audited on.
- Storage is the one activity that also carries numbers. The governing
  rules bound the environment the glass is held in and how long it may be
  held, so declared temperature, declared relative humidity and the
  unspent share of the permitted storage life are all measured when they
  are declared.
- Storage numbers are only measured once storage is governed. Conditions
  outside an envelope nobody has resolved is two findings reported as
  one, and it lets a project fix the thermostat and think the clause is
  closed.
- The envelope and the storage-life floor are declared project policy,
  not physical constants. A tighter envelope groups the same warehouse
  reading differently, which is why both are read from the policy and
  echoed back in the result.

## Workflow

1. Read the declaration for each of the four activities. Reject a case
   that names an activity twice rather than letting the last one win.
2. Resolve each activity from the kind of reference it declares, and
   demote a project tailoring to ungoverned when its record is not
   approved.
3. Read the issue of a product assurance reference against the governing
   issue, and report a superseded citation as its own state.
4. Ask packing and handling for the coated-surface protection measure,
   and report the activity that names none.
5. For storage, and only once it resolved, hold the declared temperature
   and relative humidity to the governing envelope under a named
   tolerance.
6. Still for storage, work out how much of the permitted storage life is
   unspent, and separate an overrun from a merely thin margin.
7. Roll up: list the activities nobody declared, group the rest by state,
   report the governed share of the four, and return a verdict that is
   clean only when all four are governed and storage is inside its
   bounds.

## Pitfalls

- Reading a pointer clause as nothing to do. The clause transfers the
  rules; it does not remove the obligation to say which rules, at which
  issue, for which activity.
- Accepting any reference as a governing reference. A carrier handbook
  and a warehouse habit are both references and neither is the referenced
  product assurance standard.
- Reading a reference for its name and not its issue. The right standard
  at a superseded edition passes every presence check and still describes
  a rule set nobody works to.
- Treating an unapproved tailoring as a tailoring. Until the record is
  approved it governs nothing, and a project that counts it as governed
  ships against a deviation nobody signed.
- Answering at project level. Four activities, four answers; a blanket
  citation is what lets dispatch fall through the gap while the audit
  trail looks complete.
- Forgetting that the article is coated. A packing rule that would do for
  a machined bracket says nothing about one coated face resting on the
  next, and the damage it permits appears at incoming inspection.
- Measuring storage numbers on an activity that is not governed. The
  envelope is only meaningful once the rule set that sets it has been
  resolved, and folding the two together reports one finding where there
  are two.
- Judging a storage reading that lands exactly on an envelope bound, or a
  margin that lands exactly on its floor, by bare arithmetic. The bound is
  a declared round number and the reading comes from an instrument log, so
  a value meant to sit on the bound can land a few units in the last place
  outside it; the comparison absorbs that while the bound stays as
  declared.

## Behavior contract (gate 3)

The four-activity vocabulary, the reference-kind disposition, the
tailoring approval demotion, the superseded-issue state, the
coated-surface protection demand on packing and handling, the storage
envelope test under a named tolerance, the unspent storage-life margin
with its overrun case, the suppression of storage numbers on an
ungoverned storage activity and the rolled-up four-activity verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_packing_and_storage.py against
scripts/e2008_coverglass_packing_and_storage_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_packing_and_storage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

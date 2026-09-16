---
name: e2008-pva-packaging-and-storage
description: "Use when a PVA packing, dispatch, handling or storage instruction has to be traced to its governing rules. Determine which product assurance rule set governs the packing, dispatch, handling and storage of a photovoltaic assembly under clause 5.9 of ECSS-E-ST-20-08C: resolve the reference each activity declares, hold a project deviation to an approved tailoring record, measure declared storage temperature and humidity against the governing envelope, work out the storage life still unspent, and return one rule-resolution verdict. Trigger: ecss, e-st-20-08c, pva-packaging-and-storage, pva-packing-dispatch-handling-storage-rules, pva-product-assurance-reference-resolution, pva-storage-environment-envelope, pva-storage-duration-margin, pva-packaging-tailoring-record."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-pva-packaging-and-storage, e-st-20-08c, pva-packaging-and-storage, pva-packing-dispatch-handling-storage-rules, pva-product-assurance-reference-resolution, pva-storage-environment-envelope, pva-storage-duration-margin, pva-packaging-tailoring-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Packaging and Storage (space-systems/ecss/e2008-pva-packaging-and-storage)

Use when the task is clause 5.9 of ECSS-E-ST-20-08C: the packing,
dispatch, handling and storage of a photovoltaic assembly are not set
out here at all, they are handed to the product assurance rules. This
leaf does the work a pointer clause actually creates -- saying, for each
of the four activities, which rule set governs it and whether that
answer holds.

## Domain quick reference

- A pointer clause is not an empty clause. What it demands is that the
  project can name, per activity, the governing reference and its
  standing. An activity nobody can point at is an open activity, not a
  compliant one, and that is the finding this leaf exists to raise.
- The four activities are resolved independently. Packing can rest on
  the product assurance rules while dispatch quietly runs on a carrier's
  own handbook, and a single project-level answer hides exactly that.
- The kind of reference decides the disposition, not the fact that a
  reference exists. A product assurance reference governs. A project
  tailoring governs only while its tailoring record is approved. A
  supplier instruction and an absent reference do not govern at all,
  because the point of the pointer is that the product assurance rules,
  not local custom, are the governing text.
- An unapproved tailoring is reported as its own reason. It is not the
  same finding as no reference at all: one has a document waiting on a
  signature, the other has nothing to sign.
- Storage is the one activity that also carries numbers. The governing
  rules bound the environment the assembly is held in and how long it
  may be held, so declared temperature, declared relative humidity and
  the elapsed share of the permitted storage life are all measured when
  they are declared.
- Storage numbers are only measured once the activity is governed. Out
  of envelope conditions under a rule set nobody has resolved is two
  findings reported as one, and it lets a project fix the thermostat
  and think the clause is closed.
- The envelope and the storage-life margin are declared project policy,
  not physical constants. A tighter envelope groups the same warehouse
  reading differently, which is why both are read from the policy and
  echoed back in the result.

## Workflow

1. Read the declaration for each of the four activities. Reject a case
   that names an activity twice rather than letting the last one win.
2. Resolve each activity from the kind of reference it declares, and
   demote a project tailoring to ungoverned when its record is not
   approved.
3. Record the reason an activity failed to resolve -- no reference, an
   unapproved tailoring, or a rule set outside product assurance --
   because the three have different recoveries.
4. For storage, and only once it resolved, hold the declared
   temperature and relative humidity to the governing envelope.
5. Still for storage, work out how much of the permitted storage life
   is unspent, and separate an overrun from a merely thin margin.
6. Roll up: list the activities nobody declared, group the rest by
   verdict, report the resolved share of the four, and return a verdict
   that is clean only when all four are governed and storage is inside
   its bounds.

## Pitfalls

- Reading a pointer clause as nothing to do. The clause transfers the
  rules; it does not remove the obligation to say which rules, at which
  issue, for which activity.
- Accepting any reference as a governing reference. A carrier handbook
  and a warehouse habit are both references and neither is the product
  assurance rule set.
- Treating an unapproved tailoring as a tailoring. Until the record is
  approved it governs nothing, and a project that counts it as governed
  ships against a deviation nobody signed.
- Answering at project level. Four activities, four answers; a single
  blanket citation is what lets dispatch fall through the gap while the
  audit trail looks complete.
- Measuring storage numbers on an activity that is not governed. The
  envelope is only meaningful once the rule set that sets it has been
  resolved, and folding the two together reports one finding where
  there are two.
- Judging a storage reading that lands exactly on an envelope bound, or
  a margin that lands exactly on its limit, by bare arithmetic. The
  bound is a declared round number and the reading comes from an
  instrument log, so a value meant to sit on the bound can land a few
  units in the last place outside it; the comparison absorbs that while
  the bound stays as declared.

## Behavior contract (gate 3)

The reference disposition table, the tailoring approval demotion, the
per-activity resolution, the storage envelope test, the storage life
margin and the rolled-up four-activity verdict are exercised by the
gate 3 contract test:
scripts/test_e2008_pva_packaging_and_storage.py against
scripts/e2008_pva_packaging_and_storage_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_pva_packaging_and_storage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

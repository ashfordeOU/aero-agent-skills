---
name: e2008-cell-contact-adherence-test-purpose
description: "Determine what an adherence check on a bare solar cell's contacts and bypass diode attachment has to demonstrate under ECSS-E-ST-20-08C clause 7.5.7.2.1: add the downstream welding, curing, handling, launch and cycling stressors into one demand index, decide from it whether pulling contacts is worth doing at all, derive the pull load the service peak and its margin ask for, size the sample that lets the result speak for the lot, and refuse a plan whose pull lands before any conditioning, because that number describes the as-built joint rather than the one the mission leaves behind. Use when scoping or reviewing a bare-cell contact adherence campaign. Trigger: ecss, e-st-20-08c-clause-7-5-7-2-1, bare-cell-contact-adherence-purpose, cell-diode-attachment-strength, post-conditioning-contact-pull, contact-attachment-demand-index, bare-cell-pull-load-margin."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-cell-contact-adherence-test-purpose, bare-cell-contact-adherence-purpose, cell-diode-attachment-strength, post-conditioning-contact-pull, contact-attachment-demand-index, bare-cell-pull-load-margin, bare-cell-adherence-sample-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Cell Contact Adherence Test Purpose (space-systems/ecss/e2008-cell-contact-adherence-test-purpose)

Use when the task is to state and defend why the contacts and the bypass
diode attachment of a bare solar cell are pulled after conditioning under
ECSS-E-ST-20-08C clause 7.5.7.2.1 -- which downstream steps the strength
has to survive, whether the cell carries enough of them for the check to
earn its place, and whether the planned pull can produce a number that
describes the joint the mission actually leaves behind.

## Domain quick reference

- A bare cell's contacts are unloaded as delivered. Everything that
  loads them happens later: an interconnect welded or soldered onto the
  metallisation, an adhesive curing against it, a panel handled, a
  launch shaking it, an orbit cycling it. The strength worth measuring
  is the one still there at the end of that list, not the one the line
  produced.
- That is the whole reason the pull sits after conditioning. A pull on
  an unconditioned cell answers a question nobody asked -- it reports
  the as-built joint, which was never in doubt -- so a plan that orders
  it that way is repaired rather than sentenced.
- Conditioning logged after the pull is a sequencing error and not a
  saving grace. It weakened nothing the recorded number describes, so it
  is named in the findings and credited to nothing.
- The bypass diode attachment rides on the same argument but fails
  differently. A contact that lets go costs current from one cell; a
  diode attachment that lets go removes the shadow protection of the
  whole string it was there to guard.
- Demand accumulates. A cell that is only handled carries little; a cell
  that is welded, cured, launched and then cycled carries a lot, and the
  decision to run the check at all is taken on the total rather than on
  whichever step comes to mind first.
- The load the pull has to reach is a service number, not a bench habit:
  the peak the joint sees in service, lifted by a declared margin. A
  bench that stops below it cannot separate a joint that would have held
  from one that would not.
- A sample has to satisfy two floors at once -- a count and a share of
  the lot. A large lot sampled three times meets the count and still
  lets one unlucky cell speak for thousands.
- The severities, the threshold, the margin and the sample floors are
  declared project policy rather than physical constants, so they are
  stated with the result.

## Workflow

1. Take the lot with its declared downstream attachment stressors, the
   planned step sequence, the peak service load on a contact, the pull
   the bench can apply, the sample count and the lot size.
2. Refuse an unknown or repeated stressor rather than counting it. A
   repeat inflates the demand index and can pull a check into scope that
   the real service case never justified.
3. Add the declared severities into one demand index and read the
   objectives the check would demonstrate, one per stressor.
4. Compare the index with the threshold. Below it, report that the check
   is not required and stop -- there is no plan left to grade.
5. Place the pull in the planned sequence. Conditioning before it makes
   the result a survivable strength; nothing before it makes the result
   as-built, and that stops the assessment.
6. Build the required pull load from the service peak and the declared
   margin, and screen the bench against it, reporting any shortfall in
   newtons so the plan is scoped.
7. Take the sample against both floors, then sentence the plan: purpose
   served, or inadequate with every shortfall named rather than the
   first one found.

## Pitfalls

- Pulling a contact straight off the incoming inspection bench. The
  number is real, repeatable and about the wrong joint, and it reads as
  a pass at exactly the strength the clause does not care about.
- Crediting conditioning that ran after the pull because the traveller
  shows both. Order is the entire content of a post-conditioning
  requirement; a set of steps with no order in it grades nothing.
- Scoping the check from the assembly process alone. Launch and orbital
  cycling load the same joints long after the shop floor is finished
  with them, and leaving them out of the demand can drop the check.
- Treating the diode attachment as one more contact. Its failure takes
  out a protective function for a whole string, so it is carried as its
  own objective even when the contact objectives are all satisfied.
- Setting the pull load from what the bench happens to reach. A
  capability number masquerading as a requirement guarantees a pass and
  proves nothing about service.
- Sampling by count alone. Three cells is a respectable number and a
  negligible share of a lot of several thousand, so both floors are
  applied and the failing one is named.
- Comparing a demand index or a sample fraction against its threshold by
  bare arithmetic. Both are sums or quotients of declared quantities, so
  a case built to sit exactly on a threshold can evaluate a unit in the
  last place under it and read as out of scope on one platform and in
  scope on another.

## Behavior contract (gate 3)

The stressor normalisation and its two refusals, the demand index, the
demonstration objectives, the threshold that decides whether a check is
required, the conditioning-before-pull ordering rule, the required pull
load and the bench screen, the two sample floors and the scoping verdict
are exercised by the gate 3 contract test:
scripts/test_e2008_cell_contact_adherence_test_purpose.py against
scripts/e2008_cell_contact_adherence_test_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_cell_contact_adherence_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

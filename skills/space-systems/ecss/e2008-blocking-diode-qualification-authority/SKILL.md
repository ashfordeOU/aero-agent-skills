---
name: e2008-blocking-diode-qualification-authority
description: "Determine whether a planar blocking diode lot may be treated as qualified under ECSS-E-ST-20-08C clause 12.5.1, where the customer grants qualification to the company that actually runs the production process and not to a part number: catch a mesa lot the clause never reached, find a diode type nobody granted, separate that from a type granted to a different company than the one that built the lot, refuse a grant the supplier issued about its own product, hold the granted site and process baseline against the lot as built, name a step handed to a subcontractor the grant never covered, and roll the lots into one programme verdict. Use when a blocking diode lot, process-owner change or subcontracted step is treated as qualified. Trigger: ecss, e-st-20-08c, blocking-diode-qualification-authority, blocking-diode-grant-holder-identity, blocking-diode-process-owner-change, blocking-diode-subcontracted-step-coverage, blocking-diode-grant-issuing-authority."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-qualification-authority, blocking-diode-qualification-authority, blocking-diode-grant-holder-identity, blocking-diode-process-owner-change, blocking-diode-subcontracted-step-coverage, blocking-diode-grant-issuing-authority]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes -- Qualification Authority (space-systems/ecss/e2008-blocking-diode-qualification-authority)

Use when the task is clause 12.5.1 of ECSS-E-ST-20-08C: a planar blocking
diode carries qualification because the customer granted it, and the grant
was made to the company running the production process. It is not a
property of the drawing and it is not a property of the part number. This
leaf reads the lots and the grant register as two separate things and
returns which lots may be treated as qualified.

## Domain quick reference

- The grant attaches to an organisation, not to a type designation. A
  supplier that has run every test has produced a dossier; the customer
  makes the grant, and it lands on the company whose process was assessed.
- A part number travels and a process does not. The same diode type built
  at a second company is an unqualified diode type there, and a register
  lookup keyed on the type alone returns a grant that does not apply.
- "Nobody granted this type" and "somebody else holds the grant" are
  different findings with different answers. The first needs a
  qualification campaign; the second needs a campaign at this company,
  and merging them sends the wrong letter.
- Two companies may each legitimately hold a grant for one diode type.
  Two grants to the SAME company for the same type is a register defect,
  and resolving it by sort order buries it.
- The clause reaches planar construction. A mesa part in the same lot
  stream is a different article, and reading its grant at all is already
  the wrong question.
- A granted scope pins the production site and the process baseline. A
  lot built at a second site or on a moved baseline is outside what was
  granted however current the grant is.
- A step handed to a subcontractor leaves the granted process unless the
  subcontractor was named in the grant. The lot still says the right
  company built it, which is exactly why this one hides.
- The population is lots, not types. One type can run five lots and only
  the fourth be built by a company holding nothing.

## Workflow

1. Read the lot: its identifier, the diode type, the process owner,
   production site, construction and process baseline, and refuse one that
   does not declare them.
2. Settle construction first, so a mesa lot is separated out before any
   grant is read.
3. Collect every grant the register holds for the diode type, refusing a
   register that grants the same type twice to one company.
4. Pick the grant made to the company that ran this lot, and where there
   is none, name the companies that do hold one.
5. Read the issuing party, so a supplier agreeing with itself is separated
   from a customer grant.
6. Compare the granted site and process baseline with the lot as built and
   name every attribute the grant does not reach.
7. Walk the handed-out steps against the subcontractors the grant names.
8. Rank the arms into one lot verdict: construction first, then no grant,
   then a grant held elsewhere, then an invalid issuing party, then a
   scope that misses, then an uncovered subcontracted step, then a
   withdrawal.
9. Roll the programme up: group the lots by verdict, name the types
   nobody granted and the companies holding nothing, report the qualified
   share and the arm to close first, and return a verdict that is clean
   only when every lot is qualified.

## Pitfalls

- Looking the grant up by diode type and stopping there. That is the
  lookup the clause exists to prevent, and it returns a valid-looking
  grant for a lot the customer never assessed.
- Treating a completed test programme as qualification. The programme is
  the evidence; the grant is the decision, and a supplier cannot take the
  decision about its own process.
- Accepting a third-party laboratory report as the grant. The laboratory
  states what it measured, which is what the customer reads before
  granting, and substituting one for the other removes the step.
- Merging "no grant anywhere" with "granted to another company". They
  look the same in a boolean and need two different campaigns.
- Reading a mesa lot against a planar grant. The construction question
  comes first, and answering it late produces a scope delta that hides a
  clause-scope finding.
- Ignoring the subcontracted steps. The lot record names the grant holder
  as the builder, so an uncovered step is invisible unless the handed-out
  steps are walked separately.
- Rolling up by diode type. A type qualified on four lots out of five
  reads as qualified, and the fifth lot is the one the review was for.

## Behavior contract (gate 3)

The grant policy validation, the process identity read and scope delta,
the clause-scope construction test, the register lookup with its
per-company grants, the issuing-authority test, the grant state, the
subcontracted step coverage, the ranked lot verdict, the worst-arm
selection and the programme roll-up are exercised by the gate 3 contract
test: scripts/test_e2008_blocking_diode_qualification_authority.py
against scripts/e2008_blocking_diode_qualification_authority_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2008_blocking_diode_qualification_authority.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

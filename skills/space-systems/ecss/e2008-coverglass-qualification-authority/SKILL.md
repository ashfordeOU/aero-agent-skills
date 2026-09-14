---
name: e2008-coverglass-qualification-authority
description: "Use when a coverglass type is about to be supplied as qualified. Determine whether a coverglass type may be supplied at all under ECSS-E-ST-20-08C clause 8.6.1, where the customer grants qualification status and the supplier only produces the evidence for it: find the shipment leaving with no grant on record, refuse a grant the supplier issued about its own product, match the granted scope to the material, coating and thickness actually being shipped, reject a grant dated after the supply it is meant to authorise, retire one already withdrawn or past its validity date, and roll the shipments up into one supply verdict. Trigger: ecss, e-st-20-08c-clause-8-6-1, coverglass-qualification-grant, coverglass-grant-issuing-authority, coverglass-supply-authorisation, coverglass-grant-validity-window, coverglass-qualification-scope-match."
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
  tags: [ecss, e-st-20-08-coverglass-scope, e2008-coverglass-qualification-authority, e-st-20-08c-clause-8-6-1, coverglass-qualification-grant, coverglass-grant-issuing-authority, coverglass-supply-authorisation, coverglass-grant-validity-window, coverglass-qualification-scope-match]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coverglasses -- Qualification Authority (space-systems/ecss/e2008-coverglass-qualification-authority)

Use when the task is clause 8.6.1 of ECSS-E-ST-20-08C: a coverglass type
carries qualification status because the customer granted it, and the
grant has to be in hand before the type is supplied. Finishing a test
programme and being allowed to ship are two different events, separated
by somebody else's signature and by a date. This leaf reads the shipments
and the grant register as two separate things and returns which
shipments may leave.

## Domain quick reference

- The grant is an act by the customer, not a status the supplier reaches.
  A supplier that has run every test has produced a dossier and nothing
  more, and the difference matters the first time somebody downstream
  asks who accepted the argument.
- The clause puts the grant before the supply, which makes the date part
  of the question. A grant signed after the coverglasses shipped records
  a decision taken later than the act it covers, and reading only the
  latest register state hides that completely.
- A grant carries a scope, and for a coverglass that scope is the glass
  itself: material, supplier, coating configuration and thickness class.
  A shipment differing in any of them is outside what was granted however
  recent the grant is.
- A conductive coating is not a finish, it is a different article. A
  grant taken on an uncoated or non-conductive variant does not reach the
  coated one, and the two are easy to confuse on a delivery note.
- Withdrawn and expired are not the same finding. A withdrawn grant says
  the customer changed its mind about the article; an expired one says
  nobody renewed the paperwork, and only the second can be closed by
  asking.
- Two grants for one coverglass type is a register defect, not a choice.
  Picking either one silently is how a shipment gets authorised by the
  grant that happens to sort first.
- The population is shipments, not types. One type can ship five times
  and only the fourth fall outside the validity window, which a
  type-level roll-up never shows.

## Workflow

1. Read the shipment: its identifier, the coverglass type, the supply
   date and the four configuration attributes, and refuse one that does
   not declare them.
2. Look the type up in the grant register, refusing a register that
   holds two grants for the same type rather than picking one.
3. Read the issuing party and decide whether that party may grant at
   all, so a supplier agreeing with itself is separated from a customer
   grant.
4. Build the validity window: the issue date against the supply date,
   the withdrawal state, and the validity end date where one is set,
   refusing a grant that expires before it was issued.
5. Compare the granted scope with the shipped configuration and name
   every attribute the grant does not reach.
6. Rank the arms into one shipment verdict: no grant first, then an
   invalid issuing party, then a scope that misses, then a withdrawal,
   then a grant issued after the shipment, then an expired grant.
7. Roll the programme up: group the shipments by verdict, name the
   coverglass types nobody ever granted, report the authorised share and
   the arm that has to be closed first, and return a verdict that is
   clean only when every shipment is authorised.

## Pitfalls

- Reading the register as it stands today. The question is whether the
  grant was in force on the supply date, and a grant issued last month
  authorises nothing that shipped last year.
- Treating a complete test programme as qualification. The programme is
  the evidence; the grant is the decision, and a supplier cannot take
  the decision about its own product.
- Accepting a third-party laboratory report as the grant. The laboratory
  states what it measured, which is exactly what the customer reads
  before granting, and substituting one for the other removes the step
  the clause is about.
- Matching the scope on type name alone. Two shipments can carry the
  same type designation and differ in coating configuration or thickness
  class, and the designation is the one attribute that never changes when
  the article does.
- Merging withdrawn with expired. One needs a technical answer and the
  other needs a renewal request, and a merged verdict sends the same
  email for both.
- Rolling up by coverglass type. A type that is authorised four times
  out of five reads as authorised, and the one shipment that left
  outside the window is the one the review was for.
- Silently choosing between duplicate grants. The register defect is
  itself the finding, and resolving it by sort order buries it.

## Behavior contract (gate 3)

The authority policy validation, the configuration read and scope delta,
the issuing-authority test, the validity window with its issue date,
withdrawal state and expiry, the register lookup, the ranked shipment
verdict, the worst-arm selection and the programme roll-up are exercised
by the gate 3 contract test:
scripts/test_e2008_coverglass_qualification_authority.py against
scripts/e2008_coverglass_qualification_authority_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_qualification_authority.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

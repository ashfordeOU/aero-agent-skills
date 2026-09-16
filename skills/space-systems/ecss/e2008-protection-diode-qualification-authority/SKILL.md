---
name: e2008-protection-diode-qualification-authority
description: "Use when a protection diode supply is about to leave as qualified. Determine whether protection diodes may be supplied as qualified under ECSS-E-ST-20-08C clause 9.5.1, where the customer grants qualification to the external and integral diodes of one named producer and the supplier only produces the evidence: find the shipment with no grant on record, refuse a grant the supplier issued about its own product, hold an external grant being read onto integral diodes, catch a second source shipping under the first source's grant, reject a grant dated after the supply it authorises, and retire one withdrawn or past its validity date. Trigger: ecss, e-st-20-08c-clause-9-5-1, protection-diode-qualification-grant, protection-diode-grant-issuing-authority, external-and-integral-diode-grant-scope, protection-diode-grant-validity-window, protection-diode-producer-identity-match."
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
  tags: [ecss, e-st-20-08-protection-diode-scope, e2008-protection-diode-qualification-authority, e-st-20-08c-clause-9-5-1, protection-diode-qualification-grant, protection-diode-grant-issuing-authority, external-and-integral-diode-grant-scope, protection-diode-grant-validity-window, protection-diode-producer-identity-match]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Protection Diodes -- Qualification Authority (space-systems/ecss/e2008-protection-diode-qualification-authority)

Use when the task is clause 9.5.1 of ECSS-E-ST-20-08C: protection diodes,
external and integral alike, carry qualification because the customer
granted it to a named producer's parts. Finishing a test programme and
being allowed to ship are two different events, separated by somebody
else's signature, by a producer name and by a date. This leaf reads the
supplies and the grant register as two separate things and returns which
supplies may leave.

## Domain quick reference

- The grant is an act by the customer, not a status the supplier reaches.
  A supplier that has run every test has produced a dossier and nothing
  more, and the difference matters the first time somebody downstream
  asks who accepted the argument.
- The producer is part of the grant, not part of the part number. A
  second source shipping an electrically equivalent diode ships outside
  the grant, and the datasheet equivalence is exactly what makes that easy
  to miss on a delivery note.
- External and integral are different articles, not two mounting options.
  One is a discrete diode placed beside the cell assembly, the other is
  grown into it, and their failure modes, screening and interfaces have
  almost nothing in common. A grant on one does not carry the other.
- The clause puts the grant before the supply, which makes the date part
  of the question. A grant signed after the diodes shipped records a
  decision taken later than the act it covers.
- Withdrawn and expired are not the same finding. A withdrawn grant says
  the customer changed its mind about the article; an expired one says
  nobody renewed the paperwork, and only the second can be closed by
  asking.
- The process baseline belongs in the scope. A diode type can keep its
  designation across a line change, and the designation is the one
  attribute that never moves when the article does.
- Two grants filed under one producer and kind is a register defect, not a
  choice. Picking either one silently is how a shipment gets authorised by
  the grant that happens to sort first.
- The population is supplies, not diode types. One type can ship five
  times and only the fourth fall outside the validity window, which a
  type-level roll-up never shows.

## Workflow

1. Read the supply: its identifier, the supply date, and the producer,
   diode kind, diode type and process baseline, refusing one that does not
   declare them.
2. File the register by producer and diode kind together, and refuse a
   register holding two grants under the same pair rather than picking
   one.
3. Read the issuing party and decide whether that party may grant at all,
   so a supplier or producer agreeing with itself is separated from a
   customer grant and a laboratory report is separated from both.
4. Compare the granted configuration with the supplied one and name every
   attribute the grant does not reach.
5. Build the validity window: the issue date against the supply date, the
   withdrawal state, and the validity end date where one is set, refusing
   a grant that expires before it was issued.
6. Rank the arms into one supply verdict: no grant first, then an
   inadmissible issuing party, then a scope that misses, then a
   withdrawal, then a grant issued after the supply, then an expired one.
7. Roll the programme up: group the supplies by verdict, name the
   producer and kind pairs nobody ever granted, report the authorised
   share and the arm to close first, and return a verdict that is clean
   only when every supply is authorised.

## Pitfalls

- Reading the register as it stands today. The question is whether the
  grant was in force on the supply date, and a grant issued last month
  authorises nothing that shipped last year.
- Treating a complete test programme as qualification. The programme is
  the evidence; the grant is the decision, and a supplier cannot take the
  decision about its own product.
- Filing the register by diode type alone. The type is not the key -- the
  producer and the kind are, and a type-keyed register quietly lets one
  producer's grant authorise another's parts.
- Reading an external grant onto integral diodes because the assembly is
  the same. The assembly is not the article the grant names.
- Accepting a third-party laboratory report as the grant. The laboratory
  states what it measured, which is what the customer reads before
  granting, and substituting one for the other removes the step the
  clause is about.
- Merging withdrawn with expired. One needs a technical answer and the
  other needs a renewal request, and a merged verdict sends the same email
  for both.
- Rolling up by diode type. A type authorised four times out of five reads
  as authorised, and the one supply that left outside the window is the
  one the review was for.

## Behavior contract (gate 3)

The authority policy validation, the diode kind normalisation and register
key, the configuration read and scope delta, the issuing-authority test,
the validity window with its issue date, withdrawal state and expiry, the
register lookup, the ranked supply verdict, the worst-arm selection and
the programme roll-up are exercised by the gate 3 contract test:
scripts/test_e2008_protection_diode_qualification_authority.py against
scripts/e2008_protection_diode_qualification_authority_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_protection_diode_qualification_authority.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

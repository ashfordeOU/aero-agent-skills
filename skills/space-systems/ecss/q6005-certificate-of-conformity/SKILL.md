---
name: q6005-certificate-of-conformity
description: "Validate the signed declaration issued with a delivered lot of hybrid microcircuits that the units match the ordered specification and the approved build configuration, under ECSS-Q-ST-60-05 clause 13.2.3. Use when a certificate is drafted or received: compare the ordered and delivered configurations attribute by attribute, match every difference to an approved and referenced waiver, test whether the named signatory may release product, reconcile the declared quantity and serials against the shipment, grade the certificate fields and return the completeness index with one verdict. Trigger: ecss, q-st-60-05, certificate-of-conformity, hybrid-coc-configuration-match, hybrid-coc-waiver-coverage, hybrid-coc-signatory-authority, hybrid-coc-quantity-declaration, hybrid-coc-completeness-index."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-certificate-of-conformity, hybrid-coc-configuration-match, hybrid-coc-waiver-coverage, hybrid-coc-signatory-authority, hybrid-coc-quantity-declaration, hybrid-coc-completeness-index]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Certificate of Conformity (space-systems/ecss/q6005-certificate-of-conformity)

Use when the task is clause 13.2.3 of ECSS-Q-ST-60-05: the certificate issued
with a delivered hybrid lot — a named, authorised person declaring that the
units match what was ordered, with every departure from it referenced.

## Domain quick reference

- A certificate is a signature on a comparison. The ordered configuration and
  the delivered configuration are compared attribute by attribute — part
  number, specification issue, build standard issue, screening level, lead
  finish — and each attribute that differs has to be answered.
- A waiver covers one attribute, not the certificate. A waiver raised against
  the screening level does not excuse a different drawing issue, and matching
  the count of waivers to the count of differences proves nothing.
- A waiver that exists but was never approved covers nothing. Neither does an
  approved waiver the certificate never points at, because the next reader
  has no way to find it.
- Authority is a property of the signatory, not of the signature. A legible
  name in a role that cannot release product is an unsigned certificate with
  extra ink, and an unknown role is refused rather than assumed to be fine.
- The declared quantity, the serials printed on the certificate and the units
  in the shipment are three lists. A unit the certificate does not cover has
  been delivered without a declaration; a unit the certificate covers and
  nobody shipped means two lists were kept.
- The completeness index measures what the form carries, never whether the
  statement on it is true. An unwaived difference refuses the certificate at
  any index, including a perfect one.
- The history the package carries, its format and retention rules, the cover
  sheets and the packing are graded against their own clauses.

## Workflow

1. Name the lot and collect both configurations, ordered and delivered,
   across the full set of compared attributes.
2. Difference them attribute by attribute and keep the list in the published
   order.
3. Collect the deviations and waivers, and mark each one approved or not, and
   referenced on the certificate or not.
4. Match each difference to a waiver that is both approved and referenced;
   anything left is an uncovered difference.
5. Report the waivers that fail the other way too — unapproved, approved but
   unreferenced, and raised against an attribute that in fact matches.
6. Test the signatory: named, in a role that may release product, and having
   actually signed.
7. Reconcile the declared quantity against the certificate serials, and the
   certificate serials against the shipment, in both directions.
8. Grade the certificate fields against the full published set, take weighted
   credit over total weight as the completeness index, and name the verdict —
   incomplete while a mandatory field is absent, refused on an uncovered
   difference, an unapproved waiver, a signatory finding, an unreconciled
   quantity, an illegible mandatory field or a low index, accepted with open
   actions while findings remain, accepted only when none do.

## Pitfalls

- Counting waivers instead of mapping them. Three differences and three
  waivers is a coincidence until each waiver is read against the attribute it
  names.
- Accepting an approved waiver that the certificate does not reference. The
  approval is real and invisible; every later reader sees a unit that departs
  from the order with nothing to explain it.
- Reading the signature and not the role. The most common defective
  certificate is fully filled in, cleanly signed, and signed by somebody with
  no authority to release the product.
- Reconciling the quantity against one list. The declared number, the printed
  serials and the shipped units are three statements, and the interesting
  failure is always between two of them nobody compared.
- Letting a high completeness index carry the declaration. The index says the
  form is filled in; an unwaived difference means the sentence on the form is
  false, and no amount of form-filling repairs that.
- Raising a waiver defensively against an attribute that matches. It suggests
  the comparison was never actually done, and it makes the real waivers
  harder to find.

## Behavior contract (gate 3)

The configuration comparison, the waiver coverage in all four directions, the
signatory authority checks, the three-way quantity reconciliation, the field
grading, the certificate-completeness index and the certificate verdict are
exercised by the gate 3 contract test:
scripts/test_q6005_certificate_of_conformity.py against
scripts/q6005_certificate_of_conformity_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6005_certificate_of_conformity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

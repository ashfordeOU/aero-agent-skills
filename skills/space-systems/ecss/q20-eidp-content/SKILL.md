---
name: q20-eidp-content
description: "Build and grade the end item data package of ECSS-Q-ST-20C clause 5.7.2 and its Annex B document requirements description: resolve the record list the product type actually owes rather than reusing a neighbouring delivery's index, mark each required record present and approved at a stated revision, validly declared not applicable with a justification and an approver, or missing, refuse a not-applicable declaration on a core conformity record, and confirm the certificate of conformity points at the as-built configuration list revision the package carries. Use when a delivery package is compiled or reviewed before handover. Trigger: ecss, q-st-20c-clause-5-7-2, end-item-data-package-content, annex-b-drd-document-list, certificate-of-conformity-reference, as-built-configuration-list-revision, eidp-not-applicable-justification."
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
  tags: [ecss, q-st-20-quality-assurance-scope, q20-eidp-content, end-item-data-package-content, annex-b-drd-document-list, certificate-of-conformity-reference, as-built-configuration-list-revision, eidp-not-applicable-justification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Quality Assurance -- End Item Data Package Content (space-systems/ecss/q20-eidp-content)

Use when the task is the end item data package of ECSS-Q-ST-20C clause
5.7.2 with its Annex B document requirements description: a product is
being handed over and the question is whether the records travelling
with it actually prove its conformity, for the kind of product it is.

## Domain quick reference

- The content list is per product type. Every delivery carries the same
  spine -- the package index, the certificate of conformity, the as-built
  configuration list, the nonconformance summary, the deviation and
  waiver list, the list of test reports and the open work list -- and
  then each type adds its own. Equipment owes mass properties and
  limited-life items; a system owes interface verification and the
  verification control document status; software owes its version
  description, its problem report list and its release note, and owes no
  mass properties at all. Copying a neighbouring delivery's index is the
  usual way a package ends up missing a record nobody notices.
- A record counts when it is present, at a stated revision, and
  approved. An unapproved record in the index is the same defect as an
  absent one, because an unapproved document proves nothing.
- Not applicable is a legitimate answer for some records and never for
  others. Where it is admissible it carries a justification and an
  approver, which is what makes it reviewable. On the core conformity
  records -- the index, the certificate, the as-built list -- it is
  refused outright, because without them there is no package.
- A record nobody asked for is not a defect. It is reported as an extra
  because it usually signals an index carried over from another product,
  which is worth knowing while reviewing the rest.
- The certificate of conformity and the as-built configuration list have
  to agree. A certificate citing a superseded as-built revision, or
  citing none at all, certifies a configuration the package does not
  contain, and that is the defect the whole package exists to prevent.

## Workflow

1. Resolve the required record list from the product type, refusing a
   type outside the recognised set rather than falling back to a generic
   list.
2. Normalise the submitted package: one entry per record, a revision on
   anything not declared not applicable, and a references map where a
   record points at another.
3. Decide each required record: present and approved, validly not
   applicable, unapproved, or missing.
4. Apply the not-applicable rules: refused on a core record, and
   otherwise only with both a justification and an approver.
5. List the extras separately from the findings, so they inform the
   review without failing the package.
6. Cross-check the certificate of conformity against the as-built
   configuration list revision in the package, then report the
   completeness fraction and the verdict.

## Pitfalls

- Grading a package against the common list alone. The type-specific
  records are where the gaps are, and a package can look complete while
  missing every record its type adds.
- Counting an unapproved record as delivered. The revision and the
  approval are what make the record evidence; an index entry is not.
- Accepting a not-applicable line because it is plausible. Without a
  justification and an approver it cannot be reviewed, and on a core
  record no justification is sufficient.
- Treating extras as findings. They are a signal about where the index
  came from, not a reason to hold the delivery.
- Checking the certificate exists and stopping there. Its value is the
  configuration it certifies, so the revision it cites is compared with
  the as-built list actually in the package.

## Behavior contract (gate 3)

The per-type record list resolution, the present-and-approved rule, the
not-applicable admissibility rules including the core-record refusal,
the extras listing, the completeness fraction and the certificate to
as-built revision cross-check are exercised by the gate 3 contract test:
scripts/test_q20_eidp_content.py against
scripts/q20_eidp_content_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_eidp_content.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

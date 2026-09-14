---
name: q6013-class-1-manufacturer-data-deliveries
description: "Assess whether the conformance certificates and production data delivered with a highest-assurance commercial EEE lot under ECSS-Q-ST-60-13C clause 4.3.11 actually cover that lot: match every record to the lot code and the purchased date-code window, keep an absent record apart from one standing on an approved deviation, grade an attributes-only summary against the measured values a lot owes, and return one delivery verdict with ranked findings. Use when a lot data package, certificate of conformance or production data delivery is reviewed at receiving inspection. Trigger: ecss, q-st-60-13c, class-1-manufacturer-data-delivery, lot-conformance-certificate, lot-date-code-coverage, production-variables-data, lot-data-package-verdict, receiving-inspection-data-review."
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
  tags: [ecss, q-st-60-eee-component-scope, q-st-60-13c, q6013-class-1-manufacturer-data-deliveries, class-1-manufacturer-data-delivery, lot-conformance-certificate, lot-date-code-coverage, production-variables-data, lot-data-package-verdict, receiving-inspection-data-review]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Class 1 — Manufacturer Data Deliveries (space-systems/ecss/q6013-class-1-manufacturer-data-deliveries)

Use when the task is clause 4.3.11 of ECSS-Q-ST-60-13C: the conformance
certificates and the production data a manufacturer delivers together with a
lot procured at the highest assurance level. This leaf grades a delivered data
package on whether the records it contains actually belong to the lot in the
crate, at the depth a class 1 procurement asks for.

## Domain quick reference

- A commercial part carries no space-grade traceability by default. What makes
  a class 1 lot usable is not that the manufacturer holds the data, it is that
  the data travels with the lot and names it. A certificate that names a
  different lot code proves the manufacturer's process, not this delivery.
- Two kinds of record are delivered and they answer different questions. A
  conformance certificate is a statement: this lot was built and tested to the
  agreed specification. Production data is measurement: here are the values.
  A certificate cannot stand in for the data, because a statement carries no
  distribution and a drifting lot inside limits looks identical to a centred
  one.
- Attributes data (how many passed) and variables data (what each one
  measured) are not interchangeable at class 1. The pass count hides the
  margin, and margin is the only early warning of a process that has moved
  since the qualification lot.
- Coverage is a fraction, not a yes. A data record that reaches part of the
  delivered quantity leaves the remainder undocumented; the question is what
  fraction of the lot the record reaches, against what the procurement
  specification demanded.
- Absent, waived and not-applicable are three different states and collapsing
  them loses the audit trail. A record standing on an approved deviation is a
  known, dispositioned gap. A record silently marked not-applicable is an
  undispositioned one wearing the same colour.
- A date code outside the purchased window is not automatically a reject: it
  is a mixed-lot signal that has to be raised, because shelf life, moisture
  exposure and the applicable process change history are all counted from it.

## Workflow

1. Establish the lot identity the package is offered against: the
   manufacturer lot code, the delivered quantity and the purchased date-code
   window. Normalise the lot code so two written forms of one code compare
   equal instead of reading as a mismatch.
2. Validate every delivered record: kind, lot code, date code, the number of
   units it reaches, whether it is signed, and whether it carries variables or
   attributes data. A malformed record is an input error, not a silent skip.
3. Match each record's lot code against the delivered lot. A mismatch is the
   most serious finding available, because it detaches the whole record from
   the hardware.
4. Compute the fraction of the lot each record reaches and compare it with the
   coverage the procurement specification requires, absorbing floating-point
   representation error at the boundary with a named tolerance rather than by
   lowering the required coverage.
5. Map the delivered kinds onto the kinds a class 1 lot owes. Report an absent
   kind, a waived kind and a kind marked not-applicable separately.
6. Rank the findings — lot mismatch and absence first, unsigned certificates
   and attributes-only data next, date-code and declaration gaps last — and
   return one verdict: accepted, accepted-with-actions, or rejected.
7. Carry the ranked findings into the receiving inspection record so the
   dispositioned gaps stay visible to the later lot acceptance review.

## Pitfalls

- Reading a thick data package as a complete one. Depth is not coverage: five
  records that all reach a quarter of the lot leave three quarters of the
  delivery undocumented, and the package still looks substantial.
- Accepting a certificate in place of the production data. The certificate
  answers whether the manufacturer asserts conformance; the data answers where
  inside the limits the lot actually sits, and only the second one detects
  drift before it becomes a failure in flight.
- Treating a not-applicable mark as equivalent to an approved waiver. A waiver
  names an authority and a reference; a not-applicable mark names nobody, and
  at class 1 the kinds in the required set are owed.
- Comparing lot codes as raw strings. Punctuation and case differ between a
  label, a certificate and an order line for the same lot, so an unnormalised
  comparison manufactures mismatches and hides the real ones in the noise.
- Widening the required coverage to clear an exact-equality case. An equality
  at the limit is a representation question, handled by the tolerance inside
  the comparison; the required value stays as procured.
- Discarding a date-code excursion because the electrical data passed. The
  date code drives shelf life, moisture exposure and which process change
  history applies, so an out-of-window record is a finding in its own right.

## Behavior contract (gate 3)

The lot-code normalisation, date-code window test, record validation,
coverage fraction, per-record findings, required-kind state mapping and the
delivery verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_manufacturer_data_deliveries.py against
scripts/q6013_class_1_manufacturer_data_deliveries_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_manufacturer_data_deliveries.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

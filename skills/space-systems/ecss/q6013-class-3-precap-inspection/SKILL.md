---
name: q6013-class-3-precap-inspection
description: "Use when a class 3 pre-seal record has to become a seal-release verdict. Assess whether a pre-seal inspection of a commercial EEE lot was owed and discharged at the lowest assurance class of ECSS-Q-ST-60-13C clause 6.3.4: answer not-invoked where no procurement document called the inspection up, answer not-applicable where the package has no cavity to open, void an inspection dated on or after the seal instead of booking it late, size the sample against the lot floor, admit a remote photographic or manufacturer-report route only where it names an identified device set and a report issue, accept critical internal findings on zero, and hold the lot in front of the seal naming every failing check. Trigger: ecss, q-st-60-13c-clause-6-3-4, class-three-pre-seal-inspection, precap-invocation-source, precap-remote-evidence-route, precap-sample-size-floor, critical-internal-finding-accept-on-zero."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-precap-inspection, class-three-pre-seal-inspection, precap-invocation-source, precap-remote-evidence-route, precap-sample-size-floor, critical-internal-finding-accept-on-zero]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Pre-Cap Inspection (space-systems/ecss/q6013-class-3-precap-inspection)

Use when the task is the clause 6.3.4 pre-seal inspection question of
ECSS-Q-ST-60-13C at the lowest assurance class: a lot of a commercial part is
sitting at the manufacturer with its lids off, and the question is first
whether anybody was owed a look inside, and only then whether the look that
was taken lets the seal operation proceed.

## Domain quick reference

- At this class the inspection is not a standing duty. It exists where the
  procurement specification, the component control plan or a written customer
  request called it up, and nowhere else. A lot with no invocation is answered
  not-invoked, which is a third disposition beside waived and not-applicable:
  a waiver needs an approval behind it, a non-applicability needs only the
  package family, and a non-invocation needs neither because nothing was ever
  owed.
- The inspection still only exists for a package with a cavity. A solid
  encapsulated device is never opened and never sealed, so an invocation
  against that family has nothing to look into.
- It happens in front of the seal, and the seal day is already too late. Once
  the lid is on, an internal defect is invisible and unrecoverable: no later
  electrical test sees a bond wire that is still touching or a particle that
  has not yet moved. An inspection dated on or after the seal is void, not
  late, and no paperwork repairs it.
- This class does not require anybody to travel, which is the concession that
  makes it workable on a commercial part. A remote photographic review or the
  manufacturer's own report may carry the inspection -- but the concession is
  on the attendance, not on the auditability. The photographic route has to
  identify which device each image came from and cite a report issue; the
  report-only route has to cite the manufacturer's inspection procedure as
  well, or there is nothing a later reader can reopen.
- The sample is sized from the lot, not chosen. A share of the lot rounded up,
  lifted to a floor for a small lot and capped at the lot itself, so a lot of
  four hundred does not get away with the three devices a lot of fifty owes.
- The findings are graded and the grades are not interchangeable. A critical
  internal finding -- the bond, the die attach, the loose material that moves
  under launch vibration -- accepts on zero, and that zero is not traded
  upward against a generous minor count.

## Workflow

1. Resolve the invocation first and return not-invoked where no procurement
   document called the inspection up, before reading any evidence at all.
2. Resolve the package family next and return not-applicable where it has no
   cavity, keeping that answer separate from a waiver.
3. Parse the inspection and seal days, refusing a malformed or impossible date
   rather than guessing at its intent.
4. Void the inspection where it is dated on or after the seal, and say so as a
   void record rather than as a late one.
5. Size the required sample from the lot with integer arithmetic so the
   boundary is exact, and compare the devices actually opened against it.
6. Read how the inspection was carried out and admit a remote route only
   against the references that make it auditable, naming what is missing.
7. Grade the sample, hold critical findings to zero, and compare majors and
   minors with their accept numbers.
8. Release for seal only when the timing, sample, evidence route and every
   finding grade hold; otherwise hold the lot in front of the seal and report
   every failing check, not the first one found.

## Pitfalls

- Reading an uninvoked inspection as a waived one. A waiver needs an approval
  nobody granted here; the duty simply never arose at this class, and writing
  it up as a waiver invents a signature.
- Recording a post-seal inspection as a late one. The evidence it would have
  produced no longer exists, so the record is void and the lot has no pre-seal
  inspection at all.
- Taking the remote routes as a relaxation of the record. The concession is
  that nobody has to fly; the images still have to say which device they show
  and the report still has to have an issue.
- Sizing the sample by habit. Three devices is the floor for a small lot, not
  the answer for every lot, and a large lot that inspects three has inspected
  a rounding error.
- Trading a critical finding against the major and minor counts. The critical
  accept number is zero because the failure mode is loss of the unit in
  flight, and no clean minor count offsets it.
- Reporting only the first failing check. A lot held for a short sample may
  also be held for its findings, and fixing one sends it straight back.

## Behavior contract (gate 3)

The invocation resolution, package applicability, day parsing, seal-day void
boundary, integer sample sizing, remote evidence-route admissibility, graded
finding gate and the release-or-hold disposition are exercised by the gate 3
contract test: scripts/test_q6013_class_3_precap_inspection.py against
scripts/q6013_class_3_precap_inspection_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_3_precap_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

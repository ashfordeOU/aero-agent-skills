---
name: e2006-mixed-material-assembly-evaluation
description: "Use when evaluate a spacecraft-external assembly that combines dissimilar ungrounded materials against ECSS-E-ST-20-06C clause 6.3.3.4: categorize every constituent as grounded-conductor, floating-conductor or exposed-dielectric from its surface-resistivity and bonding state, decide whether the stack qualifies as a mixed-material-assembly, quantify the resistivity decade-span between exposed ungrounded constituents that drives differential-charging across the interface, and confirm the verification evidence was raised at complete-unit level, an assembly-level electrostatic assessment or an assembly-level qualification run on a representative specimen covering every constituent, instead of stacking per-constituent coupon results. Trigger: ecss, e-st-20-electrical-scope, mixed-material-assembly, dissimilar-ungrounded-materials, floating-conductor, exposed-dielectric, differential-charging, complete-unit-verification, resistivity-decade-span."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-mixed-material-assembly-evaluation, mixed-material-assembly, dissimilar-ungrounded-materials, floating-conductor, exposed-dielectric, differential-charging, complete-unit-verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrostatic Design — Mixed-Material Assembly Evaluation (space-systems/ecss/e2006-mixed-material-assembly-evaluation)

Use when the task is the clause 6.3.3.4 obligation of ECSS-E-ST-20-06C: an
externally exposed assembly that brings dissimilar ungrounded materials
together is evaluated as one complete unit, because the electrostatic
behaviour of the joined stack is not recoverable from evidence gathered on
its constituents one at a time.

## Domain quick reference

- A constituent is categorized from two properties only: its surface
  resistivity and whether it is bonded to structure. At or below the
  conductive ceiling (1e5 ohm per square in the module default) a bonded
  constituent is a grounded-conductor and an unbonded one is a
  floating-conductor; above the ceiling the constituent is an
  exposed-dielectric whatever its backing, because the exposed face itself
  has no return path.
- Dissimilarity is what triggers the clause, not material count. Two
  ungrounded constituents are dissimilar when they fall in different
  categories, or when their surface resistivities are separated by at least
  one decade. Two identical unbonded films side by side are not a
  mixed-material-assembly; an unbonded metallic shim next to a high-
  resistivity film is.
- The decade span between exposed ungrounded constituents is the
  differential-charging driver: the wider the separation, the larger the
  potential difference the joint can sustain before it relaxes, and the less
  the constituents behave as they did on their own coupons. Beyond the
  review threshold (four decades by default) an assembly-level qualification
  run is required and an assembly-level assessment alone is not sufficient.
- Only externally exposed constituents pair. A constituent with no exposed
  area faces no ambient flux on the outer surface and is carried in the
  inventory for completeness, not in the pairing.
- Complete-unit evidence means all four of: coverage recorded at
  complete-unit level, a specimen representative of the delivered hardware,
  an environment envelope that bounds the worst case, and every constituent
  named in the evidence record. A gap in any one is an open finding.

## Workflow

1. Inventory the assembly and categorize each constituent as
   grounded-conductor, floating-conductor or exposed-dielectric. Reject a
   constituent with a missing name, a non-positive resistivity, a
   non-boolean bonding flag or a negative exposed area before it enters the
   evaluation.
2. Select the ungrounded constituents with a non-zero exposed area and form
   every pair among them. Compute each pair resistivity separation in
   decades and mark the pair dissimilar when the categories differ or the
   separation reaches one decade.
3. Decide the mixed-material verdict: the assembly is a
   mixed-material-assembly when at least one dissimilar pair exists.
   A mixed-material-assembly demands complete-unit evidence; anything else
   may be closed at constituent level.
4. Take the widest pair as the differential-charging driver and compare its
   span with the review threshold. Treat a span that sits exactly on the
   threshold as within it: the span is a difference of logarithms and can
   land a few units in the last place above the limit for a pair that is
   physically on the line.
5. Validate the verification-evidence record: known method, known coverage,
   explicit representativeness and envelope flags, and a list of covered
   constituent names. Reject an unknown method or coverage rather than
   downgrading it silently.
6. Raise a finding for each shortfall: coverage below complete-unit, an
   unrepresentative specimen, an envelope that does not bound the worst
   case, any constituent absent from the record, and a span past the review
   threshold closed by assessment alone. The assembly is compliant only when
   the finding list is empty.

## Pitfalls

- Reading a pile of per-constituent coupon results as assembly evidence.
  Each coupon was charged in isolation, with no adjacent dissimilar surface
  to charge against, so the coupon set can be entirely green while the
  joined unit sustains a large potential difference across the interface.
- Counting materials instead of testing dissimilarity. Three ungrounded
  films of the same resistivity are one electrostatic population, not a
  mixed-material-assembly; two constituents straddling the conductive
  ceiling by a few percent are a mixed-material-assembly even though their
  decade span is a fraction of a decade.
- Pairing constituents that never see the external environment. An internal
  shim with no exposed area cannot charge differentially on the outer face,
  and pairing it inflates the driver span and forces an unnecessary
  assembly-level qualification run.
- Widening the review threshold to absorb a boundary case. A pair sitting
  exactly on the limit is compliant; the fix belongs in the comparison, as a
  named tolerance on the decade span, never in the engineering limit itself.
- Treating an assembly-level assessment as interchangeable with an
  assembly-level qualification run once the span is past the review
  threshold. Beyond that separation the stack behaviour is what has to be
  observed, not predicted.

## Behavior contract (gate 3)

The constituent-categorization, dissimilarity, decade-span and
complete-unit-evidence logic is exercised by the gate 3 contract test:
scripts/test_e2006_mixed_material_assembly_evaluation.py against
scripts/e2006_mixed_material_assembly_evaluation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_mixed_material_assembly_evaluation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

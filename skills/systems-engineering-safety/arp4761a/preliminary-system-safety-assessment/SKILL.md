---
name: preliminary-system-safety-assessment
description: "Use when conducting the preliminary system safety assessment (PSSA) per ARP4761A: derive safety requirements from FHA outcomes, allocate function and item development assurance levels (FDAL/IDAL) to the proposed system architecture, and apportion the quantitative safety target for each failure condition across the contributing channels and functions. The PSSA uses fault tree, failure mode, and common cause analysis style arguments to show that the architecture can meet the quantitative safety targets before implementation, then hands the allocated safety requirements and derived requirements to the system safety assessment (SSA) for verification against the implemented system. Trigger: preliminary system safety assessment, PSSA, ARP4761A, safety target allocation, FDAL, IDAL, development assurance level, quantitative safety requirement, redundant channel allocation."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [arp4761a, pssa, safety-target-allocation, fdal, idal, development-assurance, fta, quantitative-safety-requirement, redundant-channels]
  version: 0.1.0
  author: AeroSkills
---

# Preliminary System Safety Assessment (systems-engineering-safety/arp4761a/preliminary-system-safety-assessment)

Use when the task is the preliminary system safety assessment
(PSSA) per ARP4761A: turning functional hazard assessment (FHA)
outcomes into allocated safety requirements for the proposed
system architecture, assigning function and item development
assurance levels (FDAL/IDAL), and showing by analysis that the
architecture can meet the quantitative safety targets. This leaf
is the middle step of the FHA-PSSA-SSA sequence; it is distinct
from skills/systems-engineering-safety/arp4761a/functional-hazard-assessment
(which identifies and categorizes the failure conditions upstream)
and from skills/systems-engineering-safety/arp4761a/safety-assessment
(which is the process umbrella that scopes the whole assessment
plan).

## Domain quick reference

- PSSA purpose: examine the proposed architecture against the
  safety requirements produced by the FHA and demonstrate, by
  analysis, that the architecture can meet them before the design
  is implemented.
- Inputs: FHA outcomes (failure conditions with severity
  categories, qualitative requirements, and quantitative targets
  such as Catastrophic at no more than 1e-9 per flight hour), the
  proposed architecture, and item failure rates.
- Outputs: quantitative safety targets allocated to items,
  channels, and functions; FDAL and IDAL assignments; derived
  requirements that constrain the design; and the analytical
  evidence (FTA, FMA, CCA-style) that feeds the system safety
  assessment (SSA).
- FDAL: function development assurance level per ARP4754A derived
  from severity: A = Catastrophic, B = Hazardous, C = Major,
  D = Minor, E = No safety effect. IDAL: item development
  assurance level, generally equal to the FDAL of the function the
  item implements; it may be one level lower when the item failure
  cannot by itself cause the failure condition (for example it is
  covered by architecture redundancy or detection).
- Quantitative allocation: the top-level failure condition target
  is apportioned across the contributing architecture. Independent
  contributors that combine by OR (any contributor failure causes
  the condition) share the target by sum; redundant channels that
  must all fail combine by AND and share the target by product.
  Equal allocation is the simplest scheme: target / n for OR
  gates, target ** (1 / n) for AND gates.
- Analysis techniques: FTA structures the failure logic, FMA/FMEA
  enumerates item failure modes, and common cause analysis
  (zonal ZSA, particular risk PRA, common mode CMA) checks that
  the allocation is not defeated by shared causes; Markov analysis
  covers time-dependent and dependent failure behavior.
- The PSSA is performed at the proposed-architecture stage; the
  SSA later confirms that the implemented system meets the
  allocated requirements.
- ARP4761A and ARP4754A are SAE publications; name and paraphrase
  only, per standards-map.yaml and research/briefs/06-legal-export-control.md.

## Workflow

1. Collect the FHA outcomes for each failure condition: name,
   severity category, and the quantitative safety target (for
   example a Catastrophic condition at 1e-9 per flight hour).
2. Map each severity to the function development assurance level
   with dal_for_severity; decide the item level with
   idal_for_fdal where a one-level reduction may be justified.
3. Structure the architecture logic for each condition: OR
   (independent contributors sum) or AND (redundant channels
   product).
4. Allocate the target across the contributors with
   allocate_safety_target to get the per-channel budget.
5. Validate the realized architecture with
   channel_allocation_check against the actual channel failure
   rates; confirm the margin and the meets flag.
6. Assemble the assessment with pssa_summary and draft the
   allocated safety requirement text with
   safety_requirement_text.
7. Confirm the deterministic behavior with the contract test
   scripts/test_preliminary_system_safety_assessment.py.

## Allocation model

For a failure condition with target T and n independent
contributors:

- OR gate (any contributor failure causes the condition): the
  contributors share T by sum, so the equal allocation budget is
  T / n and the architecture total is the sum of the realized
  channel rates.
- AND gate (all n channels must fail): the contributors share T by
  product, so the equal allocation budget is T ** (1 / n) and the
  architecture total is the product of the realized channel rates.

The equal allocation scheme treats every contributor the same;
where measured rates differ, the realized check replaces budgets
with the actual channel rates and reports the margin
(target / total). A margin above 1.0 means the architecture has
slack; a margin at or below 1.0 means the allocation is not met
and the architecture or the requirement must be revisited.

For AND logic the target must be a probability below 1.0; a target
at or above 1.0 cannot be apportioned into per-channel
probabilities and is rejected as unallocatable.

## Worked example

A Catastrophic failure condition "loss of both primary hydraulic
power channels" carries a quantitative safety target of 1e-9 per
flight hour. The proposed architecture uses two independent
redundant channels that must both fail for the condition to occur
(AND gate).

- dal_for_severity("catastrophic") returns FDAL A; the item
  development assurance level is also A, and
  idal_for_fdal("A", reduction_allowed=True) shows the one-level
  reduction to B is available when the item failure alone cannot
  cause the condition.
- allocate_safety_target(1e-9, 2, "and") gives each channel a
  budget of sqrt(1e-9), about 3.16e-5 per flight hour; the product
  of the two budgets round-trips to 1e-9.
- channel_allocation_check([1e-5, 2e-5], 1e-9, "and") returns a
  total of 2e-10, a margin of 5.0, and meets True: the
  architecture holds the Catastrophic target with a factor of five
  to spare.
- safety_requirement_text writes the allocated requirement, for
  example "the loss of both primary hydraulic power channels
  condition shall occur at no more than 1e-9 per flight hour,
  allocated as 3.16e-5 per channel across 2 redundant channels
  (AND)".

If instead the two channels were independent contributors that
each alone cause the condition (OR gate), the budget would be
5e-10 per channel and the realized check would use the sum of the
two rates.

## Related leaves

- functional-hazard-assessment: identifies and categorizes the
  failure conditions and sets the targets the PSSA allocates.
- safety-assessment: the process umbrella that scopes the
  FHA-PSSA-SSA sequence and the analysis set.
- failure-rate-estimation: supplies the item and channel failure
  rates used in channel_allocation_check.
- fta-fmea: builds the fault tree and failure mode analyses that
  justify the gate structure of each allocation.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_preliminary_system_safety_assessment.py

The test covers severity-to-FDAL mapping and IDAL reduction
boundaries, OR and AND target allocation round-trips, the
unallocatable target rejection (AND with a target at or above 1.0),
realized channel checks with margin, the PSSA summary assembly,
and the safety requirement text.

## Compliance

- Standards referenced, not reproduced: ARP4761A and ARP4754A text
  is proprietary (SAE); summary and paraphrase only, resolved
  reference-only in standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

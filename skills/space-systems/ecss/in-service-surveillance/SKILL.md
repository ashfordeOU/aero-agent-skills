---
name: in-service-surveillance
description: "Use when evaluate the in-service surveillance programme for a spacecraft or launcher structural assembly under ECSS-E-ST-32C section 4.8: identify items requiring periodic inspection, assign inspection type (visual, NDT, dimensional) and interval based on structural criticality and consumed fatigue fraction, assess detected damage against allowable damage limits, determine residual strength when damage exceeds the allowable, and decide whether to accept, accept under continued-flight rationale, repair, or replace the affected component. Flag items with missing residual strength analysis before continued operation. Trigger: ecss, e-st-32-structures-scope, in-service-surveillance, inspection, damage-evaluation, maintenance, repair, structural-health, fatigue-fraction, continued-flight."
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
  tags: [ecss, e-st-32-structures-scope, in-service-surveillance, inspection, damage-evaluation, maintenance, repair, structural-health, fatigue-fraction, continued-flight]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — In-Service Surveillance (space-systems/ecss/in-service-surveillance)

Use when the task is the in-service surveillance assessment of a spacecraft or
launcher structural assembly under ECSS-E-ST-32C section 4.8 — planning
periodic inspections, evaluating detected damage, and deciding on maintenance
or repair actions to maintain structural integrity throughout the service life.

## Domain quick reference

- Section 4.8 requires the programme to cover all phases where structural
  degradation can occur: ground handling, launch, and on-orbit or in-service
  operation. Items are grouped by structural criticality (fracture-critical,
  significant, or standard consequence) which drives inspection frequency.
- Inspection types are visual (surface condition, cracking, disbond), NDT
  (ultrasonic, radiographic, eddy-current — detects sub-surface flaws), and
  dimensional (checks geometric tolerances and deformation against limits).
  Each item carries exactly one primary inspection type; the type is set when
  the item enters the surveillance programme.
- Inspection interval is a function of the base interval for the item class
  reduced by a criticality factor, and further halved when the consumed fatigue
  fraction exceeds a high-fatigue threshold. This prevents an item approaching
  end of fatigue life from coasting to its nominal inspection point without
  an intermediate check.
- Damage evaluation follows a three-tier comparison against the allowable
  damage limit (ADL) set at design: damage at or below the ADL is accepted and
  documented; damage between the ADL and an extended limit requires a residual
  strength analysis before continued operation; damage beyond the extended
  limit requires repair or replacement. An item in the middle tier that lacks
  a residual strength analysis is flagged — continued operation is not
  permitted until the analysis is provided.
- Residual strength analysis must demonstrate that the damaged structure
  retains the required ultimate load capacity for the remaining service
  interval. The analysis references the fracture control plan and fatigue
  analysis for the item's current life consumption.

## Workflow

1. Inventory all structural items and assign each a criticality level:
   fracture-critical (loss of mission or vehicle on failure), significant
   (mission-capability degradation), or standard (limited consequence). Reject
   any item with an unrecognised criticality before it enters the programme.
2. For each item, assign inspection type (visual, NDT, or dimensional) and
   compute the inspection interval: start from the item's class base interval,
   apply the criticality factor (0.5 × for fracture-critical, 0.75 × for
   significant, 1.0 × for standard), then halve the result if the item's
   consumed fatigue fraction exceeds the high-fatigue threshold (0.8). Record
   whether the interval was reduced due to high fatigue.
3. At each inspection event, record all detected damage with type (crack, dent,
   corrosion, delamination, impact, scratch), measured size, and whether a
   residual strength analysis exists for that damage state.
4. Evaluate each damage report against the allowable damage limit:
   - Damage ≤ ADL: accept; document and monitor at next scheduled inspection.
   - ADL < damage ≤ 2 × ADL with residual strength analysis: accept under
     continued-flight rationale; record the analysis reference.
   - ADL < damage ≤ 2 × ADL without residual strength analysis: flag; do not
     permit continued operation until the analysis is completed.
   - Damage > 2 × ADL: repair if a qualified repair scheme exists; otherwise
     replace the component.
5. Aggregate all inspection schedules and damage dispositions into a
   surveillance result. The assessment is compliant only when no damage
   disposition remains flagged, unrepaired, or unreplaced, and no item carries
   invalid data.
6. Document findings and reduced-interval notifications in the surveillance
   report; route flagged items and repair/replace decisions to the responsible
   structural authority.

## Pitfalls

- Applying the base interval directly to fracture-critical items without the
  criticality factor — this understates inspection frequency for the highest-risk
  items and allows damage to grow undetected between inspections.
- Treating a missing residual strength analysis as a pass in the middle damage
  tier — the absence of the analysis is itself a blocking finding, not evidence
  that the structure is adequate.
- Conflating the allowable damage limit with the extended damage limit: only
  damage strictly within the ADL is accepted without further analysis. The
  extended region (ADL to 2 × ADL) always requires residual strength
  verification.
- Omitting the fatigue-fraction check on inspection interval: an item that has
  consumed more than 80 % of its fatigue allowable is more susceptible to
  crack initiation and must be inspected on a shortened cycle, not the nominal
  one.
- Accepting a damage report for an item not in the surveillance inventory —
  a damage report with no matching inventory item cannot be evaluated and must
  be flagged as an unresolved finding.

## Behavior contract (gate 3)

The inspection-interval, damage-evaluation, and full-surveillance-compliance
logic is exercised by the gate 3 contract test:
scripts/test_in_service_surveillance.py against
scripts/in_service_surveillance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_in_service_surveillance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
- Anchor clause: ECSS-E-ST-32C section 4.8 (in-service surveillance,
  ground/in-orbit inspection, damage evaluation, maintenance, repair).

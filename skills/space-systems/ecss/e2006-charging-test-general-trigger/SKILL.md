---
name: e2006-charging-test-general-trigger
description: "Use when determine whether an external surface has to go to sample testing under ECSS-E-ST-20-06C clause 6.6.1: take each surface item with the status of every material-provision and analysis-provision, downgrade a compliance-claim whose evidence cannot carry it, a bare declaration, an analytical demonstration offered against a measured-property provision, or heritage outside its qualified-envelope, trigger the sample-kind each unmet provision demands, size and sequence the resulting sample-campaign from the distinct materials it covers, and report invalid waivers, missing statuses and unsupported claims. Trigger: ecss, e-st-20-06c, charging-sample-trigger, material-provision-shortfall, sample-campaign-sizing, heritage-evidence-envelope, sample-waiver-validity, electron-beam-exposure-sample, resistivity-measurement-sample."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-charging-test-general-trigger, e-st-20-06c, charging-sample-trigger, material-provision-shortfall, sample-campaign-sizing, heritage-evidence-envelope, sample-waiver-validity, electron-beam-exposure-sample]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Sample-Trigger Rule for Surfaces (space-systems/ecss/e2006-charging-test-general-trigger)

Use when the task is the clause 6.6.1 provision of ECSS-E-ST-20-06C:
it is a trigger rule rather than a method, and it says that a surface
whose material and analysis provisions are not met goes to sample
testing. This leaf resolves each provision against the evidence
actually offered for it, triggers the sample kind every shortfall
demands, and sizes and sequences the campaign that results.

## Domain quick reference

- Each external surface item carries a status for every provision that
  applies to it: the conductive-material rule, the sheet-resistivity
  limit, electrical-continuity bonding, the surface-potential-analysis
  coverage and the biased-surface disturbance study. A provision with
  no status on record is not met — an unaddressed provision cannot be
  assumed to have passed, and this leaf reports it as both a trigger
  and a finding.
- A declared state is only as strong as its evidence, so every claim
  is resolved before it is believed. Measured data carries any
  provision. An analytical demonstration carries the provisions that
  are themselves analyses and nothing else: no calculation replaces a
  measured secondary-emission yield or a measured sheet-resistivity.
  Qualified heritage carries a provision only when the qualified
  envelope reaches the severity of this mission. A bare declaration
  carries nothing.
- The resolved states are met, not-met, not-demonstrated and
  not-applicable. The first and the last close the provision; the
  middle two both trigger a sample kind, which is the point of the
  clause: an undemonstrated provision and a failed one lead to the
  same place, and only a genuinely inapplicable provision is dropped.
- Each provision names the sample kind it triggers:
  material-characterisation and resistivity-measurement for the
  material provisions, bonding-continuity for the grounding provision,
  electron-beam-exposure and biased-plasma-exposure for the analysis
  provisions. The campaign is the union of the triggered kinds across
  every item, sized from the distinct materials each kind has to
  cover and sequenced so material data exists before exposure work
  starts.
- A waiver is not a substitute for evidence. It is valid only against
  a provision that is genuinely not applicable; a waiver placed on an
  unmet or undemonstrated provision leaves the trigger standing and
  is itself a finding.

## Workflow

1. Normalise each surface item: an identifier, a material name and a
   status for each provision. Reject an unknown provision, an unknown
   declared state, a claim of compliance with no evidence source,
   heritage with no qualified envelope, a waiver with no justification
   and a duplicate item identifier.
2. Resolve every provision against its evidence: measured data closes
   it, an analysis closes only an analysis provision, heritage closes
   it only inside its envelope, a declaration closes nothing. An
   envelope that exactly reaches the mission severity covers it — the
   comparison absorbs representation error rather than moving the
   envelope.
3. Fill in the provisions with no status on record as not-demonstrated
   and record each one as a finding, so a thin submission cannot pass
   by omission.
4. Trigger the sample kind named by every provision resolved to not-met
   or not-demonstrated, and collapse the per-item list into the
   distinct kinds in sequence order.
5. Build the campaign: group the triggered items by sample kind,
   collect the distinct materials each kind covers, size the sample
   count as the base set plus one per additional material up to the
   cap, and sequence the kinds so material characterisation precedes
   exposure work.
6. Report the findings — invalid waiver, missing status, heritage
   shortfall, unsupported claim — alongside the campaign. Sampling is
   avoidable only when no item triggers a kind.

## Pitfalls

- Reading the clause as a method for a sample campaign. It decides
  whether the campaign happens at all; the sample procedures live in
  the clauses it hands the surface over to.
- Accepting an analysis against a measured-property provision. A
  computed yield or a computed resistivity is a prediction, and
  predicting the property the provision constrains is exactly the
  situation the clause sends to sampling.
- Accepting heritage without checking the qualified envelope against
  this mission. Heritage from a benign orbit closes nothing for a
  vehicle flying a harsher environment.
- Treating a waiver as closure. A waiver against an unmet provision
  removes the paperwork, not the trigger, and the sample kind stays on
  the campaign.
- Sizing one sample set per item rather than per material. The count
  follows the distinct materials a kind has to cover, so ten items of
  one blanket material are still one base set.

## Behavior contract (gate 3)

The status validation, evidence resolution, heritage envelope check,
missing-status handling, trigger logic, campaign sizing, sequencing
and waiver assessment are exercised by the gate 3 contract test:
scripts/test_e2006_charging_test_general_trigger.py against
scripts/e2006_charging_test_general_trigger_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_charging_test_general_trigger.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

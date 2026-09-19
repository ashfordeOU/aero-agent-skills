---
name: q7046-fastener-nonconformance
description: "Determine the quarantine reach, the permitted dispositions and the signatures a nonconforming threaded fastener lot owes. Use when a finding has been raised against fasteners and someone must say how far the hold extends and what may still be done with the parts: widen the hold from the lot to every lot sharing the heat, heat-treatment charge or plating batch, widen it again to all supplier stock when the records cannot resolve which lots those were, strike rework and use-as-is off any defect that lives in the metal, retire the coating route once the re-plating cycles are spent, then name the board and customer signatures and the physical mutilation a scrap actually takes. Trigger: ecss, q-st-70-46-fasteners, fastener-lot-quarantine-scope, fastener-nonconformance-disposition, fastener-scrap-mutilation, fastener-replating-cycle-limit."
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
  tags: [ecss, q-st-70-46-fasteners, q7046-fastener-nonconformance, fastener-lot-quarantine-scope, fastener-nonconformance-disposition, fastener-scrap-mutilation, fastener-replating-cycle-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Nonconformance (space-systems/ecss/q7046-fastener-nonconformance)

Use when the task is the nonconformance clause of ECSS-Q-ST-70-46:
deciding how far a hold on fasteners has to reach, which dispositions
are genuinely available for the defect found, and what has to happen
physically before a scrapped fastener is out of the system.

## Domain quick reference

- The quarantine follows the process the defect came out of, not the
  paperwork the parts arrived on. A defect made by one operation is
  contained by the lot that went through it; one that came out of the
  heat, the heat-treatment charge or the plating tank reaches every lot
  carrying that record.
- Where the records cannot resolve which lots shared the process, the
  hold has to reach the supplier's whole stock on hand. That is not
  caution, it is the only scope the records actually support.
- A material, heat-treatment or hydrogen-embrittlement defect lives in
  the metal. No rework returns the part to the specification it was
  bought against, so the routes are return and scrap, and offering
  use-as-is on one of these is offering to fly an unknown property.
- A coating defect is a surface condition and can be stripped and
  re-applied, but only while the part has re-plating cycles left. Each
  strip removes base metal and each re-bake is another thermal exposure,
  so the route retires itself after a small number of cycles.
- A dimensional or surface defect can only be corrected by removing
  material, which a fastener cannot afford in the zones that carry the
  load. On a critical part that leaves return and scrap.
- Every disposition needs a review board. Keeping the part in the build
  against the requirement it failed, by use-as-is or repair, needs the
  customer too, because the acceptance the customer gave was against the
  requirement rather than the part.
- Scrap is a physical act. A fastener written off but left whole in a
  bin will be found and fitted, so the record of scrap and the
  mutilation of the parts are the same step, witnessed on a critical
  lot.
- Parts already installed are a recall, not a lot record. Closing the
  lot without raising it against the assemblies loses the only link
  back to where the parts went.

## Workflow

1. Establish where the defect came from and whether the traceability
   records can resolve which lots shared that process. Those two
   answers, and nothing else, set the quarantine scope.
2. Take the defect class and the criticality and build the list of
   dispositions that are genuinely available, rather than starting from
   the full list and arguing downwards.
3. For a coating defect, count the re-plating cycles already spent and
   drop the rework route when they are exhausted.
4. Check whether any of the lot is already installed. If it is, raise
   the recall against the assemblies before the lot record is touched.
5. Test the proposed disposition against the permitted list. Refuse it
   with the available options named, rather than accepting it with a
   caveat nobody reads later.
6. For an accepted disposition, name the signatures it needs, and for a
   scrap name the physical actions: mutilate, strike the lot identity
   from the stock record, record the quantity, and witness it on a
   critical lot.

## Pitfalls

- Holding only the lot the defect was found in when the defect came out
  of a shared heat. The other lots from that heat carry the same
  property and are usually the ones already in the build.
- Narrowing the hold on the strength of a traceability record that
  cannot actually resolve the process. An unresolvable record is a
  reason to widen the hold, not a reason to assume containment.
- Offering rework on an embrittlement or heat-treatment finding. The
  part can be re-baked and re-tested and it is still a part whose
  delivered property is unknown, which is the thing the specification
  was buying.
- Stripping and re-plating a part that has already been through the
  cycle limit. Each strip removes base metal from the thread flanks, so
  the part that comes back is dimensionally a different part.
- Treating scrap as a stock-record state. An unmutilated fastener in a
  scrap bin is a fastener that returns to the build, and every audit
  that has looked for this has found some.
- Closing the lot record without raising the recall for installed
  parts. The lot record is where the link to the assemblies lives, and
  it is the hardest thing to reconstruct once it is closed.

## Behavior contract (gate 3)

The quarantine scope rules, the permitted disposition sets by defect
class and criticality, the re-plating cycle limit, the approval
signatures, the physical scrap actions and the full case decision are
exercised by the gate 3 contract test:
scripts/test_q7046_fastener_nonconformance.py against
scripts/q7046_fastener_nonconformance_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_q7046_fastener_nonconformance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

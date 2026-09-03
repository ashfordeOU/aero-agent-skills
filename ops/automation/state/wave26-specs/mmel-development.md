# Wave-26 leaf spec: mmel-development (systems-engineering-safety, certification pack)

- Path: skills/systems-engineering-safety/certification/mmel-development/
- Pack: certification (existing siblings: certification-basis,
  means-of-compliance, equivalent-level-of-safety)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: systems-engineering-safety

## Claim

Develop the Master Minimum Equipment List (MMEL) proposal for a type
design from the safety assessment results: screen each candidate
equipment item for dispatch relief with the item inoperative, classify
the item as MMEL-eligible or forbidden from relief, assign the
operator-repair interval category (A, B, C, or D), attach the required
operating procedure (O) and maintenance procedure (M) flags, and check
the interaction between multiple inoperative items so that no
combination removes a safety function. Produces the per-item MMEL
proposal rows with interval category, O/M flags, and the relief verdict
that gates the MMEL submission to the certification authority.

Does NOT do: compute engine-inoperative takeoff or climb performance
(flight-mechanics oei-climb-gradient and takeoff leaves own the
performance), run the safety assessment itself (arp4761a safety-
assessment and sibling analyses produce the severity inputs this leaf
consumes), decide which regulations apply (certification-basis), or
manage post-cert change control (arp4754a configuration-management).
The operator MEL (individual airline document) is out of scope; this
leaf proposes the type-level MMEL from engineering screening rules.

## Model (implement exactly)

Item input model: list of dicts, each:
- item_id (str), name (str),
- function (str, free text),
- severity_if_inoperative (one of: none, minor, major, hazardous,
  catastrophic): severity of the failure condition that would result if
  the item is inoperative and its function is not provided,
- redundancy (one of: single-string, dual, multi): remaining
  capability when the item is inoperative,
- safety_function (bool): True when the item directly backs a
  catastrophic/hazardous failure condition (e.g. part of the
  mitigation set),
- crew_action_available (bool): flight crew can detect and compensate
  with a procedure,
- maintenance_required (bool): a maintenance task restores the item or
  the function,
- placard_required (bool): flight crew placard or log entry required.
Module constant INTERVAL_DAYS = {"A": 3, "B": 10, "C": 120,
"D": None} with D = no scheduled repair interval (documented in the
SKILL body as the typical public FAA MMEL interval policy, name and
paraphrase only; actual approval is authority-specific).
Functions:
- eligibility(item) -> (eligible_bool, reason): eligible only when
  severity_if_inoperative is major or lower; hazardous/catastrophic
  single-string items are NEVER eligible; a hazardous or catastrophic
  item is eligible only when redundancy is dual or multi AND the
  remaining channel(s) alone meet the safety objective (accept item
  with redundancy dual/multi and severity hazardous/catastrophic only
  when safety_function is False, i.e. the item is not itself the
  mitigation).
- interval_category(item) -> (category, reason): none -> D; minor ->
  D when crew_action_available or redundant else C; major -> C when
  redundant else B when crew_action_available else A; hazardous with
  dual/multi redundancy -> B with O flag; catastrophic with dual/multi
  redundancy -> A with O and M flags (only reachable when eligibility
  passed); single-string eligible items (minor/none only) -> C.
- o_m_flags(item, category) -> (o_flag, m_flag, placard): O required
  when crew_action_available or category in (A, B) or safety_function;
  M required when maintenance_required or category == A or the item is
  hazardous/catastrophic with redundancy; placard when placard_required
  or category in (A, B).
- interaction_check(items, allowed_combination_max = 1) -> issues list:
  for every pair of inoperative-eligible items, if both are in the same
  function group (module constant GROUP_OF by item name keywords: yaw,
  pitch, roll, brake, thrust, pressurization, nav, comms, flight-guidance)
  and both have safety_function True, issue "double-relief removes a
  safety function"; also issue when more than allowed_combination_max
  inoperative items share a function group.
- build_mmel_proposal(items) -> dict {rows: [{item_id, category,
  o_flag, m_flag, placard, eligible}], forbidden: [item_ids with
  reasons], issues: [...]}.
- proposal_verdict(proposal) -> (PASS/FAIL, reasons): FAIL when any
  catastrophic or hazardous single-string item is in the rows, or any
  interaction issue exists, or any row lacks O when category in (A, B);
  else PASS.
ValueError on: unknown severity, unknown redundancy, empty item list,
missing required keys.

## Worked example

Items:
1. {"item_id": "YD-1", "name": "yaw damper", "function": "dutch roll
   damping", "severity_if_inoperative": "hazardous", "redundancy":
   "dual", "safety_function": false, "crew_action_available": true,
   "maintenance_required": true, "placard_required": true}: eligible,
   category B, O True, M True, placard True.
2. {"item_id": "FCS-1", "name": "primary flight computer", "function":
   "flight control", "severity_if_inoperative": "catastrophic",
   "redundancy": "single-string", ...}: NOT eligible (forbidden list)
   with the single-string reason.
3. {"item_id": "ENT-1", "name": "cabin entertainment", "function":
   "passenger media", "severity_if_inoperative": "minor",
   "redundancy": "single-string", "crew_action_available": false,
   "maintenance_required": false, "placard_required": false}: eligible,
   category D, no O, no M.
4. A pair of inoperative items both safety_function True in group
   "brake" -> interaction issue raised and proposal_verdict FAIL.
5. ValueError on severity "very-bad" and on an empty item list.
Keep at least 16 test methods (eligibility branches, category per
severity/redundancy, O/M/placard logic, interaction group logic,
verdict branches, ValueErrors).

## Corpus tasks (ids w26-mmel-development-1/2)

Distinctive tokens: master minimum equipment list, MMEL proposal, MEL
relief, dispatch with inoperative equipment, interval category, (O)
procedure, (M) maintenance flag, inoperative item screening, repair
interval. Avoid: engine inoperative / OEI (flight-mechanics
oei-climb-gradient), means of compliance (sibling), certification
basis (sibling).

1. "screen the yaw damper and the cabin entertainment system for the
   master minimum equipment list proposal: decide dispatch relief with
   the item inoperative, assign the interval category, and flag the (O)
   operating procedure and (M) maintenance requirements"
2. "check the MMEL relief interaction for two inoperative brake system
   items that both back a safety function and return the proposal
   verdict for the certification submission"

## SKILL body notes

Pair with the arp4761a safety assessment leaves (severity inputs),
means-of-compliance (the MMEL is part of the certification data), and
the certification-basis leaf. Compliance: interval policy and
eligibility rules are paraphrased from public FAA MMEL guidance at
reference level (no verbatim policy text); standards referenced not
reproduced.

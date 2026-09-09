# Aero Agent Skills taxonomy expansion analysis (wave-50 planning, 2026-09-09)

Scope: CEO-commissioned analysis per ceo-decision-wave49-reduced-2026-09-09.md
(veda repo), split (a) taxonomy expansion openable on CEO authority within the
existing 30-id standards map, (b) standards-map expansion 30 to more ids that
changes public standards claims and needs founder GO (already requested; listed
here for the record only). Ground truth: the 12 whole-family FRESH recon
receipts in ops/automation/state/wave49-recon/ (task-0..task-11, HEAD
9c2b3fe4), wave49-state.md close note, standards-map.yaml (30 ids). Family
shorthand: SES systems-engineering-safety, MQ manufacturing-quality, FM
flight-mechanics, FTO flight-test-operations, CC cross-cutting, AERO
aerodynamics. Wave-49 recon result: 10 of 12 families NO_CANDIDATES; only
gnc-autonomy (2 GO) and structures (2 GO) yielded; six saturated families
byte-identical since prior receipts.
## 1. Map-blocked seam inventory

Every standards area the wave-49 declines cite as absent from the 30-id map,
with host family/pack, the needed id, and receipt evidence. All receipts in
ops/automation/state/wave49-recon/.

- ARINC-653 (avionics RTOS time/space partitioning). Host: avionics/fsw and
  avionics/ima. Needed id: arinc-653. Evidence: task-3 ARINC-653
  scheduling/partitioning and time/space-partitioning rows ("Owned +
  map-blocked: no arinc-653 id"; "the concept substance is ARINC 653 / DO-297
  standard text and neither id exists"), absent-id list line 87. Most
  ARINC-653-flavored seams are already OWNED (ima-partitioning MAF
  feasibility, do297 budgets, in-partition process scheduling); the unowned
  remainder is the partitioning-integrity isolation tier, token-empty and
  duplicative of owned isolation sentences.
- DO-326A / ED-202A (airworthiness security). Host: SES (arp4754a/arp4761a
  packs and certification pack). Needed id: do-326a (note ED-202A twin).
  Evidence: task-6 airworthiness/information-security seam row ("no
  do-326a/ed-202a id among the 30 ids", gate (c) FAIL; cyber/security
  vocabulary 0 hits whole tree, 0 corpus) and standards-map check line 140
  ("No security/cyber id (do-326a absent)"). Also taxonomy brief 05 section 2
  places DO-326A/ED-202A and DO-356A in the compliance backbone under the
  guidance tier.
- AMS / ISO process and material specs (manufacturing process control,
  workmanship). Host: MQ (special-processes, ndt, composites, assembly) and
  structures/materials. Needed ids: ams-2750 / ams-2760 (pyrometry, furnace
  TUS/SAT), ams heat-treatment and surface-finishing series, astm-e NDT
  test-method class, ISO/ASME machining and hole-spec class, iso-3685.
  Evidence: task-7 first-time seam table (composites fabrication, machining,
  forming, HIP, pyrometry, part-marking rows) and absence grep lines 185-188
  (ams, astm, aws, aiag, iso families all 0).
- ARINC 629 / ARINC 825 databus (and CAN/TTEthernet). Host: avionics/data-bus.
  Needed ids: arinc-629, arinc-825. Evidence: task-3 data-bus seam row
  ("ARINC 629 / ARINC 825 / TTEthernet: ZERO tree-wide hits, 0 corpus rows...
  other buses map-blocked (no arinc-629/825 ids)") and closed-veins line 68.
- DO-297 (IMA development). Host: avionics/ima. Needed id: do-297. Evidence:
  task-3 time/space-partitioning row and absent list line 87. Note the
  avionics/ima/do297 leaf exists on disk keyed reference-only to do-178c; the
  map id absence blocks deeper IMA-integration seams, not the current leaf.
- Terrain-awareness MOPS (TAWS/GPWS), Mode-S/transponder MOPS, display/ARINC
  661. Host: avionics/surveillance. Evidence: task-3 TAWS row ("no terrain or
  Mode-S MOPS id in the map (rtca-do-229/185/260b only)") and closed-veins
  lines 62-67. TAWS/GPWS and Mode-S are CLOSED (zero tokens, do not reopen);
  ARINC 661 display symbology closed since wave-44.
- Metrology instruments (CMM, surface finish). Host: MQ and CC/tolerancing.
  Needed ids: iso-15530, asme-b89, asme-b46.1, iso-4287. Evidence: task-7
  wave-48 recheck reminders 2 and 7 ("the metrology seam stays map-blocked
  until iso-15530/asme-b89/asme-b46.1 ids exist") and the in-process
  inspection row; CC task-10 N7 row (form-tolerance verification).
- Reliability-prediction parts-count vein (MIL-HDBK-217/Telcordia/SR-332).
  Host: SES arp4761a quantitative set. Needed id: mil-hdbk-217. Evidence:
  task-6 reaffirmed closures ("mil-hdbk-217/telcordia/sr-332 0... closed
  vein, map-blocked").
- ADS-33 rotorcraft handling qualities. Host: FM handling-qualities.
  Needed id: ads-33. Evidence: task-8 standards-map check line 182-183
  ("rotorcraft HQ stays map-blocked (no ads-33)").
- FAR-23 (GA certification) and FAR-121 / AC 120-42B (transport ops rules).
  Host: vehicle-design sizing weight seams and FM drift-down. Needed ids:
  far-23, far-121, ac-120-42b. Evidence: task-1 avgas row ("standards-map.yaml
  has NO far-23 id") and standards-map check line 130; task-8 drift-down STAY
  row and standards-map check lines 181-183 ("drift-down stays map-blocked
  (no far-121/ac-120-42b)").
- AC 25-7D measured-distance standard-day correction. Host: FTO performance.
  Evidence: task-9 reopen-trigger check ("no ac-25-7d id anywhere... map
  still 30 ids") and recheck-reminder lines 379-383.
- CCSDS channel coding and TLE/SGP4 orbit models. Host: space-systems
  (subsystems comms, orbit-mechanics). Needed ids: ccsds, spacetrack/sgp4.
  Evidence: task-5 comms row ("no ccsds id in the 30-id map") and
  standards-map check lines 166-168.
- FAR-21/43/145-class rules (repair/alteration classification, conformity,
  certificate issuance). Host: SES certification, MQ nonconformance.
  Evidence: task-6 conformity row gate (c) ("no issuing-authority id") and
  repair/alteration row gate (c) ("no id (far-43/145-class rules absent)").
- Part marking / UID (MIL-STD-130), AIAG (MSA/GRR), ISO 9001 base clause
  framing. Host: MQ. Evidence: task-7 part-marking row and absence grep.

Bottom line: the declines cite at least 20 absent standards ids across 8
families (the map also lacks the brief-05 test-standard ids mil-std-810h/
461g/704, though no wave-49 decline reached them). Only a subset would clear
the remaining gates if the id appeared (section 3); map-blocking is
necessary-but-not-sufficient.

## 2. CEO-authority expansion candidates (openable within the existing 30-id map)

Wave-49 was an exhaustive 12-family FRESH recon under the doctrine (gates a-f
plus the corpus-absent GO precedent: a prior receipt must have declared the
seam the natural next sibling, or a proven vein must exist). No receipt found
an openable unowned seam with a deterministic closed-form anchor except the one
deferred candidate below; section 2 is deliberately small. Fabrication or
lowered-bar proposals would violate the wave-49 quality doctrine.

### GO candidate 1: gnc-autonomy/control/adaptive-backstepping (tuning functions)

- Proposed pack path: skills/gnc-autonomy/control/adaptive-backstepping.
- Concrete leaf coverage (6): parameter-update law design (gradient and
  Lyapunov-motivated update laws for the unknown plant parameter in a
  second-order strict-feedback recursion); tuning-functions construction
  (Krstic-style estimator coupled into the recursion, z1/z2 error variables
  plus parameter-error augmentation); adaptive virtual-control and final
  control assembly with estimated parameters; composite Lyapunov stability
  audit (state plus parameter error decay); parameter convergence and
  persistent-excitation audit; cross-check against the owned siblings
  (backstepping-control exact-model case at zero adaptation, adaptive-control
  first-order MRAC case at order one).
- Existing standards-map id anchor: arp4754a (reference-only, gnc control-pack
  convention, same as backstepping-control and sliding-mode-control
  frontmatter; no new id needed).
- Why a genuine gap (verified against the tree at 9c2b3fe4): no
  adaptive-backstepping leaf exists on disk; backstepping-control (landed
  wave-49) fences the seam out ("never overlaps adaptive-control or
  l1-adaptive-control, whose gains or adaptive signals update online against
  an unknown first-order plant coefficient while this leaf's plant is fully
  known and second-order"); adaptive-control owns only the first-order MRAC
  identity ("first-order plant with an unknown plant coefficient");
  l1-adaptive-control owns the state-predictor identity. The tuning-functions
  class (unknown parameter inside the second-order strict-feedback recursion)
  is zero-owner. Corpus demand is zero, but wave-49 task-0 (declines row and
  recheck reminders) DECLARED this seam the re-probe target after
  backstepping lands and proves the identity, and instructed "do not build
  both in one wave". Backstepping landed wave-49 (rated 9.5), so the
  declaration condition is satisfied: the same corpus-absent
  declared-next-sibling path wave-49 used for backstepping itself.
- Honesty notes: the gnc receipt also closes DOBC variants (share the ADRC
  LESO total-disturbance core; not separate leaves) and mu-synthesis/D-K
  (gate d). Both stay closed.

### Probed and excluded (would-be candidates that fail on evidence)

- CC correlated-input GUM covariance form (task-10 seam N1, the family's one
  self-documented empty cell): excluded as a new leaf by the receipt itself;
  remedy is an IN-LEAF extension of uncertainty-propagation when corpus demand
  appears. CEO-authority in-place work, not a GO leaf.
- Avionics weather-radar received-power/detection-range (task-3 CONDITIONAL):
  excluded; reopen only if airborne-weather-radar fences the two identities
  out, and its desc (re-read at HEAD) does not. A twin today would
  route-fragment the owned trigger.
- Space deployment/separation/release mechanisms (task-5, the family's only
  zero-owner surface): excluded, gate (d) fail (single-equation fragments;
  yo-yo despin cross-owned to gnc attitude-dynamics).
- AERO open-jet corrections, FM IGE-climb and blade twist, FTO standard-day
  measured distance, MQ destructive GRR, avionics WCET estimation: all
  reopen-trigger gated by their receipts; none fired. Not candidates.
- Propulsion piston altitude/lapse (task-4 open finding) and the CC covariance
  form are in-place quality fixes available as CEO-authority wave work; they
  add no leaves and do not count to the GO pool.

CEO-authority viable GO count for wave-50: 1 (adaptive-backstepping), plus 0
currently-openable conditionals. Reaching 3-4 would require fence changes on
owned leaves (weather-radar) or corpus demand (no signal in the last +40
tasks).

## 3. Founder-GO expansion candidates (require standards-map additions)

Each row changes PUBLIC standards claims (standards-map.yaml feeds STANDARDS.md
and the manifest-check), so founder GO is required and already requested
separately. Listed here for the record with proposed schema fields per
standards-map.yaml conventions. Family values: regulation | guidance | quality
| space | open-spec | materials | reference-data. Status values per map.

Priority tranche 1 (best unlock-to-risk ratio, my recommendation):

- do-326a: "DO-326A/ED-202A: Airworthiness Security Process Specification".
  Family guidance, publisher RTCA/EUROCAE, status proprietary-sold, domain
  airworthiness security; gated true, summary_not_copy per existing RTCA rows.
  Unlocks the SES airworthiness-security seam (task-6) and a potential SES
  security-risk-assessment leaf family. Caveat: corpus 0 and the seam is
  process-verdict class, so a GO is not automatic; the SES process-leaf
  precedent (certification-basis, means-of-compliance,
  equivalent-level-of-safety) is the supporting convention.
- arinc-653: Family guidance, publisher ARINC (AEEC via SAE ITC), status
  proprietary-sold, domain avionics RTOS partitioning, gated true. Unlocks
  the partition-integrity isolation seam (task-3) and lets future IMA leaves
  key honestly instead of the do-178c-reference-only convention
  (ima-partitioning lines 133-137). Caveat: most ARINC-653 content is already
  owned; expected yield small without corpus demand.
- arinc-629 and arinc-825: Family guidance, publisher ARINC (SAE ITC), status
  proprietary-sold, domain avionics databus (629 parallel bus, 825 CAN-based
  low-speed bus), gated true. Unlocks data-bus protocol leaves for newer
  transports (777-class 629, CAN LRU buses), mirroring the owned 429/1553
  protocol and bus-loading pair structure (task-3). Caveat: corpus 0 today.
- ams-2750 (pyrometry/furnace TUS) plus one representative AMS
  heat-treatment or surface-finishing id: Family materials, status
  proprietary-sold, gated true. Unlocks the MQ pyrometry/SAT-TUS seam
  (task-7). Caveat: the gate (d) empirical blocker remains for most AMS/ISO
  machining and forming seams; this id alone is unlikely to produce a GO
  without corpus demand.
- astm-e (NDT test-method class, e.g. astm-e-2375 or the series-level id):
  Family guidance or materials, status proprietary-sold, gated true. Unlocks
  the MQ TOFD/PAUT/DR-CR/FMC-TFM reopen triggers (task-7 recheck reminder 2).
  Caveat: equipment-variant rows also need corpus demand.
- ads-33: Family guidance, publisher US Army (AVSCOM), status free-download or
  public-domain per actual availability (verify before claiming public
  status), domain rotorcraft handling qualities. Unlocks FM rotorcraft HQ band
  criteria (task-8 map-block row). Caveat: corpus 0.

Priority tranche 2 (record for later tranches, lower expected yield): do-297
(IMA development); metrology trio iso-15530/asme-b89/asme-b46.1 plus iso-4287;
mil-hdbk-217 (reliability parts-count); far-23 (GA block); far-121 and
ac-120-42b (drift-down/ops); ac-25-7d (FTO standard-day); ccsds and
spacetrack/sgp4 (space); mil-std-130 (UID marking); aiag (MSA GRR); iso-9001
framing id (MQ QMS clause base); terrain-awareness, Mode-S/transponder and
ARINC 661 display MOPS ids (avionics; note TAWS/Mode-S seams are CLOSED on
zero tokens, so the id alone would not reopen them). No open-spec or
reference-data additions are proposed: sep-2640 and the NACA pair already
cover those families; nothing in the receipts needs one.

Expected tranche-1 unlock, stated honestly: 2-6 candidate leaves across SES,
avionics, FM and MQ after fresh probes under the expanded map, with several
candidate seams still failing corpus/anchor gates. The expansion is a
necessary condition for healthy waves, not a guarantee of >=10 yield.

## 4. Wave-50 recommendation

- CEO-authority GO pool for wave-50: 1 viable candidate
  (gnc-autonomy/control/adaptive-backstepping), the receipt-declared next
  sibling whose deferral condition (backstepping landed and proven) is now
  satisfied. No other openable leaf-level seam survives the wave-49 fresh
  evidence; I do not promise >=10, the evidence does not support it and the
  wave-49 doctrine forbids filling the pool by fabrication or lowered bars.
- Top pack targets under CEO authority: gnc-autonomy/control (the
  adaptive-backstepping recursion core), plus in-place quality fixes in
  propulsion (piston/diesel altitude-lapse, wave-48/49 open finding) and CC
  (uncertainty-propagation covariance form) that keep the wave honest without
  minting leaves. A second leaf is reachable only if a brief directs a fence
  change on airborne-weather-radar (conditional seam), not recommended this
  cycle.
- Recommended wave-50 shape: run REDUCED (3-4 items: 1 GO leaf plus the 2-3
  in-place quality fixes), consistent with the accepted reduced-wave pacing,
  or hold and batch if the founder GO lands before dispatch.
- Structural verdict: the ONLY path to a healthy (>=10 viable leaves) wave
  under the current quality doctrine is the founder-GO standards-map expansion
  (tranche 1 above, led by do-326a, arinc-653, arinc-629/825, ams-2750,
  astm-e, ads-33). CEO authority alone cannot reopen the six saturated
  families: every NO_CANDIDATES receipt cites an existing sibling owner or a
  map-blocked seam, and the two GO families declared no further siblings
  beyond adaptive-backstepping. Recommend: founder approves tranche-1 ids at
  wave-50 planning time; wave-50 recon then re-probes the newly unblocked
  seams FRESH; wave-50 execution runs reduced regardless, with the
  map-expanded recon feeding wave-51.

Constraints honored: read-only work except this file; no git operations; no
em dashes; receipts cited by filename; no changes to skills/, eval/,
standards-map.yaml, numbers.yaml or briefs.

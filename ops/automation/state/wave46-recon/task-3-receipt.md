# WAVE-46 RECON RECEIPT: manufacturing-quality (task 3, whole family FRESH)

Probe date: 2026-09-07. Probe agent: read-only recon subagent.
Repo HEAD: d4b4d590 (wave-46 brief commit), tracked tree clean at probe start
and end; only the pre-existing untracked wave-46 prep files and this receipt
directory were present in git status.
Scope: whole manufacturing-quality family, FRESH zero-owner greps, sibling
fence reads with quotes, standards-map id greps, corpus demand check.
Baseline: wave-45 whole-family probe NO_CANDIDATES with receipts
(ops/automation/state/wave45-recon/task-4-receipt.md, HEAD 5cc8fef3); wave-44
whole-family probe NO_CANDIDATES before that. Wave-46 brief item 4: "SATURATED
reaffirmed FRESH wave-45: NO_CANDIDATES with receipts; CMM seam standards-map-
blocked. Probe only clean determinism, expect 0."
Mode: read-only except this receipt. No git operations, no edits to skills/,
eval/, docs/, Makefile, scripts/, ops/automation briefs, standards-map.yaml.
Helpers (read-only): /tmp/w46_t3_corpus.py, /tmp/w46_t3_ctx.py,
/tmp/w46_t3_grep.py, /tmp/w46_t3_fences.py.

## Verdict

NO_CANDIDATES. Saturation reaffirmed FRESH at wave-46 HEAD. Zero GO candidates.
Every plausible gap in the quality-management, SPC, NDI/inspection, metrology,
sealing, and fastener packs was re-probed with real greps and corpus demand
counts; all decline on at least one GO-bar gate (clean determinism with
published anchor, zero owner, standards-map id exists, non-stealing wordable
corpus demand). No GO evidence block produced.

## Family inventory (48 leaves, 8 packs, parity confirmed)

find skills/manufacturing-quality -mindepth 3 -name SKILL.md returns exactly 48
leaves (49 SKILL.md files with the family router skills/manufacturing-quality/
SKILL.md; router table rows `| manufacturing-quality/...` count = 48, parity OK):

- additive 2: additive-manufacturing-qualification, lpbf-parameter-development
- as9100 22: quality, nonconformance-control, supplier-control,
  counterfeit-prevention, calibration-control, corrective-action, document-control,
  fod-control, internal-quality-audit, management-review, order-requirements-review,
  risk-management, statistical-process-control, measurement-systems-analysis,
  gage-rr-anova, gage-linearity-bias-study, attribute-agreement-analysis,
  acceptance-sampling, variables-acceptance-sampling, attribute-control-charts,
  cusum-ewma-monitoring, individuals-and-moving-range-chart
- as9102 4: first-article-inspection, ballooning, delta-fai, fai-revalidation
- as9103 1: key-characteristic-management
- assembly 3: ewis-installation-quality, fastener-installation-quality,
  solid-rivet-installation-quality
- composites 1: layup-cure
- ndt 13: ndt-method-selection, ndt-personnel-qualification, ultrasonic-inspection,
  radiographic-inspection, eddy-current-inspection, liquid-penetrant-inspection,
  magnetic-particle-inspection, visual-inspection, acoustic-emission-inspection,
  computed-tomography, shearography-inspection, thermography, leak-testing
- special-processes 2: special-process-qualification, welding-qualification

Corpus: 98 of 1266 eval/hit1-corpus.yaml tasks carry
`expected_skill: "manufacturing-quality/...` (48 leaves x 2 plus the t3 engine-
overhaul future_pin pinned to as9100/quality per the corpus header); every leaf
name token matches at least 2 tasks in my coverage run, and the family router
rows are all published leaves.

## Standards-map facts (re-verified at HEAD)

standards-map.yaml holds exactly 30 `- id:` entries. Family-relevant ids present:
as9100 (line 83), as9102 (line 138), nas-410 (line 149), cmh-17 (line 281),
asme-y14-5 (line 226). Grep for every id a closed seam would need:
`grep -inE "cmm|b89|15530|b46|4287|z1.4|z1.9|mil-std-105|mil-std-414|1235|astm|
aws-d17|aiag|iso-9001|s20" standards-map.yaml` -> 0 matches (exit 1). So the
CMM/dimensional-metrology block (iso-15530, asme-b89.4.x, asme-b46.1, b1-series)
and the sampling/SPC/process blocks (z1.4, z1.9, mil-std-105/414/1235, astm-e
series, aws, aiag, iso-9001, ansi/esd-s20.20) all still hold. Existing leaves
carry as9100/as9102/nas-410/cmh-17 as reference-only and paraphrase
Z1.4/Z1.9/MIL-STD-414/AIAG-style content under that convention.

## Fresh probe evidence (real outputs)

Corpus demand battery (case-insensitive over all 1266 task bodies, comments
excluded) returned zero for every closed-seam token: cmm 0, coordinate
measuring 0, iso-15530 0, b89 0, b46 0, profilometer 0, optical comparator 0,
thread gage 0, caliper 0, height gage 0, nested gage 0, destructive gage 0,
single-trial 0, double sampling 0, multiple sampling 0, sequential sampling 0,
skip-lot 0, ltpd 0, mil-std-105 0, pre-control 0, short-run 0, quesenberry 0,
tofd 0, phased array 0, phased-array 0, digital radiography 0, computed
radiography 0, neutron radiography 0, holography 0, guided wave 0, coin-tap 0,
fokker 0, terahertz 0, sealant 0, faying 0, fillet seal 0, polysulfide 0,
primer 0, peel ply 0, out-time 0, shelf life 0, torque-tension 0, torque wrench
0, preload 0, nut factor 0, lockwire 0, cotter pin 0, crimp 0, iso-9001 0,
cost of quality 0, copq 0, dmaic 0, six sigma 0, kaizen 0, 5s 0, poka-yoke 0,
layered process audit 0, control plan 0, work instruction 0, operator
certification 0, brazing 0, soldering 0, heat treatment 0, shot peening 0,
anodize 0, plating 0, painting 0, conformal 0, hardness 0, rockwell 0, brinell
0, vickers 0, proof pressure 0, burst test 0, as4059 0, cleanliness 0.
Nonzero context checks all route to other owners or other families: destructive
testing 1 -> individuals-and-moving-range-chart; acoustic emission 1 ->
acoustic-emission-inspection (planar triangulation); micrometer/borescope ->
visual-inspection; mil-std-414 1 -> variables-acceptance-sampling (k-method);
Cp/Cpk "capability" tasks -> statistical-process-control; torque coefficient 2
-> rotorcraft hover (flight-mechanics C_Q, different quantity); roughness 5 ->
aerodynamics rough-wall friction and a stats kruskal task; adhesive 7 (w27
tasks) -> structures/composites/adhesive-bonded-joints; emat hits are the
"systematic" substring (150 files, all false positives); esd 4 -> avionics
do160 electrostatic-discharge.

Zero-owner grep battery over the whole skills/ tree (real output, highlights):
0 files for cmm, coordinate measuring, profilometer, iso-15530, b89, b46.1,
surface roughness, optical comparator, thread gage, nested gage, destructive
gage, stability study, double sampling, skip-lot, ltpd, mil-std-105, hotelling,
pre-control, short-run, quesenberry, tofd, phased array, digital radiography,
computed radiography, neutron radiography, vibrothermography, terahertz,
holograph, guided wave, coin tap, fokker, sealant, faying, fillet seal,
polysulfide, adhesive bonding, peel ply, shelf life, out-time, age control,
preload, nut factor, torque wrench, lockwire, cotter pin, crimp, brazing,
solder, shot peen, anodiz, plating, painting, conformal coating, rockwell,
brinell, vickers, cost of quality, dmaic, six sigma, kaizen, poka-yoke, layered
process audit, operator certification, s20.20, as4059, fluid cleanliness, esd
program. Owner hits: z1.4/z1.9/mil-std-414 -> acceptance-sampling and
variables-acceptance-sampling (logic + SKILL.md); runs test ->
cross-cutting/numerics/runs-test; lock-in -> thermography; pulse-echo and
through-transmission -> ultrasonic-inspection and layup-cure; torque coefficient
and torque-tension and swage -> fastener-installation-quality and
solid-rivet-installation-quality (SKILL.md + logic); heat treatment ->
special-process-qualification and additive-manufacturing-qualification; hardness
-> additive-manufacturing-qualification and fai-revalidation bodies; iso 9001 ->
as9100/quality and order-requirements-review; control plan ->
key-characteristic-management and fastener-installation-quality; work
instruction -> document-control (test only).

## Sibling fence quotes (read at HEAD, verbatim)

- measurement-systems-analysis workflow step 1: "Collect the operator-part
  measurement table: every appraiser measures every part with the same number
  of trials (2 or 3), the range method standard."
- gage-rr-anova Pitfalls: "Routing a single-trial or short study here: without
  replicated trials per cell there is no within-cell error term and no
  interaction test, so the range-based estimator in
  measurement-systems-analysis is the right tool; the ANOVA path needs n >= 2
  trials per cell."
- special-process-qualification description: "determine whether a welding, heat
  treatment, NDT, surface finishing, or composites process stays qualified
  under a proposed change by classifying the change type (parameter, equipment,
  personnel, time interval) against the qualified envelope".
- fastener-installation-quality description: "compute the clamp load from the
  applied torque with the torque coefficient, verify the clamp load and the
  torque scatter band against the joint allowables"; body: "Clamp load from
  torque: F = T / (k * D), with T the applied torque in N m, k the torque
  coefficient (typical 0.2 lubricated)"; also owns "confirm the swage collar
  engagement for lock-bolt fasteners".
- ultrasonic-inspection description: "determine discontinuity depth from time
  of flight, compute wavelength and near-field length for transducer and
  frequency selection ... size discontinuities against acceptance criteria
  using reference reflectors such as flat-bottom and side-drilled holes";
  Pitfalls: "Forgetting the round trip: depth is tof * v / 2, never tof * v."
- welding-qualification body: weld NDT interpretation "are out of scope here".
- thermography description: "choose pulsed or flash thermography versus
  lock-in thermography".
- key-characteristic-management body: "This leaf assigns the target only; the
  X-bar/R chart and Cpk index math live in the statistical-process-control".
- ewis-installation-quality description: fill ratio against the 0.40 limit,
  round-trip voltage drop against the 2% limit, bend radius, separation
  clearance (no crimp or terminal content anywhere in the family).
- solid-rivet-installation-quality: "fasteners, this leaf never applies
  torque-tension relations" (torque preload is the fastener leaf's slot).

## Re-verification of closed seams

1. CMM / dimensional metrology seam: still standards-map-blocked. Zero owners
   in the whole tree for cmm, coordinate measuring, profilometer, iso-15530,
   b89, b46.1, optical comparator, thread gage; the 30-id map has no iso-15530,
   asme-b89.4.x, asme-b46.1, asme-b1, or iso-4287 entries. Not reopened per
   brief. Corpus: cmm 0 tasks.
2. Wave-45 near-misses all re-probed FRESH this wave with the batteries above;
   every one still fails the GO bar (table below). Destructive/nested gage R&R
   remains the only methodically real but decline-justified near-miss: zero
   owners confirmed again, the MSA umbrella fence routes no-replication studies
   to the range-based estimator (quotes above), a true destructive-study
   design carries the paired-homogeneous-units and EV-versus-part-in-appraiser
   choice which is design judgment, not clean deterministic closed form, and
   corpus demand is zero.
3. Pack-by-pack seams checked: quality management (22-leaf as9100 pack: clause,
   audit, review, supplier, counterfeit, calibration, document, FOD, risk,
   CAPA, MRB, sampling, MSA, SPC all owned), statistical process control
   (X-bar/R, I-MR, p/np/c/u, CUSUM/EWMA, Cp/Cpk all owned), NDI (13-leaf ndt
   pack: RT, UT, ET, PT, MT, VT, AE, CT, shearography, thermography, leak, plus
   method selection and NAS 410 personnel), inspection (VT borescope geometry,
   FAI quartet, KC variation plans owned), metrology (map-blocked), sealing and
   fastener packs (sealant/adhesive application and torque-preload slots have
   zero owners AND zero demand AND no map id, see table).

## Declines table (standing wave-45 rows re-verified FRESH + fresh probes)

| Candidate | Gate(s) failed | One-line reason |
|---|---|---|
| destructive / nested gage R&R | d, e, f | Design judgment (paired homogeneous units, EV-versus-part-in-appraiser choice); MSA umbrella fence routes no-replication studies to the range-based estimator; gage-rr-anova needs n >= 2 trials per cell; zero corpus demand |
| gage stability study (master part over time) | e, f, seam | I-MR machinery owned by individuals-and-moving-range-chart; drift recall judgment owned by calibration-control; zero corpus tasks |
| double / multiple attribute sampling | c, e | acceptance-sampling fence is explicitly single-plan with only reduced single-normal anchor rows under as9100 reference-only; no z1.4 double-plan id; zero corpus |
| sequential / skip-lot / LTPD sampling | c, e | No map id (mil-std-1235/ANSI S-series absent); aerospace lot acceptance here is single AQL and k-method variables only; zero corpus |
| pre-control charting | d, e | Heuristic zone method, no published deterministic closed-form anchor, no map id, zero corpus |
| short-run / stabilized SPC (Z charts, Quesenberry) | c, e | Small-shift monitoring owned by cusum-ewma-monitoring; no map id; zero corpus |
| Pp/Ppk and capability extensions | seam | statistical-process-control owns Cp/Cpk math; key-characteristic-management assigns the Cpk target; corpus Cp/Cpk task routes to SPC leaf |
| GUM-style gage calibration uncertainty | c, seam | Propagation owned by cross-cutting numerics uncertainty-propagation; metrology-specific territory is the CMM seam block (no iso-15530 id); calibration-control frames TAR |
| surface roughness / finish (Ra, Rz, profilometry) | c | Map-blocked (no asme-b46.1/iso-4287 id); corpus roughness tasks are aerodynamics and stats, none quality |
| thread gaging, optical comparator, hand-tool metrology | c | Same dimensional-metrology map block (no asme-b1/iso-3611 ids); CMM seam not reopened |
| hardness testing (Rockwell/Brinell/Vickers) | c, d | No astm-e id; conversion tables tabular and empirical; zero corpus |
| tolerance stack verification | family boundary | cross-cutting tolerancing owns worst-case/RSS under asme-y14-5; no quality-side duplicate |
| per-process leaves (brazing, soldering, heat treatment, shot peen, anodize/plating, paint/coat, conformal coat) | b, c, d | special-process-qualification fence owns the qualification decision across welding, heat treatment, NDT, surface finishing, composites; content is parameter/workmanship in aws/ams/astm with no map id; zero corpus (re-grepped: brazing, solder, shot peen, anodiz, plating, painting all 0 files) |
| bond testing (coin-tap, Fokker, impedance), neutron radiography, holography, guided-wave UT, EMAT | d, e | Empirical reference-comparison methods, no clean closed-form anchor, no astm-e id, zero corpus; ndt-method-selection + 12 method leaves + nas-410 personnel own the NDT seam |
| incoming / receiving inspection planning | seam | Split-owned: counterfeit-prevention (verification controls), supplier-control (delegated verification), order-requirements-review (acceptance criteria); no gap |
| product traceability / preservation clause functions | d | Requirements traceability owned (arp4754a/mbse); manufacturing lot traceability is ISO 9001 base-clause evidence assembled by quality/internal-quality-audit/document-control; no deterministic anchor; zero corpus |
| operator competence / training certification (non-NDT) | d, e | Internal QMS procedure content, no published anchor; nas-410 (in map) is the only deterministic certification leaf; zero corpus |
| material shelf life / age control (prepreg out-time) | d | Trivial elapsed-life arithmetic on proprietary datasheets; layup-cure owns cure context; zero corpus |
| lean / six-sigma / DMAIC / kaizen / 5S / poka-yoke, COPQ, layered audit, work instructions, control plans | d, e | Qualitative methods, no deterministic anchor, no map id; corrective-action (8D/five-whys), document-control, key-characteristic-management own adjacent machinery; cross-cutting default closed; zero corpus |
| PFMEA / process-FMEA specialization | seam | risk-management owns the RPN engine, 5x5 matrix, occurrence-from-history; systems-engineering-safety arp4761a owns the design FMEA family; no gap |
| pressure / proof / burst testing | boundary | Owned by structures and flight-test-operations pressure-adjacent leaves; family scope is quality/inspection; zero corpus |
| ESD program control (EPA, wrist strap, ionizer) | c, e | Equipment ESD owned by avionics do160 electrostatic-discharge; ansi/esd-s20.20 absent from map; zero corpus |
| fluid cleanliness classes (AS4059) | c, e | No sae/iso cleanliness id in map; fod-control owns FOD context; zero corpus |
| TOFD and phased-array UT (fresh) | c, e | Zero owners, but no astm-e2373/e2491 id; ultrasonic-inspection owns the UT slot (depth = tof * v / 2, FBH/SDH calibration, angle beam); zero corpus demand |
| digital radiography / computed radiography (fresh) | c, e | Zero owners; radiographic-inspection owns the RT attenuation/IQI engine; equipment-variant content, no astm-e id, zero corpus |
| weld-specific NDT acceptance interpretation (fresh) | c, e | welding-qualification fence excludes weld NDT interpretation; part-level acceptance math owned by radiographic-inspection/ultrasonic-inspection; AWS D17.1-style band tables need an aws id that does not exist; zero corpus |
| sealant / adhesive application, fay and fillet seals (fresh) | c, d, e | Zero owners for sealant/faying/fillet seal/polysulfide/peel ply across the whole tree; workmanship content with no published deterministic anchor and no map id; structures/composites/adhesive-bonded-joints owns bond strength math (all 7 adhesive corpus tasks route there); zero quality-side demand |
| torque-preload nut-factor / secondary locking (lockwire, cotter pin) (fresh) | seam, e | fastener-installation-quality owns clamp load F = T/(k*D), torque scatter verdict, swage collar engagement; lockwire/cotter are workmanship rules with no anchor; zero corpus |
| EWIS crimp / terminal pull verification (fresh) | c, e | ewis-installation-quality owns fill ratio, voltage drop, bend radius, separation; crimp pull-test is ipc workmanship with no map id; zero corpus |
| iso-9001 clause functions beyond AS9100 scope (fresh) | seam | quality owns the AS9100 clause mapping incl ISO 9001 base clauses; order-requirements-review owns related content; no iso-9001 id and no fence gap |

## Closed veins (owner leaf per vein, reaffirmed FRESH)

- Disposition / MRB: nonconformance-control. Closed.
- CAPA / root cause: corrective-action. Closed.
- SPC: statistical-process-control, cusum-ewma-monitoring, attribute-control-
  charts, individuals-and-moving-range-chart. Closed.
- MSA: measurement-systems-analysis (umbrella), gage-rr-anova, gage-linearity-
  bias-study, attribute-agreement-analysis, calibration-control. Closed.
- Sampling: acceptance-sampling (attribute), variables-acceptance-sampling
  (k-method and M-method inside). Closed.
- FAI / variation management: first-article-inspection, ballooning, delta-fai,
  fai-revalidation, additive-manufacturing-qualification (AM FAI),
  key-characteristic-management. Closed.
- NDT/NDI: ndt-method-selection, ndt-personnel-qualification, and 11 method
  leaves (ultrasonic, radiographic, eddy-current, liquid-penetrant, magnetic-
  particle, visual, acoustic-emission, computed-tomography, shearography,
  thermography, leak-testing). Closed.
- Special processes: special-process-qualification, welding-qualification.
  Closed.
- Assembly: fastener-installation-quality, solid-rivet-installation-quality,
  ewis-installation-quality. Closed.
- Composites processing: layup-cure. Closed.
- QMS clause functions: one owner each across the 22-leaf as9100 pack. Closed.
- CMM and dimensional metrology seam: standards-map-blocked (no iso-15530,
  asme-b89.4.x, asme-b46.1, asme-b1 ids). Not reopened per brief. Closed.

## Method notes

Probe steps executed: (1) find enumeration of all 48 leaves, pack counts, and
router parity (48 rows); (2) standards-map.yaml id dump and targeted absence
grep (30 ids, exit 1 on every closed-seam id family); (3) corpus demand battery
over all 1266 task bodies plus context dumps for every nonzero hit; (4)
zero-owner grep battery of ~70 tokens over the whole skills/ tree with real
output; (5) scoping-fence extraction and verbatim quote pulls from the seam-
owner leaves (MSA umbrella, gage-rr-anova, SPC, acceptance-sampling,
special-process-qualification, welding-qualification, fastener, ewis,
ultrasonic, radiographic, thermography, key-characteristic, quality); (6) git
status clean before and after (only the pre-existing untracked wave-46 prep
files and this receipt directory); no files modified outside this receipt.

Recheck reminders for future waves: destructive/nested GRR and TOFD/phased-array
UT are the only methodically real but decline-justified near-misses. Reopen the
GRR seam only if the MSA umbrella fence changes, a published AIAG-style nested
deterministic anchor enters the corpus, or natural-language corpus demand for
destructive gage studies appears. Reopen TOFD/PAUT and DR/CR only if an astm-e
id is added to the map together with corpus demand; the metrology seam stays
map-blocked until iso-15530/asme-b89/asme-b46.1 ids exist.

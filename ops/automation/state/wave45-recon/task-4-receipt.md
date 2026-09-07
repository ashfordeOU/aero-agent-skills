# Wave-45 Recon Receipt: manufacturing-quality (task 4)

Probe date: 2026-09-07. Probe agent: read-only recon subagent.
Repo HEAD: 5cc8fef33ffa3bd5530847040ef891299dde107d (main, clean at probe start).
Scope: whole manufacturing-quality family, FRESH zero-owner greps + sibling fence reads.
Baseline: wave-44 whole-family probe NO_CANDIDATES with receipts (reaffirmed).
Mode: read-only except this receipt. No git add/commit/push, no edits to skills/,
eval/, docs/, Makefile, scripts/, ops/automation briefs, standards-map.yaml.

## Verdict

NO_CANDIDATES. Saturation reaffirmed FRESH at wave-45 HEAD. Zero GO candidates.
Every plausible gap probed below declined with a documented reason. No GO evidence
block produced (no candidate cleared gates a-f).

## Family inventory (48 leaves, 8 packs, parity confirmed)

Enumerated with find skills/manufacturing-quality -mindepth 3 -name SKILL.md (48,
plus 1 family router at skills/manufacturing-quality/SKILL.md = 49 SKILL.md total):

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

Standards-map ids available to this family (grepped, all 30): only as9100, as9102,
nas-410, cmh-17, asme-y14-5 and the design-side ids exist. No z1.4, z1.9,
mil-std-105/414/1235, iso-15530, asme-b89.4.x, asme-b46.1, astm, aws, ams, ipc,
sae, as9103 or aiag ids exist. Existing leaves all carry as9100/as9102/nas-410/cmh-17
as reference-only; sampling and MSA leaves paraphrase Z1.4/Z1.9/AIAG-style content
under the as9100 reference-only convention.

## Any GO with evidence

None. No candidate cleared the GO bar. Closest near-misses and their declines are in
the table below.

## Declines table (near-miss per plausible gap, probed FRESH)

| Near-miss candidate | Gate(s) failed | Decline reason |
|---|---|---|
| destructive / nested gage R&R (one-way nested ANOVA for tests that consume the part) | d, e, f | Zero-owner confirmed (grep: no nested/destructive gage study anywhere), and both sibling fences exclude the exact data shape: gage-rr-anova requires n >= 2 trials per cell ("the ANOVA path needs n >= 2 trials per cell") and measurement-systems-analysis requires every appraiser to measure every part ("every appraiser measures every part with the same number of trials"). However the family consciously routes no-replication studies into the MSA umbrella: gage-rr-anova Pitfalls state "Routing a single-trial or short study here: without replicated trials per cell there is no within-cell error term and no interaction test, so the range-based estimator in measurement-systems-analysis is the right tool". AIAG-style nested analysis for true destructive tests needs paired homogeneous units and carries an EV-versus-part-in-appraiser component identification choice, which is design judgment, not clean deterministic closed form. Corpus: zero of 1238 tasks touch nested or destructive gage R&R; the only destructive-testing task routes to individuals-and-moving-range-chart ("run an individuals and moving range control chart for one measurement per lot with destructive testing"), a process-control framing. MSA vein already 5 leaves deep (measurement-systems-analysis, gage-rr-anova, gage-linearity-bias-study, attribute-agreement-analysis, calibration-control); wave-44 reaffirmed the vein saturated. |
| gage stability study (master part monitored over time) | e, f, seam | Content is an I-MR chart application on a master part; the I-MR machinery and stability verdict are owned by individuals-and-moving-range-chart, and drift-based interval/recall judgment is owned by calibration-control ("set from manufacturer guidance, use history, and drift data"; "decide recall versus review when a calibrated standard drifts out of tolerance"). Two existing owners, no fence gap. Corpus: zero stability-study tasks. |
| double / multiple attribute acceptance sampling | c, e | acceptance-sampling fence is explicitly single-plan ("look up the single-sampling plan (sample size n, accept number Ac, reject number Re)") and embeds only reduced single-normal-inspection anchor rows: body Pitfalls state "Expecting the full ANSI/ASQ Z1.4 table set: only the anchor rows listed above are embedded". A double-plan leaf would be a second reduced-table variant of the same OC-curve engine under the same as9100 reference-only convention (no z1.4 id exists), with zero corpus demand today. |
| sequential / skip-lot / LTPD sampling | c, e | No standards-map id (mil-std-1235, ANSI S-series absent); aerospace lot acceptance in this corpus is AQL single-plan and k-method variables framing only; zero corpus tasks. |
| pre-control charting | d, e | Heuristic green-yellow-red zone method with no aerospace-canon deterministic closed-form anchor; zero corpus tasks; AIAG-adjacent, no map id. |
| short-run / stabilized SPC (Z charts, Quesenberry) | c, e | Small-shift monitoring already owned by cusum-ewma-monitoring; short-run machinery has no map id; zero corpus tasks. |
| Pp/Ppk long-term performance index, capability-study extensions | seam | statistical-process-control owns capability indices ("calculate the Cp and Cpk capability indices against the specification limits") and key-characteristic-management owns Cpk targets; an extension belongs inside the SPC leaf, not a new leaf. Corpus task "compute the x-bar and r chart control limits and the cpk process capability index" routes there. |
| gage calibration uncertainty budget (GUM-style) | c, seam | Generic propagation owned by cross-cutting/numerics/uncertainty-propagation; metrology-specific uncertainty is the CMM-seam (ISO 15530) territory, standards-map-blocked (no iso-15530 id). calibration-control already frames TAR and "below it the standard dominates the measurement uncertainty". |
| surface roughness / finish measurement (Ra, Rz, profilometry) | c | Metrology seam, map-blocked: no asme-b46.1 / iso-4287 id in standards-map.yaml; dimensional-metrology ids beyond asme-y14-5 are absent. Same block that closes CMM applies; not reopened. |
| thread gaging, optical comparator / machine vision, hand-tool metrology (caliper, micrometer, height gage) | c | Same metrology map-block (asme-b1 series, iso 3611 etc. absent). CMM seam (iso-15530/asme-b89.4.x) explicitly closed per wave-45 brief; adjacent dimensional-metrology leaves would need absent ids. |
| hardness testing (Rockwell/Brinell/Vickers) | c, d | No astm-e series id in map; conversion tables are tabular and empirical; mechanical verification already framed by witness-coupon leaves (additive-manufacturing-qualification, welding-qualification coupon matrix) and materials properties live in structures/materials under mmpsd. Zero corpus tasks. |
| tolerance stack verification | family boundary | Design-side GD&T and tolerance stack fully owned by cross-cutting/tolerancing (tolerance-stackup, gdandt-basics, datum-reference-frames, fastener-position-tolerance-calc) under asme-y14-5; the same worst-case/RSS math serves verification; no quality-side duplicate warranted. |
| per-process special process engineering leaves (brazing, soldering, heat treatment, shot peening, anodize/plating, painting/coating, sealant application, crimping, conformal coating) | b, c, d | special-process-qualification fence owns the qualification decision across exactly these classes: "determine whether a welding, heat treatment, NDT, surface finishing, or composites process stays qualified under a proposed change"; welding-qualification is the one per-process engineering leaf, anchored by the deterministic heat-input closed form. The other processes are parameter/workmanship content anchored in aws/ipc/ams/astm standards with no map id, qualitative acceptance tables with no-verbatim reproduction risk, and zero corpus tasks (grep: no solder, braze, peen, anodize, plating, sealant, crimp tasks). |
| bond testing (coin-tap, Fokker, mechanical impedance), neutron radiography, holography, guided-wave UT, EMAT | d, e | Empirical reference-comparison methods without clean closed-form anchors and with no map id (astm-e series absent); zero corpus tasks; ndt-method-selection and the 12 method leaves plus ndt-personnel-qualification (nas-410) own the NDT seam. |
| incoming / receiving inspection planning | seam | Split-owned: counterfeit-prevention owns incoming verification controls and supplier-control owns delegated verification and flow-down; order-requirements-review owns acceptance criteria declaration. No fence gap. |
| product traceability (lot/serial) and preservation clause functions | d | Design-side requirements traceability is owned (arp4754a requirements-traceability, mbse); manufacturing lot traceability and preservation are ISO 9001 base-clause evidence assembled by quality ("map an audit focus area to the aerospace clauses"), internal-quality-audit and document-control; no published deterministic closed-form anchor. Zero corpus tasks. |
| operator competence / training certification (non-NDT) | d, e | Internal QMS procedure content with no published deterministic anchor; ndt-personnel-qualification (nas-410) is the only certification leaf because NAS 410 exists in the map and drives deterministic recertification dates. |
| material shelf life / age control (prepreg out-time, sealant life) | d | Trivial elapsed-life arithmetic anchored to proprietary manufacturer datasheets, not a published deterministic source; layup-cure owns the cure-process context. Zero corpus tasks. |
| lean / six-sigma / DMAIC / kaizen / 5S / poka-yoke, layered process audit, COPQ, work instructions, control plan | d, e | Qualitative process methods with no clean deterministic closed-form anchor and no map id; corrective-action owns the 8D/five-whys/poka-yoke-adjacent closure machinery; cross-cutting default closed; zero corpus tasks. |
| PFMEA / process-FMEA specialization | seam | risk-management owns the RPN engine ("compute FMEA risk priority numbers from severity, likelihood, and detection ratings") plus 5x5 matrix and occurrence-from-history; design-side FMEA family lives in systems-engineering-safety/arp4761a. Same machinery, no gap. |
| pressure / proof / burst testing | boundary | Design and test-side pressure content is owned by structures and flight-test-operations pressure-adjacent leaves (grep: proof-pressure appears only as body mentions); family scope is quality/inspection, corpus has no such task. |
| ESD program control (EPA, wrist strap, ionizer verification) | c, e | Equipment ESD qualification owned by avionics/do160/electrostatic-discharge; manufacturing-side ESD programs anchor to ansi/esd-s20.20 with no map id; zero corpus tasks. |
| fluid cleanliness classes (AS4059 particle count) | c, e | No sae/iso cleanliness id in map; fod-control owns shop-floor FOD prevention context; zero corpus tasks. |

## Closed veins (owner leaf per vein, reaffirmed FRESH)

- Disposition / MRB: nonconformance-control (disposition record five elements, MRB
  authority for repair and use-as-is, re-verification). Closed.
- CAPA / root cause: corrective-action (8D, five whys, containment, effectiveness;
  tags include preventive-action). Closed.
- SPC: statistical-process-control (X-bar R, Cp/Cpk, Western Electric),
  cusum-ewma-monitoring (small shifts), attribute-control-charts (p/np/c/u),
  individuals-and-moving-range-chart (single measurement per lot, destructive
  testing, bond or coating lots). Closed.
- MSA: measurement-systems-analysis (range method umbrella with variable versus
  attribute triage and calibration versus MSA scope), gage-rr-anova, gage-linearity-
  bias-study, attribute-agreement-analysis (Cohen/Fleiss kappa). Closed.
- Sampling: acceptance-sampling (single attribute, OC curve), variables-acceptance-
  sampling (k-method and M-method both inside the leaf). Closed.
- FAI: first-article-inspection, ballooning, delta-fai, fai-revalidation,
  additive-manufacturing-qualification (AM FAI), key-characteristic-management
  (variation plan). Closed.
- NDT: 12 method/application leaves + ndt-method-selection + ndt-personnel-
  qualification. Radiography, UT, ET, PT, MT, VT (borescope aperture, magnification,
  illuminance), AE (Kaiser/Felicity, source location), CT, shearography,
  thermography, leak testing (helium conversion, scc), computed tomography porosity.
  Closed.
- Special processes: special-process-qualification (change classification,
  requalification triggers, NADCAP evidence) + welding-qualification (WPS/PQR heat
  input, preheat/interpass, coupon matrix). Closed.
- Assembly: fastener-installation-quality, solid-rivet-installation-quality,
  ewis-installation-quality (fill ratio, voltage drop, bend radius). Closed.
- Composites processing: layup-cure (ply book, cure cycle, Arrhenius degree of cure,
  Tg, C-scan). Closed.
- Supplier / counterfeit / calibration / document control / audit / management
  review / FOD / order review / risk: one owner each. Closed.
- CMM and dimensional metrology seam: standards-map-blocked (no iso-15530,
  asme-b89.4.x, b46.1, b1-series ids). Not reopened per brief. Closed.

## Method notes

Probe steps executed: (1) find enumeration of all 48 leaves; (2) frontmatter fence
dump of all 48 (description, standards, tags); (3) family router read (48 table
rows, guidance bullets); (4) standards-map.yaml id dump (30 ids, helper at /tmp);
(5) zero-owner grep battery across the whole skills tree (623 SKILL.md files, helper
at /tmp/w45_grep.py) covering 60+ plausible gap tokens from SPC, MSA, sampling,
disposition, NDT, metrology, special processes, QMS clause functions, lean and
miscellaneous seams; (6) targeted fence reads of 14 sibling leaf bodies for seam
keywords; (7) corpus demand check over all 1238 eval/hit1-corpus.yaml tasks
(helper at /tmp/w45_t4_corpus2.py): zero tasks touch any declined near-miss token;
(8) git status clean before and after; no files modified outside this receipt.

Recheck reminders for future waves: destructive/nested GRR is the only methodically
real but decline-justified near-miss; reopen only if the MSA umbrella fence changes,
if an aiag-style published deterministic anchor is added to the corpus, or if
natural-language corpus demand for destructive gage studies appears.

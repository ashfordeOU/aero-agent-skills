# Wave-47 leaf spec: virtual-deadline-scheduling (avionics, fsw pack)

- Path: skills/avionics/fsw/virtual-deadline-scheduling/
- Pack: fsw (present siblings avionics/fsw/real-time-scheduling,
  avionics/fsw/mixed-criticality-scheduling, avionics/fsw/
  shared-resource-access-control, avionics/fsw/aperiodic-server-
  scheduling, avionics/fsw/deadline-monotonic-scheduling,
  avionics/fsw/cfs-architecture, avionics/fsw/fprime-component;
  adjacent fences avionics/do178c/planning (software level and DAL
  determination) and avionics/ima/ima-partitioning (partition window
  schedules and port latency)). AV 47 probe receipt task-1 rank 1 GO;
  0 owners verified whole-tree at HEAD a4ae6d1e (the wave-47 brief
  hash a544f421 plus one ops close-out FIX that touches no skills/
  path, per the receipt).
- Claim fences (quoted from the sibling frontmatter and bodies at
  wave-46 landing and re-verified at spec time; the nearest owners
  fence out the dual-criticality EDF branch, which is the exact gap
  this leaf closes):
  - mixed-criticality-scheduling (this pack, wave 46) is the
    FIXED-PRIORITY fence of the dual-criticality model: its domain
    quick reference lines 43-45 read "Priority order: the task list
    IS the fixed-priority order, index 0 the highest priority,
    deadlines non-decreasing (deadline-monotonic order). Higher-
    priority set hp(i) = {j : j < i}." Its model is the AMC-rtb
    fixed-point response-time bound over the same C_LO/C_HI pair
    (Baruah, Burns and Davis, RTSS 2011, over the Vestal model),
    and its related-leaves line (179-180) pins the deadline shape:
    "per-task deadlines D not equal to T with release jitter, for a
    single execution-time estimate; this leaf stays on the
    implicit-deadline (D = T) sets." Its pitfall (lines 209-212)
    routes single-estimate sets away: "Applying this leaf to a
    single-estimate (C, T) task set: a task with no HI estimate
    belongs to avionics/fsw/real-time-scheduling; this leaf's model
    requires the C_LO/C_HI pair and criticality tag on every task."
    Nothing in the landed leaf claims an EDF schedule, a virtual
    deadline or a demand condition: the sibling analyzes the task
    list as a fixed-priority order and never shortens a deadline.
    The gap this leaf closes: the EDF branch of the SAME
    dual-criticality model, where the scheduler is EDF, every HI
    task runs at a shortened virtual deadline x*T in LO mode, and
    the set is admitted by closed-form per-mode demand conditions
    (Baruah, Bonifaci, D'Angelo, Li, Marchetti-Spaccamela, Megow
    and Stougie, "Scheduling Real-Time Mixed-Criticality Jobs",
    IEEE Transactions on Computers 61(8):1140-1152, 2012; public
    science, summary-only), which the fixed-priority sibling cannot
    express at all.
  - real-time-scheduling (this pack) is the SINGLE-EXECUTION-TIME
    fence: its model is one (C, T) pair per task with implicit
    deadline D = T, and its EDF verdict exists only there. Its
    domain quick reference lines 61-63 read "EDF feasibility
    (implicit deadlines): U <= 1 is necessary and sufficient,
    because EDF is optimal among all scheduling algorithms on a
    single processor." Its scope note (lines 69-73) is explicit:
    "Scope notes: WCET estimation, jitter and blocking analysis,
    and arbitrary-deadline response-time extensions are out of
    scope; the model is the classic implicit-deadline periodic task
    set. ARINC 653 partition schedule windows and message bus
    response windows are not this leaf." and its workflow line
    (94-95) pins the verdict surface: "Check the EDF alternative:
    edf_feasible(tasks) reports whether U <= 1, which for
    implicit-deadline sets is a complete EDF test." There is no
    C_LO/C_HI pair, no criticality mode and no shortened deadline
    anywhere in its model; a dual-criticality set whose HI task can
    overrun its LO estimate cannot be admitted by the sibling at
    all, and its edf_feasible full-utilization verdict is never
    claimed by this leaf.
  - do178c/planning (adjacent, level side) owns software level and
    DAL determination: its frontmatter description trigger reads
    "determine the software level or DAL (A-E) from failure-
    condition severity" and "software level determination, DAL
    assignment". The new leaf stays on scheduling tokens, refers to
    the estimates as C_LO/C_HI execution-time estimates, and never
    claims level-determination tokens. The DO-178C A-E software
    level scheme gives the criticality semantics as reference
    context only (the Vestal/EDF-VD criticality models are
    DO-178B/C DAL inspired); no level is ever determined here and
    no standard text is reproduced.
  - The family router routes the EDF branch to the single-estimate
    leaf and criticality questions to the AMC leaf only: line 151
    "Real-time scheduling feasibility questions (rate monotonic,
    response time analysis, earliest deadline first, Liu-Layland
    bound) route to the fsw real-time-scheduling sub-skill" and
    line 172 "Mixed-criticality scheduling questions (AMC
    response-time analysis with a dual-criticality execution-time
    estimate per task, hi- and lo-criticality-mode response times,
    criticality mode change) route to the fsw mixed-criticality-
    scheduling sub-skill; single-execution-time implicit-deadline
    feasibility stays with real-time-scheduling." No router row and
    no leaf claims a dual-criticality EDF or virtual-deadline
    analysis; the seam is unrouted and unowned. Build-time
    additions required (wave-45/46 precedent): one scope fence line
    in real-time-scheduling, one related-leaf line in mixed-
    criticality-scheduling, plus one avionics router row pointing
    dual-criticality EDF questions to the new leaf.
  - Whole-tree greps at prep (probe receipt gate (a), fresh at HEAD
    a4ae6d1e): the tokens edf-vd and virtual[- ]deadline return
    ZERO matches across every skills/ SKILL.md and eval/ fragment
    (grep exit 1; the only bare-word "virtual" hits tree-wide are
    GD&T "virtual condition" and AFDX "virtual link", unrelated),
    the tokens amc-max and adaptive[- ]mixed[- ]criticality return
    ZERO matches, and eval/hit1-corpus.yaml carries no edf-vd,
    virtual-deadline or dual-criticality-EDF task row over all 1286
    expected_skill rows. GENUINE avionics/fsw gap (probe receipt
    task-1, verified zero-owner, GO rank 1): no leaf owns the
    dual-criticality EDF / virtual-deadline analysis that the
    fixed-priority AMC sibling and the single-estimate EDF sibling
    cannot express.
- Standards id: do-178c (RTCA DO-178C, Software Considerations in
  Airborne Systems and Equipment Certification; the avionics software
  lifecycle context in which the scheduling analysis artifact is
  recorded), reference-only and present in standards-map.yaml (grep
  'id: do-178c' at line 61, re-verified at spec time). Ledger
  Standard: do-178c.
- Family: avionics

## Claim

Decide the offline schedulability of an avionics flight software task
set under the dual-criticality (two-criticality) execution-time model
scheduled by EDF-VD, the virtual-deadline scheduling algorithm of
Baruah et al. 2012 (this leaf writes the algorithm name edf-vd
throughout). Each task is a dict {name, criticality, C_LO,
C_HI, T} in one time unit: criticality "LO" or "HI", a low-criticality
execution-time estimate C_LO and a high-criticality estimate C_HI with
C_HI at least C_LO, and period T with the implicit deadline D = T. A
LO task carries no high estimate, so its C_HI must equal its C_LO.
There is no priority order: EDF is priority-free and any task list
order is accepted. The leaf computes the three closed-form per-mode
demand sums over the estimates: a = sum over LO tasks of C_LO / T
(the LO-mode demand of the LO tasks), b = sum over HI tasks of C_LO /
T (the LO-mode demand of the HI tasks) and c = sum over HI tasks of
C_HI / T (the HI-mode demand of the HI tasks), reports the total
LO-mode demand U_LO = a + b and the HI-mode demand U_HI = c, then
derives the common virtual-deadline factor x = b / (1 - a) by which
every HI task's deadline is shortened in LO mode (each HI task runs
at the virtual deadline x*T while the system is in LO mode; LO tasks
keep their implicit deadlines). The set is feasible when both
deterministic closed-form demand conditions hold at that factor: the
LO-mode condition a + b / x <= 1 (with the canonical factor this is
exactly U_LO <= 1, the EDF demand density of the virtual-deadline
LO-mode schedule) and the HI-mode condition c + a*x <= 1 (the demand
condition after the LO to HI criticality-mode change, when LO jobs
are dropped and HI jobs must complete by their real deadlines even
when they overrun their LO budgets). A set with no HI task needs no
tightening: x = 1 and the verdict collapses to a <= 1, the classic
implicit-deadline EDF verdict of the pack sibling on the same values.
No valid factor exists when the LO tasks alone saturate the processor
(a >= 1 with HI tasks present): x is reported as None and the verdict
is False. Produces the per-mode demand sums (a, b, c), the total
LO-mode and HI-mode demands (U_LO, U_HI), the virtual-deadline factor
x, the per-HI-task virtual deadlines x*T, the LO-mode feasible
verdict, the HI-mode feasible verdict, and the whole-set edf-vd
feasible verdict. The DO-178C software level scheme A-E frames which
tasks need the higher assurance estimate as reference-only context;
this leaf never determines a software level or DAL (avionics/do178c/
planning owns level determination) and never reproduces standard
text. Does NOT do: the AMC-rtb fixed-point response-time analysis of
the wave-46 sibling (fixed-priority interference arms charged at
C_LO and C_HI, the hi-criticality-mode-rta and lo-criticality-mode-
rta surfaces) (avionics/fsw/mixed-criticality-scheduling); the
single-estimate utilization, Liu-Layland bound, RM and plain EDF
full-utilization verdicts of a (C, T) set, including edf_feasible
(avionics/fsw/real-time-scheduling); per-task deadlines beyond the
implicit D = T with release jitter and the deadline-monotonic
priority assignment (avionics/fsw/deadline-monotonic-scheduling,
which is why no D key exists in the task dict and no order is
imposed here); shared-resource ceiling or inheritance blocking terms
(avionics/fsw/shared-resource-access-control); polling, deferrable
or sporadic server budgets for aperiodic jobs (avionics/fsw/
aperiodic-server-scheduling); the exact demand-bound schedulability
test of the generalized model (Ekberg and Yi, Real-Time Systems
50(1):48-86, 2014, a pseudo-polynomial scan over interval lengths;
reference-only here, this leaf implements the closed-form utilization
test of Baruah et al. 2012); software level and DAL determination
(avionics/do178c/planning); partition window schedules and port
latencies (avionics/ima/ima-partitioning); software bus routing and
cyclic rate-group layout (avionics/fsw/cfs-architecture, avionics/
fsw/fprime-component). Execution-time estimates C_LO and C_HI are
inputs, never estimated; the model is the single-processor preemptive
EDF schedule with synchronous releases, implicit deadlines and one
time unit per task set; offsets, release jitter, blocking, non-
preemptive execution and multiprocessor scheduling are out of scope;
the test is the deterministic closed-form Baruah et al. 2012 test
(sufficient, not exact; its published magnitude is the 4/3
processor-speedup factor for the dual-criticality case), never the
single-estimate full-utilization verdict of the pack sibling.

## Model (implement exactly)

Pure stdlib, closed form (plain division and summation only, no
iteration, no ceil, no randomness), deterministic. Module constant:
TOL = 1e-12 (the comparison tolerance used by every verdict; a
condition holds when its left side is at most its right side plus
TOL). No imports beyond math.

Task dict shape (validated identically by every public function):
{name, criticality, C_LO, C_HI, T}, name optional, all values in one
time unit, criticality exactly "LO" or "HI". Every function rejects,
with ValueError, an empty task list, a non-dict entry, a missing
C_LO/C_HI/T/criticality key, a boolean or non-positive C_LO, C_HI or
T, C_HI below C_LO, a LO task whose C_HI differs from C_LO, and a
criticality that is not "LO" or "HI". There is NO deadline key (the
deadline is implicit D = T) and NO order requirement: EDF schedules
without priorities, so any list order is accepted and no
deadline-monotonic or other ordering check exists.

Defining relations (pin these exactly; every function derives from
them):
- Per-mode demand sums over the task list, one time unit:
  a = u_lo_lo = sum over tasks with criticality LO of C_LO / T,
  b = u_hi_lo = sum over tasks with criticality HI of C_LO / T,
  c = u_hi_hi = sum over tasks with criticality HI of C_HI / T,
  U_LO = a + b (total LO-mode demand), U_HI = c (HI-mode demand).
- Virtual-deadline factor: x = b / (1 - a) when the HI set is
  non-empty and a < 1 (every HI task runs at the virtual deadline
  x*T in LO mode; x <= 1 is exactly U_LO <= 1, since x <= 1 iff
  b <= 1 - a). x = 1.0 (no tightening) when the HI set is empty
  (b = 0, which cannot happen otherwise because every C_LO is
  positive). x is None when a >= 1 with at least one HI task: the
  LO tasks alone saturate the processor and no common factor exists.
- LO-mode condition (Baruah et al. 2012 Theorem 1 form, the EDF
  demand density of the virtual-deadline LO-mode schedule):
  a + b / x <= 1. At the canonical factor this holds with equality
  (a + b / x = a + (1 - a) = 1 when HI tasks exist) and the
  substantive requirement is x <= 1, i.e. U_LO <= 1; with no HI
  task the condition is a <= 1 (the pack sibling's implicit-deadline
  EDF verdict on the same (C, T) values).
- HI-mode condition (Baruah et al. 2012 Theorem 2 form, the demand
  condition after the LO to HI criticality-mode change): c + a*x
  <= 1. Equivalent closed forms used to cross-check: the
  multiprocessor EDF-VD restatement a <= (1 - c) / (1 - c + b) and
  the all-HI-switch worst-case reduction of the FMC-EDF-VD
  feasibility condition. The a*x term is the virtual-deadline
  tightening cost: HI-mode feasibility requires the HI jobs to have
  been forced early enough in LO mode (smaller x helps the HI
  condition; larger x helps the LO condition; x = b / (1 - a) is
  the canonical smallest factor that keeps the LO-mode density at
  most 1).
- Verdicts: LO mode feasible iff the LO-mode condition holds (False
  when x is None); HI mode feasible iff the HI-mode condition holds
  (an all-LO set has an empty HI guarantee list, c = 0, and a
  vacuously True HI verdict); the whole-set verdict is LO feasible
  AND HI feasible. The test is the deterministic closed-form Baruah
  et al. 2012 test, sufficient not exact, reported as the leaf
  verdict.
- C_LO/C_HI are inputs (execution-time estimates, one time unit),
  never derived; C_HI equal to C_LO is the no-overrun case.

Functions:
- utilizations(tasks) -> dict
  Returns {"u_lo_lo": a, "u_hi_lo": b, "u_hi_hi": c, "u_lo": a + b,
  "u_hi": c}. ValueErrors of the task shape.
- virtual_deadline_factor(tasks) -> float or None
  Returns x = b / (1 - a) when HI tasks exist and a < 1, 1.0 when no
  HI task exists, None when a >= 1 with at least one HI task.
  ValueErrors of the task shape.
- virtual_deadlines(tasks) -> dict or None
  Returns {task name: x * T} for every HI task (the per-task virtual
  deadlines used in LO mode), an empty dict for an all-LO set, None
  when no factor exists (x is None). Names: a task without a "name"
  key is keyed "task". ValueErrors of the task shape.
- lo_mode_feasible(tasks) -> bool
  True iff the LO-mode condition a + b / x <= 1 holds (equivalently
  x <= 1 when HI tasks exist, a <= 1 when none do). ValueErrors of
  the task shape.
- hi_mode_feasible(tasks) -> bool
  True iff the HI-mode condition c + a*x <= 1 holds; vacuously True
  for an all-LO set. ValueErrors of the task shape.
- edf_vd_report(tasks) -> dict
  Returns {"u_lo_lo", "u_hi_lo", "u_hi_hi", "u_lo", "u_hi", "x" (the
  factor or None), "lo_feasible", "hi_feasible", "feasible",
  "virtual_deadlines" (dict or None)}. ValueErrors of the task
  shape.
- feasible(tasks) -> bool
  Convenience: edf_vd_report(tasks)["feasible"]. Same ValueErrors.

Identities to test (closed form, exact; checkable without the builder
module):
- All-LO reduction: when every task is LO-criticality the analysis
  reduces to the classic implicit-deadline EDF verdict a <= 1 over
  the single (C_LO, T) values, x reports 1.0 and the virtual-
  deadline dict is empty. Real anchors: the pack sibling's classic
  sets at C_LO = C give u_lo 0.83333333333333326 on [(1, 3),
  (1, 4), (2, 8)] with feasible True, and u_lo 1.3523809523809525
  on [(2, 3), (2, 5), (2, 7)] with feasible False.
- HI-only reduction: when every task is HI-criticality (a = 0) the
  verdict collapses to c <= 1, the plain EDF feasibility of the HI
  set at its C_HI estimates. Real anchor: [(1.0, 2.0, 5.0),
  (2.0, 4.0, 10.0)] gives u_lo_lo 0, u_hi 0.80000000000000004,
  x 0.40000000000000002, feasible True.
- No-overrun collapse: when every task carries C_HI = C_LO the
  whole verdict is exactly U_LO <= 1 (the HI condition becomes
  c + a*x = x <= 1 with c = b). Real anchor: the collapse variant
  of the worked set A gives u_lo 0.60000000000000009, x 0.5, HI
  demand c + a*x 0.5, feasible True.
- Factor bounds: 0 < x <= 1 iff U_LO = a + b <= 1; x reports None
  iff a >= 1 with at least one HI task (the LO tasks alone
  saturate the processor).
- LO-mode density identity: at the canonical factor the LO-mode
  density a + b / x equals 1 exactly when HI tasks exist (printed
  1 on the real anchor runs).
- Multiprocessor-form equivalence: on every HI-bearing set,
  a <= (1 - c) / (1 - c + b) holds iff c + a*x <= 1 holds. Real
  anchor on set A: (1 - c) / (1 - c + b) = 0.33333333333333326,
  above a 0.20000000000000001.
- Determinism: identical outputs run to run and under both
  interpreters; no randomness; no imports beyond math; TOL fixed
  at 1e-12; every comparison tolerant.
- ValueErrors across the module: empty list, missing key, boolean
  or non-positive C_LO/C_HI/T, C_HI below C_LO, LO task C_HI above
  C_LO, unknown criticality word.

## Worked example

Task set A, three avionics fsw processes in ms, any list order (EDF
is priority-free), implicit deadlines D = T:
- flight-control: criticality HI, C_LO 1.0, C_HI 2.0, T 5.0 (a HI
  task whose overrun past its 1 ms LO budget forces the
  criticality-mode change; its LO-mode deadline is shortened to the
  virtual deadline x*T);
- health-monitor: criticality HI, C_LO 2.0, C_HI 4.0, T 10.0 (the
  second HI task, same virtual-deadline factor);
- guidance: criticality LO, C_LO 2.0, C_HI 2.0, T 10.0 (a LO task,
  dropped after the criticality mode change, so only its C_LO/T
  contributes to the per-mode sums).

All values below are REAL outputs of the prep anchor script
anchor_virtual_deadline_scheduling.py (pure stdlib, closed form,
exit 0, no RNG, printed once and quoted as printed; byte-identical
under both interpreters):

- Per-mode demand sums (module output): the worked set A gives
  u_lo_lo 0.2 (guidance only: 2.0/10.0), u_hi_lo 0.4 (1.0/5.0 +
  2.0/10.0 over the HI tasks), u_hi_hi 0.8 (2.0/5.0 + 4.0/10.0),
  u_lo 0.6000000000000001 and u_hi 0.8. The LO-mode demand of the
  whole set is 0.6, at most 1.
- Virtual-deadline factor (module output): x = 0.5 exactly
  (0.4 / (1 - 0.2)). The LO-mode density identity holds with
  equality: a + b/x prints 1. The LO-mode condition is satisfied.
- HI-mode demand (module output): c + a*x = 0.90000000000000002,
  at most 1, so the HI-mode condition holds after the
  criticality-mode change: flight-control and health-monitor can
  overrun to their C_HI estimates and still meet their real
  deadlines.
- Per-task virtual deadlines (module output): virtual_deadlines
  gives {flight-control: 2.5, health-monitor: 5.0}, i.e. x*T =
  0.5 * 5.0 = 2.5 ms and 0.5 * 10.0 = 5.0 ms. While the system is
  in LO mode each HI job must finish its C_LO work by its virtual
  deadline, which forces the early progress the HI-mode condition
  needs.
- Multiprocessor-form cross-check on set A (module output): the
  equivalent restatement (1 - c) / (1 - c + b) evaluates to
  0.33333333333333326, above a 0.20000000000000001, consistent
  with the HI-mode condition c + a*x = 0.9 <= 1.
- Whole-set verdict: edf_vd_report(SET_A) gives lo_feasible True,
  hi_feasible True, feasible True: the set is admitted by the
  edf-vd test in both modes.
- Task set B (HI-mode overload, the mode-change verdict): guidance
  LO C_LO 3.0, T 10.0; flight-control HI C_LO 1.0, C_HI 3.0,
  T 10.0; health-monitor HI C_LO 2.0, C_HI 6.0, T 10.0. Module
  output: u_lo_lo 0.3, u_hi_lo 0.30000000000000004, u_hi_hi
  0.8999999999999999, u_lo 0.6000000000000001, u_hi
  0.8999999999999999. The LO-mode condition holds (density
  a + b/x prints 1, x = 0.42857142857142866), so lo_feasible is
  True. The HI-mode condition fails: c + a*x =
  1.0285714285714285, strictly above 1, so hi_feasible is False
  and the whole verdict is False. The instructive overload: the
  HI-mode demand c = 0.9 is at most 1 on its own, yet the set is
  not admitted, because the a*x tightening term 0.1285714285714286
  shows the LO tasks leave too little early slack for the mode
  change. Virtual deadlines print 4.2857142857142865 ms for both
  HI tasks (x * 10.0).
- Task set C (LO-mode overload, the no-factor verdict): guidance
  LO C_LO 8.0, T 10.0; trim LO C_LO 1.0, T 5.0; flight-control HI
  C_LO 1.0, C_HI 2.0, T 10.0. Module output: u_lo_lo 1.0 (the LO
  tasks alone saturate the processor), u_hi_lo 0.1, u_hi_hi 0.2,
  u_lo 1.1. The factor x reports None, lo_feasible False,
  hi_feasible False, feasible False: no common virtual-deadline
  factor exists and the edf-vd test rejects the set.
- Identity anchors (module output): the all-LO set [(1, 3),
  (1, 4), (2, 8)] gives u_lo 0.83333333333333326, x 1, feasible
  True with an empty virtual_deadlines dict; the all-LO overload
  [(2, 3), (2, 5), (2, 7)] gives u_lo 1.3523809523809525,
  feasible False; the HI-only set [(1.0, 2.0, 5.0), (2.0, 4.0,
  10.0)] gives u_hi 0.80000000000000004, x 0.40000000000000002,
  feasible True; the no-overrun collapse variant of set A (every
  C_HI equal to C_LO) gives u_lo 0.60000000000000009, x 0.5, HI
  demand c + a*x 0.5, feasible True.
- Determinism: two consecutive edf_vd_report(SET_A) runs return
  identical dicts; the anchor exits 0 and its internal asserts all
  pass.
- ValueErrors with real messages (module output, quoted as
  printed): an empty list raises "task list must be a non-empty
  list"; a missing C_HI raises "task 0 missing key(s) C_HI";
  C_LO = 0 raises "C_LO must be a positive number, got 0.0"; C_HI
  below C_LO raises "C_HI must be at least C_LO, got C_HI 0.5 with
  C_LO 1.0"; a LO task with C_HI above C_LO raises "a
  LO-criticality task carries no high estimate: C_HI must equal
  C_LO, got C_HI 5.0 with C_LO 1.0"; an unknown criticality word
  raises "criticality must be 'LO' or 'HI', got 'MED'"; a boolean
  C_LO raises "C_LO must be a positive number, got True".

Run the anchor and take the real outputs as assert targets; the
anchors above are real prep outputs of the anchor script (stdlib,
closed form, exit 0, no randomness, byte-identical under both
interpreters).

## Validation list (contract test must include)

1. Worked set A asserts within 1e-6 relative: edf_vd_report(SET_A)
   gives u_lo_lo 0.2, u_hi_lo 0.4, u_hi_hi 0.8, u_lo 0.6, u_hi 0.8,
   x 0.5, lo_feasible True, hi_feasible True, feasible True;
   virtual_deadlines equals {flight-control: 2.5, health-monitor:
   5.0} within 1e-9; the LO-mode density a + b/x equals 1.0 within
   1e-9; the HI-mode demand c + a*x equals 0.9 within 1e-9.
2. Worked set B asserts within 1e-6 relative: u_lo_lo 0.3,
   u_hi_lo 0.3, u_hi_hi 0.9, x 0.42857142857142866, lo_feasible
   True, hi_feasible False, feasible False; the HI-mode demand
   c + a*x equals 1.0285714285714285 within 1e-9, strictly above
   1; the per-task virtual deadlines equal 4.2857142857142865
   within 1e-9 for both HI tasks.
3. Worked set C asserts: u_lo_lo 1.0, u_hi_lo 0.1, u_hi_hi 0.2,
   x is None, lo_feasible False, hi_feasible False, feasible False,
   virtual_deadlines is None.
4. All-LO identity: every task LO-criticality collapses to the
   classic verdict: [(1, 3), (1, 4), (2, 8)] gives u_lo
   0.83333333333333326 within 1e-9, x 1.0, empty virtual_deadlines
   dict, feasible True; the overload [(2, 3), (2, 5), (2, 7)]
   gives u_lo 1.3523809523809525 within 1e-9, feasible False.
5. HI-only reduction: a = 0 collapses the verdict to c <= 1:
   [(1.0, 2.0, 5.0), (2.0, 4.0, 10.0)] gives u_lo_lo 0.0, u_hi
   0.8 within 1e-9, feasible True; an HI-only set with c above 1
   (for example C_HI 6.0 and 4.0 on the same periods) gives
   feasible False.
6. No-overrun collapse: every C_HI equal to C_LO makes the verdict
   exactly U_LO <= 1; the collapse variant of set A gives u_lo 0.6
   within 1e-9, x 0.5, HI-mode demand 0.5 within 1e-9, feasible
   True.
7. Multiprocessor-form equivalence: on set A, (1 - c) / (1 - c + b)
   equals 0.33333333333333326 within 1e-9 and is at least a; on
   every HI-bearing validation set, (1 - c) / (1 - c + b) >= a
   holds iff hi_mode_feasible holds.
8. Factor discipline: x reports 1.0 on an all-LO set; x reports
   None exactly when a >= 1 with at least one HI task (set C); on
   every factor-bearing set 0 < x <= 1 holds and u_lo = a + b is
   at most 1; lo_mode_feasible matches x <= 1 on HI-bearing sets.
9. HI guarantee scope: an all-LO set returns hi_feasible True
   (vacuous), c 0.0 and an empty virtual_deadlines dict.
10. All ValueErrors enumerated in the identity list raise from the
    named public function with the real messages quoted in the
    Worked example: empty list, missing key, boolean or
    non-positive C_LO/C_HI/T, C_HI below C_LO, LO task C_HI above
    C_LO, unknown criticality word.
11. Determinism: identical outputs run to run and under both
    interpreters; no randomness anywhere; no imports beyond math;
    module constant TOL = 1e-12. No exact-float equality on
    computed sums; use assertAlmostEqual/math.isclose everywhere.
12. Run the deterministic contract test offline (no network); it
    exits 0. Test passes under BOTH interpreters (/usr/bin/python3
    3.9.6 and ~/.pyenv/versions/3.13.12/bin/python3).

## Corpus fragment (eval/hit1-wave47-virtual-deadline-scheduling.yaml)

Query 1 (copy verbatim):
  "run the edf-vd virtual-deadline-scheduling analysis on the
  dual-criticality flight-control task set with C_LO and C_HI
  execution time estimates: assign each HI task its virtual deadline
  factor x and verify the lo-criticality-mode and hi-criticality-mode
  feasibility of the set after the criticality mode change"
  intent: "avionics/fsw; virtual-deadline-scheduling: the
  dual-criticality execution time estimates C_LO and C_HI per task,
  the common virtual-deadline factor x assigned to the HI tasks, the
  lo-criticality-mode demand condition over the LO-mode estimates and
  the hi-criticality-mode demand condition after the criticality mode
  change"
  expected_skill: "avionics/fsw/virtual-deadline-scheduling"
Query 2 (copy verbatim):
  "check the virtual-deadline-factor schedulability of the
  two-criticality process set under edf-vd: compute the per-task
  virtual deadlines x*T for the HI tasks and confirm both the LO-mode
  and the HI-mode demand conditions hold for the chosen factor"
  intent: "avionics/fsw; the virtual-deadline factor x and the
  per-HI-task virtual deadlines x*T of the two-criticality process
  set under edf-vd, then the LO-mode and the HI-mode demand
  conditions for the chosen factor"
  expected_skill: "avionics/fsw/virtual-deadline-scheduling"
Task ids: w47-virtual-deadline-scheduling-1 and -2. Prep grep (run
at spec time by the probe): each of the tokens edf-vd and
virtual[- ]deadline returns ZERO matches in every skills/ SKILL.md
and in eval/hit1-corpus.yaml (grep exit 1), and the corpus substring
scan for edf-vd or virtual-deadline task rows over all 1286
expected_skill rows is empty, so the queries are collision-free; the
sibling tasks route on single-execution-time periodic language
(real-time-scheduling), fixed-priority AMC-rtb and criticality-mode
response-time language (mixed-criticality-scheduling), blocking
language (shared-resource-access-control), server-budget language
(aperiodic-server-scheduling), per-task-deadline and jitter language
(deadline-monotonic-scheduling) and level-determination language
(do178c/planning), none of which carry dual-criticality EDF or
virtual-deadline content. The corpus tasks never reuse the
real-time-scheduling owned phrases "earliest deadline first", "cpu
utilization" or "worst case execution time". Add one fence line to
real-time-scheduling, one related-leaf line to mixed-criticality-
scheduling and one router row to skills/avionics/SKILL.md at build
time pointing dual-criticality EDF / virtual-deadline scheduling
questions to the new leaf (the aperiodic-server-scheduling,
deadline-monotonic-scheduling and mixed-criticality-scheduling
precedents).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must decide the offline
schedulability of an avionics flight software task set under the
dual-criticality execution-time model scheduled by edf-vd
virtual-deadline scheduling:" and include the outputs in the Claim
order (the per-mode demand sums, the virtual-deadline factor x, the
per-HI-task virtual deadlines x*T, the lo-criticality-mode feasible
verdict, the hi-criticality-mode feasible verdict after the
criticality mode change, the whole-set edf-vd feasible verdict),
then close with the Trigger list. Refer to the estimates as C_LO and
C_HI execution-time estimates throughout and to the algorithm as
edf-vd / virtual-deadline scheduling throughout; never use the bare
single words criticality, dal, software-level, wcet or
worst-case-execution-time as tags or standalone description terms,
never use the sibling-owned phrases "earliest deadline first", "cpu
utilization" or "worst case execution time" in any description,
trigger or tag, never claim the AMC-rtb analysis of the wave-46
sibling, and never reproduce DO-178C text (reference-only). First
tag: virtual-deadline-scheduling. Metadata tags EXACTLY as the probe
receipt gate (f) lists them, nothing else: edf-vd-analysis,
virtual-deadline-factor, hi-criticality-mode-edf,
lo-criticality-mode-edf, dual-mode-demand-check. 50-150 words,
<=1000 chars, no em dash, action verb present. Recommended wording
(129 words, 948 chars, verified at spec time):

"Use when you must decide the offline schedulability of an avionics
flight software task set under the dual-criticality execution-time
model scheduled by edf-vd virtual-deadline scheduling: each task
carries the C_LO and C_HI execution-time estimates with C_HI at
least C_LO and the implicit-deadline period T, sum the per-mode
demand contributions of the LO and HI tasks, derive the common
virtual-deadline factor x for the HI tasks, and check the
lo-criticality-mode and the hi-criticality-mode demand conditions
after the criticality mode change. Produces the per-mode demand
sums, the virtual-deadline factor x, the per-HI-task virtual
deadlines x*T, the lo-criticality-mode feasible verdict, the
hi-criticality-mode feasible verdict, and the whole-set edf-vd
feasible verdict. Trigger: edf vd scheduling, virtual deadline
scheduling, virtual deadline factor, dual criticality mode change,
lo criticality mode demand, hi criticality mode demand."

FORBIDDEN TOKENS (belong to siblings or the level side): the bare
single words criticality, dal, software-level, wcet and
worst-case-execution-time as tags or standalone description terms
(never as the claim surface; the estimates are C_LO/C_HI
execution-time estimates); earliest-deadline-first, cpu-utilization,
liu-layland-bound, rate-monotonic-scheduling, fixed-priority-
scheduling, response-time-analysis, edf-feasibility and any query or
description whose only content is a single-execution-time
implicit-deadline verdict with no C_LO/C_HI pair and no criticality
mode (real-time-scheduling); amc-rtb, amc-rtb-analysis, amc-max,
adaptive-mixed-criticality, hi-criticality-mode-rta,
lo-criticality-mode-rta, criticality-mode-change-rta and any
fixed-point response-time claim over the C_LO/C_HI estimates, which
is the wave-46 sibling's AMC-rtb model and is never run here
(mixed-criticality-scheduling); constrained-deadline-rta,
arbitrary-deadline-rta, release-jitter-rta, dm-priority-assignment,
shorter-deadline-order and any per-task-deadline, release-jitter or
queued-job content (deadline-monotonic-scheduling);
priority-ceiling-protocol, priority-inheritance, worst-case-blocking,
stack-resource-policy, blocking-time-bound, schedulability-with-
blocking (shared-resource-access-control); sporadic-server,
deferrable-server, polling-server, server-capacity,
aperiodic-response-bound, server-budget (aperiodic-server-
scheduling); software-levels, dal and any software-level or DAL
determination language (do178c/planning); arinc-653, major-frame,
partition-configuration-table, sampling-port, queuing-port,
health-monitoring (ima-partitioning); software-bus, publish-
subscribe, cfe, osal, rate-group, command-opcode, telemetry-channel
(cfs-architecture, fprime-component). Never the bare words
criticality, deadline, demand, factor, mode, edf, scheduling,
feasibility, task, analysis, utilization or level as standalone
metadata tags.

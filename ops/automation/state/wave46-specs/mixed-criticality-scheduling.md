# Wave-46 leaf spec: mixed-criticality-scheduling (avionics, fsw pack)

- Path: skills/avionics/fsw/mixed-criticality-scheduling/
- Pack: fsw (present siblings avionics/fsw/real-time-scheduling,
  avionics/fsw/shared-resource-access-control, avionics/fsw/
  aperiodic-server-scheduling, avionics/fsw/deadline-monotonic-
  scheduling, avionics/fsw/cfs-architecture, avionics/fsw/
  fprime-component; adjacent fences avionics/ima/ima-partitioning
  (partition window schedules and port latency), avionics/data-bus/
  mil-std-1553 (bus command/response windows) and avionics/do178c/
  planning (software level and DAL determination)). AV 46 probe
  receipt task-2 rank 1 GO; 0 owners verified whole-tree.
- Claim fences (quoted from the sibling frontmatter and bodies at
  prep, re-verified at spec time; the nearest owners fence out the
  dual-execution-time criticality-mode analysis, which is the exact
  gap this leaf closes):
  - real-time-scheduling (this pack) is the SINGLE-EXECUTION-TIME
    fence: its model is one (C, T) pair per task with implicit
    deadline D = T and RM priority by period. Its frontmatter
    description reads "Use when you must decide the offline
    schedulability of a periodic hard-real-time task set: compute the
    processor utilization of (C, T) tasks with implicit deadlines,
    apply the Liu-Layland utilization bound for rate-monotonic
    fixed-priority scheduling, run the exact iterative response-time
    analysis task by task, and test earliest-deadline-first
    feasibility with the full-utilization condition". Its scope note
    (lines 69-73) is explicit: "WCET estimation, jitter and blocking
    analysis, and arbitrary-deadline response-time extensions are out
    of scope; the model is the classic implicit-deadline periodic task
    set. ARINC 653 partition schedule windows and message bus response
    windows are not this leaf." and its pitfalls routing repeats it
    (lines 190-192): "Routing adjacent timing domains here: WCET
    estimation, jitter and blocking analysis, arbitrary-deadline
    extensions, ARINC 653 partition schedule windows
    (ima/ima-partitioning), and bus response windows
    (data-bus/mil-std-1553) are not this leaf's classic
    implicit-deadline periodic model." There is no C_LO/C_HI pair, no
    criticality mode, no mode change and no two-version execution
    time anywhere in its model, workflow, worked examples (sets A, B,
    C, D all carry a single C per task) or test contract. The gap
    this leaf closes: a task set whose HI task can overrun its LO
    budget, forcing the system out of the LO mode the sibling
    analyzes, cannot be admitted by the sibling at all.
  - shared-resource-access-control (this pack) is the BLOCKING-TERM-
    ONLY fence: its task model is dicts "with implicit deadline
    D = T" (body line 27), and its scope note (lines 63-67) routes
    plain feasibility away and pins execution budgets as inputs:
    "plain feasibility mathematics without the blocking term belongs
    to avionics/fsw/real-time-scheduling; WCET budgets are inputs,
    not outputs; this leaf does not model message or bus response
    windows." Its blocking term B_i is a shared-resource ceiling
    effect on one (C, T) model; no second execution-time estimate and
    no mode change exist in its equations.
  - deadline-monotonic-scheduling (this pack, wave 45) is the
    PER-TASK-DEADLINE fence: its claim covers "per-task relative
    deadlines D_i that are not the implicit D_i = T_i", release
    jitter and the arbitrary-deadline busy-period job scan; its
    implicit-deadline identity line 169 states "Implicit-deadline
    identity (D = T, J = 0): the pack sibling's sets reproduce
    exactly". It carries one C per task, no dual estimate and no
    mode change. This leaf admits only deadline-monotonic-ordered
    task lists with D no greater than T and never runs a jitter term
    or a queued-job scan; those surfaces stay with the wave-45
    sibling.
  - aperiodic-server-scheduling (this pack, wave 44) is the SERVER
    fence: its intro (line 26) exists because "the periodic-only
    model of the pack sibling cannot admit the event release at all",
    and it treats mode-change requests only as example event-driven
    jobs for a server budget. No criticality mode arithmetic lives in
    its budget sizing or response bounds.
  - do178c/planning (adjacent, level side) owns software level and
    DAL determination: its frontmatter description trigger reads
    "software level determination, DAL assignment" and its metadata
    tags include dal and software-levels. The new leaf must stay on
    scheduling tokens, refer to the estimates as C_LO/C_HI
    execution-time estimates, and never claim level-determination
    tokens. The DO-178C A-E software level scheme gives the
    criticality semantics as reference context only (the Vestal model
    is DO-178B/C DAL inspired); no level is ever determined here and
    no standard text is reproduced.
  - Whole-tree greps at prep (probe receipt gate (a), fresh at HEAD):
    the tokens mixed[- ]criticality, amc-rtb, amc-max, vestal,
    criticality-aware, dual-criticality, hi-mode and lo-mode return
    ZERO matches across every skills/ SKILL.md and eval/ fragment
    (grep exit 1), and grep -c of mixed criticality | mixed-
    criticality | amc-rtb | vestal over eval/hit1-corpus.yaml is 0.
    No corpus task routes on criticality-mode scheduling: the only
    "criticality" corpus rows are SES/ECSS level-determination tasks
    (all level/DAL flavored, none scheduling flavored). GENUINE
    avionics/fsw gap (probe receipt task-2, verified zero-owner, GO
    rank 1): no leaf owns the two-version C_LO/C_HI response-time
    analysis that the single-execution-time siblings cannot express.
- Standards id: do-178c (RTCA DO-178C, Software Considerations in
  Airborne Systems and Equipment Certification; the avionics software
  lifecycle context in which the scheduling analysis artifact is
  recorded), reference-only and present in standards-map.yaml (grep
  'id: do-178c' at line 61, re-verified at spec time). Ledger
  Standard: do-178c.
- Family: avionics

## Claim

Decide the offline schedulability of an avionics flight software task
set under the dual-criticality (two-criticality) execution-time model.
Each task is a dict {name, criticality, C_LO, C_HI, T, D} in one time
unit: criticality "LO" or "HI", a low-criticality execution-time
estimate C_LO and a high-criticality estimate C_HI with C_HI at least
C_LO, period T and relative deadline D no greater than T. A LO
task carries no high estimate, so its C_HI must equal its C_LO. The
task list is analyzed in fixed-priority order: index 0 is the highest
priority and the deadlines must be non-decreasing (the
deadline-monotonic order, which coincides with the rate-monotonic
period order on the implicit-deadline sets used below). The set is
checked in LO mode first, with the classic fixed-point response-time
analysis over the C_LO estimates for every task. Then, after the LO
to HI criticality-mode change, the HI tasks alone are checked with
the AMC-rtb fixed point (Baruah, Burns and Davis, "Response-Time
Analysis for Mixed Criticality Systems", RTSS 2011; the task model of
Vestal, "Preemptive Scheduling of Multi-Criticality Systems with
Varying Degrees of Execution Time Assurance", RTSS 2007; public
science, summary-only):

R_i(HI) = C_i(HI) + sum over higher-priority LO tasks j of
ceil(R_i / T_j) * C_j(LO) + sum over higher-priority HI tasks j of
ceil(R_i / T_j) * C_j(HI),

converged against each task's deadline: every higher-priority LO task
is charged its C_LO estimate (its jobs are dropped only after the
mode change) and every higher-priority HI task is charged its C_HI
estimate (overrun possible), and the fixed point is the deterministic
offline AMC-rtb response-time bound. A converged LO-mode response at
most D_i admits the task in LO mode; a converged HI-mode response at
most D_i admits the HI task after the mode change. The iteration is
monotone non-decreasing, so an iterate strictly past D_i can never
converge to a schedulable value and reports None (divergence), as
does a solve still moving after MAX_RTA_ITERATIONS; a diverged or
deadline-crossing task makes its mode infeasible. Produces the
per-task LO-mode response times and the LO-mode feasible verdict, the
HI-mode response times of the HI tasks under the AMC-rtb bound and
the HI-mode feasible verdict, the whole-set verdict (LO feasible and
HI feasible), and the divergence verdict when an iterate crosses a
deadline. The DO-178C software level scheme A-E frames which tasks
need the higher assurance estimate as reference-only context; this
leaf never determines a software level or DAL (avionics/do178c/
planning owns level determination) and never reproduces standard
text. Does NOT do: the single-estimate utilization, Liu-Layland
bound, RM, EDF and classic implicit-deadline response-time verdicts
of a (C, T) set (avionics/fsw/real-time-scheduling); shared-resource
ceiling or inheritance blocking terms in the fixed point
(avionics/fsw/shared-resource-access-control); polling, deferrable
or sporadic server budgets for aperiodic jobs
(avionics/fsw/aperiodic-server-scheduling); per-task deadlines beyond
D = T with release jitter, the deadline-monotonic priority assignment
function, arbitrary-deadline (D beyond T) busy-period job scans and
jitter terms in the fixed point (avionics/fsw/deadline-monotonic-
scheduling, which is why D no greater than T is enforced here);
software level and DAL determination (avionics/do178c/planning);
partition window schedules and port latencies (avionics/ima/
ima-partitioning); software bus routing and cyclic rate-group layout
(avionics/fsw/cfs-architecture, avionics/fsw/fprime-component); bus
command/response windows (avionics/data-bus/mil-std-1553). Execution
budgets C_LO and C_HI are inputs, never estimated; the model is the
single-processor fixed-priority preemptive schedule with synchronous
releases at the common critical instant, one time unit per task set;
offsets, release jitter and blocking are out of scope; the AMC-rtb
bound (not the tighter exact AMC or AMC-max variants) is the model.

## Model (implement exactly)

Pure stdlib, math.ceil only, closed form, deterministic. Module
constants: MAX_RTA_ITERATIONS = 100 (the per-solve fixed-point safety
cap; a solve that still moves after 100 passes reports None) and
CONVERGENCE_TOL = 1e-12 (an iterate that repeats within this
tolerance has converged). Every ceil term is the ceiling of an exact
rational quotient; compute ceil(a / b) as -(-a // b) when both
operands are ints, else math.ceil(a / b), and keep no floating-point
state in the iteration core beyond that division.

Task dict shape (validated identically by every public function):
{name, criticality, C_LO, C_HI, T, D}, name optional, all values in
one time unit, criticality exactly "LO" or "HI". Every function
rejects, with ValueError, an empty task list, a non-dict entry, a
missing C_LO/C_HI/T/D key, a boolean or non-positive C_LO, C_HI, T
or D, C_HI below C_LO, a LO task whose C_HI differs from C_LO, a
deadline D above T, a task list whose deadlines are not non-decreasing
(not in deadline-monotonic priority order), an index outside
[0, len(tasks)) from the per-index functions, and a HI-mode call on a
LO index.

Defining relations (pin these exactly; every function derives from
them):
- Priority order: the task list IS the priority order, index 0 the
  highest priority; the deadlines must be non-decreasing
  (deadline-monotonic order). For the implicit-deadline sets used
  throughout this spec (D = T) this order is simultaneously the
  rate-monotonic period order, so the LO-mode phase reproduces the
  pack sibling's classic response-time results on the same (C, T)
  values.
- Higher-priority set: hp(i) = {j : j < i}.
- LO-mode response time (classic fixed-point response-time analysis
  over the C_LO estimates, all tasks present at their C_LO):
  R_i(LO) = C_i(LO) + sum over j in hp(i) of
  ceil(R_i(LO) / T_j) * C_j(LO), iterated from R = C_i(LO) until an
  iterate repeats within CONVERGENCE_TOL. Feasible iff the converged
  R_i(LO) is at most D_i.
- HI-mode response time (AMC-rtb bound, HI-criticality tasks only,
  after the LO to HI criticality-mode change; LO tasks are dropped in
  HI mode, so they are guaranteed in LO mode only and appear in HI
  equations solely as higher-priority interference at their C_LO):
  R_i(HI) = C_i(HI) + sum over j in hp(i) with criticality LO of
  ceil(R_i(HI) / T_j) * C_j(LO) + sum over j in hp(i) with
  criticality HI of ceil(R_i(HI) / T_j) * C_j(HI), iterated from
  R = C_i(HI) until an iterate repeats within CONVERGENCE_TOL.
  Feasible iff the converged R_i(HI) is at most D_i. The bound is
  safe (an upper bound on the worst-case response after the mode
  change) and deterministic; it is the exact equation pinned by the
  probe receipt, not the tighter AMC or AMC-max variants.
- Divergence rule: both maps are monotone non-decreasing in R, so an
  iterate strictly past the task's own deadline D_i can never
  converge to a value at most D_i: the solve reports None. A solve
  that has not repeated within CONVERGENCE_TOL after
  MAX_RTA_ITERATIONS passes also reports None. A diverged task makes
  its mode infeasible; equality with the deadline (R = D) is
  feasible.
- Mode verdicts: LO feasible iff every task's LO-mode solve
  converges; HI feasible iff every HI task's HI-mode solve converges
  (an all-LO set has an empty HI guarantee list and a vacuously True
  HI verdict); the whole-set verdict is feasible iff LO feasible AND
  HI feasible.
- Utilization context: U_LO = sum over all tasks of C_LO / T and
  U_HI = sum over HI tasks of C_HI / T, reported in the result dicts
  but never a verdict. U above 1 is not rejected; it surfaces as
  divergence (the monotone iterates grow past the deadlines).
- C_LO/C_HI are inputs (execution-time estimates, one time unit),
  never derived; C_HI equal to C_LO is the no-overrun case.

Functions:
- lo_response_time(tasks, index) -> float or None
  LO-mode response time of task `index`: the converged fixed point
  over the C_LO estimates, or None on divergence (an iterate past
  D_i, or a solve past MAX_RTA_ITERATIONS). ValueErrors of the task
  shape and of an index outside [0, len(tasks)).
- hi_response_time(tasks, index) -> float or None
  HI-mode (AMC-rtb) response time of task `index`: the converged
  AMC-rtb fixed point, or None on divergence. ValueError when the
  task at `index` is LO-criticality: HI-mode analysis guarantees HI
  tasks only. ValueErrors of the task shape and index as above.
- lo_response_times(tasks) -> dict
  Returns {"names", "response_times" (one float or None per task in
  priority order), "feasible" (True only when every LO-mode response
  converged, each at most its own deadline), "utilization" (U_LO)}.
  ValueErrors of the task shape and of a non-deadline-monotonic
  order.
- hi_response_times(tasks) -> dict
  Returns {"names" (the HI tasks only), "response_times" (one float
  or None per HI task in priority order), "feasible" (True only when
  every HI-mode response converged, each at most its own deadline),
  "utilization" (U_HI)}. An all-LO set returns empty names and
  responses with feasible True. ValueErrors of the task shape and
  order.
- feasible(tasks) -> bool
  Convenience: lo_response_times(tasks)["feasible"] and
  hi_response_times(tasks)["feasible"]. Same ValueErrors.

Identities to test (closed form, exact; checkable without the builder
module):
- Single task: lo_response_time is C_LO exactly and hi_response_time
  is C_HI exactly (no higher-priority interference); feasible iff the
  converged value is at most D. Real anchor: the single HI task
  (C_LO 1.5, C_HI 4.0, T 10.0, D 10.0) gives R_LO 1.500000 and
  R_HI 4.000000, feasible True; the single LO task (C_LO 2.5, T 8.0)
  gives R_LO 2.500000 with an empty HI guarantee list, feasible True.
- All-LO set: when every task is LO-criticality the whole analysis
  reduces to the plain fixed-point RTA over the C_LO estimates: the
  LO-mode phase reproduces the pack sibling's classic results exactly
  and the HI-mode phase is empty. Real anchors: R_LO [1.000000,
  2.000000, 6.000000] on the sibling's [(1, 3), (1, 4), (2, 8)] set
  and [1.000000, 2.000000, 4.000000] on [(1, 5), (1, 6), (2, 10)],
  both whole-set feasible True.
- No-overrun collapse: when every task carries C_HI = C_LO (HI
  tasks cannot overrun), the AMC-rtb equation collapses to the
  classic RTA over the shared C value and every HI task's R_HI
  equals its R_LO. Real anchor: the collapse variant of the worked
  set A (flight-control C_HI 1.0, health-monitor C_HI 4.0) gives
  R_LO [1.000000, 4.000000, 8.000000] and R_HI [1.000000,
  8.000000], whole-set feasible True.
- Mode monotonicity: for every HI task, R_HI is never below R_LO
  (C_HI at least C_LO and every higher-priority interference term is
  mode-consistent), and the gap is the overrun cost. Real anchor:
  flight-control 3.000000 >= 1.000000 and health-monitor 19.000000
  >= 8.000000 on the worked set A.
- LO-mode overload: an over-subscribed set diverges in LO mode with
  the classic pattern. Real anchor: [(2, 3), (2, 5), (2, 7)] at
  C_LO = C_HI = C gives R_LO [2.000000, None, None], LO feasible
  False, matching the pack sibling's divergence result on the same
  (C, T) values.
- Convergence to a fixed point at most D: every feasible solve's
  converged value equals its own equation evaluated at itself (plug
  back within 1e-9) and sits at most its deadline.
- ValueErrors across the module: empty list, missing key, boolean or
  non-positive C_LO/C_HI/T/D, C_HI below C_LO, LO task C_HI above
  C_LO, D above T, non-deadline-monotonic order, index out of range,
  HI-mode call on a LO index.
- Determinism: identical outputs run to run and under both
  interpreters; no randomness; no imports beyond math; the
  MAX_RTA_ITERATIONS and CONVERGENCE_TOL constants fixed as above.

## Worked example

Task set A, three avionics fsw processes in ms, in deadline-monotonic
priority order (deadlines 10, 20, 50 ms ascending, each equal to its
period):
- flight-control: criticality HI, C_LO 1.0, C_HI 3.0, T 10.0,
  D 10.0 (the HI task whose overrun past its 1 ms LO budget forces
  the criticality-mode change; it is the task the corpus query calls
  level-A, a criticality reading, never a level determination);
- guidance: criticality LO, C_LO 3.0, C_HI 3.0, T 20.0, D 20.0 (a LO
  task, dropped after the mode change, higher priority than
  health-monitor so it feeds the AMC-rtb LO interference arm);
- health-monitor: criticality HI, C_LO 4.0, C_HI 10.0, T 50.0,
  D 50.0 (the bottom HI task whose HI-mode equation carries BOTH
  arms: a higher-priority LO task charged at C_LO and a
  higher-priority HI task charged at C_HI).

All values below are REAL outputs of the prep anchor
/tmp/w46spec/anchor_mixed_criticality_scheduling.py (pure stdlib,
math.ceil only, closed form, exit 0, no RNG), run once and quoted as
printed:

- LO-mode responses (module output): lo_response_times(SET_A) gives
  response_times [1.000000, 4.000000, 8.000000] ms against deadlines
  [10, 20, 50] ms, feasible True, utilization 0.330000. Iterate
  traces: flight-control 1.000000 (its own C_LO, no higher-priority
  load); guidance 3.000000 then 4.000000 (one flight-control job in
  the window, ceil(4 / 10) = 1); health-monitor 4.000000 then
  8.000000 (4 + ceil(8/10) * 1.0 + ceil(8/20) * 3.0 = 4 + 1 + 3).
  Every task closes inside its own deadline, so LO mode is feasible.
- HI-mode responses after the criticality-mode change (module
  output): hi_response_times(SET_A) covers only the HI tasks, names
  [flight-control, health-monitor], response_times [3.000000,
  19.000000] ms, feasible True, utilization 0.500000 (the HI
  guarantee demand, 3/10 + 10/50). flight-control converges at its
  own C_HI 3.000000 (no higher-priority task); guidance never
  appears in the HI list, because LO tasks are dropped after the
  mode change.
- The AMC-rtb structure on health-monitor: the fixed point
  R = 10.0 + ceil(R/10) * 3.0 + ceil(R/20) * 3.0 visits the iterates
  10.000000, 16.000000 and converges at 19.000000 ms:
  10 + ceil(10/10) * 3 + ceil(10/20) * 3 = 16 on the first pass, then
  10 + ceil(16/10) * 3 + ceil(16/20) * 3 = 10 + 6 + 3 = 19, and the
  plug back at 19 is 10 + ceil(19/10) * 3 + ceil(19/20) * 3 =
  10 + 6 + 3 = 19. The two interference arms are both live in this
  one equation: the higher-priority HI flight-control task charged
  at its C_HI 3.0 (two releases, 6 ms) and the higher-priority LO
  guidance task charged at its C_LO 3.0 (one release, 3 ms), over
  health-monitor's own C_HI 10.0. Its HI response 19.000000 sits at
  most D 50 ms; the mode-change guarantee holds.
- Mode monotonicity on set A: every HI task's HI-mode response is
  at or above its LO-mode response: flight-control 3.000000 >=
  1.000000 and health-monitor 19.000000 >= 8.000000, the cost of the
  C_HI overruns (own +2.0 ms and +6.0 ms respectively, plus the
  higher-priority HI arm at C_HI).
- Whole-set verdict: feasible(SET_A) is True: LO mode feasible and
  HI mode feasible.
- No-overrun collapse (identity check on set A): with every C_HI set
  equal to C_LO (flight-control C_HI 1.0, health-monitor C_HI 4.0),
  lo_response_times gives [1.000000, 4.000000, 8.000000] and
  hi_response_times gives [1.000000, 8.000000], each HI response
  exactly its LO response: no overrun, no extra cost, the AMC-rtb
  equation reduced to the classic RTA over the shared C.
- Task set B (HI overload, the divergence verdict): flight-control
  HI C_LO 1.0, C_HI 6.0, T 10.0, D 10.0; guidance LO C_LO 3.0,
  C_HI 3.0, T 20.0, D 20.0; health-monitor HI C_LO 4.0, C_HI 30.0,
  T 50.0, D 50.0. The LO budgets are unchanged, so LO mode is still
  feasible: response_times [1.000000, 4.000000, 8.000000], feasible
  True, utilization 0.330000. In HI mode flight-control converges at
  6.000000 (at most D 10), but health-monitor's AMC-rtb solve starts
  at its C_HI 30.000000 and the first pass gives 30 + ceil(30/10) *
  6 + ceil(30/20) * 3 = 30 + 18 + 6 = 54.000000, strictly past its
  D 50 ms, so the solve reports None: the U_HI demand 1.200000 is
  over-subscribed and the iterates can never return under the
  deadline. hi_response_times(SET_B) gives [6.000000, None],
  feasible False, and the whole-set verdict feasible(SET_B) is False.
- LO-mode overload (identity check): [(2, 3), (2, 5), (2, 7)] at
  C_LO = C_HI = C reproduces the pack sibling's divergence pattern:
  lo_response_times gives [2.000000, None, None], LO feasible False;
  the HI guarantee phase also diverges (response_times [2.000000,
  None]), whole-set False.
- Determinism: two consecutive runs of lo_response_times(SET_A)
  return identical dicts; the anchor exits 0 and its internal
  asserts (feasibility, every converged response at most its
  deadline, plug-back consistency) all pass.
- ValueErrors with real messages (module output, quoted as printed):
  an empty list raises "task list must be a non-empty list"; a
  missing D raises "task at index 0 missing key(s) D"; C_LO = 0
  raises "C_LO must be a positive number, got 0.0"; C_HI below C_LO
  raises "C_HI must be at least C_LO, got C_HI 0.5 with C_LO 1.0"; a
  LO task with C_HI above C_LO raises "a LO-criticality task carries
  no high estimate: C_HI must equal C_LO, got C_HI 5.0 with C_LO
  3.0"; D above T raises "D must be no greater than T, got D 15.0
  with T 10.0"; an unknown criticality word raises "criticality must
  be 'LO' or 'HI', got 'MED'"; a list not in deadline-monotonic
  order raises "tasks must be in deadline-monotonic priority order
  (non-decreasing D); higher priority is the lower list index"; a
  HI-mode call on the LO index raises "task 1 is LO-criticality;
  HI-mode analysis guarantees HI tasks only"; an index past the list
  raises "index out of range".

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
/tmp/w46spec/anchor_mixed_criticality_scheduling.py (stdlib math,
closed form, exit 0, no randomness, identical under both
interpreters).

## Validation list (contract test must include)

1. Worked set A asserts within 1e-6 relative: lo_response_times
   (SET_A) gives response_times [1.0, 4.0, 8.0], feasible True,
   utilization 0.33; hi_response_times(SET_A) gives names
   [flight-control, health-monitor], response_times [3.0, 19.0],
   feasible True, utilization 0.5; feasible(SET_A) is True; each
   converged response sits at most its own deadline [10, 20, 50].
2. Fixed-point plug-back identity: at the converged R, each response
   equals its equation evaluated at R within 1e-9, including the
   two-arm health-monitor HI equation 19.0 = 10.0 + ceil(19/10) *
   3.0 + ceil(19/20) * 3.0 with the ceil counts 2 and 1.
3. AMC-rtb arm structure: hi_response_time(SET_A, 2) = 19.0 within
   1e-9 with the higher-priority LO arm (guidance, C_LO 3.0) and the
   higher-priority HI arm (flight-control, C_HI 3.0) both present;
   hi_response_times excludes the LO task guidance from names and
   responses entirely.
4. HI guarantee scope: hi_response_time(SET_A, 1) raises ValueError
   with the message "task 1 is LO-criticality; HI-mode analysis
   guarantees HI tasks only"; an all-LO set returns empty HI names
   and responses with feasible True.
5. Mode monotonicity: hi_response_time(SET_A, 0) = 3.0 within 1e-9
   is at least lo_response_time(SET_A, 0) = 1.0 within 1e-9, and
   19.0 is at least 8.0 on health-monitor; the collapse variant of
   set A (C_HI equal to C_LO everywhere) gives R_HI equal to R_LO
   per HI task ([1.0, 8.0] within 1e-9 against R_LO [1.0, 4.0,
   8.0]).
6. Set B (HI overload): LO responses [1.0, 4.0, 8.0] within 1e-9,
   feasible True; HI responses [6.0, None] with health-monitor's
   first AMC-rtb pass 54.0 strictly past D 50.0 (None, never
   converged), feasible False, utilization 1.2 within 1e-6; whole
   verdict False.
7. Single-task closed forms: lo_response_time of the single HI task
   (C_LO 1.5, C_HI 4.0, T 10.0) is 1.5 within 1e-9 and
   hi_response_time is 4.0 within 1e-9, feasible True; the single LO
   task (C_LO 2.5, T 8.0) gives R_LO 2.5 within 1e-9 with an empty
   HI guarantee list and whole verdict True.
8. All-LO identity: the sibling's classic sets at C_LO = C_HI = C
   reproduce its results exactly: [1.0, 2.0, 6.0] within 1e-9 on
   [(1, 3), (1, 4), (2, 8)] and [1.0, 2.0, 4.0] within 1e-9 on
   [(1, 5), (1, 6), (2, 10)], whole verdict True; the over-subscribed
   [(2, 3), (2, 5), (2, 7)] gives LO [2.0, None, None] within 1e-9
   where converged, feasible False.
9. Convergence and divergence discipline: every feasible solve
   converged within CONVERGENCE_TOL passes and reports a float; an
   iterate strictly past D_i reports None on the same pass (set B,
   health-monitor) and no solve runs past MAX_RTA_ITERATIONS = 100
   without reporting None; equality with the deadline is feasible.
10. All ValueErrors enumerated in the identity list raise from the
    named public function with the real messages quoted in the
    Worked example: empty list, missing key, boolean or
    non-positive C_LO/C_HI/T/D, C_HI below C_LO, LO task C_HI above
    C_LO, D above T, non-deadline-monotonic order (from every
    analysis function), index outside [0, len(tasks)) (from the
    per-index functions), HI-mode call on a LO index (from
    hi_response_time and hi_response_times).
11. Determinism: identical outputs run to run and under both
    interpreters; no randomness anywhere; no imports beyond math;
    module constants MAX_RTA_ITERATIONS = 100 and
    CONVERGENCE_TOL = 1e-12. No exact-float equality on computed
    sums; use assertAlmostEqual/math.isclose everywhere.
12. Run the deterministic contract test offline (no network); it
    exits 0. Test passes under BOTH interpreters
    (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3).

## Corpus fragment (eval/hit1-wave46-mixed-criticality-scheduling.yaml)

Query 1 (copy verbatim):
  "run the mixed-criticality-scheduling amc-rtb-analysis on the
  flight-control task set where each task carries a dual-criticality
  execution time estimate C_LO and C_HI, and verify the
  hi-criticality-mode response time of the level-A task against its
  deadline after the criticality mode change"
  intent: "avionics/fsw; mixed-criticality-scheduling: the
  dual-criticality execution time estimates C_LO and C_HI per task,
  the lo-criticality-mode response-time analysis over the C_LO
  estimates, then the hi-criticality-mode AMC-rtb response time of
  the HI-criticality flight-control task against its deadline after
  the criticality-mode change"
  expected_skill: "avionics/fsw/mixed-criticality-scheduling"
Query 2 (copy verbatim):
  "check the lo-criticality-mode feasibility of the two-criticality
  process set with the C_LO estimates, then recompute the
  hi-criticality-mode response times under the AMC-rtb interference
  bound when the HI tasks overrun their LO budgets"
  intent: "avionics/fsw; lo-criticality-mode feasibility of the
  two-criticality process set over the C_LO execution-time estimates,
  then hi-criticality-mode response times of the HI tasks under the
  AMC-rtb interference bound after the HI tasks overrun their LO
  budgets"
  expected_skill: "avionics/fsw/mixed-criticality-scheduling"
Task ids: w46-mixed-criticality-scheduling-1 and -2. Prep grep (run
at spec time by the probe): each of the tokens mixed-criticality,
amc-rtb, amc-max, vestal, criticality-aware, dual-criticality,
hi-mode and lo-mode returns ZERO matches in every skills/ SKILL.md
and in eval/hit1-corpus.yaml (grep exit 1), and the corpus scan for
mixed-criticality, amc-rtb, dual-criticality, criticality-mode or
hi/lo-mode task rows is empty, so the queries are collision-free; the
sibling tasks route on single-execution-time periodic language
(real-time-scheduling), blocking language (shared-resource-access-
control), server-budget language (aperiodic-server-scheduling),
per-task-deadline and jitter language (deadline-monotonic-scheduling)
and level-determination language (do178c/planning), none of which
carry dual-estimate or criticality-mode content. Add one fence line
to real-time-scheduling and one router row to skills/avionics/SKILL.md
at build time pointing criticality-mode scheduling to the new leaf
(the aperiodic-server-scheduling and deadline-monotonic-scheduling
precedents).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must decide the offline
schedulability of an avionics flight software task set under the
dual-criticality execution-time model:" and include the outputs in
the Claim order (per-task LO-mode response times and the LO-mode
feasible verdict, the HI-mode response times of the HI tasks under
the AMC-rtb bound and the HI-mode feasible verdict, the whole-set
verdict, the divergence verdict when an iterate crosses a deadline),
then close with the Trigger list. Refer to the estimates as C_LO and
C_HI execution-time estimates throughout; never use the bare single
words criticality, dal, software-level, wcet or
worst-case-execution-time as tags or standalone description terms,
and never reproduce DO-178C text (reference-only). First tag:
mixed-criticality-scheduling. Metadata tags EXACTLY as the probe
receipt gate (f) lists them, nothing else: amc-rtb-analysis,
dual-criticality-execution-time, hi-criticality-mode-rta,
lo-criticality-mode-rta, criticality-mode-change-rta. 50-150 words,
<=1000 chars, no em dash, no content-policy sweep term (the banned
word from the builder kit), action verb present. Recommended wording
(140 words, 985 chars, verified at spec time):

"Use when you must decide the offline schedulability of an avionics
flight software task set under the dual-criticality execution-time
model: each task carries the C_LO and C_HI execution-time estimates
with C_HI at least C_LO, run the lo-criticality-mode fixed-point
response-time iteration over the C_LO estimates for every task, then
run the hi-criticality-mode amc-rtb fixed point after the
criticality-mode change, with higher-priority LO tasks charged at
C_LO and higher-priority HI tasks charged at C_HI in the
interference sum. Produces the per-task lo-mode response times and
the LO-mode feasible verdict, the hi-mode response times of the HI
tasks under the AMC-rtb bound with the HI-mode feasible verdict, the
overall mixed-criticality feasible verdict, and the divergence
verdict when an iterate crosses a deadline. Trigger: mixed
criticality scheduling, amc rtb analysis, dual criticality execution
time, lo mode feasibility, hi mode response time, criticality mode
change."

FORBIDDEN TOKENS (belong to siblings or the level side): the bare
single words criticality, dal, software-level, wcet and
worst-case-execution-time as tags or standalone description terms
(never as the claim surface; the estimates are C_LO/C_HI
execution-time estimates); liu-layland-bound, rate-monotonic-
scheduling, earliest-deadline-first, cpu-utilization,
fixed-priority-scheduling, response-time-analysis and any query whose
only content is a single-execution-time implicit-deadline verdict
with no C_LO/C_HI pair and no criticality mode (real-time-scheduling);
constrained-deadline-rta, arbitrary-deadline-rta, release-jitter-rta,
dm-priority-assignment, shorter-deadline-order and any per-task-
deadline, release-jitter or queued-job content (deadline-monotonic-
scheduling); priority-ceiling-protocol, priority-inheritance,
worst-case-blocking, stack-resource-policy, blocking-time-bound,
schedulability-with-blocking (shared-resource-access-control);
sporadic-server, deferrable-server, polling-server, server-capacity,
aperiodic-response-bound, server-budget (aperiodic-server-scheduling);
software-levels, dal and any software-level or DAL determination
language (do178c/planning); arinc-653, major-frame,
partition-configuration-table, sampling-port, queuing-port,
health-monitoring (ima-partitioning); software-bus, publish-subscribe,
cfe, osal, rate-group, command-opcode, telemetry-channel
(cfs-architecture, fprime-component). Never the bare words
criticality, deadline, jitter, response, priority, scheduling,
feasibility, task, analysis, utilization or level as standalone
metadata tags.

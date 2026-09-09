# Wave-48 leaf spec: cyclic-executive-scheduling (avionics, fsw pack)

- Path: skills/avionics/fsw/cyclic-executive-scheduling/
- Pack: fsw (present siblings avionics/fsw/real-time-scheduling,
  avionics/fsw/mixed-criticality-scheduling, avionics/fsw/
  virtual-deadline-scheduling, avionics/fsw/shared-resource-access-
  control, avionics/fsw/aperiodic-server-scheduling, avionics/fsw/
  deadline-monotonic-scheduling, avionics/fsw/cfs-architecture,
  avionics/fsw/fprime-component; adjacent fences avionics/ima/
  ima-partitioning (major-frame partition window arithmetic) and
  avionics/data-bus/mil-std-1553-bus-loading (minor-frame bus
  schedules)). AV 48 probe receipt task-1 rank 1 GO; 0 owners verified
  whole-tree at HEAD 92d84a48 (the wave-48 brief hash; tree clean at
  probe, the only untracked paths being the wave48-recon receipts).
- Claim fences (quoted from the sibling frontmatter and bodies at the
  wave-48 probe receipt and re-verified fresh at spec time; the nearest
  owners fence out the PRIORITY-DRIVEN feasibility branch, which is the
  exact gap this leaf closes):
  - real-time-scheduling (this pack) is the PRIORITY-DRIVEN fence: it
    answers RM-bound/RTA/EDF verdicts for (C, T) sets and explicitly
    hands the table-driven arithmetic away. Its body lines 32-35 read
    "It schedules the processes and partitions inside an ARINC 653
    style avionics software partition layout, pairing with
    avionics/ima/ima-partitioning, which owns the major-frame cyclic
    window arithmetic that surrounds this leaf's process set." Its
    scope note (lines 69-73) reads "Scope notes: WCET estimation,
    jitter and blocking analysis, and arbitrary-deadline response-time
    extensions are out of scope; the model is the classic
    implicit-deadline periodic task set. ARINC 653 partition schedule
    windows and message bus response windows are not this leaf." Its
    pitfall (lines 189-193) routes adjacent timing domains away:
    "Routing adjacent timing domains here: WCET estimation, jitter and
    blocking analysis, arbitrary-deadline extensions, ARINC 653
    partition schedule windows (ima/ima-partitioning), and bus response
    windows (data-bus/mil-std-1553) are not this leaf's classic
    implicit-deadline periodic model." Nothing in the landed leaf
    constructs or checks a time-triggered frame table: no line claims
    or fences a cyclic-executive frame schedule, and its standards
    stance (lines 218-220) is the model this leaf mirrors: "ARINC 653
    is not in standards-map.yaml and is not needed: the process-level
    scheduling theory is independent of the partition standard text."
    The gap this leaf closes: the TABLE-DRIVEN time-triggered frame
    schedule of the same periodic (C, T) process set, which the
    priority-driven sibling cannot express at all.
  - ima-partitioning (adjacent, one level above process sets) owns the
    PARTITION-WINDOW schedule, whose model is window durations, not
    task frame-fit: its lines 37-39 read "A partition configuration
    table assigns each partition a window duration d and a period p
    inside a repeating major frame (MAF) of duration M; the MAF must be
    a common multiple of every period so the cyclic schedule repeats
    evenly (period divides the MAF)." Its feasibility is the sum of
    d x (M / p) partition windows against the MAF plus per-window slot
    checks and IPC port latencies, ARINC 653 application partitions one
    level above process sets. It never checks (C_i, T_i) task jobs
    against a task-level frame length; the task-level frame table is
    the gap this leaf closes.
  - deadline-monotonic-scheduling and aperiodic-server-scheduling (this
    pack) name the dispatch frameworks, not a frame-table owner: their
    Related-leaves lines (deadline-monotonic-scheduling 225-228 and
    aperiodic-server-scheduling 233-236) read "avionics/fsw/
    cfs-architecture and avionics/fsw/fprime-component: software bus
    routing and cyclic rate-group dispatch layout." and "the software
    bus routing and cyclic rate-group dispatch layouts that these event
    servers sit beside." Neither claims a frame table, a hyperperiod or
    a frame length; the words "cyclic rate-group dispatch layout" are
    framework prose, not frame-table arithmetic.
  - The family router has no cyclic/frame-table/hyperperiod row
    (re-verified fresh: grep -n -i -E "cyclic|hyperperiod|frame-table"
    on skills/avionics/SKILL.md exits 1; its scheduling rows route rate
    monotonic/response time/earliest deadline first to real-time-
    scheduling, deadline-monotonic to deadline-monotonic-scheduling,
    AMC to mixed-criticality-scheduling, EDF-VD virtual deadlines to
    virtual-deadline-scheduling). No router row and no leaf claims a
    time-triggered frame table; the seam is unrouted and unowned.
    Build-time additions required (wave-45/46/47 precedent): one scope
    fence line in real-time-scheduling, one avionics router row
    pointing cyclic-executive frame-table questions to the new leaf,
    plus 2 corpus tasks.
  - Whole-tree greps at prep (probe receipt gate (a), fresh at HEAD
    92d84a48): the tokens cyclic[- ]executive, frame[- ]based[- ]
    schedul, hyperperiod, frame[- ]length, time[- ]triggered,
    master[- ]schedule and dispatch[- ]table return ZERO matches across
    every skills/ SKILL.md and eval/ fragment (grep exit 1), and the
    corpus substring scan over all 1306 task blocks finds cyclic-
    executive 0, hyperperiod 0, frame-table 0, major-cycle 0,
    time-triggered 0, frame-length 0. The only near-token hits are
    other contexts, none a task-level frame table: gnc-autonomy/control/
    gain-scheduling owns the tag "schedule-table" (control-gain
    breakpoints), ima-partitioning owns "major frame (MAF)" partition
    windows, and the data-bus and flight-test leaves use "minor frame"
    for bus and telemetry schedules. GENUINE avionics/fsw gap (probe
    receipt task-1, verified zero-owner, GO rank 1): no leaf owns the
    table-driven time-triggered frame schedule that the pack's six
    priority-driven feasibility leaves cannot express.
- Standards id: do-178c (RTCA DO-178C, Software Considerations in
  Airborne Systems and Equipment Certification; the avionics software
  lifecycle context in which the scheduling analysis artifact is
  recorded), reference-only and present in standards-map.yaml (grep
  'id: do-178c' at line 61, re-verified at spec time). Ledger
  Standard: do-178c.
- Family: avionics

## Claim

Design and check the offline feasibility of a repeating, time-triggered
cyclic executive (frame-based) schedule for a periodic avionics flight
software task set, the table-driven complement to this pack's six
priority-driven feasibility leaves. Each task is a dict {name, C, T} in
one integer time unit (ms in the worked examples): name optional,
execution time C and period T positive integers, with the implicit
deadline D = T (every job must finish before the next release of its
task). There are no priorities: the cyclic executive is priority-free,
the frame table IS the schedule, and any task list order is accepted.
The leaf computes the hyperperiod H = lcm over all T_i (the major cycle
over which the frame table repeats), the period gcd g = gcd over all
T_i, and the processor utilization U = sum of C_i / T_i, then
enumerates the admissible frame lengths: the ascending divisors f of g
(the frame length must divide every task period, so releases land on
frame boundaries) with f at least every task's execution time (each job
fits inside its own frame, f >= max C_i). For each admissible f it lays
the jobs into the frames of one hyperperiod: task i releases H / T_i
jobs per major cycle, at times 0, T_i, 2*T_i, ..., and the job released
at time t = j*f executes in frame j (frames are indexed 0 to H/f - 1,
frame j covering [j*f, (j+1)*f)), so frame j carries exactly one job of
task i iff (j*f) mod T_i == 0. It verifies per-frame capacity over the
repeating frame table: frame load(j) = sum of C_i over the tasks that
release into frame j, and no frame's total execution may exceed f
(max_frame_load <= f). It returns the constructive frame table with a
FITS or no-admissible-frame verdict: FITS when at least one admissible
frame length is capacity-feasible, choosing the SMALLEST such f (the
finest-grained feasible minor cycle), together with per-frame jobs,
per-frame loads and per-frame slack = f - load(j); no-admissible-frame
with reject_reason "frame-fit" when no divisor of g is at least max C_i
(the periods force every common frame length below some task's
execution time) or "capacity" when an admissible f exists but every
candidate over-subscribes at least one frame of the hyperperiod. The
model is the classic closed-form cyclic executive arithmetic of Baker
and Shaw ("The Cyclic Executive Model and Ada", Real-Time Systems 1(1),
1989), Locke ("Software Architecture for Hard Real-Time Applications:
Cyclic Executives vs. Fixed Priority Executives", Real-Time Systems
4(1), 1992), and Burns and Wellings ("Real-Time Systems and Programming
Languages", 4th ed., 2009, cyclic executive chapter): frame length
divides every period, every worst-case execution time fits within a
frame, no frame is over-subscribed, and the schedule repeats over the
least common multiple of the periods (public science, summary-only).
The DO-178C lifecycle standard is the reference-only context in which
the scheduling artifact is recorded; this leaf never reproduces
standard text, exactly as real-time-scheduling states for its own
process-level theory. Does NOT do: the Liu-Layland utilization bound,
exact iterative response-time analysis, the plain EDF full-utilization
verdict U <= 1 and every priority-driven feasibility verdict of a
single-estimate (C, T) set (avionics/fsw/real-time-scheduling); per-task
relative deadlines beyond the implicit D = T, deadline-monotonic
priority assignment, release jitter in the response-time iteration and
constrained/arbitrary-deadline RTA (avionics/fsw/deadline-monotonic-
scheduling); the AMC-rtb fixed-priority response-time bound over C_LO/
C_HI estimates and criticality-mode response times (avionics/fsw/
mixed-criticality-scheduling); the EDF-VD virtual-deadline factor x and
dual-criticality demand conditions (avionics/fsw/virtual-deadline-
scheduling); sporadic/deferrable/polling server budgets for aperiodic
jobs and server response bounds (avionics/fsw/aperiodic-server-
scheduling); priority-ceiling or priority-inheritance blocking terms
for shared resources (avionics/fsw/shared-resource-access-control);
ARINC 653 partition configuration tables, MAF window durations and
sampling/queuing port latencies (avionics/ima/ima-partitioning); bus
command/response or minor-frame schedules (avionics/data-bus/
mil-std-1553-bus-loading); software bus routing and cyclic rate-group
dispatch layout (avionics/fsw/cfs-architecture, avionics/fsw/
fprime-component); control-gain "schedule-table" breakpoints
(gnc-autonomy/control/gain-scheduling). C and T are inputs, never
estimated; the model is the single-processor, non-preemptive, frame-
by-frame dispatch of a periodic task set with synchronous releases,
implicit deadlines and one integer time unit per task set; offsets,
release jitter, blocking, aperiodic arrivals, job splitting across
frames, WCET estimation and multiprocessor scheduling are out of scope;
the verdict is the deterministic constructive feasibility of the
repeating frame table, never a priority-driven schedulability test.

## Model (implement exactly)

Pure stdlib, math only (math.gcd for the gcd and lcm folds), no other
imports, deterministic, no RNG, no randomness anywhere. Module
constant: TOL = 1e-12 (the comparison tolerance for the utilization
identity checks; every feasibility verdict is exact integer
comparison, max_frame_load <= f, so no tolerance enters a verdict).

Task dict shape (validated identically by every public function):
{name, C, T}, name optional (any hashable label; a task without a
"name" key is labeled "task%d" % its list index), C and T positive
integers in one time unit (ms in the worked examples). Every function
rejects, with ValueError, an empty task list, a non-dict entry, a
missing C or T key, a boolean C or T, a non-integer C or T, and a
non-positive C or T. There is NO deadline key (the deadline is implicit
D = T) and NO priority or order requirement: the cyclic executive is
priority-free, so any list order is accepted and no ordering check
exists. frame_loads and frame_table additionally reject a frame length
f that is not a positive integer dividing every task period.

Defining relations (pin these exactly; every function derives from
them), all integer arithmetic:
- Hyperperiod (major cycle): H = lcm over all T_i, computed by the
  fold lcm(a, b) = a * b // gcd(a, b) over the task periods. The frame
  table over frames 0..H/f - 1 repeats exactly every H time units.
- Period gcd: g = gcd over all T_i. A frame length divides every task
  period iff it divides g, so the candidate frame lengths are the
  divisors of g.
- Processor utilization: U = sum over tasks of C_i / T_i (float,
  reported for the necessary-condition identity only).
- Admissible frame lengths: the ascending divisors f of g with
  f >= max C_i (frame-fit rule: every job fits inside its own frame).
- Frame dispatch: task i releases H / T_i jobs per hyperperiod, at
  times 0, T_i, 2*T_i, ..., H - T_i. The job released at time t = j*f
  executes in frame j, so frame j carries exactly one job of task i iff
  (j*f) mod T_i == 0. Frame j covers [j*f, (j+1)*f), j = 0..H/f - 1.
- Per-frame load over one hyperperiod: load(j) = sum of C_i over tasks
  i with (j*f) mod T_i == 0, j = 0..H/f - 1.
- Capacity-feasible frame length: f is capacity-feasible iff
  max over j of load(j) <= f (no frame's total execution exceeds f).
- Verdicts: FITS when at least one admissible frame length is
  capacity-feasible, choosing the smallest such f, with the full
  constructive frame table; no-admissible-frame with reject_reason
  "frame-fit" when admissible_frame_lengths is empty (no divisor of g
  reaches max C_i) and "capacity" when admissible lengths exist but
  every candidate over-subscribes some frame. U <= 1 is NECESSARY for a
  FITS verdict but NOT sufficient (a capacity rejection can occur with
  U < 1 when one frame must hold more execution than f).

Functions:
- hyperperiod(tasks) -> int
  H = lcm over all task periods. ValueErrors of the task shape.
- period_gcd(tasks) -> int
  g = gcd over all task periods. ValueErrors of the task shape.
- utilization(tasks) -> float
  U = sum of C_i / T_i over the tasks. ValueErrors of the task shape.
- admissible_frame_lengths(tasks) -> list
  Ascending divisors f of g with f >= max C_i, the frame-fit
  candidates. Empty when no such divisor exists. ValueErrors of the
  task shape.
- frame_loads(tasks, f) -> list
  Per-frame loads load(j) for j = 0..H/f - 1 over one hyperperiod at
  frame length f. ValueErrors of the task shape plus: f must be a
  positive integer dividing every task period.
- max_frame_load(tasks, f) -> int
  max(frame_loads(tasks, f)), the worst frame total. Same ValueErrors.
- feasible_frame_lengths(tasks) -> list
  The admissible frame lengths f with max_frame_load(tasks, f) <= f
  (capacity-feasible candidates), ascending. ValueErrors of the task
  shape.
- frame_table(tasks, f) -> list
  Constructive frame table at frame length f: one dict per frame
  {frame, start_ms, end_ms, jobs, load, slack} with frame the 0-based
  index, start_ms = j*f, end_ms = (j+1)*f, jobs the task names
  releasing into that frame in task-list order (empty list for an idle
  frame), load = load(j), slack = f - load(j). ValueErrors of
  frame_loads.
- cyclic_executive_report(tasks) -> dict
  Returns {"hyperperiod": H, "period_gcd": g, "max_execution_time":
  max C_i, "utilization": U, "admissible_frame_lengths": [...],
  "feasible_frame_lengths": [...], "verdict": "FITS" or
  "no-admissible-frame", "reject_reason": None, "frame-fit" or
  "capacity", "frame_length": the smallest capacity-feasible f or None,
  "frame_count": H / f or None, "max_frame_load": max load or None,
  "min_slack": f - max_frame_load or None, "frame_table": the frame
  table list or None}. ValueErrors of the task shape.
- feasible(tasks) -> bool
  Convenience: cyclic_executive_report(tasks)["verdict"] == "FITS".
  Same ValueErrors.

Identities to test (closed form, exact; checkable without the builder
module):
- Coprime-periods hyperperiod identity: on periods 3, 4, 5 (pairwise
  coprime) the hyperperiod is exactly their product, 60. Real anchor:
  hyperperiod on T 3, 4, 5 prints 60 = 3*4*5, with period_gcd 1.
- Frame-divisibility rejection identity: when max C_i exceeds g, no
  divisor of the period gcd reaches max C_i and the verdict is
  no-admissible-frame with reject_reason "frame-fit". Real anchor:
  T = (25, 40), C = (3, 8) gives g = 5, max C = 8, admissible [], U =
  0.32, verdict no-admissible-frame.
- Total-load identity over one hyperperiod: sum over frames of
  load(j) equals sum over tasks of C_i * (H / T_i), the total work
  released per major cycle, and both equal H * U. Real anchor on the
  worked set A at f = 25: sum of frame loads 25 = sum_i C_i * H / T_i
  25 = H * U 25.0 (equal within TOL).
- Jobs-per-hyperperiod identity: sum over tasks of H / T_i equals the
  number of jobs in the frame table. Real anchor on set A: 7 jobs in 4
  frames, sum over frames of jobs 7.
- Slack-sum identity: sum over frames of slack(j) = (H / f) * f minus
  total load = H - sum_i C_i * (H / T_i). Real anchor on set A: sum of
  per-frame slacks 75 = n_frames * f - total_load = 4 * 25 - 25 = 75.
- Necessary-not-sufficient identity: U <= 1 is necessary but not
  sufficient for FITS. Real anchor: the worked set B has U 0.6 yet
  verdict no-admissible-frame, because frame 0 must hold all three
  co-released jobs, 8 + 9 + 10 = 27 > 25.
- Capacity-tight frame identity: the worst frame's slack is exactly
  f - max_frame_load; set A frame 0 holds all three tasks, load 12,
  slack 13 at f = 25, the minimum slack of the table.
- Determinism: identical outputs run to run and under both
  interpreters; no randomness; no imports beyond math; TOL fixed at
  1e-12.
- ValueErrors across the module: empty list, non-dict entry, missing C
  or T key, boolean C or T, zero or negative T, non-integer C, frame
  length not dividing a period.

## Worked example

Task set A, three avionics fsw processes in ms, implicit deadlines
D = T, no priorities (the cyclic executive is priority-free):
- flight-control: C 3, T 25 (a 40 Hz flight control law task);
- guidance: C 4, T 50 (a 20 Hz guidance task);
- health-monitor: C 5, T 100 (a 10 Hz health monitoring task).

All values below are REAL outputs of the prep anchor script
anchor_cyclic_executive.py (pure stdlib, math only, exit 0, no RNG,
printed once and quoted as printed; byte-identical under both
interpreters /usr/bin/python3 3.9.6 and
~/.pyenv/versions/3.13.12/bin/python3):

- Set-level report (module output): hyperperiod 100 (lcm of 25, 50,
  100, the major cycle over which the table repeats), period_gcd 25,
  max_execution_time 5, utilization 0.25. The admissible frame lengths
  are the divisors of 25 that are at least 5: [5, 25]. Candidate f = 5
  is rejected on capacity: max_frame_load(SET_A, 5) = 12 > 5, because
  frame 0 holds all three co-released jobs (3 + 4 + 5 = 12), while
  candidate f = 25 is accepted: max_frame_load(SET_A, 25) = 12 <= 25.
  feasible_frame_lengths [25], verdict "FITS", frame_length 25 (the
  smallest capacity-feasible admissible f), frame_count 4 (100 / 25).
- Frame table at f = 25 (module output, quoted as printed): frame_loads
  [12, 3, 7, 3], frame_slacks [13, 22, 18, 22]. Frame-by-frame: frame
  0 | [0,25) ms | flight-control, guidance, health-monitor | load 12 |
  slack 13; frame 1 | [25,50) ms | flight-control | load 3 | slack 22;
  frame 2 | [50,75) ms | flight-control, guidance | load 7 | slack 18;
  frame 3 | [75,100) ms | flight-control | load 3 | slack 22. Frame 0
  is the capacity-tight frame: all three tasks release at time 0 and
  their total 12 ms leaves 13 ms slack in the 25 ms frame. Frames 1 and
  3 carry only the 40 Hz flight-control job, frame 2 carries the
  flight-control job plus the 20 Hz guidance job released at 50 ms; the
  10 Hz health-monitor job releases once per major cycle, at time 0.
  The table repeats every 100 ms.
- Identity anchors on set A (module output): sum of frame loads 25 =
  sum_i C_i * H / T_i = 3*4 + 4*2 + 5*1 = 25 = H * U = 100 * 0.25 =
  25.0 (equal within TOL True); 7 jobs per hyperperiod = 4 + 2 + 1,
  placed as 7 jobs across the 4 frames (3 + 1 + 2 + 1); sum of
  per-frame slacks 75 = n_frames * f - total_load = 4 * 25 - 25 = 75.
- Task set B (the no-admissible-frame capacity path): flight-control
  C 8, T 25; guidance C 9, T 50; health-monitor C 10, T 100. Module
  output: hyperperiod 100, period_gcd 25, max_execution_time 10,
  utilization 0.6, admissible_frame_lengths [25],
  feasible_frame_lengths [], verdict "no-admissible-frame",
  reject_reason "capacity", frame_length None. The instructive
  necessary-not-sufficient case: U = 0.6 <= 1 yet no frame length is
  feasible, because frame 0 must hold all three co-released jobs and
  8 + 9 + 10 = 27 > 25 (frame 1 holds only the flight-control job 8,
  but the health-monitor job releases once per major cycle into frame
  0, so the over-subscription is unavoidable at the only admissible
  frame length, 25).
- Task set C (the no-admissible-frame frame-fit path): flight-control
  C 3, T 25; display C 8, T 40. Module output: period_gcd 5,
  max_execution_time 8, admissible_frame_lengths [], verdict
  "no-admissible-frame", reject_reason "frame-fit", utilization 0.32.
  The periods share gcd 5, so every common frame length divides 5 and
  is at most 5 ms, below the display task's 8 ms execution time: the
  frame-fit rule f >= max C_i cannot be met even though the processor
  is only 32% loaded.
- Coprime identity anchor (module output): hyperperiod(T=3,4,5) = 60 =
  3*4*5, period_gcd 1.
- Feasibility reduction (module output): feasible(SET_A) True,
  feasible(SET_B) False, feasible(frame-divisibility set) False.
- Determinism: repeated cyclic_executive_report(SET_A) returns an
  identical dict; the anchor exits 0 and its internal asserts all
  pass.
- ValueErrors with real messages (module output, quoted as printed):
  an empty list raises "task list must be a non-empty list"; a non-dict
  entry raises "task 0 must be a dict"; a missing T raises "task 0
  missing key(s) T"; a boolean C raises "C must be a positive integer,
  got True"; a zero T raises "T must be a positive integer, got 0"; a
  non-integer C raises "C must be a positive integer, got 1.5"; a frame
  length that does not divide every period raises "frame length f must
  divide every task period, got f=7, periods [25]".

Run the anchor and take the real outputs as assert targets; the anchors
above are real prep outputs of the anchor script (stdlib, math only,
exit 0, no randomness, byte-identical under both interpreters).

## Validation list (contract test must include)

1. Worked set A report asserts: hyperperiod 100, period_gcd 25,
   max_execution_time 5, utilization 0.25 (math.isclose, rel_tol
   1e-6), admissible_frame_lengths [5, 25],
   feasible_frame_lengths [25], verdict "FITS", reject_reason None,
   frame_length 25, frame_count 4, max_frame_load 12, min_slack 13;
   frame_loads(SET_A, 25) equals [12, 3, 7, 3] exactly (integer
   equality is exact); frame_slacks equal [13, 22, 18, 22] exactly;
   frame_table row 0 jobs equal [flight-control, guidance,
   health-monitor] with load 12 and slack 13, row 2 jobs equal
   [flight-control, guidance] with load 7 and slack 18.
2. Worked set A candidate rejection and acceptance: max_frame_load
   (SET_A, 5) equals 12, strictly above 5; max_frame_load(SET_A, 25)
   equals 12, at most 25; feasible_frame_lengths(SET_A) equals [25]
   (f = 5 admissible but not capacity-feasible, f = 25 the smallest
   feasible).
3. Worked set B asserts: admissible_frame_lengths [25],
   feasible_frame_lengths [], verdict "no-admissible-frame",
   reject_reason "capacity", frame_length None, frame_count None,
   max_frame_load None, min_slack None; utilization 0.6 (math.isclose,
   rel_tol 1e-6); the necessary-not-sufficient identity holds (U <= 1
   with verdict no-admissible-frame).
4. Worked set C asserts: period_gcd 5, max_execution_time 8,
   admissible_frame_lengths [], verdict "no-admissible-frame",
   reject_reason "frame-fit"; utilization 0.32 (math.isclose, rel_tol
   1e-6); feasible_frame_lengths [].
5. Coprime hyperperiod identity: hyperperiod on T = (3, 4, 5) equals
   60; period_gcd equals 1; the identity H = 3 * 4 * 5 holds exactly.
6. Total-load identity over one hyperperiod on set A at f = 25: sum of
   frame_loads equals sum over tasks of C * (H // T) equals 25; H * U
   equals 25.0 within 1e-9 (math.isclose); jobs per hyperperiod equals
   sum of H // T = 7, matching the sum over frames of len(jobs).
7. Slack-sum identity on set A: sum of frame slacks equals
   frame_count * f - sum of frame loads = 75 exactly; min_slack equals
   f - max_frame_load = 25 - 12 = 13.
8. Single-task and idle-frame boundary: a one-task set {C 3, T 25}
   gives hyperperiod 25, admissible_frame_lengths [5, 25],
   feasible_frame_lengths [5, 25], verdict FITS at frame_length 5
   (frame_loads [3, 0, 0, 0, 0] at f = 5 over 5 frames, the task's one
   release per major cycle landing in frame 0, with frame slacks
   [2, 5, 5, 5, 5]); a frame with no release in the table carries
   jobs [] and slack f.
9. Admissible-length enumeration boundary: frame lengths never exceed
   the period gcd, never fall below max C_i, and every returned f
   divides every T_i; on a set with g = 1 and max C_i = 1 the only
   admissible f is 1.
10. All ValueErrors enumerated in the identity list raise from the
    named public function with the real messages quoted in the Worked
    example: empty list, non-dict entry, missing key, boolean C,
    zero T, non-integer C, frame length not dividing a period; frame
    length f must also reject non-positive and non-integer f with a
    ValueError.
11. Determinism: identical outputs run to run and under both
    interpreters; no randomness anywhere; no imports beyond math;
    module constant TOL = 1e-12. No exact-float equality on computed
    sums; use assertAlmostEqual/math.isclose everywhere (integer loads,
    slacks, hyperperiod and gcd compares are exact).
12. Run the deterministic contract test offline (no network); it exits
    0. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3).

## Corpus fragment (eval/hit1-wave48-cyclic-executive-scheduling.yaml)

Query 1 (copy verbatim):
  "run the cyclic-executive-scheduling analysis on the periodic flight
  control software task set and lay out the repeating cyclic frame
  table: compute the hyperperiod as the least common multiple of the
  task periods, choose a frame length that divides every task period,
  verify each task worst-case execution time fits inside its own
  frame, and confirm every per-frame execution total stays within the
  frame length"
  intent: "avionics/fsw; cyclic-executive-scheduling: the hyperperiod
  as the least common multiple of the task periods, an admissible
  frame length dividing every task period, the frame-fit check that
  each task worst-case execution time fits inside its own frame, and
  the per-frame capacity check that every per-frame execution total
  stays within the frame length over the repeating cyclic frame
  table"
  expected_skill: "avionics/fsw/cyclic-executive-scheduling"
Query 2 (copy verbatim):
  "design the cyclic-executive-scheduling frame table for the periodic
  avionics tasks: compute the hyperperiod as the least common multiple
  of the periods, pick the frame length dividing every period, and
  check the frame-fit feasibility of the repeating frame table frame
  by frame"
  intent: "avionics/fsw; the repeating cyclic frame table of a
  periodic avionics task set: the hyperperiod as the least common
  multiple of the periods, the frame length dividing every period, and
  the frame-fit feasibility check of the repeating frame table frame
  by frame"
  expected_skill: "avionics/fsw/cyclic-executive-scheduling"
Task ids: w48-cyclic-executive-scheduling-1 and -2. Prep grep (run at
spec time by the probe): each of the tokens cyclic[- ]executive,
hyperperiod, frame[- ]length, time[- ]triggered, master[- ]schedule
and dispatch[- ]table returns ZERO matches in every skills/ SKILL.md
and in eval/hit1-corpus.yaml (grep exit 1), and the corpus substring
scan for cyclic-executive, hyperperiod, frame-table, major-cycle,
time-triggered or frame-length task rows over all 1306 expected_skill
rows is empty, so the queries are collision-free; the sibling tasks
route on single-execution-time periodic language and priority-driven
verdict language (real-time-scheduling), deadline-monotonic and jitter
language (deadline-monotonic-scheduling), AMC-rtb and criticality-mode
language (mixed-criticality-scheduling), EDF-VD and virtual-deadline
language (virtual-deadline-scheduling), server-budget language
(aperiodic-server-scheduling), blocking language (shared-resource-
access-control), partition-window language (ima-partitioning) and
bus-schedule language (data-bus/mil-std-1553-bus-loading), none of
which carry frame-table or hyperperiod content. The corpus tasks never
reuse the sibling-owned phrases "earliest deadline first", "cpu
utilization", "liu layland bound", "rate monotonic", "deadline
monotonic", "major frame", "MAF", "partition window", "rate group",
"minor frame schedule", "schedule table" or "breakpoint"; they refer to
the repeat period as the "hyperperiod" and to the artifact as the
"cyclic frame table". Add one fence line to real-time-scheduling and
one router row to skills/avionics/SKILL.md at build time pointing
cyclic-executive frame-table and hyperperiod questions to the new leaf
(the aperiodic-server-scheduling, deadline-monotonic-scheduling and
mixed-criticality-scheduling precedents).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design and verify the offline
repeating time-triggered cyclic executive frame table for a periodic
avionics flight software task set:" (or the equivalent action-verb
opening in the Claim language) and include the outputs in the Claim
order (the hyperperiod as the least common multiple of the task
periods, the admissible frame length dividing every task period, the
frame-fit check that each task execution time fits inside its own
frame, the per-frame capacity check that every per-frame execution
total stays within the frame length, the repeating cyclic frame table
with per-frame loads and slack, and the FITS or no-admissible-frame
verdict), then close with the Trigger list. Refer to the repeat period
as the "hyperperiod" and to the artifact as the "cyclic frame table"
throughout; never use the sibling-owned phrases "earliest deadline
first", "cpu utilization", "liu layland bound", "rate monotonic",
"deadline monotonic", "major frame", "MAF", "partition window", "rate
group", "minor frame schedule", "schedule table" or "breakpoint" in any
description, trigger or tag, never claim a priority-driven verdict (the
Liu-Layland bound, exact RTA, EDF U <= 1, deadline-monotonic assignment,
AMC-rtb or the EDF-VD x factor) owned by the six scheduling siblings,
and never reproduce DO-178C text (reference-only). First tag:
cyclic-executive-scheduling. Metadata tags EXACTLY as the probe receipt
gate (f) lists them, nothing else: cyclic-executive-scheduling,
cyclic-frame-table, frame-length-selection, hyperperiod-design,
time-triggered-frame-schedule, frame-fit-feasibility,
frame-boundary-release. 50-150 words, <=1000 chars, no em dash, action
verb present. Recommended wording (137 words, 937 chars, verified at
spec time):

"Use when you must design and verify the offline repeating frame table
of a time-triggered cyclic executive for a periodic avionics flight
software task set with implicit deadlines: compute the hyperperiod as
the least common multiple of the task periods, choose an admissible
frame length that divides every task period and is at least every task
execution time C_i, lay each frame-boundary release into the frame that
starts at its release time over the hyperperiod, and confirm every
per-frame execution total stays within the frame length. Produces the
hyperperiod, the admissible and capacity-feasible frame lengths, the
constructive cyclic frame table with per-frame loads and per-frame
slack, and a FITS or no-admissible-frame verdict with the reject
reason. Trigger: cyclic executive scheduling, cyclic frame table,
hyperperiod, frame length selection, frame fit feasibility, time
triggered frame schedule, frame boundary release."

FORBIDDEN TOKENS (belong to siblings or adjacent leaves): the bare
single words wcet, priority, utilization, deadline, jitter, blocking,
deadline-monotonic, edf, amc-rtb, edf-vd, rate-group, major-frame,
maf, partition-window, minor-frame, schedule-table and breakpoint as
tags or standalone description terms; rate-monotonic-scheduling,
liu-layland-bound, response-time-analysis, earliest-deadline-first,
cpu-utilization, edf-feasibility and any query or description whose
only content is a priority-driven feasibility verdict over (C, T)
values with no frame table (real-time-scheduling);
constrained-deadline-rta, arbitrary-deadline-rta, release-jitter-rta,
dm-priority-assignment and any per-task-deadline or release-jitter
content (deadline-monotonic-scheduling); amc-rtb, amc-rtb-analysis,
adaptive-mixed-criticality, hi-criticality-mode-rta,
lo-criticality-mode-rta, criticality-mode-change-rta and any fixed-
point response-time claim over C_LO/C_HI estimates (mixed-criticality-
scheduling); edf-vd, virtual-deadline-factor, dual-mode-demand-check
and any virtual-deadline scaling content (virtual-deadline-scheduling);
sporadic-server, deferrable-server, polling-server, server-capacity,
aperiodic-response-bound, server-budget (aperiodic-server-scheduling);
priority-ceiling-protocol, priority-inheritance, worst-case-blocking,
blocking-time-bound (shared-resource-access-control); arinc-653,
major-frame, partition-configuration-table, sampling-port,
queuing-port, health-monitoring (ima-partitioning); software-bus,
publish-subscribe, cfe, osal, rate-group, command-opcode,
telemetry-channel (cfs-architecture, fprime-component); minor-frame,
bus-schedule, command-response-window (data-bus/mil-std-1553-bus-
loading). Never the bare words cyclic, executive, frame, table,
schedule, feasibility, task, analysis or hyperperiod as standalone
metadata tags.

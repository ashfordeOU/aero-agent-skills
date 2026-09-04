# Wave-32 leaf spec: data-control-coupling-analysis (avionics, do178c pack)

- Path: skills/avionics/do178c/data-control-coupling-analysis/
- Pack: do178c. Siblings: planning, development, verification,
  software-testing, configuration-management, tool-qualification,
  airworthiness-liaison.
- Standards id: do-178c (reference-only; gated - name + paraphrase
  only, NEVER reproduce objective tables or appendix text). Ledger
  Standard: do-178c.
- Family: avionics

## Claim

Analyze data coupling and control coupling between software components
of an airborne system for the DO-178C level-A coupling objective:
identify shared-variable data-coupling items between component pairs
from their written and read variable sets with declared synchronization
suppression, identify control-coupling items across call edges where a
caller-written variable is read by the callee, compute the coupling
coverage ratio against declared evidence, and return the PASS or FAIL
verdict with the uncovered item list. Produces the data-coupling item
list, the control-coupling item list, the coverage ratio and the
evidence verdict that gate the level-A inter-component coupling
objective.

Does NOT do: intra-component structural coverage (statement, decision,
MC/DC - avionics/do178c/verification owns control-flow coverage
analysis at the software level); requirements traceability and derived
requirements (avionics/do178c/development owns requirement-to-code
trace links); airframe/FCS structural coupling flight test
(flight-test-operations/envelope/structural-coupling-test owns gain and
phase margins of the flight control system with the airframe - a
different 'coupling' domain); software process planning
(avionics/do178c/planning). This leaf owns INTER-component data and
control coupling analysis for airborne software at level A only; the
paraphrased objective never reproduces the gated DO-178C objective
tables.

## Model (implement exactly)

Represent components as declared inputs: component ids, each with a set
of written variables, a set of read variables, and (optionally) a set
of declared synchronization pairs (component, variable) that suppress
data-coupling items (a declared handshake/protected port). Call edges
are directed pairs (caller, callee).

Functions (pure stdlib, deterministic):

- data_coupling_items(components, sync_declarations=None) -> list of
  items. components: dict {comp_id: {"writes": set, "reads": set}}.
  For each ordered pair (A, B), A != B, shared = writes(A) & reads(B);
  an item (A, B, var) exists for each var in shared UNLESS the pair
  (A, B, var) is in sync_declarations (a declared synchronization
  suppresses the item). Sorted output: by (A, B, var) for
  determinism. ValueErrors: unknown component referenced in
  sync_declarations.
- control_coupling_items(components, call_edges) -> list of items.
  call_edges: list of (caller, callee). For each edge (A, B): for each
  var in writes(A) & reads(B) where the variable is written before the
  call (modeled as: any var in writes(A) & reads(B)), emit (A, B,
  var). Sorted by (caller, callee, var).  ValueError if an edge
  references an unknown component.
- coupling_coverage_ratio(items, evidence_flags) -> float covered /
  total (0.0 when no items; ratio in [0,1]). evidence_flags: set or
  dict of item keys (A,B,var) with evidence present. ValueError if any
  evidence key is not in items (evidence for a nonexistent item).
- coverage_verdict(items, evidence_flags) -> dict {ratio, covered,
  total, verdict}: verdict "PASS" when ratio == 1.0 (all items
  covered) else "FAIL" with uncovered = [items not in evidence],
  sorted. (Level-A coupling evidence rule paraphrased: every
  identified inter-component coupling item needs evidence; never
  reproduce the gated objective text.)
- analyze_coupling(components, call_edges, evidence_flags,
  sync_declarations=None) -> dict {data_items, control_items,
  total_items, covered, ratio, verdict, uncovered_items,
  component_count}. ValueErrors propagate.

ALL functions deterministic, no RNG, stdlib only. Items are tuples
(A, B, var); evidence_flags is a set of the same tuples.

## Worked example

Components: A writes {X}, reads {}; B reads {X}, writes {Y}; C reads
{X} and {Y}, writes {}; D reads {}, writes {Y}. Call edges: (A, B),
(B, C).  No sync declarations.

Run your module and take the real outputs as assert targets, then check
the bounds:
- data items: (A, B, X) only (B reads X; C reads X but no A-C edge in
  the data-coupling model which is pairwise over ALL components: also
  (A, C, X) since A writes X and C reads X).  So data items = [(A,B,X),
  (A,C,X)] and also (B, C, Y) because B writes Y and C reads Y - but
  wait D writes Y and C reads Y so (D, C, Y) too.  Enumerate exactly:
  writes(A)={X}, reads(C)={X,Y} -> (A,C,X); writes(B)={Y}, reads(C)={X,Y}
  -> (B,C,Y); writes(D)={Y}, reads(C)={X,Y} -> (D,C,Y); writes(A)={X},
  reads(B)={X} -> (A,B,X).  Data items sorted: [(A,B,X), (A,C,X),
  (B,C,Y), (D,C,Y)] = 4 items.
- With sync_declarations {(A, C, X)}: items = [(A,B,X), (B,C,Y),
  (D,C,Y)] = 3 (the A-C handshake is declared, so its item is
  suppressed).
- control items over edges (A,B), (B,C): (A,B,X) from the A->B edge
  (X written by A, read by B); (B,C,Y) from B->C.  Control items =
  [(A,B,X), (B,C,Y)] = 2.
- Evidence covering all 4 data + 2 control items -> ratio 1.0 PASS.
  Evidence missing (A,C,X) -> ratio 5/6 = 0.833 -> FAIL with
  uncovered [(A,C,X)].
- coverage_verdict with an empty item list returns ratio 0.0 and
  verdict PASS (no items, nothing uncovered).
- component_count = 4.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: sync declaration or call edge referencing an unknown
  component; evidence key not in the item list.
- Data-coupling suppression: declaring the synchronization removes
  exactly that item and nothing else.
- Data coupling is symmetric-pairwise: (A,B,X) exists when A writes X
  and B reads X; the pair (B,A,X) does NOT exist (B does not write X).
- Control coupling exists only along declared call edges: (A,C,X)
  control item does NOT exist when there is no A->C edge even though
  the data item exists.
- Sorting: outputs sorted by (A, B, var) tuple order.
- Coverage: ratio 1.0 -> PASS; partial -> FAIL with the sorted
  uncovered list; empty items -> PASS at ratio 0.0.
- Determinism: no RNG, identical outputs run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave32-data-control-coupling-analysis.yaml)

Query 1 (copy verbatim):
  "identify the data coupling and control coupling items between airborne software components from their written and read variable sets and the call graph for the level A coupling objective"
  intent: "avionics; DO-178C level A data and control coupling item identification"
  expected_skill: "avionics/do178c/data-control-coupling-analysis"
Query 2 (copy verbatim):
  "compute the coupling coverage ratio and evidence verdict for shared-variable and call-edge coupling items of an airborne software architecture"
  intent: "avionics; inter-component coupling coverage and evidence verdict"
  expected_skill: "avionics/do178c/data-control-coupling-analysis"
Task ids: w32-data-control-coupling-analysis-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must analyze data coupling and
control coupling between airborne software components:" and include the
outputs in the Claim. First tag: data-control-coupling-analysis.
Additional tags ONLY: data-coupling-analysis, control-coupling-analysis,
shared-variable-pairs, coupling-coverage-evidence, level-a-objectives.
NEVER single generic words (coupling, coverage, analysis, software,
verification). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): MC/DC, decision coverage,
statement coverage, modified condition decision (avionics/do178c/
verification owns intra-component structural coverage); traceability,
derived requirement, HLR, LLR (avionics/do178c/development); gain
margin, phase margin, flight control coupling, airframe structural
mode (flight-test-operations/envelope/structural-coupling-test owns the
FCS/airframe coupling domain); tool qualification (tool-qualification).
The word "coverage" may appear only as "coupling coverage" - never as
bare structural coverage.

Tags: [data-control-coupling-analysis, data-coupling-analysis,
control-coupling-analysis, shared-variable-pairs,
coupling-coverage-evidence, level-a-objectives]

Sibling-citation lines for Related leaves: avionics/do178c/verification
(control-flow coverage sibling; this leaf owns inter-component
coupling, that leaf owns intra-component structural coverage),
avionics/do178c/development (requirements traceability),
avionics/do178c/software-testing (execution-based testing that supplies
coupling evidence), flight-test-operations/envelope/
structural-coupling-test (distinct airframe coupling domain).

Ledger Standard: do-178c.

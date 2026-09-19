"""Nominal and redundant duplication of actuator electronics.

Anchor: ECSS-E-ST-20-21C clause 5.2.2 (paraphrased into an
implementable procedure; no standard text is reproduced).

The clause duplicates the actuator electronics into a nominal chain and
a redundant chain so that no single failure can take actuation away.
Duplication is a property of the function set, not of the box count: a
second box that still depends on one shared sequencer, one shared
secondary supply or one function that was never duplicated leaves the
single point of failure exactly where it was.

Procedure implemented here:

1. Categorize every declared block by the function it performs and by
   the chain it is assigned to: nominal, redundant or shared between
   the two. Reject an unknown assignment and a duplicate block
   identifier.
2. Find the functions that are genuinely duplicated -- present in both
   chains -- and the functions that appear in one chain only.
3. Collect the single points of failure: every shared block that is not
   internally redundant, and every function that only one chain
   carries.
4. Compute the reliability the architecture actually buys. Blocks
   inside one chain are in series, the two chains are in parallel, and
   the shared blocks multiply the parallel result because no amount of
   duplication downstream rescues a shared block upstream.
5. Report the fault tolerance order -- one when nothing is a single
   point of failure, zero otherwise -- and the reliability that would
   be reached if the shared blocks were duplicated too, which is the
   engineering case for doing it.

Stdlib only, offline, deterministic.
"""

CHAIN_NOMINAL = "nominal"
CHAIN_REDUNDANT = "redundant"
ASSIGNMENT_SHARED = "shared"

CHAINS = (CHAIN_NOMINAL, CHAIN_REDUNDANT)
ASSIGNMENTS = (CHAIN_NOMINAL, CHAIN_REDUNDANT, ASSIGNMENT_SHARED)

FINDING_SHARED_BLOCK = "shared-block-single-point"
FINDING_UNDUPLICATED_FUNCTION = "function-in-one-chain-only"
FINDING_EMPTY_CHAIN = "chain-carries-no-block"

# A reliability is a product of floats, so a case built to land exactly
# on a bound can sit a few units in the last place away from it. A part
# in a million million is far below any declared failure rate and
# absorbs that representation error without relaxing anything.
RELIABILITY_TOLERANCE = 1.0e-12


def _non_empty_text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _probability(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (label, value))
    return value


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_block(block):
    """Validate one electronics block and return a normalized copy."""
    if not isinstance(block, dict):
        raise ValueError("block must be a mapping, got %r" % (block,))
    block_id = _non_empty_text("block id", block.get("id"))
    assignment = block.get("assignment")
    if assignment not in ASSIGNMENTS:
        raise ValueError(
            "block %s has unknown assignment %r (expected one of %s)"
            % (block_id, assignment, ", ".join(ASSIGNMENTS))
        )
    internally_redundant = _boolean(
        "block %s internally_redundant" % block_id,
        block.get("internally_redundant", False),
    )
    if internally_redundant and assignment != ASSIGNMENT_SHARED:
        raise ValueError(
            "block %s is not shared, so internally_redundant has no meaning"
            % block_id
        )
    return {
        "id": block_id,
        "function": _non_empty_text(
            "block %s function" % block_id, block.get("function")
        ),
        "assignment": assignment,
        "failure_probability": _probability(
            "block %s failure_probability" % block_id,
            block.get("failure_probability", 0.0),
        ),
        "internally_redundant": internally_redundant,
    }


def validate_design(blocks):
    """Validate the declared block set and return normalized records."""
    if not isinstance(blocks, (list, tuple)):
        raise ValueError("blocks must be a sequence of mappings")
    if not blocks:
        raise ValueError("blocks must not be empty")
    normalized = [validate_block(b) for b in blocks]
    seen = set()
    for record in normalized:
        if record["id"] in seen:
            raise ValueError("duplicate block id %s" % record["id"])
        seen.add(record["id"])
    return normalized


def chain_blocks(blocks, chain):
    """Blocks assigned to one chain, shared blocks excluded."""
    if chain not in CHAINS:
        raise ValueError(
            "chain must be one of %s, got %r" % (", ".join(CHAINS), chain)
        )
    return [b for b in validate_design(blocks) if b["assignment"] == chain]


def shared_blocks(blocks):
    """Blocks that both chains depend on."""
    return [b for b in validate_design(blocks) if b["assignment"] == ASSIGNMENT_SHARED]


def duplicated_functions(blocks):
    """Functions carried by both the nominal and the redundant chain."""
    records = validate_design(blocks)
    nominal = {b["function"] for b in records if b["assignment"] == CHAIN_NOMINAL}
    redundant = {b["function"] for b in records if b["assignment"] == CHAIN_REDUNDANT}
    return tuple(sorted(nominal & redundant))


def unduplicated_functions(blocks):
    """Functions one chain carries alone, shared functions excluded."""
    records = validate_design(blocks)
    nominal = {b["function"] for b in records if b["assignment"] == CHAIN_NOMINAL}
    redundant = {b["function"] for b in records if b["assignment"] == CHAIN_REDUNDANT}
    return tuple(sorted(nominal ^ redundant))


def single_point_failures(blocks):
    """Block ids whose single failure takes actuation away."""
    records = validate_design(blocks)
    alone = set(unduplicated_functions(records))
    spf = {b["id"] for b in records if b["assignment"] == ASSIGNMENT_SHARED and not b["internally_redundant"]}
    spf |= {
        b["id"]
        for b in records
        if b["assignment"] in CHAINS and b["function"] in alone
    }
    return sorted(spf)


def series_reliability(records):
    """Reliability of blocks in series, from their failure probabilities."""
    reliability = 1.0
    for record in records:
        reliability *= 1.0 - record["failure_probability"]
    return reliability


def chain_reliability(blocks, chain):
    """Reliability of one chain taken on its own."""
    return series_reliability(chain_blocks(blocks, chain))


def parallel_reliability(first, second):
    """Reliability of two alternatives either of which suffices."""
    for label, value in (("first", first), ("second", second)):
        _probability(label, value)
    return 1.0 - (1.0 - float(first)) * (1.0 - float(second))


def system_reliability(blocks):
    """Reliability of the duplicated architecture as declared."""
    records = validate_design(blocks)
    shared = series_reliability(shared_blocks(records))
    pair = parallel_reliability(
        chain_reliability(records, CHAIN_NOMINAL),
        chain_reliability(records, CHAIN_REDUNDANT),
    )
    return shared * pair


def reliability_if_shared_were_duplicated(blocks):
    """Reliability once every shared block is duplicated as well."""
    records = validate_design(blocks)
    shared = series_reliability(shared_blocks(records))
    pair = parallel_reliability(
        chain_reliability(records, CHAIN_NOMINAL),
        chain_reliability(records, CHAIN_REDUNDANT),
    )
    return parallel_reliability(shared, shared) * pair


def fault_tolerance_order(blocks):
    """One when no single failure loses actuation, zero otherwise."""
    return 0 if single_point_failures(blocks) else 1


def redundancy_findings(blocks):
    """Findings against the duplication requirement."""
    records = validate_design(blocks)
    findings = []
    for record in shared_blocks(records):
        if not record["internally_redundant"]:
            findings.append(
                {
                    "code": FINDING_SHARED_BLOCK,
                    "subject": record["id"],
                    "detail": "%s is shared by both chains and is not internally "
                    "redundant" % record["function"],
                }
            )
    alone = unduplicated_functions(records)
    for function in alone:
        findings.append(
            {
                "code": FINDING_UNDUPLICATED_FUNCTION,
                "subject": function,
                "detail": "only one chain carries this function",
            }
        )
    for chain in CHAINS:
        if not chain_blocks(records, chain):
            findings.append(
                {
                    "code": FINDING_EMPTY_CHAIN,
                    "subject": chain,
                    "detail": "the %s chain carries no block of its own" % chain,
                }
            )
    return sorted(findings, key=lambda f: (f["code"], f["subject"]))


def assess_actuator_electronics_redundancy(blocks):
    """Grade a declared nominal and redundant actuator electronics set."""
    records = validate_design(blocks)
    findings = redundancy_findings(records)
    declared = system_reliability(records)
    improved = reliability_if_shared_were_duplicated(records)
    return {
        "block_count": len(records),
        "nominal_block_ids": sorted(b["id"] for b in chain_blocks(records, CHAIN_NOMINAL)),
        "redundant_block_ids": sorted(
            b["id"] for b in chain_blocks(records, CHAIN_REDUNDANT)
        ),
        "shared_block_ids": sorted(b["id"] for b in shared_blocks(records)),
        "duplicated_functions": duplicated_functions(records),
        "unduplicated_functions": unduplicated_functions(records),
        "single_point_failures": single_point_failures(records),
        "fault_tolerance_order": fault_tolerance_order(records),
        "nominal_chain_reliability": chain_reliability(records, CHAIN_NOMINAL),
        "redundant_chain_reliability": chain_reliability(records, CHAIN_REDUNDANT),
        "system_reliability": declared,
        "reliability_if_shared_duplicated": improved,
        "reliability_gain_available": improved - declared,
        "findings": findings,
        "finding_codes": sorted({f["code"] for f in findings}),
        "compliant": not findings,
    }

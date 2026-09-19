"""Cross strapped command interfaces of the actuator electronics.

Anchor: ECSS-E-ST-20-21C clause 5.2.3 (paraphrased into an
implementable procedure; no standard text is reproduced).

Each actuator electronics chain has to accept the arm, the select and
the fire command from either command chain. That is what makes the two
electronics chains genuinely interchangeable: if the nominal
electronics only listens to the nominal command chain, then losing one
command chain costs one electronics chain as well, and the duplication
paid for upstream buys nothing.

The acceptance matrix has three axes -- command type, receiving
electronics chain, and originating command chain -- so full cross
strapping is a set of twelve cells, every one of them accepted.

Procedure implemented here:

1. Validate the declared acceptance cells. Reject an unknown command
   type, an unknown chain name and a cell declared twice, because a
   duplicate cell lets one contradictory declaration hide behind
   another.
2. Work out which of the twelve required cells are missing, either
   never declared or declared as not accepted, and report the coverage
   as a fraction so a partially cross strapped design is visible.
3. Check the isolation of every accepted cross strap. A cell whose
   command chain differs from the receiving electronics chain is a
   cross strap, and an unisolated one propagates a fault from the
   command chain into the electronics it was supposed to protect.
4. Remove each command chain in turn and report what actuation
   capability survives: an electronics chain is still commandable only
   when it accepts all three command types from a command chain that
   is still there.
5. Close with a verdict and findings naming the missing cells, the
   unisolated cross straps and any command chain whose loss takes
   actuation away.

Stdlib only, offline, deterministic.
"""

COMMAND_ARM = "arm"
COMMAND_SELECT = "select"
COMMAND_FIRE = "fire"
COMMAND_TYPES = (COMMAND_ARM, COMMAND_SELECT, COMMAND_FIRE)

ELECTRONICS_NOMINAL = "nominal-electronics"
ELECTRONICS_REDUNDANT = "redundant-electronics"
ELECTRONICS_CHAINS = (ELECTRONICS_NOMINAL, ELECTRONICS_REDUNDANT)

COMMAND_CHAIN_NOMINAL = "nominal-command-chain"
COMMAND_CHAIN_REDUNDANT = "redundant-command-chain"
COMMAND_CHAINS = (COMMAND_CHAIN_NOMINAL, COMMAND_CHAIN_REDUNDANT)

# Which command chain is the home chain of which electronics chain. A
# cell that pairs an electronics chain with any other command chain is
# a cross strap and carries the isolation duty.
HOME_COMMAND_CHAIN = {
    ELECTRONICS_NOMINAL: COMMAND_CHAIN_NOMINAL,
    ELECTRONICS_REDUNDANT: COMMAND_CHAIN_REDUNDANT,
}

REQUIRED_CELL_COUNT = len(COMMAND_TYPES) * len(ELECTRONICS_CHAINS) * len(COMMAND_CHAINS)

FINDING_CELL_NOT_ACCEPTED = "command-cell-not-accepted"
FINDING_CROSS_STRAP_NOT_ISOLATED = "cross-strap-not-isolated"
FINDING_COMMAND_CHAIN_LOSS_FATAL = "command-chain-loss-loses-actuation"


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_cell(cell):
    """Validate one declared acceptance cell and normalize it."""
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    command_type = cell.get("command_type")
    if command_type not in COMMAND_TYPES:
        raise ValueError(
            "unknown command_type %r (expected one of %s)"
            % (command_type, ", ".join(COMMAND_TYPES))
        )
    electronics = cell.get("electronics_chain")
    if electronics not in ELECTRONICS_CHAINS:
        raise ValueError(
            "unknown electronics_chain %r (expected one of %s)"
            % (electronics, ", ".join(ELECTRONICS_CHAINS))
        )
    command_chain = cell.get("command_chain")
    if command_chain not in COMMAND_CHAINS:
        raise ValueError(
            "unknown command_chain %r (expected one of %s)"
            % (command_chain, ", ".join(COMMAND_CHAINS))
        )
    accepted = _boolean("accepted", cell.get("accepted", True))
    isolated = _boolean("isolated", cell.get("isolated", True))
    return {
        "command_type": command_type,
        "electronics_chain": electronics,
        "command_chain": command_chain,
        "accepted": accepted,
        "isolated": isolated,
        "is_cross_strap": command_chain != HOME_COMMAND_CHAIN[electronics],
    }


def validate_matrix(cells):
    """Validate the declared acceptance matrix and normalize it."""
    if not isinstance(cells, (list, tuple)):
        raise ValueError("cells must be a sequence of mappings")
    if not cells:
        raise ValueError("cells must not be empty")
    normalized = [validate_cell(c) for c in cells]
    seen = set()
    for record in normalized:
        key = cell_key(record)
        if key in seen:
            raise ValueError("duplicate acceptance cell %s" % (key,))
        seen.add(key)
    return normalized


def cell_key(record):
    """Identity of one cell: command type, electronics chain, command chain."""
    return (
        record["command_type"],
        record["electronics_chain"],
        record["command_chain"],
    )


def required_cells():
    """The twelve cells full cross strapping has to cover."""
    return tuple(
        (command_type, electronics, command_chain)
        for command_type in COMMAND_TYPES
        for electronics in ELECTRONICS_CHAINS
        for command_chain in COMMAND_CHAINS
    )


def accepted_keys(cells):
    """Keys of the cells the design declares as accepted."""
    return {cell_key(r) for r in validate_matrix(cells) if r["accepted"]}


def missing_cells(cells):
    """Required cells that are absent or declared as not accepted."""
    present = accepted_keys(cells)
    return tuple(key for key in required_cells() if key not in present)


def coverage_fraction(cells):
    """Share of the twelve required cells that are accepted."""
    return (REQUIRED_CELL_COUNT - len(missing_cells(cells))) / float(
        REQUIRED_CELL_COUNT
    )


def cross_strap_cells(cells):
    """Accepted cells whose command chain is not the home chain."""
    return [r for r in validate_matrix(cells) if r["accepted"] and r["is_cross_strap"]]


def unisolated_cross_straps(cells):
    """Keys of the accepted cross straps that declare no isolation."""
    return tuple(sorted(cell_key(r) for r in cross_strap_cells(cells) if not r["isolated"]))


def command_type_fully_cross_strapped(cells, command_type):
    """True when both electronics chains take this command from both chains."""
    if command_type not in COMMAND_TYPES:
        raise ValueError(
            "unknown command_type %r (expected one of %s)"
            % (command_type, ", ".join(COMMAND_TYPES))
        )
    present = accepted_keys(cells)
    return all(
        (command_type, electronics, command_chain) in present
        for electronics in ELECTRONICS_CHAINS
        for command_chain in COMMAND_CHAINS
    )


def commandable_electronics(cells, available_command_chains):
    """Electronics chains that can still take all three commands."""
    if not isinstance(available_command_chains, (list, tuple, set, frozenset)):
        raise ValueError("available_command_chains must be a collection")
    available = tuple(available_command_chains)
    for chain in available:
        if chain not in COMMAND_CHAINS:
            raise ValueError(
                "unknown command chain %r (expected one of %s)"
                % (chain, ", ".join(COMMAND_CHAINS))
            )
    present = accepted_keys(cells)
    survivors = []
    for electronics in ELECTRONICS_CHAINS:
        for chain in available:
            if all(
                (command_type, electronics, chain) in present
                for command_type in COMMAND_TYPES
            ):
                survivors.append(electronics)
                break
    return tuple(survivors)


def command_chain_loss_report(cells):
    """Surviving electronics chains after losing each command chain."""
    report = {}
    for lost in COMMAND_CHAINS:
        remaining = tuple(c for c in COMMAND_CHAINS if c != lost)
        report[lost] = commandable_electronics(cells, remaining)
    return report


def command_interface_findings(cells):
    """Findings against the cross strapping requirement."""
    records = validate_matrix(cells)
    findings = []
    for key in missing_cells(records):
        findings.append(
            {
                "code": FINDING_CELL_NOT_ACCEPTED,
                "subject": "%s/%s/%s" % key,
                "detail": "the %s command is not accepted by %s from %s" % key,
            }
        )
    for key in unisolated_cross_straps(records):
        findings.append(
            {
                "code": FINDING_CROSS_STRAP_NOT_ISOLATED,
                "subject": "%s/%s/%s" % key,
                "detail": "the cross strap carrying %s into %s from %s declares "
                "no isolation" % key,
            }
        )
    for lost, survivors in sorted(command_chain_loss_report(records).items()):
        if not survivors:
            findings.append(
                {
                    "code": FINDING_COMMAND_CHAIN_LOSS_FATAL,
                    "subject": lost,
                    "detail": "losing %s leaves no electronics chain able to take "
                    "all three commands" % lost,
                }
            )
    return sorted(findings, key=lambda f: (f["code"], f["subject"]))


def assess_command_interfaces(cells):
    """Grade a declared actuator electronics command acceptance matrix."""
    records = validate_matrix(cells)
    findings = command_interface_findings(records)
    return {
        "declared_cell_count": len(records),
        "required_cell_count": REQUIRED_CELL_COUNT,
        "accepted_cell_count": len(accepted_keys(records)),
        "missing_cells": missing_cells(records),
        "coverage_fraction": coverage_fraction(records),
        "cross_strap_count": len(cross_strap_cells(records)),
        "unisolated_cross_straps": unisolated_cross_straps(records),
        "fully_cross_strapped_commands": tuple(
            c for c in COMMAND_TYPES if command_type_fully_cross_strapped(records, c)
        ),
        "command_chain_loss": command_chain_loss_report(records),
        "findings": findings,
        "finding_codes": sorted({f["code"] for f in findings}),
        "compliant": not findings,
    }

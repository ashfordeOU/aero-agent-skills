#!/usr/bin/env python3
"""Model-based systems engineering (MBSE) logic (paraphrase).

Common-knowledge summary (standards-map.yaml, arp4754a: gated):
MBSE is a way of executing systems engineering with models as the
primary artifacts: requirements modeled against functional and
logical architectures, functions allocated to design elements, and
analysis (safety, performance) run on the architecture. Traceability
links requirements through design to verification. Open-source
toolchains: Capella (functional architecture), OSATE/AADL
(architecture analysis), Papyrus (SysML modeling).
"""

MBSE_STAGES = (
    "requirements-modeling",
    "functional-architecture",
    "logical-architecture",
    "allocation",
    "analysis",
    "traceability",
)

TOOL_BY_TASK = {
    "functional-architecture": "capella",
    "requirements-modeling": "papyrus",
    "sysml-modeling": "papyrus",
    "architecture-analysis": "osate",
}


def workflow_stages():
    """Ordered MBSE workflow stages."""
    return list(MBSE_STAGES)


def allocation_closure(functions, allocated):
    """Every function must be allocated to a design element before the
    model closes; returns (closed, unallocated)."""
    unallocated = [f for f in functions if f not in set(allocated)]
    return (len(unallocated) == 0, unallocated)


def traceability_status(linked, total, critical=False):
    """Traceability closure: safety-critical items require full
    linkage; non-critical allow a small gap."""
    if linked < 0 or total <= 0:
        raise ValueError("invalid traceability counts: %r / %r" % (linked, total))
    if linked > total:
        raise ValueError("linked (%d) exceeds total (%d)" % (linked, total))
    required = total if critical else max(0, int(total * 0.9))
    return "closed" if linked >= required else "open"


def tool_for_task(task):
    """Open-source modeling tool for an MBSE task."""
    if task not in TOOL_BY_TASK:
        raise ValueError("unknown MBSE task: %r" % (task,))
    return TOOL_BY_TASK[task]

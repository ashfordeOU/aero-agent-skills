#!/usr/bin/env python3
"""DO-297 IMA architecture allocation engine (stdlib only, deterministic, offline).

Implements, from common engineering practice in the spirit of DO-297 (the
standard text is proprietary RTCA material and is paraphrased, never
reproduced here):

- Integrity level mapping: failure-condition severity maps to an
  integrity level (catastrophic -> A, hazardous -> B, major -> C, minor
  -> D, no effect -> E), consistent with the DO-178C software level
  approach (referenced only).
- Availability class mapping: class 1 functions must remain available on
  demand, class 2 permits loss of function with a warning, class 3
  permits loss without warning. Levels A and B map to class 1, level C
  to class 2, levels D and E to class 3.
- Allocation: each application is assigned to exactly one partition; one
  or more partitions share a module. The partition budget is the sum of
  the demands of the applications it hosts; the module totals are the
  sums over all partitions. An allocation fits only when every module
  dimension (cpu_units, memory_bytes, io_ports) stays within the module
  budget, within a floating-point tolerance.
- Contention: an issue is raised for any application whose demand
  exceeds the module budget in a dimension, and for any module dimension
  whose aggregate demand exceeds the budget. The over-budget application
  is named in the report.
- Module acceptance criteria: deterministic statements covering platform
  definition, module acceptance testing, resource usage verification,
  failure containment, availability demonstration, and incremental
  certification credit.
- Development assurance steps: a deterministic per-integrity-level list
  covering planning, requirements, design, verification, configuration
  management, and airworthiness liaison.

Units: cpu_units in abstract units, memory in bytes, io_ports in port
count. All comparisons use ALLOCATION_TOLERANCE to absorb floating-point
rounding.
"""

INTEGRITY_LEVELS = ("A", "B", "C", "D", "E")
AVAILABILITY_CLASSES = (1, 2, 3)
RESOURCE_DIMS = ("cpu_units", "memory_bytes", "io_ports")
RESOURCE_NAMES = {"cpu_units": "cpu", "memory_bytes": "memory", "io_ports": "io"}

# Floating-point slack for budget comparisons (deterministic).
ALLOCATION_TOLERANCE = 1e-9

_SEVERITY_TO_INTEGRITY = {
    "catastrophic": "A",
    "hazardous": "B",
    "major": "C",
    "minor": "D",
    "no-effect": "E",
}

_INTEGRITY_TO_AVAILABILITY = {"A": 1, "B": 1, "C": 2, "D": 3, "E": 3}


def severity_to_integrity(severity):
    """Map a failure-condition severity to the integrity level (A-E).

    Worked: "catastrophic" maps to A, "major" to C, "no-effect" to E.
    Raises ValueError for an unknown severity.
    """
    key = str(severity).strip().lower()
    if key not in _SEVERITY_TO_INTEGRITY:
        raise ValueError(
            "unknown severity %r (expected one of %s)"
            % (severity, ", ".join(sorted(_SEVERITY_TO_INTEGRITY)))
        )
    return _SEVERITY_TO_INTEGRITY[key]


def availability_class(integrity):
    """Map an integrity level to the availability class (1-3).

    Worked: A maps to class 1 (remain available on demand), C to class 2
    (loss permitted with warning), E to class 3 (loss without warning).
    Raises ValueError for an unknown integrity level.
    """
    level = str(integrity).strip().upper()
    if level not in _INTEGRITY_TO_AVAILABILITY:
        raise ValueError(
            "unknown integrity level %r (expected one of %s)"
            % (integrity, ", ".join(INTEGRITY_LEVELS))
        )
    return _INTEGRITY_TO_AVAILABILITY[level]


def _validate_module(module):
    if not isinstance(module, dict) or not module.get("name"):
        raise ValueError("module must be a dict with a non-empty 'name'")
    for dim in RESOURCE_DIMS:
        value = module.get(dim)
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(
                "module %r: %s must be a non-negative number, got %r"
                % (module["name"], dim, value)
            )


def _validate_application(app):
    if not isinstance(app, dict) or not app.get("name"):
        raise ValueError("application must be a dict with a non-empty 'name'")
    level = str(app.get("integrity", "")).strip().upper()
    if level not in INTEGRITY_LEVELS:
        raise ValueError(
            "application %r: integrity must be one of %s, got %r"
            % (app["name"], ", ".join(INTEGRITY_LEVELS), app.get("integrity"))
        )
    cls = app.get("availability")
    if cls not in AVAILABILITY_CLASSES:
        raise ValueError(
            "application %r: availability must be one of %s, got %r"
            % (app["name"], ", ".join(str(c) for c in AVAILABILITY_CLASSES), cls)
        )
    for dim in RESOURCE_DIMS:
        value = app.get(dim)
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(
                "application %r: %s must be a non-negative number, got %r"
                % (app["name"], dim, value)
            )


def resource_totals(applications):
    """Sum the CPU, memory, and I/O demand of a list of applications.

    Returns a (cpu, memory, io) tuple. Worked: applications demanding
    40/400000/6, 30/300000/4, and 20/200000/3 total 90/900000/13.
    """
    cpu = sum(float(a["cpu_units"]) for a in applications)
    mem = sum(float(a["memory_bytes"]) for a in applications)
    io = sum(float(a["io_ports"]) for a in applications)
    return cpu, mem, io


def partition_budgets(applications_by_partition):
    """Compute the per-partition resource budget of each partition.

    applications_by_partition maps a partition name to the list of
    applications hosted in it. Returns a dict of
    partition name -> (cpu, memory, io). Worked: two applications of
    40/400000/6 and 30/300000/4 in partition P-1 give (70, 700000, 10).
    """
    budgets = {}
    for partition, apps in applications_by_partition.items():
        budgets[partition] = resource_totals(apps)
    return budgets


def allocate_applications(module, applications, partitions=None):
    """Allocate applications to partitions on a module and check budgets.

    module: dict with name, cpu_units, memory_bytes, io_ports.
    applications: list of dicts with name, integrity (A-E), availability
        (1-3), cpu_units, memory_bytes, io_ports.
    partitions: optional dict mapping application name to partition name;
        when omitted, each application gets its own partition named
        "P-<application name>". Applications named in partitions must
        exist in applications; every application must be assigned.

    Returns a dict with:
      - allocations: list of records {application, partition, integrity,
        availability, cpu_units, memory_bytes, io_ports}
      - partition_budgets: partition name -> (cpu, memory, io)
      - module_totals: (cpu, memory, io) summed over the module

    Raises ValueError when a module dimension is exceeded (over budget),
    naming the over-budget applications in that dimension. Budget
    equality within ALLOCATION_TOLERANCE is accepted.
    """
    _validate_module(module)
    for app in applications:
        _validate_application(app)

    app_names = [a["name"] for a in applications]
    if len(set(app_names)) != len(app_names):
        raise ValueError("application names must be unique")

    if partitions is None:
        by_partition = {("P-%s" % name): [name] for name in app_names}
    else:
        by_partition = {}
        assigned = set()
        for app_name, partition in partitions.items():
            if app_name not in app_names:
                raise ValueError(
                    "partition map references unknown application %r" % app_name
                )
            by_partition.setdefault(partition, []).append(app_name)
            assigned.add(app_name)
        missing = [n for n in app_names if n not in assigned]
        if missing:
            raise ValueError(
                "unassigned applications: %s" % ", ".join(sorted(missing))
            )

    by_name = {a["name"]: a for a in applications}
    allocations = []
    for partition, names in sorted(by_partition.items()):
        for name in sorted(names):
            app = by_name[name]
            allocations.append(
                {
                    "application": name,
                    "partition": partition,
                    "integrity": str(app["integrity"]).strip().upper(),
                    "availability": app["availability"],
                    "cpu_units": float(app["cpu_units"]),
                    "memory_bytes": float(app["memory_bytes"]),
                    "io_ports": float(app["io_ports"]),
                }
            )

    budgets = {
        p: resource_totals([by_name[n] for n in names])
        for p, names in by_partition.items()
    }
    cpu, mem, io = resource_totals(applications)

    over = []
    for dim, demanded, budget in (
        ("cpu_units", cpu, module["cpu_units"]),
        ("memory_bytes", mem, module["memory_bytes"]),
        ("io_ports", io, module["io_ports"]),
    ):
        if demanded > budget + ALLOCATION_TOLERANCE:
            offenders = sorted(
                a["name"] for a in applications if a[dim] > 0
            )
            over.append(
                "module %r %s demand %.3f exceeds budget %.3f (over-budget "
                "applications: %s)"
                % (module["name"], RESOURCE_NAMES[dim], demanded, budget,
                   ", ".join(offenders))
            )
    if over:
        raise ValueError("; ".join(over))

    return {
        "module": module["name"],
        "allocations": allocations,
        "partition_budgets": budgets,
        "module_totals": (cpu, mem, io),
    }


def contention_report(module, applications):
    """Check an application set against a module for resource contention.

    Returns a deterministic list of issue dicts, each with:
      - kind: "application" (a single app exceeds the module budget in a
        dimension, or its addition first pushes the aggregate demand over
        the budget) or "module" (aggregate demand exceeds the budget)
      - resource: "cpu", "memory", or "io"
      - name: application or module name
      - demanded, budget: numeric values for the dimension

    An allocation that fits every dimension returns an empty list.
    Worked: module budget 100 CPU with apps of 60, 30, 20 CPU (FMS,
    ADIRU, Display) yields an application issue naming FMS, whose
    addition pushes the aggregate past the budget (name-ordered
    cumulative sum: ADIRU 30, Display 50, FMS 110 over 100), and a
    module issue for cpu with demanded 110 and budget 100.
    """
    _validate_module(module)
    for app in applications:
        _validate_application(app)

    issues = []
    cpu, mem, io = resource_totals(applications)
    for dim, demanded, budget in (
        ("cpu_units", cpu, module["cpu_units"]),
        ("memory_bytes", mem, module["memory_bytes"]),
        ("io_ports", io, module["io_ports"]),
    ):
        if demanded > budget + ALLOCATION_TOLERANCE:
            issues.append(
                {
                    "kind": "module",
                    "resource": RESOURCE_NAMES[dim],
                    "name": module["name"],
                    "demanded": demanded,
                    "budget": budget,
                }
            )
            # Name the over-budget application: the first app in
            # name-ordered cumulative order whose addition crosses the
            # budget in this dimension.
            cumulative = 0.0
            for app in sorted(applications, key=lambda a: a["name"]):
                cumulative += float(app[dim])
                if cumulative > budget + ALLOCATION_TOLERANCE:
                    issues.append(
                        {
                            "kind": "application",
                            "resource": RESOURCE_NAMES[dim],
                            "name": app["name"],
                            "demanded": float(app[dim]),
                            "budget": budget,
                        }
                    )
                    break
    for app in applications:
        for dim in RESOURCE_DIMS:
            demanded = float(app[dim])
            budget = float(module[dim])
            if demanded > budget + ALLOCATION_TOLERANCE:
                issues.append(
                    {
                        "kind": "application",
                        "resource": RESOURCE_NAMES[dim],
                        "name": app["name"],
                        "demanded": demanded,
                        "budget": budget,
                    }
                )
    return issues


def acceptance_criteria(module, applications, allocations=None):
    """Generate deterministic module acceptance criteria (list of str).

    The criteria cover platform definition, module acceptance testing,
    resource usage verification, failure containment, availability
    demonstration, and incremental certification credit. The list is
    deterministic for a given module and application set, so it can be
    used as a checklist in the module acceptance plan.
    """
    _validate_module(module)
    for app in applications:
        _validate_application(app)
    levels = sorted({str(a["integrity"]).strip().upper() for a in applications})
    classes = sorted({int(a["availability"]) for a in applications})
    cpu, mem, io = resource_totals(applications)
    name = module["name"]
    return [
        "Module %s acceptance: platform definition and configuration index "
        "frozen for the accepted module population" % name,
        "Module %s acceptance: module acceptance test shows every hosted "
        "partition boots and executes within its allocated windows" % name,
        "Module %s acceptance: resource usage verified within budget "
        "(cpu %.3f of %.3f, memory %.3f of %.3f bytes, io %.3f of %.3f ports)"
        % (name, cpu, module["cpu_units"], mem, module["memory_bytes"],
           io, module["io_ports"]),
        "Module %s acceptance: failure containment between partitions "
        "demonstrated for integrity levels %s" % (name, "/".join(levels)),
        "Module %s acceptance: availability classes %s demonstrated under "
        "fault injection of shared resources"
        % (name, "/".join(str(c) for c in classes)),
        "Module %s acceptance: incremental certification credit recorded so "
        "accepted modules and applications can be reused with reduced "
        "re-verification" % name,
    ]


def development_assurance_steps(integrity_level):
    """Lay out the development assurance steps for one integrity level.

    Returns a deterministic list of step strings: planning, requirements,
    design, verification, configuration management, and airworthiness
    liaison. The verification step scales with the level (level A adds
    rigorous coverage, level E reduces to minimal activity). Worked:
    level A includes "Verify the design with rigorous coverage evidence";
    level E includes only baseline configuration management.
    """
    level = str(integrity_level).strip().upper()
    if level not in INTEGRITY_LEVELS:
        raise ValueError(
            "unknown integrity level %r (expected one of %s)"
            % (integrity_level, ", ".join(INTEGRITY_LEVELS))
        )
    steps = [
        "Plan the development assurance activities for integrity level %s" % level,
        "Capture and review the requirements for level %s" % level,
        "Design the item to satisfy the requirements at level %s" % level,
    ]
    if level in ("A", "B"):
        steps.append(
            "Verify the design with rigorous coverage evidence at level %s" % level
        )
    elif level in ("C", "D"):
        steps.append(
            "Verify the design with focused coverage evidence at level %s" % level
        )
    else:
        steps.append(
            "Verify the design with minimal activity at level %s" % level
        )
    steps.append(
        "Apply configuration management and problem reporting at level %s" % level
    )
    if level in ("A", "B", "C"):
        steps.append(
            "Liaise with the airworthiness authority on level %s evidence" % level
        )
    return steps


if __name__ == "__main__":
    # Self-check: print the worked example from SKILL.md.
    module = {"name": "IMA-1", "cpu_units": 100, "memory_bytes": 1_000_000,
              "io_ports": 16}
    apps = [
        {"name": "FMS", "integrity": "A", "availability": 1,
         "cpu_units": 40, "memory_bytes": 400_000, "io_ports": 6},
        {"name": "ADIRU", "integrity": "B", "availability": 1,
         "cpu_units": 30, "memory_bytes": 300_000, "io_ports": 4},
        {"name": "Display", "integrity": "C", "availability": 2,
         "cpu_units": 20, "memory_bytes": 200_000, "io_ports": 3},
    ]
    result = allocate_applications(module, apps)
    print("allocations:", len(result["allocations"]))
    print("module_totals:", result["module_totals"])
    print("contention:", contention_report(module, apps))
    for criterion in acceptance_criteria(module, apps):
        print("-", criterion)

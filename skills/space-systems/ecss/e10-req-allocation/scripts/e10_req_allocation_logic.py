#!/usr/bin/env python3
"""ECSS-E-ST-10C requirement allocation logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
clause 5.2.3.5 requires every requirement to be allocated to the
function(s) it drives (functional analysis) and to the product-tree
element(s) -- configuration items (CIs) -- that implement it. Both
sides are required before an allocation counts as complete; this
module tracks allocations against a fixed function tree and product
tree, checks allocation completeness, and traces functions to the CIs
that carry their requirements (and back).

All functions are pure: none of them mutate the allocations mapping
passed in; each returns a new mapping.
"""


def allocate_requirement(allocations, requirement, functions_for_req, elements_for_req, functions, product_tree):
    """Return a new allocations mapping with requirement allocated to the
    given functions and product-tree elements (CIs).

    Validates that every named function is in functions and every named
    element is in product_tree, and that both sides are non-empty (a
    requirement allocated to only a function or only a CI is not
    complete per clause 5.2.3.5). Raises ValueError on any violation.
    """
    unknown_functions = sorted(set(functions_for_req) - set(functions))
    if unknown_functions:
        raise ValueError("unknown function(s): %r" % (unknown_functions,))
    unknown_elements = sorted(set(elements_for_req) - set(product_tree))
    if unknown_elements:
        raise ValueError("unknown product-tree element(s): %r" % (unknown_elements,))
    if not functions_for_req:
        raise ValueError("requirement %r has no functional allocation" % (requirement,))
    if not elements_for_req:
        raise ValueError("requirement %r has no product-tree allocation" % (requirement,))
    new_allocations = dict(allocations)
    new_allocations[requirement] = {
        "functions": tuple(sorted(set(functions_for_req))),
        "elements": tuple(sorted(set(elements_for_req))),
    }
    return new_allocations


def allocation_status(allocations, requirement):
    """'allocated' if requirement carries a (function, element) record,
    else 'unallocated'. allocate_requirement never stores a one-sided
    record, so any stored record is complete."""
    return "allocated" if requirement in allocations else "unallocated"


def coverage_report(requirements, allocations):
    """(allocated, unallocated) requirement lists, each in the order the
    requirements were given."""
    allocated = [r for r in requirements if r in allocations]
    unallocated = [r for r in requirements if r not in allocations]
    return (allocated, unallocated)


def elements_for_function(allocations, function):
    """Sorted product-tree elements (CIs) allocated, via requirements, to
    the given function -- traces functional analysis through to
    configuration items per clause 5.2.3.5."""
    elements = set()
    for record in allocations.values():
        if function in record["functions"]:
            elements.update(record["elements"])
    return sorted(elements)


def requirements_for_element(allocations, element):
    """Sorted requirement IDs allocated to the given product-tree element
    (CI)."""
    return sorted(r for r, record in allocations.items() if element in record["elements"])


def unallocated_functions(functions, allocations):
    """Sorted functions from the reference function tree that carry no
    allocated requirement (orphan functions worth a second look)."""
    used = set()
    for record in allocations.values():
        used.update(record["functions"])
    return sorted(set(functions) - used)


def unallocated_elements(product_tree, allocations):
    """Sorted product-tree elements (CIs) that carry no allocated
    requirement (orphan CIs worth a second look)."""
    used = set()
    for record in allocations.values():
        used.update(record["elements"])
    return sorted(set(product_tree) - used)

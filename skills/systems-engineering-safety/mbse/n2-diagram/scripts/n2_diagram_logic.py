#!/usr/bin/env python3
"""N2 interface diagram logic (paraphrase, common methodology).

Common-knowledge summary (standards-map.yaml, arp4754a: interface
requirements capture is part of the system development process; the
N2 chart is a standard interface analysis tool used to define and
review data interfaces between functions or components): an N2
diagram arranges the system elements along the matrix diagonal and
records each interface pair in the off-diagonal cell of its source
row and target column. The cell value is the number of interfaces
from the row element to the column element. The interface count per
element is the row sum plus the column sum (outgoing plus incoming).
A missing data link is a required interface pair whose cell is zero.
An isolated element has a zero total count. This module is pure
stdlib; no third-party imports.
"""


def _validate_elements(elements):
    """Check the element list: non-empty, unique, non-empty strings."""
    if not isinstance(elements, (list, tuple)) or len(elements) == 0:
        raise ValueError("elements must be a non-empty list, got %r" % (elements,))
    for el in elements:
        if not isinstance(el, str) or not el.strip():
            raise ValueError("each element must be a non-empty string, got %r" % (el,))
    if len(set(elements)) != len(elements):
        raise ValueError("element names must be unique, got %r" % (elements,))


def _normalize_pairs(pairs, elements, label):
    """Validate (source, target) pairs and map them to row/column indices.

    Rejects unknown endpoints and self interfaces; returns a list of
    (row, column) index tuples in the given order.
    """
    if not isinstance(pairs, (list, tuple)):
        raise ValueError("%s must be a list of (source, target) pairs, got %r" % (label, pairs))
    index = {name: i for i, name in enumerate(elements)}
    out = []
    for pair in pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("%s entry must be a (source, target) pair, got %r" % (label, pair))
        src, tgt = pair
        if not isinstance(src, str) or not isinstance(tgt, str):
            raise ValueError("%s names must be strings, got %r" % (label, pair))
        if src not in index:
            raise ValueError("%s source '%s' not in elements" % (label, src))
        if tgt not in index:
            raise ValueError("%s target '%s' not in elements" % (label, tgt))
        if src == tgt:
            raise ValueError("%s self interface %r is not allowed in an N2 diagram" % (label, pair))
        out.append((index[src], index[tgt]))
    return out


def _validate_matrix(elements, matrix):
    """Check the matrix shape: square, one row and column per element."""
    n = len(elements)
    if not isinstance(matrix, (list, tuple)) or len(matrix) != n:
        raise ValueError("matrix must have one row per element, got %r" % (matrix,))
    for row in matrix:
        if not isinstance(row, (list, tuple)) or len(row) != n:
            raise ValueError("each matrix row must have one column per element, got %r" % (row,))
        for cell in row:
            if not isinstance(cell, int) or cell < 0:
                raise ValueError("matrix cells must be non-negative ints, got %r" % (cell,))


def build_matrix(elements, interfaces):
    """NxN interface matrix: cell[i][j] counts interfaces from i to j.

    Row and column order follows the elements list; diagonal cells
    stay zero because self interfaces are rejected. Raises ValueError
    on invalid input.
    """
    _validate_elements(elements)
    pairs = _normalize_pairs(interfaces, elements, "interfaces")
    n = len(elements)
    matrix = [[0] * n for _ in range(n)]
    for i, j in pairs:
        matrix[i][j] += 1
    return matrix


def interface_counts(elements, matrix):
    """Interface count per element: row sum plus column sum.

    Each interface is counted once per endpoint, so an element that
    sends k interfaces and receives m interfaces has count k + m.
    Raises ValueError when the matrix shape or content is invalid.
    """
    _validate_elements(elements)
    _validate_matrix(elements, matrix)
    n = len(elements)
    counts = {}
    for i, name in enumerate(elements):
        row_sum = sum(matrix[i])
        col_sum = sum(matrix[j][i] for j in range(n))
        counts[name] = row_sum + col_sum
    return counts


def total_interfaces(elements, matrix):
    """Total interface entries: sum of every off-diagonal cell.

    Equals the number of interface pairs when the pairs are unique.
    Raises ValueError when the matrix shape or content is invalid.
    """
    _validate_elements(elements)
    _validate_matrix(elements, matrix)
    return sum(sum(row) for row in matrix)


def missing_links(elements, matrix, required_pairs):
    """Required interface pairs with zero modeled interfaces.

    Returns the list of (source, target) pairs, in required order,
    whose cell in the matrix is zero. An empty result means every
    required data link is modeled. Raises ValueError on invalid input.
    """
    _validate_elements(elements)
    _validate_matrix(elements, matrix)
    pairs = _normalize_pairs(required_pairs, elements, "required_pairs")
    missing = []
    for idx, (i, j) in enumerate(pairs):
        if matrix[i][j] == 0:
            missing.append((required_pairs[idx][0], required_pairs[idx][1]))
    return missing


def isolated_elements(elements, matrix):
    """Elements with zero interfaces (no outgoing and no incoming).

    Returns the list of element names with a zero total count.
    Raises ValueError when the matrix shape or content is invalid.
    """
    _validate_elements(elements)
    _validate_matrix(elements, matrix)
    counts = interface_counts(elements, matrix)
    return [name for name in elements if counts[name] == 0]


def render_matrix(elements, matrix):
    """ASCII text rendering of the N2 matrix with a header row.

    The first line lists the column elements; every following line
    starts with the row element name, then one cell per column.
    Raises ValueError on invalid input.
    """
    _validate_elements(elements)
    _validate_matrix(elements, matrix)
    n = len(elements)
    col_w = max([len(name) for name in elements] + [1])
    name_w = max([len(name) for name in elements] + [1])
    lines = [" " * name_w + " " + " ".join(name.rjust(col_w) for name in elements)]
    for i, name in enumerate(elements):
        cells = " ".join(str(matrix[i][j]).rjust(col_w) for j in range(n))
        lines.append(name.rjust(name_w) + " " + cells)
    return "\n".join(lines)

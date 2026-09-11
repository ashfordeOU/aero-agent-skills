import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1006_char_identifiability_logic import detect_numeric_gaps, assess_identifiability

r1 = [{"id": "REQ-SYS-001"}, {"id": "REQ-SYS-003"}]
assert detect_numeric_gaps(r1, "REQ-SYS-") == [], "single gap should be tolerated"

r2 = [{"id": "REQ-SYS-001"}, {"id": "REQ-SYS-010"}]
g = detect_numeric_gaps(r2, "REQ-SYS-")
assert len(g) == 1 and g[0]["missing_count"] == 8, "large gap should be detected"

r3 = [{"id": "REQ-SYS-001"}, {"id": "REQ-SYS-002"}]
assert assess_identifiability(r3)["compliant"] is True

try:
    assess_identifiability("bad")
    assert False, "should raise"
except TypeError:
    pass

print("smoke OK")

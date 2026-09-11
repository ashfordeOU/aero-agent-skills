import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import e1009_time_logic as m

errors = []

v = m.tai_to_tt(0.0)
if abs(v - 32.184) > 1e-9:
    errors.append(f"tai_to_tt: {v}")

v = m.gps_to_tai(m.tai_to_gps(1000.0))
if abs(v - 1000.0) > 1e-9:
    errors.append(f"gps roundtrip: {v}")

v = m.tai_to_utc(m.utc_to_tai(500.0, 37), 37)
if abs(v - 500.0) > 1e-9:
    errors.append(f"utc roundtrip: {v}")

v = m.get_epoch_jd("J2000.0")
if abs(v - 2451545.0) > 0.001:
    errors.append(f"J2000 JD: {v}")

v = m.jd_to_mjd(2451545.0)
if abs(v - 51544.5) > 1e-6:
    errors.append(f"jd_to_mjd: {v}")

v = m.days_from_j2000(2451545.0)
if abs(v) > 1e-9:
    errors.append(f"days_from_j2000 at epoch: {v}")

v = m.centuries_from_j2000(2451545.0 + 36525.0)
if abs(v - 1.0) > 1e-9:
    errors.append(f"centuries: {v}")

try:
    m.validate_time_scale("XYZ")
    errors.append("no TimeScaleError for XYZ")
except m.TimeScaleError:
    pass

try:
    m.check_frame_time_scale("ECI", "UTC")
    errors.append("no FrameTimeScaleError for ECI+UTC")
except m.FrameTimeScaleError:
    pass

try:
    m.tai_to_utc(1000.0, -1)
    errors.append("no ValueError for negative leaps")
except ValueError:
    pass

try:
    m.tai_to_utc(1000.0, True)
    errors.append("no ValueError for bool leaps")
except ValueError:
    pass

if errors:
    print("ERRORS:", errors)
    sys.exit(1)
print("Spot-checks: OK")

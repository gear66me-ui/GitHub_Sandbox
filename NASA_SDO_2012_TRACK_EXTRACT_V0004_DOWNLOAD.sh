#!/usr/bin/env bash
set -euo pipefail

BASE="https://raw.githubusercontent.com/gear66me-ui/GitHub_Sandbox/main"
TARGET="${1:-NASA_SDO_2012_TRACK_EXTRACT.py}"

curl -fsSL --retry 3 --retry-delay 1 \
  "$BASE/NASA_SDO_2012_TRACK_EXTRACT_V0003_DOWNLOAD.sh" \
  | bash -s -- "$TARGET"

python - "$TARGET" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

text = text.replace('VERSION = "V0003"', 'VERSION = "V0004"', 1)

marker = '\ndef normalize_and_fill(frame_table: pd.DataFrame) -> pd.DataFrame:\n'
if marker not in text:
    raise RuntimeError("normalize_and_fill insertion marker not found")

insertion = r'''

def select_continuous_venus_track(frame_table: pd.DataFrame) -> pd.DataFrame:
    table = frame_table.copy()
    required = [
        "frame_index",
        "solar_cx_px",
        "solar_cy_px",
        "solar_radius_px",
        "venus_cx_px",
        "venus_cy_px",
        "venus_radius_px",
        "venus_quality",
        "venus_detected",
    ]
    missing = [name for name in required if name not in table.columns]
    if missing:
        raise RuntimeError(f"Trajectory filter missing columns: {missing}")

    table["venus_detected_raw"] = table["venus_detected"].astype(bool)
    for name in (
        "venus_cx_px",
        "venus_cy_px",
        "venus_radius_px",
        "venus_quality",
    ):
        table[f"{name}_raw_detector"] = table[name]

    solar_radius = table["solar_radius_px"].to_numpy(dtype=float)
    x_norm = (
        table["venus_cx_px"].to_numpy(dtype=float)
        - table["solar_cx_px"].to_numpy(dtype=float)
    ) / solar_radius
    y_norm = (
        table["solar_cy_px"].to_numpy(dtype=float)
        - table["venus_cy_px"].to_numpy(dtype=float)
    ) / solar_radius
    radius_norm = table["venus_radius_px"].to_numpy(dtype=float) / solar_radius
    quality = table["venus_quality"].to_numpy(dtype=float)
    detected = table["venus_detected"].to_numpy(dtype=bool)
    frame = table["frame_index"].to_numpy(dtype=float)

    finite = (
        detected
        & np.isfinite(x_norm)
        & np.isfinite(y_norm)
        & np.isfinite(radius_norm)
        & np.isfinite(quality)
        & np.isfinite(frame)
        & (solar_radius > 0.0)
    )
    if np.count_nonzero(finite) < 80:
        raise RuntimeError("Too few finite detections for trajectory filtering.")

    median_radius = float(np.median(radius_norm[finite]))
    radius_tolerance = max(0.008, 0.35 * median_radius)
    candidate = (
        finite
        & (quality >= 0.12)
        & (np.abs(radius_norm - median_radius) <= radius_tolerance)
    )
    candidate_indices = np.flatnonzero(candidate)
    if candidate_indices.size < 80:
        candidate_indices = np.flatnonzero(finite)
    if candidate_indices.size < 80:
        raise RuntimeError("Too few radius-consistent Venus candidates.")

    frame_min = float(np.min(frame[candidate_indices]))
    frame_span = float(np.max(frame[candidate_indices]) - frame_min)
    if frame_span <= 0.0:
        raise RuntimeError("Trajectory frame span is zero.")
    u_all = (frame - frame_min) / frame_span

    u = u_all[candidate_indices]
    x = x_norm[candidate_indices]
    y = y_norm[candidate_indices]
    rn = radius_norm[candidate_indices]
    q = np.clip(quality[candidate_indices], 0.0, 1.0)

    residual_limit = max(0.030, 1.80 * median_radius)
    radius_limit = max(0.008, 0.30 * median_radius)
    rng = np.random.default_rng(20120605)
    best_mask = None
    best_score = -np.inf
    trial_count = min(9000, max(2500, 3 * candidate_indices.size))

    for _ in range(trial_count):
        pair = rng.integers(0, candidate_indices.size, size=2)
        i = int(pair[0])
        j = int(pair[1])
        if i == j:
            continue
        du = float(u[j] - u[i])
        if abs(du) < 0.18:
            continue
        vx = float((x[j] - x[i]) / du)
        vy = float((y[j] - y[i]) / du)
        speed = math.hypot(vx, vy)
        if not (0.45 <= speed <= 2.80):
            continue
        x0 = float(x[i] - vx * u[i])
        y0 = float(y[i] - vy * u[i])
        residual = np.hypot(x - (x0 + vx * u), y - (y0 + vy * u))
        inlier = (
            (residual <= residual_limit)
            & (np.abs(rn - median_radius) <= radius_limit)
        )
        count = int(np.count_nonzero(inlier))
        if count < 40:
            continue
        span = float(np.ptp(u[inlier]))
        if span < 0.45:
            continue
        median_residual = float(np.median(residual[inlier]))
        mean_quality = float(np.mean(q[inlier]))
        score = count + 350.0 * span + 80.0 * mean_quality - 900.0 * median_residual
        if score > best_score:
            best_score = score
            best_mask = inlier

    if best_mask is None:
        raise RuntimeError(
            "No continuous moving Venus trajectory passed the RANSAC constraints."
        )

    inlier = best_mask.copy()
    coeff_x = np.zeros(2, dtype=float)
    coeff_y = np.zeros(2, dtype=float)
    for _ in range(8):
        if np.count_nonzero(inlier) < 20:
            break
        design = np.column_stack((np.ones(np.count_nonzero(inlier)), u[inlier]))
        coeff_x, *_ = np.linalg.lstsq(design, x[inlier], rcond=None)
        coeff_y, *_ = np.linalg.lstsq(design, y[inlier], rcond=None)
        predicted_x = coeff_x[0] + coeff_x[1] * u
        predicted_y = coeff_y[0] + coeff_y[1] * u
        residual = np.hypot(x - predicted_x, y - predicted_y)
        median_residual, sigma_residual = robust_scale(residual[inlier])
        adaptive_limit = min(
            0.085,
            max(0.018, 1.20 * median_radius, median_residual + 3.5 * sigma_residual),
        )
        updated = (
            (residual <= adaptive_limit)
            & (np.abs(rn - median_radius) <= radius_limit)
        )
        if np.array_equal(updated, inlier):
            break
        inlier = updated

    selected_count = int(np.count_nonzero(inlier))
    selected_span = float(np.ptp(u[inlier])) if selected_count else 0.0
    speed = math.hypot(float(coeff_x[1]), float(coeff_y[1]))
    minimum_count = max(180, int(round(0.045 * len(table))))
    if selected_count < minimum_count:
        raise RuntimeError(
            f"Continuous Venus track has only {selected_count} inliers; "
            f"minimum required is {minimum_count}."
        )
    if selected_span < 0.55:
        raise RuntimeError(
            f"Continuous Venus track spans only {selected_span:.3f} of the video."
        )
    if not (0.45 <= speed <= 2.80):
        raise RuntimeError(
            f"Continuous Venus track speed {speed:.6f} R_sun/video is implausible."
        )

    selected_global = np.zeros(len(table), dtype=bool)
    selected_global[candidate_indices[inlier]] = True
    predicted_x_all = coeff_x[0] + coeff_x[1] * u_all
    predicted_y_all = coeff_y[0] + coeff_y[1] * u_all
    residual_all = np.hypot(x_norm - predicted_x_all, y_norm - predicted_y_all)

    table["venus_track_inlier"] = selected_global
    table["trajectory_model_x_norm"] = predicted_x_all
    table["trajectory_model_y_norm"] = predicted_y_all
    table["trajectory_residual_norm"] = residual_all
    table["trajectory_speed_norm_per_video"] = speed
    table["venus_detected"] = selected_global
    table["venus_source"] = np.where(
        selected_global,
        "DETECTED_CONTINUOUS_TRACK",
        "REJECTED_SUNSPOT_OR_ARTIFACT",
    )

    reject = ~selected_global
    table.loc[
        reject,
        ["venus_cx_px", "venus_cy_px", "venus_radius_px", "venus_quality"],
    ] = np.nan

    print(
        "DEBUG | continuous Venus track selected | "
        f"raw_detections={int(np.count_nonzero(detected))} | "
        f"selected={selected_count} | "
        f"span={selected_span:.6f} | "
        f"speed={speed:.6f} R_sun/video"
    )
    return table
'''

text = text.replace(marker, insertion + marker, 1)

old_main = '''    raw_table, metadata = process_video(config)\n    normalized_table = normalize_and_fill(raw_table)\n'''
new_main = '''    raw_table, metadata = process_video(config)\n    filtered_table = select_continuous_venus_track(raw_table)\n    normalized_table = normalize_and_fill(filtered_table)\n'''
if old_main not in text:
    raise RuntimeError("main trajectory-filter patch marker not found")
text = text.replace(old_main, new_main, 1)

old_angle = '''        track_angle_deg=float(\n            np.degrees(np.arctan2(direction[1], direction[0]))\n        ),\n'''
new_angle = '''        track_angle_deg=float(\n            (np.degrees(np.arctan2(direction[1], direction[0])) + 90.0)\n            % 180.0\n            - 90.0\n        ),\n'''
if old_angle not in text:
    raise RuntimeError("TLS angle normalization patch marker not found")
text = text.replace(old_angle, new_angle, 1)

path.write_text(text, encoding="utf-8")
PY

python -m py_compile "$TARGET"

python - "$TARGET" <<'PY'
from pathlib import Path
import runpy
import sys
import numpy as np
import pandas as pd

path = Path(sys.argv[1])
namespace = runpy.run_path(str(path))
select_track = namespace["select_continuous_venus_track"]

rng = np.random.default_rng(1769)
count = 1200
frame = np.arange(count, dtype=float)
u = frame / (count - 1)
true_x = -0.82 + 1.64 * u
true_y = 0.23 - 0.31 * u
is_true = rng.random(count) < 0.66
x = np.where(is_true, true_x + rng.normal(0.0, 0.006, count), 0.18 + rng.normal(0.0, 0.008, count))
y = np.where(is_true, true_y + rng.normal(0.0, 0.006, count), 0.31 + rng.normal(0.0, 0.008, count))
solar_radius = np.full(count, 200.0)
solar_cx = np.full(count, 256.0)
solar_cy = np.full(count, 256.0)
radius_px = np.where(is_true, 6.2 + rng.normal(0.0, 0.15, count), 5.7 + rng.normal(0.0, 0.25, count))

table = pd.DataFrame({
    "frame_index": frame,
    "time_s": frame / 30.0,
    "solar_cx_px": solar_cx,
    "solar_cy_px": solar_cy,
    "solar_radius_px": solar_radius,
    "solar_quality": np.ones(count),
    "solar_method": ["TEST"] * count,
    "venus_cx_px": solar_cx + x * solar_radius,
    "venus_cy_px": solar_cy - y * solar_radius,
    "venus_radius_px": radius_px,
    "venus_quality": np.where(is_true, 0.85, 0.72),
    "venus_detected": np.ones(count, dtype=bool),
    "venus_source": ["TEST"] * count,
})

filtered = select_track(table)
selected = filtered["venus_track_inlier"].to_numpy(dtype=bool)
selected_true = int(np.count_nonzero(selected & is_true))
selected_false = int(np.count_nonzero(selected & ~is_true))
if selected_true < 650 or selected_false > 40:
    raise RuntimeError(
        f"Trajectory regression failed: true={selected_true}, false={selected_false}"
    )
print(
    "Regression test: moving Venus trajectory isolated from stationary sunspot | "
    f"true={selected_true} | false={selected_false}"
)
PY

SHA256="$(sha256sum "$TARGET" | awk '{print $1}')"
printf 'Downloaded and verified: %s\n' "$TARGET"
printf 'Version: V0004\n'
printf 'SHA-256: %s\n' "$SHA256"

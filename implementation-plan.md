# Implementation Plan: Data Normalization & Outlier Replacement

**Project:** Fall-detection-system
**Goal:** Replace sustained "wrong subject" detections (background people picked up for 0-30 frames) with values reconstructed from surrounding good data — never dropping frames — before the data reaches feature engineering / training.

---

## 1. Problem Summary

- MediaPipe pose tracking occasionally locks onto a person in the background instead of the recording subject.
- This isn't single-frame jitter — it's a **sustained run of 30-50 frames** with a wrong (but internally consistent) trajectory.
- Left uncleaned, this corrupts `analyze_features.py` statistics and `train_model.py` sequences, since the GRU will learn from motion that isn't the subject's.

---

## 2. Scope

| In scope | Out of scope (later phase) |
|---|---|
| Post-hoc cleaning of already-recorded `data/raw/session_*.csv` files | Live rejection during `collect_data.py` capture |
| Centroid-jump detection + fill (interpolation / hold-last-good) | Multi-person MediaPipe handling / re-identification |
| Config-driven thresholds | Automatic threshold tuning |

**Note on approach:** outlier frames are never deleted. Interior outlier runs (good frame on both sides) get linear interpolation between those good frames. Runs touching the start/end of a session (no good frame on one side) get filled by holding the nearest good frame's values. This keeps every session's frame count and `TIME_STEPS` sequence alignment intact — dropping frames would shift the 10-frame windows `train_model.py` builds and could silently misalign labels.

---

## 3. Pipeline Placement

```
collect_data.py          (existing, unchanged)
        │
        ▼
data/raw/session_*.csv    (existing raw files — kept as-is, untouched, for audit)
        │
        ▼
normalize_data.py   ← NEW STEP
        │
        ▼
data/clean/session_*.csv  ← NEW output directory
        │
        ▼
analyze_features.py / train_model.py   (point these at data/clean/ instead of data/raw/)
```

Raw CSVs are never modified in place — cleaning always writes to a separate `data/clean/` directory so you can always compare before/after or re-run with different thresholds.

---

## 4. Step-by-Step Implementation

### Step 1 — Confirm column structure
- [ ] Open one `session_*.csv` and list actual column names (e.g. `left_hip_x`, `left_hip_y`, or whatever `pose_estimator.py` emits).
- [ ] Confirm which landmarks are most reliably tracked (hips are usually stable — avoid hands/feet, which occlude often).

### Step 2 — Drop in `normalize_data.py`
- [ ] Add the script to the project root (or a new `preprocessing/` folder).
- [ ] Update `CENTROID_LANDMARKS` to match real column names from Step 1.

### Step 3 — Calibrate thresholds on real data
- [ ] Pick 2-3 sessions known to have a background-person run.
- [ ] Run the script with `JUMP_THRESHOLD` logging enabled (print raw centroid distances per frame) to see where the real jump sits vs. normal subject movement.
- [ ] Set `JUMP_THRESHOLD` just above normal movement, `MIN_OUTLIER_RUN` around 5 (filters genuine short jitter from real subject swaps).

### Step 4 — Batch-process existing sessions
- [ ] Write a small wrapper that loops `normalize_data.py` over every file in `data/raw/`, writing to `data/clean/`.
- [ ] Log a summary: filename, frames flagged, how each run was filled (interpolated vs. held-from-edge).

### Step 5 — Spot-check results
- [ ] For each session with flagged frames, plot centroid X/Y over time (before vs. after cleaning) to visually confirm the flagged run corresponds to the background-person jump, not a real fast movement (e.g. an actual fall).
- [ ] **Important:** a real fall is also a sudden movement — verify the threshold doesn't accidentally treat real fall frames as outliers and flatten them into held/interpolated (non-real) values. This is the main risk of this approach and needs manual review, not just automated trust.
- [ ] Check how large the held-from-edge runs are — if a session starts with 40+ frames of "held" (non-real) data, that's a lot of synthetic signal feeding into training; consider re-recording sessions with large edge runs instead of relying on the fill.

### Step 6 — Wire into the rest of the pipeline
- [ ] Update `config.py` to point `DATA_DIR` (or equivalent) at `data/clean/` instead of `data/raw/`.
- [ ] Re-run `analyze_features.py` on cleaned data, compare feature statistics report to the old one — confidence check that variance dropped where expected.
- [ ] Re-train (`train_model.py`) and re-run `evaluate_model.py`, compare metrics against the pre-cleaning model.

### Step 7 (stretch) — Prevent at collection time
- [ ] In `pose_estimator.py`, track the previous frame's centroid.
- [ ] If MediaPipe can return multiple pose candidates, select the one closest to the previous centroid instead of the default/first result.
- [ ] If only single-pose detection is available, this step isn't applicable — rely on Step 6 output only.

---

## 5. Risks / Things to Watch

- **False positives on real falls:** a fall is a large, fast movement — don't let the outlier filter treat it as a "different subject" and overwrite it with held/interpolated (non-real) values. This is why Step 5 (visual spot-check) is not optional.
- **Threshold is scene-dependent:** distance-to-background-person varies with camera setup, so `JUMP_THRESHOLD` calibrated on one recording setup may not transfer to another. Re-check threshold if camera position changes.
- **Held-from-edge frames are synthetic, not real motion.** They keep frame count and sequence alignment intact, but a large held run (e.g. 40 frames of a static held pose) means that stretch of the sequence contributes no real motion signal to training. Flag sessions with large held runs for review rather than treating the fill as equivalent to a clean recording.

---

## 6. Definition of Done

- [ ] All existing `data/raw/` sessions have a corresponding cleaned file in `data/clean/`, same frame count as the original (no frames dropped).
- [ ] Feature statistics report regenerated from cleaned data.
- [ ] Model retrained on cleaned data with evaluation metrics logged for comparison against the old model.
- [ ] Threshold values and rationale documented in this file or `config.py` comments, so they're not "magic numbers" for future you.
- [ ] Sessions with unusually large held-from-edge runs flagged and reviewed (consider re-recording if the synthetic portion is too large a share of the session).

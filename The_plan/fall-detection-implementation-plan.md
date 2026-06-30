# Fall Detection System — Unified Implementation Plan

**Project:** `tinarmon/fall-detection-system`
**Goal:** Consolidate the existing codebase into a clean, menu-driven, production-ready application with one-click setup and launch on Windows.

---

## Overview

This plan restructures the project into a single CLI-controlled application. Instead of running individual scripts manually, a user launches `main.py`, picks an option from a numbered menu, and the system routes to the correct subroutine — data collection, feature extraction, training, or live inference — while staying resilient to missing files or runtime errors.

---

## Phase 1 — Directory Architecture

Reorganize the repo so models, core logic, and entry points are clearly separated.

```text
tinarmon/fall-detection-system/
├── assets/
│   ├── fall_model.keras             # Trained neural network weights
│   └── pose_landmarker_full.task    # MediaPipe pose model
├── core/
│   ├── pose_estimator.py            # Landmark detection/processing
│   └── angle_calculator.py          # Joint angle geometry
├── config.py                        # Paths, window sizes, landmark indices
├── main.py                          # NEW — master CLI menu controller
├── collect_data.py                  # UPDATED — unified data acquisition engine
├── analyze_features.py              # Feature extraction
├── train_model.py                   # Model training
├── live_inference.py                # Real-time prediction engine
├── requirements.txt                 # Pruned, top-level dependencies
├── setup.bat                        # One-click Windows installer
└── run.bat                          # One-click Windows launcher
```

**Required to secure this phase:**
- Confirm `fall_model.keras` and `pose_landmarker_full.task` are the correct, current model artifacts before relocating them into `assets/`.
- Update every hardcoded path reference in existing scripts to pull from `config.py` rather than relative strings.

---

## Phase 2 — Import-Safe Refactoring

Every script that the master menu calls into must be safe to `import` without side effects.

1. **Encapsulate execution logic** — wrap the main loop of `collect_data.py`, `analyze_features.py`, and `live_inference.py` in dedicated functions (`run_collection()`, `run_analysis()`, `run_inference()`, etc.).
2. **Add a main guard** to each file:
   ```python
   if __name__ == "__main__":
       run_collection()
   ```
   This keeps each script independently runnable from the terminal while remaining dormant when imported by `main.py`.

**Why this matters:** without this guard, importing any of these modules into the menu controller would immediately trigger camera access, file I/O, or training — long before the user makes a menu selection.

---

## Phase 3 — Data Acquisition Engine Upgrade

The data acquisition engine splits into distinct processing behaviors based on the input source, to maximize runtime efficiency and data reliability. Instead of appending frames to a single global dataset, the system generates a unique, self-contained file for every session.

### 3.1 Session Initialization & Dynamic Path Allocation
Before opening any video stream or camera feed, the system establishes the session's properties:
1. **Metadata collection prompt** — request a Subject ID or Session Name via the terminal (e.g. `SubjectA` or `User_01`).
2. **Dynamic pathing** — generate a unique, isolated file path using the subject name and an execution timestamp: `data/raw/session_{Subject_ID}_{YYYYMMDD_HHMMSS}.csv`.
3. **Atomic memory buffer** — initialize an empty tracking array (`frame_buffer = []`) in RAM. To prevent storage bottlenecks and frame drops, rows are cached in memory during playback and written to disk in a single "atomic flush" when the session cleanly terminates.

### 3.2 Input Source Routing & Labeling Strategy
- On launch, prompt: `[1] Real-time Webcam Stream` or `[2] Local Video File`.
- For local video files (automated pre-labeled batch ingestion):
  - Strip stray leading/trailing quote characters (`'` or `"`) that terminals add when a file is dragged and dropped.
  - **Upfront batch label prompt** — ask the user to assign a global behavioral tag to the file before processing: enter `0` for Still/Normal or `1` for Fall Event.
  - The processing loop applies this pre-selected label to every frame automatically, removing the need for manual real-time hotkeys.

### 3.3 Runtime Controls (Webcam vs. Video File)

**Mode A — Real-Time Webcam Stream (live hand-labeling)**
Requires manual keypress actions to map behavioral states to incoming live frames.

| Key | Action |
|-----|--------|
| `0` | Tag incoming frames as Still/Normal (standing, sitting, baseline) |
| `1` | Tag incoming frames as Fall Event (descent, impact, post-fall) |
| `Space` / `p` | Pause/resume memory buffer recording |
| `q` / `Esc` | Trigger atomic write to disk, close camera resource, and return to menu |

HUD feedback: `RECORDING: STILL (0)` (green), `RECORDING: FALL (1)` (orange), `PAUSED` (red).

**Mode B — Local Video File (hands-free processing)**
Processes pre-recorded media automatically based on the upfront label choice.

| Key / Event | Action |
|-------------|--------|
| *Automatic* | Sequentially labels all captured frames using the pre-selected global tag (`0` or `1`) |
| `Space` / `p` | Pause/resume frame playback visualization |
| `q` / `Esc` | Stop processing early (triggers an atomic flush of rows extracted up to that point) |
| *End of file* | Automatically flushes the memory buffer to disk, releases file handles, and returns to the menu cleanly |

HUD feedback: `PROCESSING BATCH: LABEL 0` or `PROCESSING BATCH: LABEL 1`, alongside a progress indicator.

### 3.4 CSV Schema & Normalization Pipeline
- **Auto-header injection** — because every session creates a brand-new file, the system automatically writes a clean header row before dumping the buffered data array.
- **Schema layout** — includes embedded metadata to prevent file mismatch confusion: `[timestamp, subject_id, input_source, label, left_angle, right_angle, x11, y11, ...]`.
- **Scale-invariant normalization** — convert pixel coordinates to `points_norm` ratios (`0.0–1.0`) before buffering, so frames collected from low-resolution webcams share identical geometric features with high-definition pre-labeled video files when combined during model training.

**Required to secure this phase:**
- Decide and document the exact landmark indices and ordering used in `points_norm` so future contributors don't silently break the schema.
- Validate that quote-stripping logic doesn't also strip legitimate characters from filenames containing apostrophes.
- Confirm the pre-label prompt clearly distinguishes "label this whole file" from the live hotkeys, so users don't confuse the two modes.
- Define a Subject ID validation rule (e.g. disallow spaces or path-breaking characters) so generated session filenames stay filesystem-safe.
- Decide how partial sessions (early `q`/`Esc` exit) are surfaced to the user — e.g. confirm the atomic flush count of rows saved before returning to the menu.

---

## Phase 4 — Master CLI Controller (`main.py`)

### 4.1 Behavior
- Clears the terminal (`cls` on Windows, `clear` on macOS/Linux) after each subroutine completes, returning to a clean menu view.

### 4.2 Menu Map
| Option | Action |
|--------|--------|
| `1` | Data Acquisition → `collect_data.py` |
| `2` | Feature Engineering → `analyze_features.py` |
| `3` | Model Training → `train_model.py` |
| `4` | Real-time Tracking → `live_inference.py` |
| `5` | Metadata Diagnostics → confirms `fall_model.keras` and `pose_landmarker_full.task` exist at expected paths |
| `0` | Exit → releases resources, closes threads cleanly |

### 4.3 Exception Handling
Wrap every subroutine call in `try/except`. On a missing file or library error:
- Print a readable diagnostic message (not a raw traceback) to the user.
- Return control to the main menu rather than crashing the process.

---

## Phase 5 — Desktop Automation Shells (Windows)

Removes the need to manually create or activate virtual environments.

### `setup.bat`
1. Checks for a local Python installation.
2. Creates an isolated virtual environment: `python -m venv venv`.
3. Upgrades pip: `python -m pip install --upgrade pip`.
4. Installs the pruned `requirements.txt`.

### `run.bat`
```batch
@echo off
call .\venv\Scripts\activate.bat
python main.py
pause
```

**Required to secure this phase:**
- Pin dependency versions in `requirements.txt` (avoid unpinned `pip install` that could pull breaking updates later).
- Test `setup.bat` on a machine without Python pre-installed to confirm the failure message is clear rather than a silent crash.

---

## Phase 6 — Integration & Validation

1. **Fresh-environment test** — delete the local `venv/` folder and any generated config, then re-run `setup.bat` to confirm a fully hands-free, repeatable install.
2. **Menu loop test** — walk every option in `main.py` in sequence, confirming that exiting a camera stream or finishing a video file always returns control to the menu without leaving orphaned threads or hung OpenCV windows.
3. **Schema regression test** — run a sample collection session and confirm the resulting CSV rows match the expected header order and normalized value ranges (0–1 for `points_norm`).

---

## Summary Checklist

- [ ] Move model/asset files into `assets/`, update all path references via `config.py`
- [ ] Add `core/pose_estimator.py` and `core/angle_calculator.py`
- [ ] Refactor `collect_data.py`, `analyze_features.py`, `live_inference.py` into importable functions with `__main__` guards
- [ ] Build unified input routing (webcam vs. file) with quote-stripping for dragged file paths
- [ ] Build unified input routing (webcam with live `0`/`1` hotkey labeling vs. pre-recorded video files with upfront automated batch labeling)
- [ ] Build dynamic session path generator (`data/raw/session_Subject_Timestamp.csv`) and an atomic in-memory row buffer
- [ ] Implement upfront pre-label prompts for video ingestion to fully automate batch extraction
- [ ] Inject embedded metadata tracking columns (`timestamp`, `subject_id`, `input_source`) into the CSV header schema
- [ ] Implement CSV auto-header detection and `points_norm` normalization
- [ ] Build `main.py` master menu with screen-clear, routing, and try/except recovery
- [ ] Write `setup.bat` and `run.bat`
- [ ] Pin dependency versions in `requirements.txt`
- [ ] Run fresh-environment and full menu-loop validation

"""
Sustained Harmonic Walking (SHW) detection from tri-axial accelerometry.

Implements a simplified version of the method from Urbanek et al. 2015
("Prediction of sustained harmonic walking in the free-living environment
using raw accelerometry data").  Operates on the vector-magnitude signal
sqrt(x^2 + y^2 + z^2) — orientation-independent, so the same algorithm
works regardless of how the sensor is worn.

Pipeline (per file):
  1. Compute vector magnitude (VM) and infer sample rate from timestamps.
  2. Slide a short window (3s) across VM with a 1s hop.
  3. For each window: detrend, FFT, restrict to the walking band
     (0.5–3 Hz, i.e. 30–180 steps/min), measure the spectral power
     concentration at the dominant peak ("harmonicity").
  4. Classify each window with a hysteresis pair of thresholds:
       STRONG (clean periodic motion — definite walking core)
       WEAK   (still mostly periodic — rampup/rampdown, brief cadence drift)
       NONE   (not walking)
  5. A segment is a maximal contiguous run of WEAK-or-STRONG windows
     that contains at least one STRONG window.  This lets the boundaries
     reach into the unstable edges of a bout instead of clipping them
     off, which avoids "shading only the middle of a long walking block".
  6. Bridge segments separated by a small gap (≤ MAX_GAP_SECONDS) —
     merges micro-dropouts within one walking episode.
  7. Drop merged segments shorter than MIN_SUSTAINED_SECONDS.
"""

import numpy as np
import pandas as pd


# --- Tuning constants -----------------------------------------------------
WINDOW_SECONDS = 3.0
HOP_SECONDS = 1.0
# Plausible walking step-frequency band.  Slowest practical walk ≈30 steps/min
# (0.5 Hz); fastest ≈180 steps/min (3 Hz) before transitioning to running.
WALKING_MIN_HZ = 0.5
WALKING_MAX_HZ = 3.0
# Hysteresis thresholds on harmonicity = peak_power / band_power.
# STRONG must be cleared for a window to *start* a walking core.
# WEAK is used only to *extend* an existing core through unstable edges
# (rampup/rampdown) and brief cadence drift.
HARMONICITY_STRONG = 0.5
HARMONICITY_WEAK = 0.4
# A single STRONG window can be a fluke (clean-looking 3s of fidgeting,
# sleep movement, etc.) so require this many consecutive STRONG windows
# before a run is anchored.  Prevents extension into long noise sequences.
MIN_STRONG_RUN = 2
# Bridge segments separated by ≤ this many seconds.  Merges micro-dropouts
# inside a single walking episode (e.g. one bad window mid-bout).
MAX_GAP_SECONDS = 3.0
# Minimum duration of a (post-merge) run to qualify as SHW.
MIN_SUSTAINED_SECONDS = 10.0


def _infer_fs(timestamps):
    """Estimate sample rate (Hz) from a datetime64 timestamp array."""
    if len(timestamps) < 2:
        return None
    diffs_ns = np.diff(timestamps).astype("timedelta64[ns]").astype(np.int64)
    diffs_ns = diffs_ns[diffs_ns > 0]
    if len(diffs_ns) == 0:
        return None
    dt_s = float(np.median(diffs_ns)) / 1e9
    if dt_s <= 0:
        return None
    return 1.0 / dt_s


def detect_walking_segments(pdf):
    """Detect sustained harmonic walking segments in an accelerometry frame.

    Parameters
    ----------
    pdf : DataFrame
        Must contain ``timestamp`` (datetime64), ``x``, ``y``, ``z`` columns.

    Returns
    -------
    list of dict
        Each entry has keys ``start_time`` (Timestamp), ``end_time``
        (Timestamp), ``duration_s`` (float), ``mean_step_freq_hz`` (float).
        Empty list if no qualifying segments are found.
    """
    if pdf is None or len(pdf) < 2:
        return []

    ts = pdf["timestamp"].values
    vm = np.sqrt(
        pdf["x"].values ** 2 + pdf["y"].values ** 2 + pdf["z"].values ** 2
    )

    fs = _infer_fs(ts)
    if fs is None:
        return []

    win = int(round(WINDOW_SECONDS * fs))
    hop = max(1, int(round(HOP_SECONDS * fs)))
    if win < 4 or len(vm) < win:
        return []

    taper = np.hanning(win)
    freqs = np.fft.rfftfreq(win, d=1.0 / fs)
    band_mask = (freqs >= WALKING_MIN_HZ) & (freqs <= WALKING_MAX_HZ)
    band_freqs = freqs[band_mask]

    # Per-window record: start/end sample indices, harmonicity, peak freq.
    # Keep raw sample indices (not center times) so segments can later be
    # reported with full window extents, not just window centers.
    windows = []
    for start in range(0, len(vm) - win + 1, hop):
        seg = vm[start : start + win]
        seg = (seg - seg.mean()) * taper
        spec = np.abs(np.fft.rfft(seg)) ** 2
        band_spec = spec[band_mask]
        total = band_spec.sum()
        if total <= 0:
            harmonicity = 0.0
            peak_freq = 0.0
        else:
            peak_idx = int(np.argmax(band_spec))
            harmonicity = float(band_spec[peak_idx] / total)
            peak_freq = float(band_freqs[peak_idx])
        windows.append(
            {
                "start_idx": start,
                "end_idx": start + win,
                "harmonicity": harmonicity,
                "peak_freq": peak_freq,
            }
        )

    if not windows:
        return []

    runs = _hysteresis_runs(windows)
    segments = _runs_to_segments(runs, windows, ts)
    segments = _bridge_small_gaps(segments)
    segments = [s for s in segments if s["duration_s"] >= MIN_SUSTAINED_SECONDS]
    return segments


def _hysteresis_runs(windows):
    """Find maximal contiguous runs of WEAK-or-STRONG windows that contain
    at least ``MIN_STRONG_RUN`` consecutive STRONG windows.

    The STRONG threshold gates *whether* a run qualifies; the WEAK threshold
    sets *how far* the run extends.  Unstable rampup/rampdown windows that
    sit between STRONG cleanly periodic activity and non-walking get pulled
    into the segment instead of being clipped off.

    Requiring a *consecutive* STRONG cluster (not just a single STRONG
    window anywhere in the run) prevents an isolated clean window in noisy
    data from dragging a long sequence of mildly-periodic neighbours into
    a spurious segment.

    Returns
    -------
    list of (int, int)
        Inclusive (first_window_idx, last_window_idx) pairs.
    """
    runs = []
    in_run = False
    strong_streak = 0
    has_anchor = False
    start_idx = 0
    for i, w in enumerate(windows):
        if w["harmonicity"] >= HARMONICITY_WEAK:
            if not in_run:
                in_run = True
                start_idx = i
                strong_streak = 0
                has_anchor = False
            if w["harmonicity"] >= HARMONICITY_STRONG:
                strong_streak += 1
                if strong_streak >= MIN_STRONG_RUN:
                    has_anchor = True
            else:
                strong_streak = 0
        else:
            if in_run and has_anchor:
                runs.append((start_idx, i - 1))
            in_run = False
            strong_streak = 0
            has_anchor = False
    if in_run and has_anchor:
        runs.append((start_idx, len(windows) - 1))
    return runs


def _runs_to_segments(runs, windows, ts):
    """Convert (window_idx_start, window_idx_end) runs into time-bounded
    segments using full window extents (not centers)."""
    segments = []
    for first_i, last_i in runs:
        sample_start = windows[first_i]["start_idx"]
        sample_end = windows[last_i]["end_idx"] - 1
        sample_end = min(sample_end, len(ts) - 1)
        start_t = pd.Timestamp(ts[sample_start])
        end_t = pd.Timestamp(ts[sample_end])
        duration_s = (end_t - start_t).total_seconds()
        strong_freqs = [
            windows[i]["peak_freq"]
            for i in range(first_i, last_i + 1)
            if windows[i]["harmonicity"] >= HARMONICITY_STRONG
            and windows[i]["peak_freq"] > 0
        ]
        mean_freq = float(np.mean(strong_freqs)) if strong_freqs else 0.0
        segments.append(
            {
                "start_time": start_t,
                "end_time": end_t,
                "duration_s": duration_s,
                "mean_step_freq_hz": mean_freq,
                # Carry STRONG freqs forward so bridge-merge can recompute
                # the mean across merged runs without re-scanning windows.
                "_strong_freqs": strong_freqs,
            }
        )
    return segments


def _bridge_small_gaps(segments):
    """Merge segments separated by a gap ≤ MAX_GAP_SECONDS."""
    if not segments:
        return []
    merged = [segments[0]]
    for seg in segments[1:]:
        prev = merged[-1]
        gap = (seg["start_time"] - prev["end_time"]).total_seconds()
        if gap <= MAX_GAP_SECONDS:
            merged_freqs = prev["_strong_freqs"] + seg["_strong_freqs"]
            prev["end_time"] = seg["end_time"]
            prev["duration_s"] = (
                prev["end_time"] - prev["start_time"]
            ).total_seconds()
            prev["mean_step_freq_hz"] = (
                float(np.mean(merged_freqs)) if merged_freqs else 0.0
            )
            prev["_strong_freqs"] = merged_freqs
        else:
            merged.append(seg)
    # Drop the carryover field — internal to the merge step
    for seg in merged:
        seg.pop("_strong_freqs", None)
    return merged

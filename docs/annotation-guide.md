# Annotation Guide

## Overview

Annotations in this tool represent **time boundaries of physical performance test activities** within continuous wrist-worn accelerometry recordings. Each annotation marks when a specific activity (e.g., a Chair Stand Test) began and ended, along with metadata about individual repetitions, scoring selections, and review status.

The goal is to produce a structured dataset that links raw accelerometry signals to clinically meaningful physical performance events for frailty assessment research.

## Activity types and colors

Each activity type is displayed as a colored overlay on the signal plot:

| Activity | Overlay color | Description |
|----------|--------------|-------------|
| **Chair Stand** | Cyan | Repeated sit-to-stand cycles measuring lower-extremity strength |
| **TUG** | Yellow | Timed Up and Go — stand, walk 3 m, turn, walk back, sit |
| **3-Meter Walk** | Magenta | Short-distance gait speed measurement |
| **6-Minute Walk** | Green | Submaximal endurance test — walk as far as possible in 6 minutes |

See [Physical Performance Tests](tests-overview.md) for detailed descriptions of each test, including what the accelerometry signals look like and how to identify them.

## The three flags

After marking an activity episode, annotators use three flags to add structured metadata. Each flag serves a distinct purpose in the annotation workflow.

### Segment

**Visual pattern:** diagonal stripes

The segment flag marks **individual repetitions within an activity episode**. Many physical performance tests consist of multiple discrete movements within a single episode. For example, a Chair Stand Test episode contains five sit-to-stand cycles — each cycle is one segment.

- **Chair Stand**: mark each sit-to-stand-to-sit cycle as a separate segment (typically 5 segments per episode)
- **TUG**: usually a single segment covering the entire movement sequence
- **3-Meter Walk**: one segment per trial (some protocols include multiple trials)
- **6-Minute Walk**: typically one segment for the full walk

### Scoring

**Visual pattern:** dot pattern

The scoring flag marks **which segment the annotator selected for frailty assessment scoring**. After segmenting an episode into individual repetitions, the annotator uses their judgement to pick the one segment that best represents the activity. Only one segment per episode should carry the scoring flag.

Choose the segment where:
- The participant's movement was smooth and clearly executed
- The accelerometry signal is unambiguous
- The participant did not pause, use hands for support, or deviate from the test protocol

### Review

**Visual pattern:** checkerboard

The review flag marks **difficult-to-interpret signals for review by other annotators**. When the accelerometry data is noisy, ambiguous, or the annotator is uncertain about segment boundaries, they should apply the review flag and add a note explaining the concern.

Common reasons to flag for review:
- Overlapping activities that are hard to separate
- Sensor artifacts or signal dropout
- Uncertainty about whether a movement is a test activity or normal daily activity
- Ambiguous segment boundaries (e.g., the participant paused mid-repetition)

Flags are **toggles** — clicking the same flag button again removes it. Multiple flags can coexist on the same annotation (e.g., a segment can be both the scoring selection and flagged for review).

## Complete workflow example: Chair Stand Test

This walkthrough covers the full annotation process for a typical Chair Stand Test episode.

### 1. Mark the full episode

Navigate to the portion of the file where the chair stands occur. Box-select the entire time range covering all five repetitions and click **Chairstand**. A cyan overlay appears on the plot.

### 2. Segment each repetition

Reduce the window size to zoom in so that individual sit-to-stand cycles are clearly visible. For each cycle:
- Box-select the time range of that single repetition
- Click **Segment**

You should end up with five segment boxes (diagonal stripe pattern) inside the cyan activity overlay.

### 3. Select one segment for scoring

Identify the cleanest, most representative repetition — for example, the third stand where the participant's movement was smooth and the signal is unambiguous. Select that segment and click **Scoring**. A dot pattern appears on the chosen segment.

### 4. Flag anything unclear

If one of the repetitions has a noisy signal or the participant appears to have paused mid-stand:
- Select that segment
- Click **Review** (checkerboard pattern appears)
- Add a note in the sidebar (e.g., "possible pause at top of stand — unclear if completed")

### 5. Add notes

Use the **Notes** field in the sidebar to attach free-text context to any annotation. Click **Save notes** to persist.

### 6. Export

Click **Export** in the toolbar to save all annotations to disk. The app writes an Excel file for the current user.

## Annotation export format

Annotations are saved as Excel files in `data/output/`, one file per user, with the naming pattern:

```
data/output/annotations_{username}.xlsx
```

Each row in the file represents one annotation. The columns are:

| Column | Type | Description |
|--------|------|-------------|
| `fname` | string | Source HDF5 filename |
| `artifact` | string | Activity type (e.g., "chairstand", "tug", "3mw", "6mw") |
| `segment` | bool | Whether this annotation is a segment marker |
| `scoring` | bool | Whether this segment was selected for scoring |
| `review` | bool | Whether this annotation is flagged for review |
| `start_epoch` | float | Start time as Unix epoch (seconds) |
| `end_epoch` | float | End time as Unix epoch (seconds) |
| `start_time` | string | Start time as formatted string |
| `end_time` | string | End time as formatted string |
| `annotated_at` | string | Timestamp when the annotation was created |
| `user` | string | Username of the annotator |
| `notes` | string | Free-text notes attached by the annotator |

## Tips for efficient annotation

- **Start with a large window** (e.g., 3600 seconds) to scan for activity episodes, then zoom in to annotate.
- **Use the range selector minimap** to quickly navigate to different parts of the file.
- **Annotate all episodes of one activity type** before moving to the next — this helps maintain consistency.
- **Export frequently** so your work is saved. The app does not auto-save annotations; you must click Export.
- **Use notes liberally** — they help other annotators (and your future self) understand ambiguous decisions.
- **Flag rather than guess** — when in doubt, apply the review flag and move on. It is faster and more reliable than spending time on an uncertain annotation.

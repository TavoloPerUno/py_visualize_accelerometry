---
title: "Accelerometry Annotation Tool: A Web-Based Platform for Collaborative Labeling of Wearable Sensor Data from Physical Performance Assessments"
tags:
  - Python
  - accelerometry
  - wearable sensors
  - annotation
  - physical performance
  - gait analysis
  - aging research
authors:
  - name: Manu Murugesan
    orcid: 0000-0000-0000-0000
    affiliation: 1
affiliations:
  - name: National Social Life, Health, and Aging Project (NSHAP), University of Chicago, USA
    index: 1
date: 12 March 2026
bibliography: paper.bib
---

# Summary

The Accelerometry Annotation Tool is an open-source web application for visualizing and annotating tri-axial accelerometry data collected during standardized physical performance assessments. Built with Panel [@panel2023] and Bokeh [@bokeh2023], it enables research teams to collaboratively label time boundaries of clinical tests---including the Chair Stand Test, Timed Up and Go (TUG), 3-Meter Walk Test, and 6-Minute Walk Test---in large wearable sensor recordings. The tool renders datasets exceeding 500,000 data points interactively using the Largest Triangle Three Buckets (LTTB) downsampling algorithm [@steinar2013], supports multi-user annotation workflows with role-based access control, and persists labels in Excel format for downstream statistical analysis. A live demo, full documentation, and PyPI package (`pip install accelerometry-annotator`) are publicly available.

# Statement of Need

Wrist-worn accelerometers are increasingly used in aging, rehabilitation, and clinical research to objectively quantify physical function [@troiano2014; @mathie2004]. Longitudinal studies such as the National Social Life, Health, and Aging Project (NSHAP) [@waite2014] collect tri-axial accelerometry signals while participants perform standardized physical performance tests that are strong predictors of fall risk, disability, and mortality in older adults. These include: the 30-second Chair Stand Test, which measures lower-extremity strength [@jones1999]; the Timed Up and Go (TUG) test, where completion times exceeding 12 seconds indicate elevated fall risk [@podsiadlo1991; @cdc_steadi]; the 3-Meter Walk Test, a gait speed assessment recognized as "the sixth vital sign" [@fritz2009; @studenski2011]; and the 6-Minute Walk Test, a submaximal endurance measure used in cardiac and pulmonary research [@enright2003].

Extracting meaningful features from these signals requires accurate temporal annotation of test boundaries within continuous recordings. In practice, this annotation task is performed by multiple trained research staff who must visually inspect high-frequency time series (typically 50--100 Hz), identify activity transitions, and mark precise start and end times. Existing workflows rely on general-purpose tools (spreadsheets, MATLAB scripts, or custom desktop applications) that lack support for collaborative annotation, real-time visualization of large datasets, or deployment on shared computing infrastructure.

The Accelerometry Annotation Tool addresses these gaps by providing a purpose-built, browser-based platform that combines efficient large-dataset visualization, structured annotation with clinical test-specific labels, and multi-user collaboration with role-based access control---all deployable on local workstations, shared HPC clusters, or cloud platforms.

# State of the Field

Several tools exist for time-series annotation in adjacent domains. Label Studio and Prodigy offer general-purpose annotation frameworks but lack accelerometry-specific features such as tri-axial signal overlay, clinical test vocabularies, and LTTB downsampling for high-frequency sensor data. ELAN and Anvil target video and audio annotation with timeline synchronization but do not handle the data scales typical of wearable sensor studies. ActiLife (ActiGraph) provides proprietary accelerometry analysis but is closed-source, single-user, and tightly coupled to specific hardware. To our knowledge, no existing open-source tool combines interactive visualization of large accelerometry datasets, structured annotation for physical performance tests, and collaborative multi-user workflows in a web-based interface.

# Software Design

The application follows a per-session architecture where each authenticated user receives an independent `AppState` instance managing their current file, time window, signal data, and annotations. This design avoids shared mutable state between concurrent sessions while allowing administrators to manage users and audit annotations in real time.

**Visualization.** Raw accelerometry files typically contain 500,000+ samples per axis. Rendering all points in the browser causes severe performance degradation. The tool applies the Largest Triangle Three Buckets (LTTB) algorithm [@steinar2013] to reduce each axis to approximately 10,000 visually representative points for the main plot and 2,000 for the minimap range selector. An optional C extension (`lttbc`) accelerates downsampling, with a graceful fallback to strided sampling when unavailable. The y-axis range is computed explicitly from signal data rather than using Bokeh's `DataRange1d`, preventing annotation overlay quads from distorting the signal display.

**Annotation workflow.** Users select a time range via Bokeh's box-select tool (implemented through invisible scatter points overlaid on signal lines) and assign a clinical test label with a single click. Each annotation records the activity type, start/end timestamps, segment/scoring/review flags, free-text notes, and a user audit trail. Annotations are rendered as color-coded quad overlays with distinct hatch patterns for flagged states, and persisted to per-user Excel files for integration with existing statistical workflows.

**Multi-user collaboration.** The tool supports role-based access with annotator and administrator roles. Files are distributed to annotators deterministically using a seeded random shuffle, ensuring reproducible assignment across server restarts. Administrators can impersonate users to review annotations and manage accounts through a built-in admin panel.

**Deployment.** The application supports three deployment modes: local development via `panel serve`, shared HPC deployment through a self-service Slurm script that automates job submission and SSH tunneling, and cloud deployment on platforms such as Hugging Face Spaces via Docker.

# Research Impact

The Accelerometry Annotation Tool was developed for and is actively used by the NSHAP research team at the University of Chicago to annotate wrist-worn accelerometry data collected during in-home physical performance assessments of older adults. The tool supports the ongoing analysis of accelerometry signals from NSHAP's nationally representative longitudinal cohort, enabling feature extraction for studies of physical function, fall risk, and aging trajectories. By providing a collaborative, web-based annotation platform, the tool has reduced the time required for multi-annotator labeling workflows and enabled systematic inter-annotator reliability assessment.

# AI Usage Disclosure

Generative AI tools (Claude, Anthropic) were used during development to assist with code generation, documentation writing, and manuscript drafting. All AI-generated content was reviewed, tested, and validated by the authors.

# Acknowledgements

This work is supported by the National Social Life, Health, and Aging Project (NSHAP), funded by the National Institute on Aging (NIA).

# References

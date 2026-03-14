Accelerometry Annotation Tool
=============================

A web-based application for annotating accelerometry data from
physical performance tests, built with `Panel <https://panel.holoviz.org/>`_ and
`Bokeh <https://bokeh.org/>`_. Developed by the
`NSHAP Lab <https://www.norc.org/research/projects/national-social-life-health-and-aging-project.html>`_
at the University of Chicago.

Key features
------------

- **LTTB downsampling** — renders 500K+ data points per axis as ~10,000 visually
  representative points using the Largest Triangle Three Buckets algorithm
- **Box-select annotation** — click and drag on the signal plot to annotate
  activity episodes (Chair Stand, TUG, 3-Meter Walk, 6-Minute Walk)
- **Segment / Scoring / Review flags** — mark individual repetitions, select the
  best segment for frailty assessment scoring, and flag ambiguous signals for
  peer review
- **Multi-user collaboration** — deterministic file assignment, per-user
  annotation files, admin impersonation, and role management
- **Auto-save to Excel** — one-click export to per-user Excel files in
  ``data/output/``
- **HPC deployment** — self-service connect script for Slurm clusters with
  automatic SSH tunneling

Quick start
-----------

.. code-block:: bash

   panel serve visualize_accelerometry/app.py \
       --port 5601 \
       --basic-auth credentials.json \
       --cookie-secret $(python -c "import secrets; print(secrets.token_hex(32))") \
       --allow-websocket-origin localhost:5601 \
       --basic-login-template visualize_accelerometry/templates/login.html

Then open http://localhost:5601/app in your browser.

Links
-----

- `Live demo <https://tavoloperuno-accelerometry-viewer-demo.hf.space/>`_
- `PyPI package <https://pypi.org/project/accelerometry-annotator/>`_

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting-started
   usage

.. toctree::
   :maxdepth: 2
   :caption: Annotation Guide

   annotation-guide
   tests-overview

.. toctree::
   :maxdepth: 2
   :caption: Deployment

   slurm-deployment
   shared-server-startup
   legacy-pbs-startup

.. toctree::
   :maxdepth: 2
   :caption: Development

   architecture
   data-format
   api

"""Reserved for future raw .fit file parsing.

Current sync pipeline uses the Strava /streams endpoint (cleaner timeseries
keyed by type), which is sufficient for our deep analysis goals.

A future path to add raw-device fidelity:
- Download the original upload via Strava's export_original endpoint.
- Parse with `fitparse` and write to a separate `ride_samples_raw` table.
- Keep the streams-based pipeline as the canonical source and use raw as a
  fallback or supplement.
"""

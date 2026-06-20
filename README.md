# fit

A simple, local-first tool for cyclists who want to actually own their ride data.

Pulls activities from Strava, stores summary + per-second telemetry (HR, power, cadence, GPS, elevation, grade, temp) in a local SQLite database. Designed for personal analysis. No competition framing.

## Why

Strava is great at storing rides. It is not great at letting you do real analysis on your own data. This project gives you:

- A clean SQLite schema you can query with any tool.
- Full sample-level data, not just summaries.
- A foundation to layer in Whoop, Apple Health, and other sources later.
- Everything stays on your machine. Your ride data never leaves.

## What it does

1. One-time OAuth authorization with Strava (`activity:read_all` scope).
2. Pulls new activities incrementally (or full backfill) via the Strava API.
3. For each activity, fetches the detail endpoint + the streams endpoint and writes into SQLite.
4. Dedupes by Strava activity id, so repeated syncs are safe.
5. Refreshes access tokens automatically when they expire.

## Status

Working: OAuth, incremental + bounded sync, schema, ingestion of summary/streams/laps.

Planned: full historical backfill with rate-limit-aware pacing, analysis CLI (EF, HR drift, time in zones), Whoop + Apple Health ingestion, FTP/HR-zone configuration.

## Setup

```bash
git clone https://github.com/dcmountainbiker/fit.git
cd fit
pip install -r requirements.txt
```

Create a Strava API application at https://www.strava.com/settings/api:
- Authorization Callback Domain: `localhost`
- Website: this repo URL is fine.

Put the credentials in `~/.config/fit/strava.env`:

```
STRAVA_CLIENT_ID=...
STRAVA_CLIENT_SECRET=...
```

Run the one-time OAuth flow (opens a localhost listener, prints an authorize URL):

```bash
python3 src/strava_oauth.py
```

Then sync:

```bash
python3 -m src.sync --limit 10   # last 10 activities
python3 -m src.sync                # incremental since last sync
python3 -m src.sync --full         # full historical backfill
```

The SQLite database lives at `data/fit.db`. Query it with any tool.

## Schema

See [`sql/schema.sql`](sql/schema.sql).

- `rides` — one row per activity, with summary metrics (date, duration, distance, avg/max HR, avg/max/normalized power, elevation gain, cadence, temperature, etc.).
- `ride_samples` — per-second telemetry (timestamp, lat, lon, altitude, distance, speed, hr, power, cadence, temperature, grade).
- `ride_laps` — lap splits as Strava represents them.
- `sync_state` — sync bookkeeping.

## License

MIT. See [LICENSE](LICENSE).

## Non-goals

- No leaderboards.
- No social features.
- No competition framing.

This is a personal data tool. Use it however you want.

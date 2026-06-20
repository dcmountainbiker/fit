# fit

A simple, local-first tool for cyclists who want to actually own their ride data.

Pulls activities from Strava, parses the underlying `.fit` files (Wahoo, Garmin, etc.), and stores them in a local SQLite database with full per-second telemetry (HR, power, cadence, GPS, elevation). Designed for deep personal analysis, not social comparison.

## Why

Strava is great at storing rides. It is not great at letting you do real analysis on your own data. This project gives you:

- A clean SQLite schema you can query with any tool.
- Full sample-level data, not just summaries.
- A foundation to layer in Whoop, Apple Health, and other sources later.
- Everything stays on your machine. Your ride data never leaves.

## What it does

1. Authenticates with Strava once via OAuth.
2. Pulls new activities on demand or on a schedule.
3. Downloads the original `.fit` file for each activity.
4. Parses it and inserts summary, samples, and laps into SQLite.
5. Dedupes by file hash so repeated syncs are safe.

## Status

Early. Schema and ingestion first. Analysis tooling later.

## Setup

See [`docs/setup.md`](docs/setup.md) (coming).

You will need:
- Python 3.11+
- A Strava API application (free, takes 2 minutes at https://www.strava.com/settings/api)

## Schema

See [`sql/schema.sql`](sql/schema.sql).

Three core tables:
- `rides` — one row per activity, with summary metrics.
- `ride_samples` — per-second telemetry.
- `ride_laps` — lap splits when the device recorded them.

## License

MIT. See [LICENSE](LICENSE).

## Non-goals

- No leaderboards.
- No social features.
- No "you crushed it" notifications.

This is a personal data tool. Use it however you want.

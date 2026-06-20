-- fit: local SQLite schema for cycling activity data
-- All times stored as ISO 8601 UTC strings unless noted.
-- Distances in meters, durations in seconds, power in watts, HR in bpm,
-- cadence in rpm, altitude in meters, speed in m/s, temperature in C.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- One row per ride/activity.
CREATE TABLE IF NOT EXISTS rides (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    strava_id           INTEGER UNIQUE,             -- Strava activity id, if synced via Strava
    file_hash           TEXT UNIQUE NOT NULL,       -- sha256 of source .fit file, dedupe key
    file_path           TEXT,                       -- relative path to archived .fit, if kept
    source              TEXT NOT NULL,              -- 'strava', 'manual', etc.
    device              TEXT,                       -- e.g. 'Wahoo ELEMNT Bolt'
    sport               TEXT,                       -- 'cycling', 'running', etc.
    name                TEXT,                       -- activity name from Strava or device
    start_time_utc      TEXT NOT NULL,              -- ISO 8601 UTC
    start_time_local    TEXT,                       -- ISO 8601 local (no offset suffix)
    timezone            TEXT,                       -- IANA tz, e.g. 'America/New_York'
    duration_s          REAL NOT NULL,              -- elapsed seconds (wall clock)
    moving_time_s       REAL,                       -- seconds in motion
    distance_m          REAL,
    elevation_gain_m    REAL,
    elevation_loss_m    REAL,
    avg_speed_mps       REAL,
    max_speed_mps       REAL,
    avg_hr              REAL,
    max_hr              REAL,
    avg_power_w         REAL,
    max_power_w         REAL,
    normalized_power_w  REAL,
    intensity_factor    REAL,
    tss                 REAL,
    work_kj             REAL,
    avg_cadence_rpm     REAL,
    max_cadence_rpm     REAL,
    avg_temperature_c   REAL,
    calories            REAL,
    start_lat           REAL,
    start_lon           REAL,
    raw_summary_json    TEXT,                       -- full session summary for fields not modeled
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_rides_start_time_utc ON rides(start_time_utc);
CREATE INDEX IF NOT EXISTS idx_rides_sport          ON rides(sport);

-- Per-record telemetry. Most devices emit roughly 1 Hz.
CREATE TABLE IF NOT EXISTS ride_samples (
    ride_id        INTEGER NOT NULL REFERENCES rides(id) ON DELETE CASCADE,
    t_s            REAL NOT NULL,           -- seconds since ride start
    timestamp_utc  TEXT NOT NULL,           -- absolute timestamp
    lat            REAL,
    lon            REAL,
    altitude_m     REAL,
    distance_m     REAL,                    -- cumulative
    speed_mps      REAL,
    hr             INTEGER,
    power_w        INTEGER,
    cadence_rpm    INTEGER,
    temperature_c  REAL,
    grade_pct      REAL,
    left_right_balance REAL,
    PRIMARY KEY (ride_id, t_s)
);

CREATE INDEX IF NOT EXISTS idx_samples_ride_id   ON ride_samples(ride_id);
CREATE INDEX IF NOT EXISTS idx_samples_timestamp ON ride_samples(timestamp_utc);

-- Lap splits when present in the .fit file.
CREATE TABLE IF NOT EXISTS ride_laps (
    ride_id        INTEGER NOT NULL REFERENCES rides(id) ON DELETE CASCADE,
    lap_index      INTEGER NOT NULL,
    start_time_utc TEXT NOT NULL,
    duration_s     REAL,
    distance_m     REAL,
    avg_hr         REAL,
    max_hr         REAL,
    avg_power_w    REAL,
    max_power_w    REAL,
    normalized_power_w REAL,
    avg_speed_mps  REAL,
    max_speed_mps  REAL,
    avg_cadence_rpm REAL,
    elevation_gain_m REAL,
    PRIMARY KEY (ride_id, lap_index)
);

-- Sync bookkeeping for Strava (and future sources).
CREATE TABLE IF NOT EXISTS sync_state (
    source           TEXT PRIMARY KEY,             -- 'strava'
    last_synced_utc  TEXT,
    last_activity_at TEXT,                         -- watermark for incremental sync
    notes            TEXT
);

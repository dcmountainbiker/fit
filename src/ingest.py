"""Insert a Strava activity (summary + detail + streams) into SQLite."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any


def _hash_activity(summary: dict[str, Any]) -> str:
    """Stable dedupe key for a Strava activity."""
    h = hashlib.sha256()
    h.update(str(summary.get("id")).encode())
    h.update(b"|")
    h.update((summary.get("start_date") or "").encode())
    return h.hexdigest()


def insert_activity(
    conn: sqlite3.Connection,
    summary: dict[str, Any],
    detail: dict[str, Any] | None,
    streams: dict[str, dict] | None,
) -> int | None:
    """Insert ride + samples + laps. Returns rides.id or None if already present."""
    file_hash = _hash_activity(summary)

    existing = conn.execute(
        "SELECT id FROM rides WHERE file_hash = ? OR strava_id = ?",
        (file_hash, summary.get("id")),
    ).fetchone()
    if existing:
        return None

    d = detail or summary
    start_latlng = summary.get("start_latlng") or [None, None]

    cur = conn.execute(
        """
        INSERT INTO rides (
            strava_id, file_hash, source, device, sport, name,
            start_time_utc, start_time_local, timezone,
            duration_s, moving_time_s, distance_m,
            elevation_gain_m, elevation_loss_m,
            avg_speed_mps, max_speed_mps,
            avg_hr, max_hr,
            avg_power_w, max_power_w, normalized_power_w,
            intensity_factor, tss, work_kj,
            avg_cadence_rpm, max_cadence_rpm,
            avg_temperature_c, calories,
            start_lat, start_lon,
            raw_summary_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            summary.get("id"),
            file_hash,
            "strava",
            d.get("device_name") or summary.get("device_name"),
            (summary.get("type") or "").lower(),
            summary.get("name"),
            summary.get("start_date"),
            summary.get("start_date_local"),
            summary.get("timezone"),
            summary.get("elapsed_time"),
            summary.get("moving_time"),
            summary.get("distance"),
            summary.get("total_elevation_gain"),
            d.get("elev_low") and d.get("elev_high") and None,  # not directly given
            summary.get("average_speed"),
            summary.get("max_speed"),
            summary.get("average_heartrate"),
            summary.get("max_heartrate"),
            summary.get("average_watts"),
            summary.get("max_watts"),
            d.get("weighted_average_watts") or summary.get("weighted_average_watts"),
            None,  # IF: needs FTP
            d.get("suffer_score"),  # not TSS but a Strava analog; null is fine
            (summary.get("kilojoules") or d.get("kilojoules")),
            summary.get("average_cadence"),
            d.get("max_cadence"),
            summary.get("average_temp"),
            d.get("calories"),
            start_latlng[0] if start_latlng else None,
            start_latlng[1] if start_latlng else None,
            json.dumps(d, default=str),
        ),
    )
    ride_id = cur.lastrowid

    # Samples from streams.
    if streams:
        time_s = (streams.get("time") or {}).get("data") or []
        latlng = (streams.get("latlng") or {}).get("data") or []
        alt = (streams.get("altitude") or {}).get("data") or []
        dist = (streams.get("distance") or {}).get("data") or []
        spd = (streams.get("velocity_smooth") or {}).get("data") or []
        hr = (streams.get("heartrate") or {}).get("data") or []
        watts = (streams.get("watts") or {}).get("data") or []
        cad = (streams.get("cadence") or {}).get("data") or []
        temp = (streams.get("temp") or {}).get("data") or []
        grade = (streams.get("grade_smooth") or {}).get("data") or []

        from datetime import datetime, timedelta
        start_dt = datetime.fromisoformat((summary.get("start_date") or "").replace("Z", "+00:00")) if summary.get("start_date") else None

        rows = []
        for i, t in enumerate(time_s):
            lat = lon = None
            if i < len(latlng) and latlng[i]:
                lat, lon = latlng[i][0], latlng[i][1]
            ts = (start_dt + timedelta(seconds=t)).isoformat() if start_dt else None
            rows.append((
                ride_id, t, ts,
                lat, lon,
                alt[i] if i < len(alt) else None,
                dist[i] if i < len(dist) else None,
                spd[i] if i < len(spd) else None,
                hr[i] if i < len(hr) else None,
                watts[i] if i < len(watts) else None,
                cad[i] if i < len(cad) else None,
                temp[i] if i < len(temp) else None,
                grade[i] if i < len(grade) else None,
                None,
            ))
        if rows:
            conn.executemany(
                """
                INSERT OR REPLACE INTO ride_samples (
                    ride_id, t_s, timestamp_utc, lat, lon, altitude_m, distance_m,
                    speed_mps, hr, power_w, cadence_rpm, temperature_c, grade_pct,
                    left_right_balance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    # Laps from detail.
    if detail and detail.get("laps"):
        for i, lap in enumerate(detail["laps"]):
            conn.execute(
                """
                INSERT INTO ride_laps (
                    ride_id, lap_index, start_time_utc, duration_s, distance_m,
                    avg_hr, max_hr, avg_power_w, max_power_w, normalized_power_w,
                    avg_speed_mps, max_speed_mps, avg_cadence_rpm, elevation_gain_m
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ride_id, i,
                    lap.get("start_date"),
                    lap.get("elapsed_time"),
                    lap.get("distance"),
                    lap.get("average_heartrate"),
                    lap.get("max_heartrate"),
                    lap.get("average_watts"),
                    lap.get("max_watts"),
                    None,
                    lap.get("average_speed"),
                    lap.get("max_speed"),
                    lap.get("average_cadence"),
                    lap.get("total_elevation_gain"),
                ),
            )

    conn.commit()
    return ride_id

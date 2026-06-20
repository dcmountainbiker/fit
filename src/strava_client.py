"""Strava API client with automatic token refresh and rate-limit awareness."""

from __future__ import annotations

import time
from typing import Any

import requests

from src.config import load_env, save_env

API_BASE = "https://www.strava.com/api/v3"
TOKEN_URL = "https://www.strava.com/oauth/token"


class RateLimitError(Exception):
    """Raised when Strava returns 429."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class StravaClient:
    def __init__(self) -> None:
        self.env = load_env()
        self.session = requests.Session()
        self._maybe_refresh()

    # --- auth ---

    def _maybe_refresh(self) -> None:
        expires_at = int(self.env.get("STRAVA_TOKEN_EXPIRES_AT", "0") or "0")
        # Refresh if missing or expiring within 5 minutes.
        if expires_at and expires_at - int(time.time()) > 300:
            return
        self._refresh()

    def _refresh(self) -> None:
        resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": self.env["STRAVA_CLIENT_ID"],
                "client_secret": self.env["STRAVA_CLIENT_SECRET"],
                "grant_type": "refresh_token",
                "refresh_token": self.env["STRAVA_REFRESH_TOKEN"],
            },
            timeout=15,
        )
        resp.raise_for_status()
        tok = resp.json()
        self.env["STRAVA_ACCESS_TOKEN"] = tok["access_token"]
        self.env["STRAVA_REFRESH_TOKEN"] = tok["refresh_token"]
        self.env["STRAVA_TOKEN_EXPIRES_AT"] = str(tok["expires_at"])
        save_env(self.env)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.env['STRAVA_ACCESS_TOKEN']}"}

    # --- rate limit helpers ---

    @staticmethod
    def _read_rate_limits(resp: requests.Response) -> dict[str, int]:
        limits: dict[str, int] = {}
        # X-RateLimit-Limit: "15-minute,daily" e.g. "200,2000"
        # X-RateLimit-Usage: e.g. "27,401"
        try:
            l = resp.headers.get("X-RateLimit-Limit", "")
            u = resp.headers.get("X-RateLimit-Usage", "")
            if l and u:
                ll = [int(x) for x in l.split(",")]
                uu = [int(x) for x in u.split(",")]
                limits = {
                    "limit_15min": ll[0],
                    "limit_daily": ll[1],
                    "usage_15min": uu[0],
                    "usage_daily": uu[1],
                }
        except Exception:
            pass
        return limits

    # --- requests ---

    def get(self, path: str, **kwargs) -> requests.Response:
        self._maybe_refresh()
        url = path if path.startswith("http") else f"{API_BASE}{path}"
        resp = self.session.get(url, headers=self._headers(), timeout=30, **kwargs)
        if resp.status_code == 401:
            self._refresh()
            resp = self.session.get(url, headers=self._headers(), timeout=30, **kwargs)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "900"))
            raise RateLimitError("Rate limited by Strava", retry_after=retry_after)
        resp.raise_for_status()
        return resp

    # --- domain methods ---

    def athlete(self) -> dict[str, Any]:
        return self.get("/athlete").json()

    def list_activities(
        self,
        before: int | None = None,
        after: int | None = None,
        per_page: int = 30,
        max_pages: int = 50,
    ) -> list[dict[str, Any]]:
        """Page through /athlete/activities."""
        out: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            params = {"per_page": per_page, "page": page}
            if before:
                params["before"] = before
            if after:
                params["after"] = after
            resp = self.get("/athlete/activities", params=params)
            batch = resp.json()
            if not batch:
                break
            out.extend(batch)
            if len(batch) < per_page:
                break
        return out

    def activity_detail(self, activity_id: int) -> dict[str, Any]:
        return self.get(f"/activities/{activity_id}", params={"include_all_efforts": "false"}).json()

    def download_original(self, activity_id: int) -> tuple[bytes, str]:
        """Download the original uploaded file for an activity.

        Returns (bytes, suggested_filename). For Wahoo this is a .fit file.
        Strava's export_original returns a 302 to a signed CloudFront URL.
        """
        # Strava's "export_original" is on the web side, not the API.
        # The API has /activities/{id}/streams which gives parsed timeseries,
        # which is actually cleaner for our purposes than re-parsing .fit.
        # We'll use streams as the primary source.
        raise NotImplementedError("Use streams() instead; see sync logic.")

    def streams(self, activity_id: int, keys: list[str] | None = None) -> dict[str, dict]:
        if keys is None:
            keys = [
                "time", "latlng", "altitude", "distance",
                "velocity_smooth", "heartrate", "watts", "cadence",
                "temp", "moving", "grade_smooth",
            ]
        params = {"keys": ",".join(keys), "key_by_type": "true"}
        return self.get(f"/activities/{activity_id}/streams", params=params).json()

    def last_rate_limits(self) -> dict[str, int]:
        # The last response headers; convenience only.
        return {}  # tracked per-call; caller can inspect resp directly.

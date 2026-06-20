"""Strava OAuth + activity sync.

Stub: real implementation will:
- Run a one-time OAuth flow against http://localhost:<port>/callback.
- Persist tokens to ./secrets/strava_tokens.json (gitignored).
- Refresh tokens automatically.
- List activities since the last watermark and download original .fit files.
"""

from __future__ import annotations

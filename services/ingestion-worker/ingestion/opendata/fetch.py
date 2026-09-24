"""
Download helpers with an on-disk cache, plus provenance logging.

Open-data portals are slow and rate-limited; every file is cached under
DATA_DIR/cache keyed by URL, and re-downloaded only when older than max_age.
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
import time
import urllib.request
import zipfile
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

USER_AGENT = "NeighborIQ/0.3 (+https://github.com/e-choness/neighboriq)"
CACHE_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parents[2] / "data")) / "cache"


def download(url: str, max_age_hours: float = 24 * 7, timeout: int = 300) -> Path:
    """Return a local path for url, downloading it if missing or stale."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(url.split("?")[0]).suffix[:8] or ".bin"
    path = CACHE_DIR / f"{hashlib.sha256(url.encode()).hexdigest()[:24]}{suffix}"
    if path.exists() and (time.time() - path.stat().st_mtime) < max_age_hours * 3600:
        return path
    logger.info("Downloading %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    tmp = path.with_suffix(path.suffix + ".part")
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as out:  # noqa: S310
        while chunk := resp.read(1 << 20):
            out.write(chunk)
    tmp.replace(path)
    return path


def open_text(path: Path, member_suffix: str | None = None, encoding: str = "utf-8-sig") -> io.TextIOBase:
    """Open a (possibly zipped) text file. For zips, pick the first member ending with member_suffix."""
    if zipfile.is_zipfile(path):
        archive = zipfile.ZipFile(path)
        names = [
            n for n in archive.namelist() if not member_suffix or n.lower().endswith(member_suffix.lower())
        ]
        if not names:
            raise FileNotFoundError(f"{path}: no member ending with {member_suffix!r}")
        return io.TextIOWrapper(archive.open(names[0]), encoding=encoding, newline="")
    return open(path, encoding=encoding, newline="")


def log_load(
    session: Session,
    source: str,
    licence: str,
    status: str,
    rows: int | None,
    message: str = "",
    attribution: str = "",
) -> None:
    session.execute(
        text("""
            INSERT INTO od_load_log (source, row_count, licence, attribution, status, message)
            VALUES (:source, :rows, :licence, :attribution, :status, :message)
        """),
        {
            "source": source,
            "rows": rows,
            "licence": licence,
            "attribution": attribution[:512],
            "status": status,
            "message": message[:2000],
        },
    )

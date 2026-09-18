"""SQLite-backed persistent lookup table for mapping ISIN to TickerTape records."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
import sqlite3
from typing import Optional

from folioman_intelligence.clients.tickertape.constants import DEFAULT_CACHE_DIR
from folioman_intelligence.clients.tickertape.lookup.models import ISINMapping

logger = logging.getLogger(__name__)


class ISINLookupTable:
    """Persistent SQLite store mapping mutual fund ISINs to TickerTape records."""

    def __init__(
        self,
        db_path: Optional[Path | str] = None,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
    ) -> None:
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(cache_dir) / "isin_lookup.db"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create and return a configured sqlite3 connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database schema and indexes."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mf_isin_lookup (
                    isin TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    name TEXT NOT NULL,
                    amc TEXT,
                    plan TEXT,
                    option TEXT,
                    url TEXT NOT NULL,
                    nav REAL,
                    updated_at TEXT NOT NULL
                )
                """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lookup_record_id ON mf_isin_lookup(record_id)"
            )
            conn.commit()

    def get(self, isin: str) -> Optional[ISINMapping]:
        """Fetch mapping for a specific ISIN."""
        clean_isin = isin.strip().upper()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM mf_isin_lookup WHERE isin = ?", (clean_isin,)
            )
            row = cursor.fetchone()
            if row:
                return ISINMapping.model_validate(dict(row))
        return None

    def get_batch(self, isins: list[str]) -> dict[str, ISINMapping]:
        """Fetch mappings for multiple ISINs at once."""
        clean_isins = [i.strip().upper() for i in isins if i.strip()]
        if not clean_isins:
            return {}

        placeholders = ",".join("?" for _ in clean_isins)
        result: dict[str, ISINMapping] = {}

        with self._get_connection() as conn:
            cursor = conn.execute(
                f"SELECT * FROM mf_isin_lookup WHERE isin IN ({placeholders})",
                clean_isins,
            )
            for row in cursor.fetchall():
                mapping = ISINMapping.model_validate(dict(row))
                result[mapping.isin] = mapping

        return result

    def get_by_record_id(self, record_id: str) -> Optional[ISINMapping]:
        """Fetch mapping by TickerTape record_id (e.g. 'M_QUNG')."""
        clean_id = record_id.strip()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM mf_isin_lookup WHERE record_id = ?", (clean_id,)
            )
            row = cursor.fetchone()
            if row:
                return ISINMapping.model_validate(dict(row))
        return None

    def get_all_record_ids(self) -> set[str]:
        """Return a set of all indexed TickerTape record_ids."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT record_id FROM mf_isin_lookup")
            return {row[0] for row in cursor.fetchall()}

    def get_all_isins(self) -> set[str]:
        """Return a set of all indexed ISINs."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT isin FROM mf_isin_lookup")
            return {row[0] for row in cursor.fetchall()}

    def upsert(self, mapping: ISINMapping) -> None:
        """Insert or update a single ISIN mapping."""
        self.upsert_batch([mapping])

    def upsert_batch(self, mappings: list[ISINMapping]) -> None:
        """Insert or update multiple ISIN mappings in a single atomic transaction."""
        if not mappings:
            return

        query = """
        INSERT INTO mf_isin_lookup (
            isin, record_id, slug, name, amc, plan, option, url, nav, updated_at
        ) VALUES (
            :isin, :record_id, :slug, :name, :amc, :plan, :option, :url, :nav, :updated_at
        )
        ON CONFLICT(isin) DO UPDATE SET
            record_id = excluded.record_id,
            slug = excluded.slug,
            name = excluded.name,
            amc = excluded.amc,
            plan = excluded.plan,
            option = excluded.option,
            url = excluded.url,
            nav = excluded.nav,
            updated_at = excluded.updated_at
        """
        payloads = [m.model_dump() for m in mappings]
        with self._get_connection() as conn:
            conn.executemany(query, payloads)
            conn.commit()

        logger.debug("Upserted %d mappings into SQLite lookup table", len(mappings))

    def count(self) -> int:
        """Return total number of indexed mappings in lookup table."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM mf_isin_lookup")
            return cursor.fetchone()[0]

    def all(self) -> list[ISINMapping]:
        """Return all mappings in the database."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM mf_isin_lookup ORDER BY name ASC")
            return [ISINMapping.model_validate(dict(row)) for row in cursor.fetchall()]

    def clear(self) -> None:
        """Clear all entries from the lookup table."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM mf_isin_lookup")
            conn.commit()

    def export_json(self, filepath: Path | str) -> Path:
        """Export the full lookup table to a JSON file."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        records = [m.model_dump() for m in self.all()]
        with open(target, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        return target

    def export_csv(self, filepath: Path | str) -> Path:
        """Export the full lookup table to a CSV file."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        records = [m.model_dump() for m in self.all()]
        if not records:
            fieldnames = list(ISINMapping.model_fields.keys())
        else:
            fieldnames = list(records[0].keys())

        with open(target, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        return target

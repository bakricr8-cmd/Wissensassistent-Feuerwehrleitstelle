from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Generator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "wissensassistent.sqlite3"


@contextmanager
def connect(
    database_path: Path = DATABASE_PATH,
) -> Generator[sqlite3.Connection, None, None]:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(database_path: Path = DATABASE_PATH) -> None:
    with connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS document_versions (
                id INTEGER PRIMARY KEY,
                document_id TEXT NOT NULL,
                version TEXT NOT NULL,
                filename TEXT NOT NULL,
                document_type TEXT,
                responsible_unit TEXT,
                status TEXT NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                content_hash TEXT NOT NULL,
                extracted_hash TEXT NOT NULL,
                pages_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (document_id, version)
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY,
                occurred_at TEXT NOT NULL,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                details_json TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE
            );

            CREATE INDEX IF NOT EXISTS idx_document_versions_id
                ON document_versions (document_id, valid_from, valid_to);
            CREATE INDEX IF NOT EXISTS idx_audit_events_time
                ON audit_events (occurred_at);
            """
        )
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(document_versions)"
            ).fetchall()
        }
        if "extracted_hash" not in columns:
            connection.execute(
                "ALTER TABLE document_versions ADD COLUMN extracted_hash TEXT"
            )
            rows = connection.execute(
                "SELECT id, pages_json FROM document_versions"
            ).fetchall()
            migrated_hashes: list[dict[str, str]] = []
            for row in rows:
                extracted_hash = hashlib.sha256(
                    row["pages_json"].encode("utf-8")
                ).hexdigest()
                connection.execute(
                    "UPDATE document_versions SET extracted_hash = ? WHERE id = ?",
                    (extracted_hash, row["id"]),
                )
                migrated_hashes.append(
                    {"version_record_id": str(row["id"]), "extracted_hash": extracted_hash}
                )
            if migrated_hashes:
                _append_audit_event(
                    connection,
                    "extracted_hashes_migrated",
                    "system",
                    {"versions": migrated_hashes},
                )
        if "document_type" not in columns:
            connection.execute(
                "ALTER TABLE document_versions ADD COLUMN document_type TEXT"
            )
        if "responsible_unit" not in columns:
            connection.execute(
                "ALTER TABLE document_versions ADD COLUMN responsible_unit TEXT"
            )


def _verify_audit_rows(rows: list[sqlite3.Row]) -> bool:
    previous_hash = "GENESIS"
    for row in rows:
        if row["previous_hash"] != previous_hash:
            return False
        payload = "\n".join(
            (
                row["occurred_at"],
                row["action"],
                row["actor"],
                row["details_json"],
                previous_hash,
            )
        )
        expected_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if row["event_hash"] != expected_hash:
            return False
        previous_hash = row["event_hash"]
    return True


def _append_audit_event(
    connection: sqlite3.Connection,
    action: str,
    actor: str,
    details: dict[str, Any],
) -> None:
    audit_rows = connection.execute(
        "SELECT * FROM audit_events ORDER BY id"
    ).fetchall()
    if not _verify_audit_rows(audit_rows):
        raise sqlite3.DatabaseError(
            "Das Prüfprotokoll ist beschädigt; neue Änderungen wurden gestoppt."
        )
    previous = connection.execute(
        "SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1"
    ).fetchone()
    previous_hash = previous["event_hash"] if previous else "GENESIS"
    occurred_at = datetime.now(timezone.utc).isoformat()
    details_json = json.dumps(
        details, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    payload = "\n".join(
        (occurred_at, action, actor, details_json, previous_hash)
    )
    event_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    connection.execute(
        """
        INSERT INTO audit_events
            (occurred_at, action, actor, details_json, previous_hash, event_hash)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (occurred_at, action, actor, details_json, previous_hash, event_hash),
    )


def insert_document_version(
    *,
    document_id: str,
    version: str,
    filename: str,
    document_type: str | None,
    responsible_unit: str | None,
    status: str,
    valid_from: str,
    valid_to: str | None,
    content_hash: str,
    extracted_hash: str,
    pages_json: str,
    actor: str,
    database_path: Path = DATABASE_PATH,
) -> bool:
    """Speichert eine Version einmalig; gleiche Importe bleiben unverändert."""
    with connect(database_path) as connection:
        existing = connection.execute(
            """
            SELECT content_hash FROM document_versions
            WHERE document_id = ? AND version = ?
            """,
            (document_id, version),
        ).fetchone()
        if existing:
            if existing["content_hash"] == content_hash:
                return False
            raise ValueError(
                f"Version {version} des Dokuments '{document_id}' existiert "
                "bereits mit anderem Inhalt. Versionen sind unveränderlich."
            )

        created_at = datetime.now(timezone.utc).isoformat()
        connection.execute(
            """
            INSERT INTO document_versions
                (document_id, version, filename, document_type, responsible_unit,
                 status, valid_from, valid_to, content_hash, extracted_hash,
                 pages_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                version,
                filename,
                document_type,
                responsible_unit,
                status,
                valid_from,
                valid_to,
                content_hash,
                extracted_hash,
                pages_json,
                created_at,
            ),
        )
        _append_audit_event(
            connection,
            "document_version_added",
            actor,
            {
                "document_id": document_id,
                "version": version,
                "filename": filename,
                "document_type": document_type,
                "responsible_unit": responsible_unit,
                "status": status,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "content_hash": content_hash,
                "extracted_hash": extracted_hash,
            },
        )
    return True


def list_document_versions(
    database_path: Path = DATABASE_PATH,
) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM document_versions ORDER BY document_id, valid_from, id"
        ).fetchall()
        audit_rows = connection.execute(
            "SELECT * FROM audit_events ORDER BY id"
        ).fetchall()

    if not _verify_audit_rows(audit_rows):
        raise sqlite3.DatabaseError(
            "Das Prüfprotokoll ist beschädigt; Dokumentversionen werden nicht "
            "verwendet."
        )

    audited_versions: dict[tuple[str, str], dict[str, Any]] = {}
    migrated_hashes: dict[str, str] = {}
    for event in audit_rows:
        try:
            details = json.loads(event["details_json"])
        except json.JSONDecodeError as error:
            raise sqlite3.DatabaseError(
                "Ein Prüfprotokoll-Eintrag enthält ungültige Details."
            ) from error
        if event["action"] == "document_version_added":
            key = (details.get("document_id"), details.get("version"))
            audited_versions[key] = details
        elif event["action"] == "extracted_hashes_migrated":
            for item in details.get("versions", []):
                migrated_hashes[item["version_record_id"]] = item["extracted_hash"]

    stored_keys: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["document_id"], row["version"])
        stored_keys.add(key)
        details = audited_versions.get(key)
        if details is None:
            raise sqlite3.DatabaseError(
                f"Dokumentversion '{row['document_id']}' Version "
                f"{row['version']}' ist nicht im Prüfprotokoll verankert."
            )
        for field in (
            "filename",
            "document_type",
            "responsible_unit",
            "status",
            "valid_from",
            "valid_to",
            "content_hash",
        ):
            if details.get(field) != row[field]:
                raise sqlite3.DatabaseError(
                    f"Metadaten von '{row['document_id']}' Version "
                    f"{row['version']}' stimmen nicht mit dem Prüfprotokoll überein."
                )
        expected_extracted_hash = details.get("extracted_hash") or migrated_hashes.get(
            str(row["id"])
        )
        if (
            expected_extracted_hash is not None
            and expected_extracted_hash != row["extracted_hash"]
        ):
            raise sqlite3.DatabaseError(
                f"Textintegrität von '{row['document_id']}' Version "
                f"{row['version']}' stimmt nicht mit dem Prüfprotokoll überein."
            )

    if set(audited_versions) != stored_keys:
        raise sqlite3.DatabaseError(
            "Das Prüfprotokoll verweist auf fehlende Dokumentversionen."
        )
    return [dict(row) for row in rows]


def log_query(
    *,
    question: str,
    answer: str | None,
    mode: str,
    model: str | None,
    citations: list[dict[str, Any]],
    valid_on: date,
    actor: str = "prototype-user",
    error: str | None = None,
    database_path: Path = DATABASE_PATH,
) -> None:
    details: dict[str, Any] = {
        "question": question,
        "answer": answer,
        "mode": mode,
        "model": model,
        "valid_on": valid_on.isoformat(),
        "citations": citations,
    }
    if error:
        details["error"] = error
    with connect(database_path) as connection:
        _append_audit_event(
            connection,
            "query_failed" if error else "query_answered",
            actor,
            details,
        )


def list_audit_events(
    limit: int = 100,
    database_path: Path = DATABASE_PATH,
) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM audit_events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def verify_audit_chain(database_path: Path = DATABASE_PATH) -> bool:
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM audit_events ORDER BY id"
        ).fetchall()
    return _verify_audit_rows(rows)

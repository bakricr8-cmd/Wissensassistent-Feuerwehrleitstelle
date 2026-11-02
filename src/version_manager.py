from __future__ import annotations

import hashlib
import hmac
import json
from datetime import date
from pathlib import Path
from typing import Any

from src.database import (
    DATABASE_PATH,
    insert_document_version,
    list_document_versions,
)
from src.document_loader import PageContent


ALLOWED_STATUSES = {"freigegeben", "entwurf"}


class VersionConflictError(ValueError):
    """Mehrere freigegebene Versionen sind gleichzeitig gültig."""


class DocumentIntegrityError(ValueError):
    """Der gespeicherte Dokumenttext stimmt nicht mehr mit seinem Hash überein."""


def _parse_metadata(
    metadata: dict[str, Any],
) -> tuple[str, str, date, date | None]:
    for field in ("dokument_id", "version", "status", "gueltig_ab"):
        value = metadata.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Pflichtfeld '{field}' fehlt oder ist ungültig.")

    document_id = metadata["dokument_id"].strip()
    version = metadata["version"].strip()
    status = metadata["status"].strip().lower()
    if status not in ALLOWED_STATUSES:
        raise ValueError("Status muss 'freigegeben' oder 'entwurf' sein.")
    if "gueltig_bis" not in metadata:
        raise ValueError(
            "Pflichtfeld 'gueltig_bis' fehlt; null bedeutet unbegrenzt."
        )
    valid_to_text = metadata["gueltig_bis"]
    if valid_to_text is not None and not isinstance(valid_to_text, str):
        raise ValueError("'gueltig_bis' muss ein ISO-Datum oder null sein.")

    try:
        valid_from = date.fromisoformat(metadata["gueltig_ab"])
        valid_to = (
            date.fromisoformat(valid_to_text)
            if isinstance(valid_to_text, str) and valid_to_text.strip()
            else None
        )
    except ValueError as error:
        raise ValueError(
            "Gültigkeitsdaten müssen ISO-Daten (JJJJ-MM-TT) sein."
        ) from error

    if isinstance(valid_to_text, str) and not valid_to_text.strip():
        raise ValueError("'gueltig_bis' muss ein ISO-Datum oder null sein.")
    if valid_to and valid_to < valid_from:
        raise ValueError("Das Gültigkeitsende liegt vor dem Gültigkeitsbeginn.")
    return document_id, version, valid_from, valid_to


def register_document_version(
    *,
    filename: str,
    raw_content: bytes,
    pages: tuple[PageContent, ...],
    metadata: dict[str, Any],
    actor: str = "prototype-user",
    database_path: Path = DATABASE_PATH,
) -> bool:
    document_id, version, valid_from, valid_to = _parse_metadata(metadata)
    status = metadata["status"].strip().lower()
    document_type = _optional_text(metadata.get("dokumentart"), "Dokumentart")
    responsible_unit = _optional_text(
        metadata.get("zustaendige_stelle"), "Zuständige Stelle"
    )
    filename = Path(filename).name
    content_hash = hashlib.sha256(raw_content).hexdigest()
    existing_versions = list_document_versions(database_path)

    for existing in existing_versions:
        if (
            existing["document_id"] == document_id
            and existing["version"] == version
        ):
            unchanged = (
                existing["content_hash"] == content_hash
                and existing["filename"] == filename
                and existing["document_type"] == document_type
                and existing["responsible_unit"] == responsible_unit
                and existing["status"] == status
                and existing["valid_from"] == valid_from.isoformat()
                and existing["valid_to"]
                == (valid_to.isoformat() if valid_to else None)
            )
            if unchanged:
                return False
            raise ValueError(
                f"Version {version} des Dokuments '{document_id}' ist bereits "
                "mit abweichendem Inhalt oder anderen Metadaten registriert."
            )

    if status == "freigegeben":
        for existing in existing_versions:
            if (
                existing["document_id"] != document_id
                or existing["status"] != "freigegeben"
            ):
                continue
            existing_from = date.fromisoformat(existing["valid_from"])
            existing_to = (
                date.fromisoformat(existing["valid_to"])
                if existing["valid_to"]
                else None
            )
            overlaps = (
                (valid_to is None or existing_from <= valid_to)
                and (existing_to is None or valid_from <= existing_to)
            )
            if overlaps:
                raise VersionConflictError(
                    f"Der Zeitraum überschneidet sich mit Version "
                    f"{existing['version']} von '{document_id}'."
                )

    pages_json = json.dumps(
        [{"page_number": page.page_number, "text": page.text} for page in pages],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    extracted_hash = hashlib.sha256(pages_json.encode("utf-8")).hexdigest()
    return insert_document_version(
        document_id=document_id,
        version=version,
        filename=filename,
        document_type=document_type,
        responsible_unit=responsible_unit,
        status=status,
        valid_from=valid_from.isoformat(),
        valid_to=valid_to.isoformat() if valid_to else None,
        content_hash=content_hash,
        extracted_hash=extracted_hash,
        pages_json=pages_json,
        actor=actor,
        database_path=database_path,
    )


def _optional_text(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"'{label}' muss Text sein.")
    value = value.strip()
    return value or None


def get_active_documents(
    as_of: date,
    database_path: Path = DATABASE_PATH,
) -> list[dict[str, Any]]:
    versions = list_document_versions(database_path)
    active_by_id: dict[str, list[dict[str, Any]]] = {}
    for version in versions:
        if version["status"] != "freigegeben":
            continue
        valid_from = date.fromisoformat(version["valid_from"])
        valid_to = (
            date.fromisoformat(version["valid_to"])
            if version["valid_to"]
            else None
        )
        if valid_from <= as_of and (valid_to is None or as_of <= valid_to):
            stored_hash = version["extracted_hash"]
            actual_hash = hashlib.sha256(
                version["pages_json"].encode("utf-8")
            ).hexdigest()
            hashes_match = bool(stored_hash) and hmac.compare_digest(
                stored_hash, actual_hash
            )
            if not hashes_match:
                raise DocumentIntegrityError(
                    f"Der gespeicherte Text von '{version['document_id']}' "
                    f"Version {version['version']} wurde verändert. "
                    "Diese Quelle wurde nicht verwendet."
                )
            active_by_id.setdefault(version["document_id"], []).append(version)

    conflicts = {
        document_id: entries
        for document_id, entries in active_by_id.items()
        if len(entries) > 1
    }
    if conflicts:
        details = "; ".join(
            f"{document_id}: {', '.join(item['version'] for item in entries)}"
            for document_id, entries in sorted(conflicts.items())
        )
        raise VersionConflictError(
            f"Mehrere freigegebene Versionen sind am {as_of.isoformat()} gültig "
            f"({details}). Suche wurde zum Schutz vor veralteten Angaben gestoppt."
        )
    return [entries[0] for entries in active_by_id.values()]

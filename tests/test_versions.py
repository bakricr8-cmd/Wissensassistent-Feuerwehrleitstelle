from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.database import (
    initialize_database,
    list_document_versions,
    verify_audit_chain,
)
from src.document_loader import PageContent
from src.version_manager import (
    VersionConflictError,
    get_active_documents,
    register_document_version,
)


class VersionManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "test.sqlite3"
        initialize_database(self.database_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def register(
        self,
        version: str,
        text: str,
        valid_from: str,
        valid_to: str | None,
        status: str = "freigegeben",
        document_id: str = "testdokument",
        document_type: str | None = None,
        responsible_unit: str | None = None,
    ) -> bool:
        raw_content = text.encode("utf-8")
        return register_document_version(
            filename=f"{version}.txt",
            raw_content=raw_content,
            pages=(PageContent(page_number=None, text=text),),
            metadata={
                "dokument_id": document_id,
                "version": version,
                "dokumentart": document_type,
                "zustaendige_stelle": responsible_unit,
                "status": status,
                "gueltig_ab": valid_from,
                "gueltig_bis": valid_to,
            },
            database_path=self.database_path,
        )

    def test_only_date_valid_approved_version_is_active(self) -> None:
        self.register("1.0", "alte Fassung", "2026-01-01", "2026-06-30")
        self.register("2.0", "neue Fassung", "2026-07-01", None)
        self.register(
            "3.0", "Entwurf", "2026-01-01", None, status="entwurf"
        )

        active = get_active_documents(date(2026, 8, 1), self.database_path)

        self.assertEqual([document["version"] for document in active], ["2.0"])

    def test_rejects_overlapping_approved_versions(self) -> None:
        self.register("1.0", "erste Version", "2026-01-01", None)
        with self.assertRaises(VersionConflictError):
            self.register("2.0", "zweite Version", "2026-06-01", None)

    def test_version_cannot_be_overwritten(self) -> None:
        self.register("1.0", "Originaltext", "2026-01-01", None)
        with self.assertRaises(ValueError):
            self.register("1.0", "Geänderter Text", "2026-01-01", None)

    def test_document_type_and_responsible_unit_are_kept(self) -> None:
        self.register(
            "1.0",
            "Originaltext",
            "2026-01-01",
            None,
            document_type="Dienstanweisung",
            responsible_unit="Leitstelle",
        )

        stored = list_document_versions(self.database_path)[0]

        self.assertEqual(stored["document_type"], "Dienstanweisung")
        self.assertEqual(stored["responsible_unit"], "Leitstelle")

    def test_withdrawal_is_not_offered_as_a_supported_status(self) -> None:
        with self.assertRaisesRegex(ValueError, "Status muss"):
            self.register(
                "1.0",
                "Originaltext",
                "2026-01-01",
                None,
                status="zurueckgezogen",
            )

    def test_identical_reimport_is_idempotent_and_audited(self) -> None:
        self.assertTrue(
            self.register("1.0", "Originaltext", "2026-01-01", None)
        )
        self.assertFalse(
            self.register("1.0", "Originaltext", "2026-01-01", None)
        )

        self.assertEqual(len(list_document_versions(self.database_path)), 1)
        self.assertTrue(verify_audit_chain(self.database_path))

    def test_detects_tampered_audit_event(self) -> None:
        self.register("1.0", "Originaltext", "2026-01-01", None)
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(
                "UPDATE audit_events SET actor = 'manipuliert' WHERE id = 1"
            )
            connection.commit()
        finally:
            connection.close()

        self.assertFalse(verify_audit_chain(self.database_path))
        with self.assertRaises(sqlite3.DatabaseError):
            self.register(
                "1.0",
                "Neue Version",
                "2027-01-01",
                None,
                document_id="anderes-dokument",
            )


if __name__ == "__main__":
    unittest.main()

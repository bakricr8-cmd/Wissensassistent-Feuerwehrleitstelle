from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.database import initialize_database, list_audit_events, log_query
from src.document_loader import PageContent
from src.document_search import citation_records, search_documents
from src.rag_pipeline import OllamaError, build_prompt, generate_answer
from src.version_manager import DocumentIntegrityError, register_document_version


class RetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "test.sqlite3"
        initialize_database(self.database_path)
        self._register(
            "freigegeben",
            "Die interne Softwareschulung findet dienstags um 10 Uhr statt.",
            "freigegeben",
            "2026-01-01",
            None,
        )
        self._register(
            "abgelaufen",
            "Die Schulung findet freitags statt.",
            "freigegeben",
            "2025-01-01",
            "2025-12-31",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _register(
        self,
        document_id: str,
        text: str,
        status: str,
        valid_from: str,
        valid_to: str | None,
    ) -> None:
        raw_content = text.encode("utf-8")
        register_document_version(
            filename=f"{document_id}.txt",
            raw_content=raw_content,
            pages=(PageContent(page_number=None, text=text),),
            metadata={
                "dokument_id": document_id,
                "version": "1.0",
                "status": status,
                "gueltig_ab": valid_from,
                "gueltig_bis": valid_to,
            },
            database_path=self.database_path,
        )

    def test_retrieval_returns_current_matching_sources_only(self) -> None:
        results = search_documents(
            "Wann findet die Softwareschulung statt?",
            as_of=date(2026, 2, 1),
            database_path=self.database_path,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].document_id, "freigegeben")
        self.assertIn("dienstags", results[0].text)
        self.assertEqual(results[0].version, "1.0")

    def test_unmatched_question_does_not_return_random_context(self) -> None:
        results = search_documents(
            "Drehleiter Waldbrand",
            as_of=date(2026, 2, 1),
            database_path=self.database_path,
        )

        self.assertEqual(results, [])

    def test_tampered_stored_text_is_not_retrieved(self) -> None:
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(
                "UPDATE document_versions SET pages_json = ? "
                "WHERE document_id = 'freigegeben'",
                (
                    json.dumps(
                        [{"page_number": None, "text": "manipulierter Text"}]
                    ),
                ),
            )
            connection.commit()
        finally:
            connection.close()

        with self.assertRaises(DocumentIntegrityError):
            search_documents(
                "Softwareschulung",
                as_of=date(2026, 2, 1),
                database_path=self.database_path,
            )

    def test_tampered_document_metadata_is_not_used(self) -> None:
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(
                "UPDATE document_versions SET valid_from = '2020-01-01' "
                "WHERE document_id = 'freigegeben'"
            )
            connection.commit()
        finally:
            connection.close()

        with self.assertRaises(sqlite3.DatabaseError):
            search_documents(
                "Softwareschulung",
                as_of=date(2026, 2, 1),
                database_path=self.database_path,
            )

    def test_prompt_contains_source_identity_and_untrusted_data_rule(self) -> None:
        results = search_documents(
            "Softwareschulung",
            as_of=date(2026, 2, 1),
            database_path=self.database_path,
        )
        messages = build_prompt("Wann?", results)

        self.assertIn("nicht vertrauenswürdige", messages[0]["content"])
        self.assertIn("freigegeben, Version 1.0", messages[1]["content"])
        self.assertEqual(len(citation_records(results)), 1)
        self.assertIn(
            "Die interne Softwareschulung findet dienstags um 10 Uhr statt.",
            citation_records(results)[0]["text"],
        )

    def test_query_audit_records_date_and_cited_text(self) -> None:
        results = search_documents(
            "Softwareschulung",
            as_of=date(2026, 2, 1),
            database_path=self.database_path,
        )
        log_query(
            question="Softwareschulung",
            answer="Dienstags um 10 Uhr.",
            mode="Fundstellen (ohne KI)",
            model=None,
            citations=citation_records(results),
            valid_on=date(2026, 2, 1),
            database_path=self.database_path,
        )

        event = list_audit_events(1, self.database_path)[0]
        details = json.loads(event["details_json"])

        self.assertEqual(details["valid_on"], "2026-02-01")
        self.assertEqual(details["citations"][0]["version"], "1.0")
        self.assertIn("dienstags", details["citations"][0]["text"])

    def test_ollama_rejects_non_local_endpoint(self) -> None:
        results = search_documents(
            "Softwareschulung",
            as_of=date(2026, 2, 1),
            database_path=self.database_path,
        )

        with self.assertRaises(OllamaError):
            generate_answer(
                "Wann?",
                results,
                endpoint="http://example.com:11434",
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

import streamlit as st

from src.database import (
    DATABASE_PATH,
    initialize_database,
    list_audit_events,
    list_document_versions,
    log_query,
    verify_audit_chain,
)
from src.document_loader import extract_document, load_metadata_file
from src.document_search import RetrievedChunk, citation_records, search_documents
from src.rag_pipeline import OllamaError, generate_answer
from src.version_manager import (
    VersionConflictError,
    get_active_documents,
    register_document_version,
)


PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLE_DOCUMENTS = PROJECT_ROOT / "Dokumente"
SAMPLE_METADATA = SAMPLE_DOCUMENTS / "metadaten.json"
DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
ACTOR = "prototype-user"


def bootstrap_sample_documents() -> int:
    metadata_by_file = load_metadata_file(SAMPLE_METADATA)
    imported = 0
    for filename, metadata in metadata_by_file.items():
        source = SAMPLE_DOCUMENTS / filename
        if not source.is_file():
            raise ValueError(
                f"Zu '{filename}' gibt es keinen Quelldatei-Eintrag in "
                "Dokumente/."
            )
        raw_content = source.read_bytes()
        pages = extract_document(source.name, raw_content, allow_empty=True)
        if register_document_version(
            filename=source.name,
            raw_content=raw_content,
            pages=pages,
            metadata=metadata,
            actor="sample-import",
        ):
            imported += 1
    return imported


def _render_sources(chunks: list[RetrievedChunk]) -> None:
    if not chunks:
        return
    with st.expander("Belegte Fundstellen", expanded=True):
        for index, chunk in enumerate(chunks, start=1):
            st.markdown(
                f"**[{index}] {chunk.citation}**  \n"
                f"Dokumentart: {chunk.document_type or 'nicht festgelegt'} · "
                f"Zuständige Stelle: "
                f"{chunk.responsible_unit or 'nicht festgelegt'}  \n"
                f"Datei: `{chunk.filename}`"
            )
            st.caption(chunk.text)


def _render_chat_message(message: dict[str, Any]) -> None:
    with st.chat_message(message["role"]):
        if message.get("valid_on"):
            st.caption(
                f"Für Dokumente gültig am {message['valid_on'].strftime('%d.%m.%Y')}"
            )
        if message.get("error"):
            st.error(message["content"])
        else:
            st.markdown(message["content"])
        sources = message.get("sources", [])
        if sources:
            _render_sources(sources)


def _answer_question(
    question: str,
    mode: str,
    model: str,
    endpoint: str,
    valid_on: date,
) -> tuple[str, list[RetrievedChunk]]:
    chunks = search_documents(question, as_of=valid_on)
    if not chunks:
        answer = (
            "In den aktuell freigegebenen und gültigen Dokumentversionen "
            "wurden keine passenden Textstellen gefunden."
        )
        log_query(
            question=question,
            answer=answer,
            mode=mode,
            model=model if mode == "Ollama (lokal)" else None,
            citations=[],
            valid_on=valid_on,
        )
        return answer, []

    if mode == "Ollama (lokal)":
        answer = generate_answer(
            question, chunks, model=model, endpoint=endpoint
        )
    else:
        answer = (
            "Ich habe passende Fundstellen gefunden. "
            "Die Fundstellen unten sind keine formulierte Antwort."
        )

    log_query(
        question=question,
        answer=answer,
        mode=mode,
        model=model if mode == "Ollama (lokal)" else None,
        citations=citation_records(chunks),
        valid_on=valid_on,
    )
    return answer, chunks


def _render_upload_form() -> None:
    st.subheader("Neue Dokumentversion aufnehmen")
    st.caption(
        "Eine registrierte Version kann nicht überschrieben werden. "
        "Änderungen müssen als neue Version mit eigenem Gültigkeitszeitraum "
        "eingestellt werden."
    )
    with st.form("document_upload", clear_on_submit=True):
        upload = st.file_uploader(
            "Dokument (PDF, TXT oder Markdown)",
            type=["pdf", "txt", "md"],
        )
        document_id = st.text_input("Dokument-ID")
        version = st.text_input("Version")
        document_type = st.selectbox(
            "Dokumentart",
            [
                "Nicht festgelegt",
                "Dienstanweisung",
                "Einsatzinformation",
                "Checkliste",
                "Bedarfsplan",
                "SOP",
                "Katastrophenschutzkonzept",
                "Sonstige",
            ],
        )
        responsible_unit = st.text_input(
            "Zuständige Stelle (optional)",
            help="Zum Beispiel Organisationseinheit oder Dokumentverantwortliche.",
        )
        status = st.selectbox(
            "Status",
            ["freigegeben", "entwurf"],
        )
        valid_from = st.date_input("Gültig ab", value=date.today())
        unlimited = st.checkbox("Ohne Gültigkeitsende", value=True)
        valid_to = None
        if not unlimited:
            valid_to = st.date_input("Gültig bis", value=date.today())
        submitted = st.form_submit_button("Version registrieren")

    if not submitted:
        return
    if upload is None:
        st.error("Bitte zuerst eine Datei auswählen.")
        return

    metadata = {
        "dokument_id": document_id,
        "version": version,
        "dokumentart": (
            None if document_type == "Nicht festgelegt" else document_type
        ),
        "zustaendige_stelle": responsible_unit,
        "status": status,
        "gueltig_ab": valid_from.isoformat(),
        "gueltig_bis": valid_to.isoformat() if valid_to else None,
    }
    try:
        raw_content = upload.getvalue()
        pages = extract_document(upload.name, raw_content)
        added = register_document_version(
            filename=upload.name,
            raw_content=raw_content,
            pages=pages,
            metadata=metadata,
            actor=ACTOR,
        )
    except (OSError, ValueError, sqlite3.Error) as error:
        st.error(f"Dokumentversion konnte nicht registriert werden: {error}")
        return

    if added:
        st.success(
            f"Version {version} von '{document_id}' wurde unveränderlich "
            "registriert und protokolliert."
        )
    else:
        st.info("Diese identische Dokumentversion ist bereits registriert.")


def _render_versions() -> None:
    versions = list_document_versions()
    st.subheader("Dokumentenstand")
    st.metric("Gespeicherte Dokumentversionen", len(versions))
    try:
        active = get_active_documents(date.today())
        st.metric("Heute gültige, freigegebene Dokumente", len(active))
    except VersionConflictError as error:
        active = []
        st.error(str(error))

    if versions:
        st.dataframe(
            [
                {
                    "Dokument-ID": item["document_id"],
                    "Version": item["version"],
                    "Datei": item["filename"],
                    "Dokumentart": item["document_type"] or "Nicht festgelegt",
                    "Zuständige Stelle": item["responsible_unit"] or "Nicht festgelegt",
                    "Status": item["status"],
                    "Gültig ab": item["valid_from"],
                    "Gültig bis": item["valid_to"] or "unbegrenzt",
                    "SHA-256": item["content_hash"],
                }
                for item in versions
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Es sind noch keine Dokumente registriert.")


def _render_audit_log() -> None:
    st.subheader("Prüfprotokoll")
    valid_chain = verify_audit_chain()
    if valid_chain:
        st.success("Hash-Kette intakt.")
    else:
        st.error(
            "Die Prüfprotokoll-Hash-Kette ist beschädigt. "
            "Vertrauen Sie den Protokolldaten nicht."
        )

    events = list_audit_events()
    st.caption(
        f"{len(events)} zuletzt angezeigte Ereignisse. "
        "Fragen und Antworten werden lokal in der Datenbank gespeichert."
    )
    if events:
        st.dataframe(
            [
                {
                    "Zeitpunkt (UTC)": event["occurred_at"],
                    "Aktion": event["action"],
                    "Akteur": event["actor"],
                    "Details": json.dumps(
                        json.loads(event["details_json"]),
                        ensure_ascii=False,
                    ),
                    "Prüfhash": event["event_hash"],
                }
                for event in events
            ],
            width="stretch",
            hide_index=True,
        )


def main() -> None:
    st.set_page_config(
        page_title="Feuerwehr-Wissensassistent",
        layout="wide",
    )
    st.title("Feuerwehr-Wissensassistent")
    st.caption("Prototyp · lokale Dokumentensuche mit Quellen und Versionierung")
    st.warning(
        "Nur mit fiktiven oder ausdrücklich freigegebenen Testdokumenten "
        "verwenden. Fragen und Antworten werden lokal protokolliert. "
        "Kein Einsatzsystem: KI-Antworten müssen anhand der Originalquelle "
        "geprüft werden."
    )

    try:
        initialize_database()
        imported = bootstrap_sample_documents()
    except (OSError, ValueError, sqlite3.Error) as error:
        st.error(f"Initialisierung fehlgeschlagen: {error}")
        st.stop()
        return

    if imported:
        st.toast(f"{imported} Beispieldokument(e) importiert.")

    with st.sidebar:
        st.header("Antwortmodus")
        mode = st.radio(
            "Modus",
            ["Fundstellen (ohne KI)", "Ollama (lokal)"],
            help=(
                "Ollama sendet ausschließlich die Frage und abgerufene "
                "Textstellen an den lokalen Ollama-Dienst."
            ),
        )
        model = st.text_input("Ollama-Modell", value="qwen3:4b-instruct")
        endpoint = st.text_input(
            "Ollama-Endpunkt", value=DEFAULT_OLLAMA_ENDPOINT
        )
        _render_upload_form()
        st.caption(f"Lokale Datenbank: `{DATABASE_PATH}`")

    question_tab, versions_tab, audit_tab = st.tabs(
        ["Fragen", "Dokumentenstand", "Prüfprotokoll"]
    )
    with question_tab:
        messages = st.session_state.setdefault("messages", [])
        for message in messages:
            _render_chat_message(message)
        question = st.chat_input("Frage zu den freigegebenen Dokumenten …")
        if question:
            user_message = {"role": "user", "content": question}
            messages.append(user_message)
            _render_chat_message(user_message)
            valid_on = date.today()
            try:
                answer, chunks = _answer_question(
                    question,
                    mode,
                    model.strip(),
                    endpoint.strip(),
                    valid_on,
                )
                assistant_message = {
                    "role": "assistant",
                    "content": answer,
                    "sources": chunks,
                    "valid_on": valid_on,
                }
            except (
                OllamaError,
                VersionConflictError,
                OSError,
                sqlite3.Error,
                ValueError,
            ) as error:
                try:
                    log_query(
                        question=question,
                        answer=None,
                        mode=mode,
                        model=model.strip() if mode == "Ollama (lokal)" else None,
                        citations=[],
                        valid_on=valid_on,
                        error=str(error),
                    )
                except sqlite3.Error as audit_error:
                    st.error(
                        f"Zusätzlich konnte der Fehler nicht protokolliert "
                        f"werden: {audit_error}"
                    )
                assistant_message = {
                    "role": "assistant",
                    "content": f"Fehler: {error}",
                    "sources": [],
                    "error": True,
                    "valid_on": valid_on,
                }
            messages.append(assistant_message)
            _render_chat_message(assistant_message)

    with versions_tab:
        _render_versions()
    with audit_tab:
        _render_audit_log()


if __name__ == "__main__":
    main()

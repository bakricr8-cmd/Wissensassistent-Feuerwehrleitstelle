from __future__ import annotations

import json
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class PageContent:
    page_number: int | None
    text: str


def extract_document(
    filename: str,
    content: bytes,
    *,
    allow_empty: bool = False,
) -> tuple[PageContent, ...]:
    """Liest Text aus PDF-, TXT- oder Markdown-Dateien ein."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            raise ValueError(f"Das PDF '{filename}' ist verschlüsselt.")
        pages = tuple(
            PageContent(
                page_number=index,
                text=(page.extract_text() or "").strip(),
            )
            for index, page in enumerate(reader.pages, start=1)
        )
    elif suffix in {".txt", ".md"}:
        try:
            text = content.decode("utf-8-sig").strip()
        except UnicodeDecodeError as error:
            raise ValueError(
                f"'{filename}' ist keine gültige UTF-8-Datei."
            ) from error
        pages = (PageContent(page_number=None, text=text),)
    else:
        raise ValueError("Unterstützte Dateiformate: PDF, TXT und Markdown.")

    if not any(page.text for page in pages) and not (
        allow_empty and suffix in {".txt", ".md"}
    ):
        raise ValueError(
            f"Aus '{filename}' konnte kein Text extrahiert werden. "
            "Gescannte PDFs benötigen vor dem Import eine OCR-Verarbeitung."
        )
    return pages


def load_metadata_file(metadata_path: Path) -> dict[str, dict[str, object]]:
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Metadatendatei '{metadata_path}' kann nicht gelesen werden: {error}"
        ) from error

    if not isinstance(data, dict):
        raise ValueError("metadaten.json muss ein JSON-Objekt enthalten.")
    if any(not isinstance(value, dict) for value in data.values()):
        raise ValueError("Jeder Metadateneintrag muss ein JSON-Objekt sein.")
    return data

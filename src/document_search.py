from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.database import DATABASE_PATH
from src.version_manager import get_active_documents


WORD_PATTERN = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", re.UNICODE)
CHUNK_WORDS = 120
CHUNK_OVERLAP = 20


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: str
    version: str
    filename: str
    document_type: str | None
    responsible_unit: str | None
    page_number: int | None
    chunk_number: int
    content_hash: str
    text: str
    score: float

    @property
    def citation(self) -> str:
        page = f", Seite {self.page_number}" if self.page_number else ""
        return (
            f"{self.document_id}, Version {self.version}{page}, "
            f"Abschnitt {self.chunk_number}"
        )


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in WORD_PATTERN.findall(text)]


def _make_chunks(documents: list[dict[str, Any]]) -> list[RetrievedChunk]:
    chunks: list[RetrievedChunk] = []
    for document in documents:
        pages = json.loads(document["pages_json"])
        chunk_number = 0
        for page in pages:
            words = page["text"].split()
            if not words:
                continue
            stride = CHUNK_WORDS - CHUNK_OVERLAP
            for start in range(0, len(words), stride):
                text = " ".join(words[start:start + CHUNK_WORDS])
                if not text:
                    continue
                chunk_number += 1
                chunks.append(
                    RetrievedChunk(
                        document_id=document["document_id"],
                        version=document["version"],
                        filename=document["filename"],
                        document_type=document["document_type"],
                        responsible_unit=document["responsible_unit"],
                        page_number=page["page_number"],
                        chunk_number=chunk_number,
                        content_hash=document["content_hash"],
                        text=text,
                        score=0.0,
                    )
                )
                if start + CHUNK_WORDS >= len(words):
                    break
    return chunks


def search_documents(
    question: str,
    *,
    as_of: date | None = None,
    top_k: int = 4,
    database_path: Path = DATABASE_PATH,
) -> list[RetrievedChunk]:
    query_terms = _tokens(question)
    if not query_terms or top_k <= 0:
        return []

    documents = get_active_documents(as_of or date.today(), database_path)
    chunks = _make_chunks(documents)
    if not chunks:
        return []

    tokenized = [_tokens(chunk.text) for chunk in chunks]
    document_frequencies: Counter[str] = Counter()
    for tokens in tokenized:
        document_frequencies.update(set(tokens))

    average_length = sum(map(len, tokenized)) / len(tokenized)
    scores: list[tuple[float, RetrievedChunk]] = []
    total_chunks = len(chunks)
    k1 = 1.5
    b = 0.75
    query_counts = Counter(query_terms)

    for chunk, tokens in zip(chunks, tokenized, strict=True):
        frequencies = Counter(tokens)
        length = len(tokens)
        score = 0.0
        for term, query_frequency in query_counts.items():
            term_frequency = frequencies[term]
            if term_frequency == 0:
                continue
            frequency_in_chunks = document_frequencies[term]
            inverse_document_frequency = math.log(
                1
                + (total_chunks - frequency_in_chunks + 0.5)
                / (frequency_in_chunks + 0.5)
            )
            denominator = term_frequency + k1 * (
                1 - b + b * length / average_length
            )
            score += (
                inverse_document_frequency
                * term_frequency
                * (k1 + 1)
                / denominator
                * query_frequency
            )
        if score > 0:
            scores.append(
                (
                    score,
                    RetrievedChunk(
                        document_id=chunk.document_id,
                        version=chunk.version,
                        filename=chunk.filename,
                        document_type=chunk.document_type,
                        responsible_unit=chunk.responsible_unit,
                        page_number=chunk.page_number,
                        chunk_number=chunk.chunk_number,
                        content_hash=chunk.content_hash,
                        text=chunk.text,
                        score=score,
                    ),
                )
            )

    scores.sort(
        key=lambda item: (
            -item[0],
            item[1].document_id,
            item[1].version,
            item[1].chunk_number,
        )
    )
    return [chunk for _, chunk in scores[:top_k]]


def citation_records(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    return [
        {
            "document_id": chunk.document_id,
            "version": chunk.version,
            "filename": chunk.filename,
            "document_type": chunk.document_type,
            "responsible_unit": chunk.responsible_unit,
            "page_number": chunk.page_number,
            "chunk_number": chunk.chunk_number,
            "content_hash": chunk.content_hash,
            "text": chunk.text,
        }
        for chunk in chunks
    ]

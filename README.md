# Wissensassistent-Feuerwehrleitstelle

Lokaler Forschungs- und Entwicklungsprototyp für die Suche in Dienstanweisungen, Alarm- und Ausrückeordnungen (AAO), Standard Operating Procedures (SOPs) und Katastrophenschutzkonzepten. Das Projekt entsteht für die Feuerwehr der Stadt Krefeld.

## Prototyp-Funktionen

- Streamlit-Oberfläche mit Frage-/Antwortansicht und Dokumentenverwaltung
- Import von PDF-, TXT- und Markdown-Dateien
- BM25-Volltext-Retrieval über lokal gespeicherte Dokumentinhalte
- Optional: Antwortgenerierung mit einem lokalen Ollama-Modell
- Anzeige von Dokumentart, zuständiger Stelle, Version und Fundstelle
- SQLite-Versionierung: bestehende Versionen können nicht überschrieben werden
- Berücksichtigung des Status und des Gültigkeitszeitraums
- Prüfprotokoll mit Gültigkeitsstichtag, verwendeten Textstellen und Quellenhashes
- Mitgelieferte fiktive Beispieldokumente werden beim Start einmalig importiert

Die Dokumentarten in der Oberfläche sind eine erste Auswahl, noch keine mit der Feuerwehr abgestimmte Taxonomie. Auch Zuständigkeiten und Freigabeabläufe müssen im Auftaktgespräch geklärt werden. Die Suche verwendet vorerst BM25; Ollama ist nur für die optionale Antwortformulierung zuständig.

## Projektstruktur

```text
app.py                    Streamlit-Oberfläche
src/
  database.py              SQLite-Schema, Versionen und Prüfprotokoll
  document_loader.py       PDF-/Text-Extraktion und Metadatenimport
  document_search.py       BM25-Suche und Quellenangaben
  rag_pipeline.py          Promptaufbau und Ollama-Anbindung
  version_manager.py       Gültigkeits- und Versionsregeln
Dokumente/                 Fiktive Beispieldokumente und Metadaten
tests/                     Tests für Retrieval und Versionierung
data/                      Lokale Datenbank (wird nicht eingecheckt)
```

## Voraussetzungen

- Python 3.11 oder neuer
- Für KI-generierte Antworten optional: Ollama und ein lokales Chatmodell
- Keine Ollama-Installation für Retrieval-only erforderlich

## Installation unter Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Start

```powershell
streamlit run app.py
```

Beim ersten Start werden die Beispielversionen aus `Dokumente/` und `Dokumente/metadaten.json` in `data/wissensassistent.sqlite3` übernommen. Die alte Version der Schulungsunterlage bleibt als Historie erhalten, wird aber außerhalb ihres Gültigkeitszeitraums nicht für Antworten verwendet.

Im Seitenbereich kann zwischen **Fundstellen (ohne KI)** und **Ollama (lokal)** gewechselt werden. Für Ollama muss der Dienst laufen und das ausgewählte Modell vorhanden sein, beispielsweise:

```powershell
ollama pull qwen3:4b-instruct
```

Der lokale Ollama-Port und der Modellname sind in der Oberfläche änderbar. Aus Datenschutzgründen akzeptiert die Antwortgenerierung nur HTTP auf `localhost` oder einer Loopback-IP. Ist Ollama nicht erreichbar, zeigt die Anwendung einen Fehler an und wechselt nicht stillschweigend in einen anderen Antwortmodus.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Die Tests benötigen keine Ollama-Instanz. Sie prüfen unter anderem Gültigkeitszeiträume, Versionen, Fundstellen und das Prüfprotokoll.

## Dokumentpflege und Nachvollziehbarkeit

Beim Import werden Dokument-ID, Dokumentart, zuständige Stelle, Versionsnummer, Status (`freigegeben` oder `entwurf`) und Gültigkeitszeitraum erfasst. Dokumentart und zuständige Stelle dürfen vorerst offenbleiben. Freigegebene Versionen derselben Dokument-ID dürfen keine überlappenden Zeiträume haben. Bei einer Frage prüft die Suche die Gültigkeit für den angezeigten Stichtag. Datum, Antwort und die tatsächlich verwendeten Textstellen werden mit Versionsangabe und Datei-Hash protokolliert.

Der Prototyp kann Versionen aufnehmen, aber noch keinen abgestimmten Freigabe- oder Rücknahmeprozess abbilden. Wie eine zuständige Stelle eine Freigabe, Korrektur oder kurzfristige Rücknahme dokumentiert, muss mit der Feuerwehr besprochen werden.

Die gespeicherten Dateien und Ereignisse sind durch SHA-256-Hashes miteinander verknüpft. Änderungen an Text, Metadaten oder Protokoll lassen sich dadurch erkennen. Das ist keine revisionssichere Archivierung: Eine lokale SQLite-Datei kann außerhalb der Anwendung ersetzt werden.

Vor einem Test mit Krefelder Unterlagen sollte geklärt werden:

- Welche Unterlagen und Ablageorte gehören zum Projekt?
- Wer hält ein Dokument aktuell und wer gibt neue Versionen frei?
- Welche Status und Gültigkeitsregeln gelten heute?
- Welche Beispieldokumente dürfen für den Prototyp verwendet werden?
- Welche Fundstelle soll in einer Antwort sichtbar sein?
- Welche Anforderungen gelten für Zugriffsrechte, Datenschutz und Protokollierung?

## Sicherheit und Grenzen

- Ausschließlich fiktive oder ausdrücklich freigegebene Testdaten verwenden.
- Fragen und Antworten werden lokal in SQLite protokolliert. Die Datenbank liegt unter `data/` und wird durch `.gitignore` vom Git-Repository ausgeschlossen.
- Der Prototyp hat keine Benutzeranmeldung, Rollen, OCR, abgestimmten Freigabe- und Rücknahmeprozess oder garantierte semantische Suche.
- Die Hash-Kette ersetzt keine revisionssichere Langzeitarchivierung.
- KI-Antworten können unvollständig oder falsch sein. Quellen sind immer anhand des freigegebenen Originaldokuments zu prüfen.
- Das System ist nicht für operative Dispositionsentscheidungen freigegeben.
